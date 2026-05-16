# 主线量化交易系统 V3 实战版

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-orange.svg)

**主线量化交易系统V3** 是一个专注于A股主线概念板块的量化交易系统，采用六层架构设计，融合了传统量化策略与AI智能分析。

## 核心特性

- **六层架构**: 数据引擎 → AI分析 → 策略引擎 → 风险控制 → 交易执行 → 监控通知
- **多源数据**: 东方财富/新浪/腾讯多源数据融合，Parquet+DuckDB本地存储
- **12维度评分**: 趋势动量/连续强度/量能/资金流向/市场情绪等
- **四层风控**: 仓位管理 + 止损止盈 + 风险预算 + 压力测试
- **AI增强**: 4专业Agent并行分析，DeepSeek驱动决策
- **实盘就绪**: 模拟交易 + 订单管理 + 多通道通知

## 快速开始

### 安装

```bash
pip install -r requirements.txt
```

### 数据采集

```bash
python main.py collect --type daily --start 2024-01-01
```

### 主线扫描

```bash
python main.py scan --strategy mainline
```

### AI增强交易

```bash
python main.py trade --ai --capital 1000000
```

### 回测验证

```bash
python main.py backtest --strategy mainline --start 2024-01-01 --end 2024-12-31
```

## 项目结构

```
mainline_quant_v3/
├── config/                      # TOML配置文件
├── data_engine/                # 数据引擎
│   ├── collector.py           # 多源数据采集
│   ├── storage.py             # Parquet+DuckDB存储
│   ├── query.py              # 统一查询接口
│   └── factors.py            # 技术因子计算
├── ai_engine/                 # AI分析引擎
│   ├── agents/               # 4个专业Agent
│   ├── orchestrator.py       # Agent协调器
│   └── decision.py           # AI决策引擎
├── strategy_engine/           # 策略引擎
│   ├── signals/             # 信号检测
│   ├── events/              # 事件引擎
│   ├── strategies/          # 策略实现
│   └── combiner.py          # 信号融合
├── risk_engine/              # 风险控制
│   ├── position.py          # 仓位管理
│   ├── stop.py              # 止损止盈
│   ├── budget.py            # 风险预算
│   └── stress.py            # 压力测试
├── trade_engine/             # 交易执行
├── monitor_engine/           # 监控通知
├── backtest_engine/          # 回测引擎
├── utils/                   # 工具模块
└── main.py                  # CLI入口
```

## 核心策略

### 主线轮动策略 (权重45%)

12维度评分系统，识别市场主线：
- 趋势动量、连续上涨天数、成交额排名
- 资金流向、市场情绪、板块轮动
- 技术形态、估值支撑、宏观共振
- 机构持仓、新闻催化、风险调整

主线生命周期管理：萌芽 → 爆发 → 高潮 → 退潮

### 龙头战法 (权重30%)

6维度真龙头识别：
- 率先涨停、封单量级、带动效应
- 动量强度、资金流向、市值适配

### 缠论择时 (权重25%)

- 分型买卖点检测
- 中枢震荡交易
- 三类买卖点识别

## 风控体系

| 模块 | 功能 |
|------|------|
| 仓位管理 | 凯利公式、风险平价、单票/板块限额 |
| 止损止盈 | 固定/ATR/移动/时间/结构止损 |
| 风险预算 | 日/周/月亏损限额、连续亏损熔断 |
| 压力测试 | 历史极端行情、蒙特卡洛模拟 |

## 配置说明

### 环境变量 (.env)

```bash
# AI配置
DEEPSEEK_API_KEY=your_api_key_here

# 数据配置
DATA_PATH=./data
```

### 策略配置 (config/strategy.toml)

```toml
[mainline]
min_score = 70
confirm_days = 3
max_position = 0.8
```

### 风控配置 (config/risk.toml)

```toml
[stop_loss]
fixed = -0.08
atr_multiplier = 2.0
trailing = -0.05

[budget]
daily_loss_limit = -0.02
max_drawdown = -0.15
circuit_break_count = 3
```

## 数据API

```python
from data_engine import get_collector, get_storage, get_query

collector = get_collector()

# 股票K线
kline = collector.get_stock_kline('600000', start_date='2024-01-01')

# 概念板块K线
concept_kline = collector.get_concept_kline('BK0612')

# 概念成分股
constituents = collector.get_concept_constituent('BK0612')

# 资金流向
flow = collector.get_capital_flow('600000')

# 龙虎榜
billboard = collector.get_billboard()
```

## 策略使用

```python
from strategy_engine import MainlineRotateStrategy, LeaderStrategy, ChanStrategy, SignalCombiner

# 初始化策略
mainline = MainlineRotateStrategy()
leader = LeaderStrategy()
chan = ChanStrategy()
combiner = SignalCombiner(mainline, leader, chan)

# 融合信号
signal = combiner.combine(concept_code, concept_name, kline)
```

## 风控使用

```python
from risk_engine import PositionManager, StopLoss, RiskBudget

position_mgr = PositionManager()
stop_loss = StopLoss()
risk_budget = RiskBudget()

# 检查仓位
if position_mgr.can_buy(stock_code):
    amount = position_mgr.calculate_buy_amount(stock_code, capital, price)

# 检查止损
signal = stop_loss.check_signal(stock_code, current_price)
```

## AI分析

```python
from ai_engine import AgentOrchestrator, AIDecisionEngine

# 初始化AI引擎
orchestrator = AgentOrchestrator(api_key='your_key')
decision_engine = AIDecisionEngine(orchestrator)

# AI分析
analysis = orchestrator.analyze(stock_code, stock_name, market_data)

# AI决策
decision = decision_engine.make_decision(stock_code, stock_name, market_data, strategy_signals)
```

## 回测

```python
from backtest_engine import BacktestEngine, MetricsCalculator

engine = BacktestEngine(initial_capital=1000000)
result = engine.run(strategy, start_date='2024-01-01', end_date='2024-12-31')

metrics = MetricsCalculator.calculate_all(result['equity_curve'], result['trades'])
print(f"年化收益: {metrics['annual_return']:.2%}")
print(f"夏普比率: {metrics['sharpe_ratio']:.2f}")
print(f"最大回撤: {metrics['max_drawdown']:.2%}")
```

## 参考项目

本系统参考了以下优秀开源项目：

- [adata](https://github.com/1nchaos/adata) - A股多源数据获取库
- [czsc](https://github.com/wukan1986/czsc) - 缠论量化库
- [quant-trading](https://github.com/je-suis-tm/quant-trading) - 量化策略集合
- [zer0share](https://github.com/zer0share/zer0share) - 数据管道
- [aiagents-stock](https://github.com/aiagents-stock/aiagents-stock) - AI量化分析

## 免责声明

**本系统仅供学习研究使用，不构成任何投资建议！**

- 量化交易有风险，历史表现不代表未来收益
- 请充分测试验证后再考虑实盘应用
- 投资决策请谨慎，风险自负

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交Issue。
