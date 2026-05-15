# 主线量化交易系统 (Mainline Quant)

## 📊 项目简介

一个专注于A股主线概念板块识别的量化交易系统，通过LLM小组设计的评分系统识别市场主线，选择龙头股进行交易。

### 核心特点

- ✅ **多数据源**：新浪/腾讯双API，数据稳定
- ✅ **主线识别**：评分系统识别市场主线
- ✅ **回测框架**：轻量自开发回测，验证策略
- ✅ **风控完善**：止盈止损、仓位管理
- ✅ **本地缓存**：SQLite缓存，减少请求

---

## 📋 项目背景

由LLM子代理小组协作开发，经过20+轮讨论设计。

### LLM小组讨论决策

| 决策 | 说明 |
|------|------|
| 数据源 | 用requests直接调用新浪/腾讯API，含均线/前复权 |
| 评分系统 | 简化版3维度：涨跌幅排名50分+连涨30分+涨停20分 |
| 回测框架 | 轻量自开发，考虑手续费和滑点 |
| 龙头选择 | 成交额前3+涨跌幅前3 |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 数据获取示例

```python
from mainline_quant.data.fetcher_v2 import get_data_provider

# 初始化数据提供者
provider = get_data_provider()

# 获取股票K线（含均线数据！）
kline = provider.get_stock_kline('600000', count=100)
print(kline)

# 获取实时行情
quotes = provider.get_realtime_sina(['600000', '000001'])
print(quotes)

# 获取概念板块
concepts = provider.get_all_concepts()
print(concepts.head())
```

### 3. 主线策略示例

```python
from mainline_quant.data.fetcher_v2 import get_data_provider
from mainline_quant.strategy.mainline_v2 import SimplifiedMainlineStrategy

# 初始化
provider = get_data_provider()
strategy = SimplifiedMainlineStrategy(provider)

# 扫描主线
mainlines = strategy.scan_mainline_simplified()
print(mainlines.head(10))

# 筛选龙头
if not mainlines.empty:
    best = mainlines.iloc[0]
    leaders = strategy.select_leaders_simplified(best['concept_code'])
    print(f"主线: {best['concept_name']}, 龙头: {leaders}")
```

### 4. 回测示例

```python
from mainline_quant.backtest.simple_backtest import BacktestEngine

# 初始化回测引擎（初始资金10万）
engine = BacktestEngine(initial_capital=100000)

# 模拟交易
engine.buy('600000', 10.0, 1000, '2025-01-01')
engine.sell('600000', 12.0, 1000, '2025-01-10')

# 打印回测报告
engine.print_report()
```

---

## 📁 项目结构

```
mainline_quant/
├── mainline_quant/         # 核心代码包
│   ├── data/               # 数据模块
│   │   └── fetcher_v2.py   # 推荐：新版数据获取
│   ├── strategy/           # 策略模块
│   │   └── mainline_v2.py  # 推荐：简化版主线策略
│   ├── backtest/           # 回测模块
│   │   └── simple_backtest.py
│   └── utils/              # 工具模块
│       └── risk.py
├── examples/               # 示例代码
│   ├── example_data.py
│   ├── example_strategy.py
│   └── example_backtest.py
├── docs/                   # 文档
├── README.md
├── requirements.txt
└── LICENSE
```

---

## 📊 评分系统说明

### 简化版（当前使用）

| 维度 | 权重 | 说明 |
|------|------|------|
| 今日涨跌幅排名 | 50分 | 排名第1得50分 |
| 连续上涨天数 | 30分 | ≥5天得30分 |
| 涨停家数 | 20分 | ≥15家得20分 |

**入场条件**：综合评分≥70分
**空仓条件**：最高评分<60分

---

## ⚠️ 免责声明

本项目**仅供学习研究使用，不构成任何投资建议**。

- 量化交易有风险，历史表现不代表未来收益
- 请充分测试验证后再考虑实盘应用
- 投资决策请谨慎，风险自负

---

## 📄 开源协议

MIT License

---

## 👥 关于

由LLM子代理小组协作开发。
