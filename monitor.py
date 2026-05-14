#!/usr/bin/env python3
"""
模拟盘每日监控
- 从腾讯API获取实时价格
- 计算持仓盈亏
- 检查止损止盈信号
- 输出报告
"""
import sqlite3
import subprocess
import os
import datetime
from pathlib import Path

DB_PATH = os.path.expanduser('~/.hermes/simulator/simulator.db')

def get_conn():
    return sqlite3.connect(DB_PATH)

def get_price(code):
    """获取腾讯实时价格"""
    code = code.lower().replace('sh', '').replace('sz', '')
    prefix = 'sh' if code.startswith(('6', '9')) else 'sz'
    url = f"https://qt.gtimg.cn/q={prefix}{code}"
    try:
        result = subprocess.run(
            ['curl', '-s', '--max-time', '5', url],
            capture_output=True, timeout=10
        )
        raw = result.stdout.decode('gbk').strip()
        if '"' not in raw:
            return None
        parts = raw.split('"')[1].split('~')
        if len(parts) > 4:
            return {'current': float(parts[3]), 'prev_close': float(parts[4])}
    except:
        pass
    return None

def get_strategy_color(conn, strategy):
    row = conn.execute('SELECT color FROM strategies WHERE name=?', (strategy,)).fetchone()
    return row[0] if row else '⚪'

def check_czsc_signal(code):
    """检查CZSC卖点信号"""
    prefix = 'sh' if code.startswith(('6', '9')) else 'sz'
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayfqkline&param={prefix}{code},day,,,,,40,qfq&r=0.1"
    try:
        result = subprocess.run(['curl', '-s', '--max-time', '10', url],
                              capture_output=True, timeout=15)
        raw = result.stdout.decode('utf-8').strip()
        if '=' in raw:
            raw = raw.split('=', 1)[1]
        data = __import__('json').loads(raw)
        day_data = data.get('data', {}).get(prefix + code, {}).get('qfqday', [])
        if not day_data:
            day_data = data.get('data', {}).get(prefix + code, {}).get('day', [])
        
        closes = [float(d[2]) for d in day_data[-20:] if len(d) >= 4]
        volumes = [float(d[5]) if len(d) > 5 else 0 for d in day_data[-20:]]
        highs = [float(d[3]) for d in day_data[-20:] if len(d) >= 4]
        
        if len(closes) < 20:
            return None, 0, ""
        
        ma5 = sum(closes[-5:]) / 5
        ma5_prev = sum(closes[-10:-5]) / 5
        ma20 = sum(closes[-20:]) / 20
        vol_ma5 = sum(volumes[-5:]) / 5
        vol_ratio = volumes[-1] / vol_ma5 if vol_ma5 > 0 else 0
        
        high20 = max(highs[-20:])
        is_new_high = closes[-1] >= high20
        ma5_turning_down = ma5 < ma5_prev
        down_days = sum(1 for i in range(1, 4) if closes[-i] < closes[-i-1])
        
        signals = []
        if is_new_high and ma5_turning_down:
            signals.append(('一卖', 3))
        if is_new_high and (closes[-1] - closes[-2]) / closes[-2] < 0.01:
            signals.append(('一卖', 3))
        if closes[-1] < ma5 and closes[-1] < closes[-3]:
            signals.append(('二卖', 2))
        if closes[-1] < ma20 and vol_ratio > 1.5:
            signals.append(('三卖', 2))
        if down_days >= 3 and vol_ratio > 1.5:
            signals.append(('警示', 1))
        
        hit = any(s[1] == 3 for s in signals) or any(s[1] == 2 for s in signals)
        level = 3 if any(s[1] == 3 for s in signals) else 2 if any(s[1] == 2 for s in signals) else 1 if signals else 0
        return hit, level, ';'.join([s[0] for s in signals])
    except:
        return None, 0, ""

def main():
    conn = get_conn()
    
    positions = conn.execute('''
        SELECT code, name, cost, shares, buy_date, strategy, stop_loss, target1, target2, target3
        FROM positions WHERE status="持仓"
    ''').fetchall()
    
    conn.close()
    
    if not positions:
        print("📭 当前无持仓")
        return
    
    print("=" * 70)
    print(f"A股模拟盘监控 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    alerts = []
    warnings = []
    
    # 按策略分组，先获取所有color
    strategy_colors = {}
    tmp_conn = get_conn()
    for row in tmp_conn.execute('SELECT name, color FROM strategies').fetchall():
        strategy_colors[row[0]] = row[0]
    tmp_conn.close()
    
    by_strategy = {}
    for pos in positions:
        by_strategy.setdefault(pos[5], []).append(pos)
    
    for strategy, pos_list in by_strategy.items():
        color = strategy_colors.get(strategy, '⚪')
        
        print(f"\n{color} 【{strategy}】")
        print("-" * 60)
        
        for code, name, cost, shares, buy_date, strategy, stop_loss, target1, target2, target3 in pos_list:
            price_info = get_price(code)
            if not price_info:
                print(f"  {name}({code}): 获取价格失败")
                continue
            
            current = price_info['current']
            prev_close = price_info['prev_close']
            pnl_pct = (current - cost) / cost * 100
            daily_chg = (current - prev_close) / prev_close * 100
            
            hold_days = (datetime.datetime.now().date() - datetime.datetime.strptime(buy_date, '%Y-%m-%d').date()).days
            
            # 检查止损
            status = "✅安全"
            if current <= stop_loss:
                status = "⚠️止损"
                alerts.append(f"{strategy}/{name}: 触发止损 {pnl_pct:+.1f}%")
            # 检查止盈
            elif target3 and current >= target3:
                status = "🎯止盈3"
                alerts.append(f"{strategy}/{name}: 触及目标3 {pnl_pct:+.1f}%")
            elif target2 and current >= target2:
                status = "🎯止盈2"
                alerts.append(f"{strategy}/{name}: 触及目标2 {pnl_pct:+.1f}%")
            elif target1 and current >= target1:
                status = "🎯止盈1"
                alerts.append(f"{strategy}/{name}: 触及目标1 {pnl_pct:+.1f}%")
            # CZSC缠论卖点
            elif strategy == 'CZSC缠论':
                sell_hit, sell_level, signal = check_czsc_signal(code)
                if sell_hit:
                    status = f"🔴缠论卖点L{sell_level}"
                    alerts.append(f"{strategy}/{name}: 缠论卖点 {signal}")
            
            print(f"  {name}: {cost:.2f} → {current:.2f} | {pnl_pct:+.1f}% | 今{daily_chg:+.1f}% | {status} ({hold_days}天)")
    
    print("\n" + "=" * 70)
    if alerts:
        print("🚨 需要操作:")
        for a in alerts:
            print(f"  • {a}")
    else:
        print("✅ 所有持仓安全，无需操作")
    print()

if __name__ == '__main__':
    main()
