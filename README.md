# A股模拟盘 | SQLite + 腾讯API | 四策略独立追踪 | 开源量化工具

> 用 SQLite 替代 Excel 记模拟交易，支持 Branch V / CZSC缠论 / 主力突破 / 小市值国九条 四套策略，腾讯免费API实时行情，Cron飞书定时推送

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/loganshi-ops/a-stock-simulator)](https://github.com/loganshi-ops/a-stock-simulator)

## 解决什么问题

| 痛点 | 解决方案 |
|------|---------|
| Excel 列类型混乱（文本变数字、日期乱码） | SQLite 数据库，单一数据源，类型安全 |
| 止损止盈靠手算，容易忘 | 买入时自动计算，写入数据库 |
| 多策略持仓混在一起 | 四套策略独立参数，独立记录 |
| 手动查行情，容易忘记 | 腾讯免费 API，自动获取实时价格 |
| 忘记持仓情况，止损过了才反应过来 | Cron 定时推送，飞书告警 |

## 功能特点

- **零成本** — 腾讯免费 API，无需付费数据源
- **SQLite 存储** — 告别 Excel 乱码，类型安全，可查询
- **四策略独立** — Branch V / CZSC缠论 / 主力突破 / 小市值国九条
- **自动止损止盈** — 买入时自动计算，写入数据库
- **实时行情** — 腾讯 API，自动获取持仓现价
- **Cron 推送** — 9:00 / 11:00 / 14:00 自动飞书推送

## 快速开始

### 安装

```bash
git clone https://github.com/loganshi-ops/a-stock-simulator.git
cd a-stock-simulator
```

### 买入建仓

```bash
python3 trade.py buy CZSC缠论 SZ002241 歌尔股份 25.85 1200
```

```
✅ 买入成功: CZSC缠论 歌尔股份(SZ002241) 1200股@25.85
   止损: 23.78 | 目标1: 29.73 | 目标2: 31.02 | 目标3: 33.61
```

### 查看持仓

```bash
python3 trade.py list                    # 全部策略
python3 trade.py list CZSC缠论           # 单策略
```

### 卖出平仓

```bash
python3 trade.py sell CZSC缠论 SZ002241 30.0 600 "止盈一半"  # 部分卖出
python3 trade.py sell Branch_V SZ600456 28.0 1000 "止损"     # 止损
```

### 每日监控

```bash
python3 monitor.py
```

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

## 策略参数

| 策略 | 止损 | 止盈1 | 止盈2 | 止盈3 | 持仓上限 |
|------|------|-------|-------|-------|---------|
| Branch_V | -12% | +30% | +50% | +80% | 1825天 |
| CZSC缠论 | -8% | +15% | +20% | +30% | 28天 |
| 主力突破 | -8% | +10% | +20% | +30% | 90天 |
| 小市值国九 | -8% | — | — | — | 90天 |

**Branch V 止盈规则：** 目标1(+30%) 卖出1/3 → 目标2(+50%) 再卖1/3 → 目标3(+80%) 清仓

## 数据库结构

```sql
-- 持仓表
positions (code, name, cost, shares, buy_date, strategy, stop_loss, target1, target2, target3, status)

-- 交易记录表
trades (trade_date, code, name, action, price, shares, amount, pnl, reason, strategy)

-- 策略参数表
strategies (name, stop_loss_pct, take_profit1, take_profit2, take_profit3, color)
```

数据库路径：`~/.hermes/simulator/simulator.db`

## 飞书 Cron 推送

在 Hermes Agent 中创建 Cron 任务：

```
时间: 0 9,11,14 * * 1-5
脚本: simulator/monitor.py
推送: 飞书
```

每工作日 9:00 / 11:00 / 14:00 自动推送持仓报告。

## 适用场景

- 个人投资者记录 A股模拟交易
- 量化策略信号验证（先模拟再实盘）
- 多策略组合跟踪
- 无需付费数据源

## 不适用场景

| 需求 | 推荐工具 |
|------|---------|
| 回测功能 | 聚宽 / BigQuant |
| 实盘自动交易 | QMT / PTrade |
| 完整交易 API | vnpy |

## 相关项目

- [聚宽 (JoinQuant)](https://www.joinquant.com/) — A股回测
- [BigQuant](https://bigquant.com/) — AI量化平台
- [QMT](https://www.thinktrading.net/) — 迅投QMT实盘

## License

MIT
