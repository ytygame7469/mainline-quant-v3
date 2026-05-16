# 主线量化交易系统 (Mainline Quant)

## 📊 项目简介

一个专注于A股主线概念板块识别的量化交易系统，通过LLM小组设计的评分系统识别市场主线，选择龙头股进行交易。

### 核心特点

- ✅ **多数据源**：新浪/腾讯/东方财富API，数据稳定
- ✅ **主线识别**：8维度评分系统识别市场主线
- ✅ **龙头选择**：4维度智能选股
- ✅ **风险控制**：仓位管理、止损止盈
- ✅ **回测框架**：轻量自开发回测，验证策略
- ✅ **本地缓存**：SQLite缓存，减少请求

---

## 📋 项目背景

由LLM子代理小组协作开发，经过20+轮讨论设计和增强。

### LLM小组20轮讨论增强

详细讨论记录请查看：[LLM_TEAM_DISCUSSION_20_ROUNDS.md](LLM_TEAM_DISCUSSION_20_ROUNDS.md)

### 增强功能演进

| 模块 | 说明 |
|------|------|
| 数据模块 (P0) | ✅ 概念板块数据获取、K线、成分股 |
| 策略评分 (P0) | ✅ 8维度评分系统，满分100分 |
| 龙头选择 (P0) | ✅ 4维度龙头股评分和选择 |
| 风险控制 (P1) | ✅ 仓位管理、止损止盈 |
| 回测指标 (P1) | 🔄 已有基础，待增强 |
| 实时监控 (P2) | ⏳ 待开发 |
| 参数优化 (P2) | ⏳ 待开发 |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 完整示例（推荐）

```python
from mainline_quant.data import get_data_provider, get_concept_data
from mainline_quant.strategy import get_scoring, get_leader_selector
from mainline_quant.risk import get_position_manager, get_stop_loss

# 1. 初始化数据模块
stock_data = get_data_provider()
concept_data = get_concept_data()

# 2. 获取概念板块列表
concepts = concept_data.get_all_concepts()
print(f"共 {len(concepts)} 个概念板块")

# 3. 扫描并评分概念板块
scoring = get_scoring(concept_data, stock_data)
mainline_candidates = scoring.scan_all_concepts(top_n=20)

# 4. 选择龙头股
if not mainline_candidates.empty:
    top_concept = mainline_candidates.iloc[0]
    print(f"\n选中概念: {top_concept['concept_name']}")
    print(f"综合评分: {top_concept['total_score']}")
    
    leader_selector = get_leader_selector(concept_data, stock_data)
    leaders = leader_selector.select_leaders(top_concept['concept_code'], num_leaders=5)
    print("\n龙头股:")
    print(leaders)

# 5. 初始化风控模块
position_manager = get_position_manager()
stop_loss = get_stop_loss()
```

### 3. 数据获取示例

```python
from mainline_quant.data import get_data_provider, get_concept_data

# 初始化数据提供者
provider = get_data_provider()
concept_data = get_concept_data()

# 获取股票K线（含均线数据！）
kline = provider.get_stock_kline('600000', count=100)
print(kline)

# 获取实时行情
quotes = provider.get_realtime_sina(['600000', '000001'])
print(quotes)

# 获取概念板块K线（东方财富API）
concept_kline = concept_data.get_concept_kline('BK0612', count=100)
print(concept_kline)

# 获取概念板块成分股
constituents = concept_data.get_concept_constituent('BK0612')
print(constituents)
```

### 4. 主线策略示例（旧版兼容）

```python
from mainline_quant.data import get_data_provider
from mainline_quant.strategy import SimplifiedMainlineStrategy

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

### 5. 回测示例

```python
from mainline_quant.backtest import BacktestEngine

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
│   │   ├── fetcher_v2.py   # 股票数据获取
│   │   └── concept_data.py # 概念板块数据（新）
│   ├── strategy/           # 策略模块
│   │   ├── mainline_v2.py  # 简化版主线策略
│   │   ├── scoring.py      # 8维度评分系统（新）
│   │   └── leader_selector.py # 龙头股选择（新）
│   ├── risk/               # 风控模块（新）
│   │   └── position_manager.py # 仓位管理、止损止盈
│   └── backtest/           # 回测模块
│       └── simple_backtest.py
├── examples/               # 示例代码
│   ├── example_data.py
│   ├── example_strategy.py
│   ├── example_backtest.py
│   └── complete_example.py # 完整示例（新）
├── references/             # 参考项目
│   ├── adata/
│   ├── Ashare/
│   └── zer0share/
├── LLM_TEAM_DISCUSSION_20_ROUNDS.md # 20轮讨论报告
├── README.md
├── requirements.txt
└── LICENSE
```

---

## 📊 评分系统说明

### 增强版（推荐，新）

| 维度 | 权重 | 说明 |
|------|------|------|
| 今日涨跌幅排名 | 25分 | >5%得25分 |
| 连续上涨天数 | 15分 | ≥5天得15分 |
| 涨停家数 | 20分 | ≥15家得20分 |
| 成交额排名 | 15分 | >100亿得15分 |
| 涨跌比 | 10分 | ≥3:1得10分 |
| 主力资金流入 | 10分 | 简化版用涨跌幅替代 |
| 均线形态 | 5分 | 5日>10日>20日得5分 |

**入场条件**：综合评分≥70分
**空仓条件**：最高评分<60分

### 简化版（旧版兼容）

| 维度 | 权重 | 说明 |
|------|------|------|
| 今日涨跌幅排名 | 50分 | 排名第1得50分 |
| 连续上涨天数 | 30分 | ≥5天得30分 |
| 涨停家数 | 20分 | ≥15家得20分 |

---

## 🏆 龙头股选择（新）

| 维度 | 权重 | 说明 |
|------|------|------|
| 成交额排名 | 40分 | >50亿得40分 |
| 涨跌幅 | 30分 | 涨停得30分 |
| 技术形态 | 20分 | 均线多头得20分 |
| 历史地位 | 10分 | 600/000开头得10分 |

---

## 🛡️ 风险控制（新）

### 仓位管理

| 配置 | 默认值 |
|------|--------|
| 总仓位上限 | 80% |
| 单个概念板块上限 | 30% |
| 单只股票上限 | 10% |
| 单笔交易比例 | 5% |

### 止损止盈

| 配置 | 默认值 |
|------|--------|
| 止损比例 | -8% |
| 止盈比例 | +15% |
| 移动止盈回撤 | -5% |

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

由LLM子代理小组协作开发，经过20+轮讨论设计和增强。

