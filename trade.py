#!/usr/bin/env python3
"""
模拟盘交易操作工具
用法:
  python3 trade.py buy <策略> <代码> <名称> <价格> <数量>
  python3 trade.py sell <策略> <代码> <价格> <数量> [原因]
  python3 trade.py list [策略]
  python3 trade.py pending
"""
import sqlite3
import sys
import os
from datetime import datetime

DB_PATH = os.path.expanduser('~/.hermes/simulator/simulator.db')

def get_conn():
    return sqlite3.connect(DB_PATH)

def get_strategy_params(conn, strategy):
    row = conn.execute(
        'SELECT stop_loss_pct, take_profit1, take_profit2, take_profit3 FROM strategies WHERE name=?',
        (strategy,)
    ).fetchone()
    if not row:
        print(f"❌ 未知策略: {strategy}")
        sys.exit(1)
    return {'stop_loss_pct': row[0], 'tp1': row[1], 'tp2': row[2], 'tp3': row[3]}

def cmd_buy(strategy, code, name, price, shares):
    """买入建仓"""
    conn = get_conn()
    
    # 检查是否已有持仓
    existing = conn.execute(
        'SELECT id, shares FROM positions WHERE code=? AND strategy=? AND status="持仓"',
        (code, strategy)
    ).fetchone()
    if existing:
        print(f"⚠️ {name}({code}) 已在 {strategy} 持仓中，增持中...")
        # 合并计算新成本
        old_shares = existing[1]
        old_cost = conn.execute(
            'SELECT cost FROM positions WHERE id=?', (existing[0],)
        ).fetchone()[0]
        total_cost = old_cost * old_shares + price * shares
        new_shares = old_shares + shares
        new_cost = total_cost / new_shares
        conn.execute(
            'UPDATE positions SET cost=?, shares=? WHERE id=?',
            (round(new_cost, 3), new_shares, existing[0])
        )
        print(f"  合并: 成本 {old_cost}×{old_shares} + {price}×{shares} = {new_cost:.3f}, 数量 {new_shares}")
    else:
        params = get_strategy_params(conn, strategy)
        
        # 计算止损价和目标价
        stop_loss = round(price * (1 - params['stop_loss_pct']), 2)
        tp1 = round(price * (1 + params['tp1']), 2) if params['tp1'] else None
        tp2 = round(price * (1 + params['tp2']), 2) if params['tp2'] else None
        tp3 = round(price * (1 + params['tp3']), 2) if params['tp3'] else None
        
        conn.execute('''
            INSERT INTO positions (code, name, cost, shares, buy_date, strategy, stop_loss, target1, target2, target3)
            VALUES (?, ?, ?, ?, date('now'), ?, ?, ?, ?, ?)
        ''', (code, name, price, shares, strategy, stop_loss, tp1, tp2, tp3))
        
        print(f"✅ 买入成功: {strategy} {name}({code}) {shares}股@{price}")
        print(f"   止损: {stop_loss} | 目标1: {tp1} | 目标2: {tp2} | 目标3: {tp3}")
    
    # 记录交易
    amount = round(price * shares, 2)
    conn.execute('''
        INSERT INTO trades (trade_date, code, name, action, price, shares, amount, strategy)
        VALUES (date('now'), ?, ?, '买入', ?, ?, ?, ?)
    ''', (code, name, price, shares, amount, strategy))
    
    conn.commit()
    conn.close()

def cmd_sell(strategy, code, price, shares, reason=''):
    """卖出平仓"""
    conn = get_conn()
    
    pos = conn.execute(
        'SELECT id, name, cost, shares FROM positions WHERE code=? AND strategy=? AND status="持仓"',
        (code, strategy)
    ).fetchone()
    if not pos:
        print(f"❌ {code} 在 {strategy} 中无持仓")
        conn.close()
        sys.exit(1)
    
    pos_id, name, cost, held_shares = pos
    if shares > held_shares:
        print(f"❌ 持有 {held_shares} 股，无法卖出 {shares} 股")
        conn.close()
        sys.exit(1)
    
    pnl = round((price - cost) * shares, 2)
    amount = round(price * shares, 2)
    
    if shares == held_shares:
        # 全部卖出，更新持仓状态
        conn.execute(
            'UPDATE positions SET status="卖出" WHERE id=?',
            (pos_id,)
        )
        print(f"✅ 全部卖出: {name}({code}) {shares}股@{price}, 盈亏: {pnl:+.2f}")
    else:
        # 部分卖出，减少数量
        conn.execute(
            'UPDATE positions SET shares=? WHERE id=?',
            (held_shares - shares, pos_id)
        )
        print(f"✅ 部分卖出: {name}({code}) {shares}股@{price}, 盈亏: {pnl:+.2f}")
    
    conn.execute('''
        INSERT INTO trades (trade_date, code, name, action, price, shares, amount, pnl, reason, strategy)
        VALUES (date('now'), ?, ?, '卖出', ?, ?, ?, ?, ?, ?)
    ''', (code, name, price, shares, amount, pnl, reason, strategy))
    
    conn.commit()
    conn.close()

def cmd_list(strategy=None):
    """列出持仓"""
    conn = get_conn()
    
    if strategy:
        rows = conn.execute('''
            SELECT code, name, cost, shares, buy_date, strategy, stop_loss, target1, target2
            FROM positions WHERE strategy=? AND status="持仓"
        ''', (strategy,)).fetchall()
        print(f"\n📊 {strategy} 持仓:")
    else:
        rows = conn.execute('''
            SELECT code, name, cost, shares, buy_date, strategy, stop_loss, target1, target2
            FROM positions WHERE status="持仓" ORDER BY strategy
        ''').fetchall()
        print(f"\n📊 全部持仓:")
    
    if not rows:
        print("  空仓")
    else:
        for r in rows:
            days = (datetime.now().date() - datetime.strptime(r[4], '%Y-%m-%d').date()).days
            print(f"  {r[1]}({r[0]}) 成本:{r[2]} 数量:{r[3]}天:{days}天 止损:{r[6]} 目标:{r[7]}/{r[8]}")
    
    conn.close()

def cmd_pending():
    """待操作提醒"""
    import subprocess
    
    conn = get_conn()
    positions = conn.execute(
        'SELECT code, name, cost, shares, strategy, stop_loss, target1 FROM positions WHERE status="持仓"'
    ).fetchall()
    conn.close()
    
    if not positions:
        print("📭 无持仓")
        return
    
    print("\n🔔 持仓概览:")
    for code, name, cost, shares, strategy, stop_loss, target1 in positions:
        print(f"  {name}({code}) 成本:{cost} 止损:{stop_loss} 目标1:{target1}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == 'buy' and len(sys.argv) >= 7:
        _, _, strategy, code, name, price, shares = sys.argv[:7]
        cmd_buy(strategy, code, name, float(price), int(shares))
    elif cmd == 'sell' and len(sys.argv) >= 6:
        _, _, strategy, code, price, shares = sys.argv[:6]
        reason = sys.argv[6] if len(sys.argv) > 6 else ''
        cmd_sell(strategy, code, float(price), int(shares), reason)
    elif cmd == 'list':
        strategy = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_list(strategy)
    elif cmd == 'pending':
        cmd_pending()
    else:
        print(__doc__)
