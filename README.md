# A股模拟盘 SQLite 系统

> 用 SQLite + 腾讯免费 API 搭建的本地 A 股模拟交易工具，支持四套策略、止损止盈、Cron 飞书推送

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 解决的问题

| 痛点 | 解决方案 |
|------|---------|
| Excel 列错位、类型混乱 | SQLite 数据库，单一数据源 |
| 手动计算止损止盈 | 买入时自动计算，写入数据库 |
| 付费行情数据 | 腾讯免费 API，实时价格 |
| 忘记持仓情况 | Cron 定时推送，飞书告警 |
| 多策略混在一起 | 四套策略独立参数，独立追踪 |

## 快速开始

### 1. 安装

```bash
git clone https://github.com/YOUR_USERNAME/a-stock-simulator.git
cd a-stock-simulator
```

### 2. 买入建仓

```bash
python3 trade.py buy CZSC缠论 SZ002241 歌尔股份 25.85 1200
```

输出：
```
✅ 买入成功: CZSC缠论 歌尔股份(SZ002241) 1200股@25.85
   止损: 23.78 | 目标1: 29.73 | 目标2: 31.02 | 目标3: 33.61
```

### 3. 查看持仓

```bash
python3 trade.py list
python3 trade.py list CZSC缠论  # 单策略
```

### 4. 卖出平仓

```bash
# 全部卖出
python3 trade.py sell CZSC缠论 SZ002241 30.0 1200 "止盈"

# 部分卖出（先减半仓）
python3 trade.py sell CZSC缠论 SZ002241 30.0 600 "止盈一半"
```

### 5. 每日监控

```bash
python3 monitor.py
```

输出示例：
```
======================================================================
A股模拟盘监控 2025-05-14 10:30
======================================================================

🔴 【CZSC缠论】
------------------------------------------------------------
  歌尔股份: 25.85 → 31.20 | +17.8% | 今+2.1% | 🎯止盈1 (12天)

【Branch_V】
------------------------------------------------------------
  中航西飞: 28.50 → 25.30 | -11.2% | 今-0.8% | ⚠️止损 (25天)

======================================================================
🚨 需要操作:
  • Branch_V/中航西飞: 触发止损 -11.2%
```

## 命令一览

| 命令 | 说明 |
|------|------|
| `buy <策略> <代码> <名称> <价格> <数量>` | 买入建仓 |
| `sell <策略> <代码> <价格> <数量> [原因]` | 卖出平仓 |
| `list [策略]` | 查看持仓 |
| `pending` | 待操作提醒 |

## 策略参数

| 策略 | 止损 | 止盈1 | 止盈2 | 止盈3 |
|------|------|-------|-------|-------|
| Branch_V | -12% | +30% | +50% | +80% |
| CZSC缠论 | -8% | +15% | +20% | +30% |
| 主力突破 | -8% | +10% | +20% | +30% |
| 小市值国九 | -8% | — | — | — |

**Branch_V 止盈规则：** 目标1(+30%) 卖出1/3 → 目标2(+50%) 再卖1/3 → 目标3(+80%) 清仓

## 数据库

SQLite 自动创建，首次买入时初始化。

```sql
-- 持仓表
positions (code, name, cost, shares, buy_date, strategy, stop_loss, target1, target2, target3, status)

-- 交易记录表
trades (trade_date, code, name, action, price, shares, amount, pnl, reason, strategy)

-- 策略参数表
strategies (name, stop_loss_pct, take_profit1, take_profit2, take_profit3, color)
```

数据库路径：`~/.hermes/simulator/simulator.db`

## 飞书 Cron 推送（可选）

在 Hermes Agent 中创建 Cron 任务：

```
时间: 0 9,11,14 * * 1-5
脚本: /Users/openclaw/.hermes/simulator/monitor.py
推送: 飞书
```

每工作日 9:00 / 11:00 / 14:00 自动推送持仓报告到飞书群。

## 适用场景

- 个人投资者记录模拟交易
- 策略信号验证（先模拟再实盘）
- 多策略组合跟踪
- **零成本**：无需任何付费数据源

## 不适用场景

| 需求 | 推荐工具 |
|------|---------|
| 回测功能 | 聚宽 / BigQuant |
| 实盘自动交易 | QMT / PTrade |
| 完整交易 API | vnpy |

## License

MIT
