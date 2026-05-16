# 主线量化交易系统 V3 - 完整技术文档

## 📖 目录

1. [系统简介](#1-系统简介)
2. [数据获取模块（超级详细）](#2-数据获取模块超级详细)
3. **[连板队列识别模块](#3-连板队列识别模块)** ⭐⭐⭐ 新功能
4. **[龙虎榜分析模块](#4-龙虎榜分析模块)** ⭐⭐⭐ 新功能
5. **[涨停原因与主线扩散分析](#5-涨停原因与主线扩散分析)** ⭐⭐⭐ 新功能
6. [回测引擎](#6-回测引擎)
7. [策略引擎](#7-策略引擎)
8. [风控系统](#8-风控系统)
9. [AI分析模块](#9-ai分析模块)
10. [交易执行](#10-交易执行)
11. [快速开始](#11-快速开始)
12. [常见问题与故障排查](#12-常见问题与故障排查)

---

## 1. 系统简介

### 1.1 这是什么系统？

这是一个**A股主线量化交易系统**，专门用于捕捉A股市场的主线热点板块机会。

**核心特点：**
- 🎯 只做主线热点板块（不碰冷门股）
- 📊 量化分析 + AI辅助决策
- 🛡️ 多重风控保护
- ⚡ 支持回测和实盘交易

### 1.2 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        六大核心模块                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│  │  数据引擎     │ ──▶ │  AI分析模块  │ ──▶ │  策略引擎    │   │
│  │  Data Engine │     │  AI Engine   │     │  Strategy    │   │
│  └──────────────┘     └──────────────┘     └──────────────┘   │
│        │                                        │              │
│        ▼                                        ▼              │
│  ┌──────────────┐                       ┌──────────────┐     │
│  │   风控系统   │                       │  交易执行    │     │
│  │ Risk Engine  │                       │Trade Engine  │     │
│  └──────────────┘                       └──────────────┘     │
│        │                                        │              │
│        └────────────────┬─────────────────────────┘              │
│                         ▼                                      │
│                  ┌──────────────┐                              │
│                  │  监控通知    │                              │
│                  │  Monitor     │                              │
│                  └──────────────┘                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 目录结构

```
mainline_quant_v3/
├── data_engine/              # 数据获取模块 ⭐⭐⭐ 最重要
│   ├── collector.py          # 数据采集器（实时API）
│   ├── storage.py            # 数据存储（DuckDB）
│   ├── query.py             # 数据查询
│   ├── factors.py           # 技术指标计算
│   └── config.py            # 配置
│
├── strategy_engine/          # 策略引擎
│   ├── strategies/          # 策略实现
│   │   ├── mainline_strategy.py    # 主线策略
│   │   ├── leader_selector.py      # 龙头选股
│   │   └── chan_strategy.py        # 缠论策略
│   ├── signals/             # 信号系统
│   │   ├── momentum_signals.py     # 动量信号
│   │   ├── volume_signals.py       # 量能信号
│   │   └── fund_flow_signals.py    # 资金流向信号
│   └── events/              # 事件系统
│
├── backtest_engine/         # 回测引擎
│   ├── engine.py            # 核心回测引擎
│   └── metrics.py           # 绩效指标计算
│
├── risk_engine/             # 风控系统
│   ├── position.py         # 仓位管理
│   ├── stop.py             # 止损止盈
│   ├── budget.py           # 资金管理
│   └── stress.py           # 压力测试
│
├── ai_engine/              # AI分析模块
│   ├── orchestrator.py     # AI协调器
│   ├── decision.py         # AI决策
│   └── agents/             # AI智能体
│       ├── tech_analyst.py         # 技术分析AI
│       ├── fund_analyst.py          # 资金分析AI
│       ├── flow_analyst.py          # 主力流向AI
│       └── sentiment_analyst.py     # 情绪分析AI
│
├── trade_engine/           # 交易执行
│   ├── broker/            # 券商接口
│   │   └── simulator.py   # 模拟交易
│   └── order.py          # 订单管理
│
├── monitor_engine/        # 监控通知
│   ├── market.py         # 市场监控
│   ├── position.py       # 持仓监控
│   └── notifier.py      # 通知系统
│
├── config/               # 配置文件
│   ├── config.toml       # 主配置
│   ├── strategy.toml     # 策略配置
│   └── risk.toml         # 风控配置
│
├── run_backtest.py       # 回测运行脚本
├── main.py              # 主程序入口
└── requirements.txt     # 依赖包
```

---

## 2. 数据获取模块（超级详细）⭐⭐⭐

这是系统最重要的部分，也是最复杂的部分。我会讲得非常详细，确保任何人都能看懂！

### 2.1 数据从哪里来？

我们的系统从**三个主要数据源**获取A股数据：

```
┌─────────────────────────────────────────────────────────────────┐
│                      数据源优先级                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  第1优先级：新浪财经 (Sina)     🌟 最常用                        │
│  ────────────────────────────────────────────────               │
│  优点：速度快、数据全、支持均线                                  │
│  缺点：需要代理访问                                             │
│  API：https://quotes.sina.cn                                     │
│                                                                 │
│  第2优先级：腾讯财经 (Tencent)                                   │
│  ────────────────────────────────────────────────               │
│  优点：数据准确、支持前复权                                      │
│  缺点：有时候数据延迟                                           │
│  API：https://web.ifzq.gtimg.cn                                 │
│                                                                 │
│  第3优先级：东方财富 (Eastmoney)                                │
│  ────────────────────────────────────────────────               │
│  优点：概念板块数据最全                                          │
│  缺点：速度较慢                                                 │
│  API：https://push2.eastmoney.com                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 为什么需要代理？

**重要说明：** 某些网络环境下（如云服务器），直接访问国内股票网站会被限制。

```
┌─────────────────────────────────────────────────────────────────┐
│                      网络访问说明                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  情况1：能直接访问（本地电脑）                                  │
│  ────────────────────────────────────────────────               │
│  直接运行即可，代码会自动访问数据源                              │
│                                                                 │
│  情况2：无法直接访问（云服务器）                                │
│  ────────────────────────────────────────────────               │
│  需要配置代理，代码会自动使用代理访问                            │
│  代理地址：http://127.0.0.1:18080                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 collector.py 详解（最核心）

这是数据获取的核心文件，我一行一行解释：

#### 2.3.1 文件开头

```python
# -*- coding: utf-8 -*-
"""
数据获取模块 - 使用实时API
支持：新浪财经、腾讯财经、东方财富
通过本地代理获取数据
"""
import json
import math
import time
import os
import random
from datetime import datetime

import pandas as pd
import requests
```

**解释：**
- `# -*- coding: utf-8 -*-`：告诉Python这个文件使用UTF-8编码，支持中文
- `import`：导入需要用到的库
- `pandas`：处理表格数据
- `requests`：发送HTTP请求获取网页数据

#### 2.3.2 代理设置函数

```python
# ============================================================
# 代理设置（重要！）
# ============================================================

def _clear_proxy():
    """清除所有代理设置"""
    for key in list(os.environ.keys()):
        if key.lower().endswith('proxy'):
            del os.environ[key]

def _setup_proxy():
    """设置代理访问国内网站"""
    os.environ['HTTP_PROXY'] = 'http://127.0.0.1:18080'
    os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:18080'
```

**解释：**
- `_clear_proxy()`：清除所有代理，防止代理冲突
- `_setup_proxy()`：设置代理，让requests通过代理访问国内网站
- 有些云服务器无法直接访问新浪、腾讯等网站，需要通过代理

#### 2.3.3 请求头设置（防止被网站封禁）

```python
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

_SINA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://finance.sina.com.cn",  # 重要！告诉网站我们从哪来的
    "Accept": "*/*",
}
```

**解释：**
- `User-Agent`：伪装成浏览器，防止被网站识别为爬虫
- `Referer`：告诉网站我们是从新浪财经过来的
- 不同网站需要不同的请求头

#### 2.3.4 获取股票K线数据（最重要的函数）

```python
def _stock_market_sina(stock_code, count=250):
    """
    新浪财经 API 获取日K线
    
    参数：
        stock_code: 股票代码，如 '600519'（茅台）
        count: 获取多少天的数据，默认250天（约一年）
    
    返回：
        DataFrame，包含：trade_date, open, close, high, low, volume, amount等
    
    例如：
        df = _stock_market_sina('600519', 100)  # 获取茅台最近100天数据
    """
    _setup_proxy()  # 设置代理
    
    try:
        # 1. 处理股票代码格式
        # 新浪需要 'sh600519' 或 'sz000001' 格式
        if stock_code.startswith("6"):
            symbol = f"sh{stock_code}"  # 上海股票用sh前缀
        else:
            symbol = f"sz{stock_code}"  # 深圳股票用sz前缀
        
        # 2. 构建API URL
        # 新浪K线API：获取日K线数据
        url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData?symbol={symbol}&scale=240&datalen={count}"
        
        # 3. 发送请求
        resp = requests.get(url, headers=_SINA_HEADERS, timeout=15)
        
        # 4. 检查是否成功
        if resp.status_code != 200:
            return pd.DataFrame()  # 失败返回空数据
        
        # 5. 解析JSON数据
        data = resp.json()  # 转换为Python字典
        if not data:
            return pd.DataFrame()
        
        # 6. 转换为DataFrame（表格）
        df = pd.DataFrame(data)
        
        # 7. 重命名列名（新浪返回的列名和我们想要的不一样）
        df = df.rename(columns={'day': 'trade_date'})  # 'day' 改成 'trade_date'
        
        # 8. 处理日期格式
        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
        df['stock_code'] = stock_code
        df['trade_time'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # 9. 转换数据类型（字符串转数字）
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 10. 计算涨跌额、涨跌幅
        df['pre_close'] = df['close'].shift(1).fillna(df['close'])  # 昨天的收盘价
        df['change'] = df['close'] - df['pre_close']  # 涨跌额
        df['change_pct'] = (df['change'] / df['pre_close'] * 100).round(2)  # 涨跌幅%
        
        # 11. 计算成交额
        if 'amount' not in df.columns:
            df['amount'] = df['volume'] * df['close']
        
        # 12. 返回结果
        return df[['stock_code', 'trade_time', 'trade_date', 'open', 'close', 'high', 'low', 
                   'volume', 'amount', 'change_pct', 'change', 'turnover_ratio', 'pre_close']]
                   
    except Exception as e:
        print(f"获取失败: {e}")
        return pd.DataFrame()  # 出错返回空数据
```

**返回的数据格式示例：**

```
stock_code  trade_date     open   close    high     low     volume      amount  change_pct
600519      2024-01-02  1780   1805   1820   1775   2345678   4200000000    1.45
600519      2024-01-03  1805   1790   1810   1780   1987654   3560000000   -0.83
600519      2024-01-04  1790   1815   1825   1785   2567890   4650000000    1.40
```

#### 2.3.5 获取概念板块成分股

```python
def _concept_constituent_east(concept_code):
    """
    东方财富 API 获取概念板块的成分股
    
    参数：
        concept_code: 概念板块代码，如 'BK0891'（白酒概念）
    
    返回：
        DataFrame，包含：stock_code（股票代码）, short_name（股票名称）
    
    例如：
        df = _concept_constituent_east('BK0891')  # 获取白酒概念的所有成分股
    """
    _setup_proxy()  # 设置代理
    
    curr_page = 1
    data = []
    
    # 东方财富分页返回，每页200条
    while curr_page < 100:
        # 构建API URL
        url = (
            f"https://push2.eastmoney.com/api/qt/clist/get"
            f"?fid=f62&po=1&pz=200&pn={curr_page}&np=1&fltt=2&invt=2"
            f"&fs=b:{concept_code}&fields=f12,f14"
        )
        
        # 发送请求
        r = _request("get", url)
        if r is None:
            break
        
        # 解析JSON
        res_json = r.json()
        res_data = res_json["data"]
        if not res_data:
            break
        
        # 提取数据
        res_data = res_data["diff"]
        for item in res_data:
            data.append({
                "stock_code": item["f12"],  # 股票代码
                "short_name": item["f14"]   # 股票名称
            })
        
        curr_page += 1
    
    # 转换为DataFrame
    result_df = pd.DataFrame(data=data, columns=["stock_code", "short_name"])
    if not result_df.empty:
        result_df["concept_code"] = concept_code
    
    return result_df
```

**返回的数据格式示例：**

```
stock_code  short_name  concept_code
600519      贵州茅台    BK0891
000858      五粮液      BK0891
000568      泸州老窖    BK0891
002304      洋河股份    BK0891
600809      山西汾酒    BK0891
...
```

#### 2.3.6 Collector 类（统一接口）

```python
class Collector:
    """
    数据采集器 - 统一的数据获取接口
    
    这个类把三个数据源的API封装起来，
    自动处理失败和重试，对外提供统一的数据接口
    """
    
    def __init__(self):
        """初始化"""
        self.cfg = engine_config
    
    def get_stock_kline(self, stock_code, start_date=None, end_date=None):
        """
        获取股票K线数据
        
        使用方法：
            collector = Collector()
            
            # 获取最近250天的数据
            df = collector.get_stock_kline('600519')
            
            # 获取指定时间段的数据
            df = collector.get_stock_kline('600519', '2024-01-01', '2024-12-31')
        
        内部流程：
            1. 先尝试新浪API
            2. 失败则尝试腾讯API
            3. 再失败则尝试东方财富API
            4. 全部失败返回空数据
        """
        _clear_proxy()  # 清除代理
        
        # 计算需要获取的天数
        if start_date and end_date:
            from datetime import datetime as dt
            start_dt = dt.strptime(start_date, "%Y-%m-%d")
            end_dt = dt.strptime(end_date, "%Y-%m-%d")
            days = (end_dt - start_dt).days
            count = min(days + 10, 500)  # 多取10天保险
        else:
            count = 250
        
        # 1. 优先尝试新浪
        print(f"正在获取 {stock_code} 的K线数据...")
        df = _stock_market_sina(stock_code, count)
        if not df.empty:
            print(f"✓ 新浪成功获取 {len(df)} 条数据")
            return df
        
        # 2. 腾讯备用
        df = _stock_market_qq(stock_code, count)
        if not df.empty:
            print(f"✓ 腾讯成功获取 {len(df)} 条数据")
            return df
        
        # 3. 东方财富备用
        df = _stock_market_east(stock_code, start_date, end_date)
        if not df.empty:
            print(f"✓ 东方财富成功获取 {len(df)} 条数据")
            return df
        
        print(f"✗ 所有数据源都失败了！")
        return pd.DataFrame()
    
    def get_concept_constituent(self, concept_code):
        """
        获取概念板块的成分股
        
        使用方法：
            collector = Collector()
            
            # 获取白酒概念的成分股
            df = collector.get_concept_constituent('BK0891')
            
            # 获取芯片概念的成分股
            df = collector.get_concept_constituent('BK0901')
        """
        _clear_proxy()
        
        # 1. 优先尝试东方财富实时API
        df = _concept_constituent_east(concept_code)
        if not df.empty:
            print(f"✓ 实时获取概念 {concept_code} 成功，共 {len(df)} 只股票")
            return df
        
        # 2. 失败则使用本地缓存（adata）
        print(f"实时API失败，使用本地缓存...")
        # ... 本地缓存逻辑 ...
        
        return pd.DataFrame()
```

### 2.4 使用示例

#### 示例1：获取单只股票数据

```python
from data_engine.collector import Collector

# 创建采集器
collector = Collector()

# 获取茅台最近100天的数据
df = collector.get_stock_kline('600519', count=100)

print(df.head())  # 打印前几行
print(f"总共获取了 {len(df)} 天的数据")
```

**输出：**
```
  stock_code  trade_date     open   close    high     low     volume
0     600519   2024-01-02  1780   1805   1820   1775   2345678
1     600519   2024-01-03  1805   1790   1810   1780   1987654
2     600519   2024-01-04  1790   1815   1825   1785   2567890
总共获取了 100 天的数据
```

#### 示例2：获取概念板块成分股

```python
# 获取白酒概念的所有成分股
df = collector.get_concept_constituent('BK0891')

print(f"白酒概念共有 {len(df)} 只成分股：")
print(df)
```

**输出：**
```
白酒概念共有 20 只成分股：
  stock_code  short_name
0     600519     贵州茅台
1     000858     五粮液
2     000568     泸州老窖
3     002304     洋河股份
4     600809     山西汾酒
...
```

#### 示例3：获取多只股票数据

```python
# 获取概念的所有成分股
stocks = collector.get_concept_constituent('BK0891')

# 获取每只股票的K线
all_data = {}
for _, row in stocks.iterrows():
    code = row['stock_code']
    name = row['short_name']
    
    print(f"正在获取 {name} ({code}) 的数据...")
    df = collector.get_stock_kline(code, count=250)
    
    if not df.empty:
        all_data[code] = df
        print(f"  ✓ 成功获取 {len(df)} 条数据")
    else:
        print(f"  ✗ 获取失败")

print(f"\n总共成功获取 {len(all_data)} 只股票的数据")
```

### 2.5 数据字段说明

```python
# K线数据字段说明

{
    'stock_code': '600519',           # 股票代码
    'trade_date': '2024-01-02',       # 交易日期
    'trade_time': '2024-01-02 00:00:00',  # 交易时间
    
    # 价格数据
    'open': 1780.00,                 # 开盘价
    'close': 1805.00,                # 收盘价
    'high': 1820.00,                 # 最高价
    'low': 1775.00,                  # 最低价
    'pre_close': 1780.00,            # 昨日收盘价
    
    # 成交量数据
    'volume': 2345678,               # 成交量（股）
    'amount': 4200000000,            # 成交额（元）
    'turnover_ratio': 0.18,         # 换手率（%）
    
    # 涨跌数据
    'change': 25.00,                # 涨跌额（元）
    'change_pct': 1.45,             # 涨跌幅（%）
}
```

### 2.6 常见问题

#### Q1: 请求超时怎么办？

```python
# 设置更长的超时时间
resp = requests.get(url, timeout=30)  # 30秒超时

# 或者捕获异常重试
for i in range(3):
    try:
        resp = requests.get(url, timeout=30)
        break
    except Timeout:
        print(f"超时，重试第{i+1}次...")
        time.sleep(5)
```

#### Q2: 被网站封禁怎么办？

```python
# 1. 使用代理
_setup_proxy()

# 2. 降低请求频率
time.sleep(1)  # 每次请求间隔1秒

# 3. 更换User-Agent
headers['User-Agent'] = 'Mozilla/5.0 (不同浏览器的标识)'
```

#### Q3: 返回数据为空怎么办？

```python
# 检查返回数据
df = _stock_market_sina('600519', 100)

if df.empty:
    print("数据为空！尝试其他数据源...")
    
    # 尝试腾讯
    df = _stock_market_qq('600519', 100)
    
    if df.empty:
        # 尝试东方财富
        df = _stock_market_east('600519', '2024-01-01', '2024-12-31')
```

### 2.7 数据源API地址汇总

| 数据源 | API地址 | 用途 | 速度 |
|--------|---------|------|------|
| 新浪财经 | `https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData` | K线数据 | 快 |
| 腾讯财经 | `https://web.ifzq.gtimg.cn/appstock/app/fqkline/get` | K线数据（前复权）| 快 |
| 东方财富 | `https://push2.eastmoney.com/api/qt/clist/get` | 概念成分股 | 中 |
| 东方财富K线 | `https://push2his.eastmoney.com/api/qt/stock/kline/get` | 历史K线 | 慢 |

---

## 3. 连板队列识别模块 ⭐⭐⭐

### 3.1 什么是连板队列？

连板队列是识别A股市场中连续涨停股票的重要工具，是捕捉主线行情的核心。

**核心功能：**
- 识别每日涨停股票
- 计算连板高度
- 识别龙头股
- 构建连板队列

### 3.2 模块位置

```
/workspace/mainline_quant_v3/strategy_engine/limit_up_queue.py
```

### 3.3 核心函数详解

#### 3.3.1 `identify_limit_up_stocks()` - 识别涨停股票

```python
from strategy_engine.limit_up_queue import identify_limit_up_stocks

# 识别指定日期的涨停股
limit_up_list = identify_limit_up_stocks(stock_kline_data, '2024-12-31')

for stock in limit_up_list:
    print(f"{stock['stock_code']}: {stock['change_pct']:.1f}%")
```

**说明：**
- 主板股票涨停阈值：9.8%
- 创业板/科创板股票涨停阈值：19.8%
- 自动识别股票板块

#### 3.3.2 `calculate_consecutive_limit_ups()` - 计算连板高度

```python
from strategy_engine.limit_up_queue import calculate_consecutive_limit_ups

# 计算单只股票的连板高度
con_days, limit_dates = calculate_consecutive_limit_ups(stock_kline)

print(f"连板高度: {con_days}")
print(f"涨停日期: {limit_dates}")
```

**返回值：**
- `con_days`: 连续涨停天数
- `limit_dates`: 涨停日期列表

#### 3.3.3 `build_limit_up_queue()` - 构建连板队列

```python
from strategy_engine.limit_up_queue import build_limit_up_queue

# 构建连板队列（按连板高度排序）
limit_up_queue = build_limit_up_queue(stock_dict)

print("连板队列:")
print(limit_up_queue[['stock_code', 'consecutive_days', 'is_leader']])
```

#### 3.3.4 `identify_leader_stocks()` - 识别龙头股

```python
from strategy_engine.limit_up_queue import identify_leader_stocks

# 识别龙头股（默认>=3板）
leaders = identify_leader_stocks(limit_up_queue, leader_threshold=3)

print(f"发现 {len(leaders)} 只龙头股")
```

### 3.4 连板队列数据结构

```python
{
    'stock_code': '600519',
    'short_name': '贵州茅台',
    'consecutive_days': 5,     # 连板高度
    'limit_up_dates': [...],   # 涨停日期
    'is_leader': True          # 是否龙头
}
```

---

## 4. 龙虎榜分析模块 ⭐⭐⭐

### 4.1 什么是龙虎榜？

龙虎榜是A股市场每天收盘后公布的异动股票交易数据，包含主力资金的买卖情况。

**核心功能：**
- 获取龙虎榜数据
- 识别机构专用席位
- 分析龙虎榜上榜后次日表现
- 提取热门股

### 4.2 模块位置

```
/workspace/mainline_quant_v3/strategy_engine/billboard_analyzer.py
```

### 4.3 核心函数详解

#### 4.3.1 `get_billboard_data()` - 获取龙虎榜数据

```python
from strategy_engine.billboard_analyzer import get_billboard_data

# 获取今日龙虎榜
billboard_df = get_billboard_data(date='2024-12-31')

print(f"获取到 {len(billboard_df)} 条龙虎榜数据")
```

#### 4.3.2 `analyze_billboard_stock()` - 分析单只股票的龙虎榜

```python
from strategy_engine.billboard_analyzer import analyze_billboard_stock

# 分析茅台的龙虎榜
analysis = analyze_billboard_stock(billboard_df, '600519')

print(f"上榜次数: {analysis['on_list_count']}")
print(f"总净买入: {analysis['total_net_amount']}")
```

#### 4.3.3 `identify_institutional_buyers()` - 识别机构专用席位

```python
from strategy_engine.billboard_analyzer import identify_institutional_buyers

# 识别机构买入
institutional_buys = identify_institutional_buyers(billboard_df)

for buy in institutional_buys:
    print(f"{buy['stock_code']}: {buy['buyer_name']}")
```

#### 4.3.4 `analyze_next_day_performance()` - 分析龙虎榜次日表现

```python
from strategy_engine.billboard_analyzer import analyze_next_day_performance

# 分析上榜后的次日表现
next_day = analyze_next_day_performance(
    '2024-12-30',  # 上榜日期
    stock_kline, 
    '600519'
)

print(f"次日涨跌幅: {next_day['next_change_pct']:.1f}%")
```

### 4.4 龙虎榜数据字段

```python
{
    'stock_code': '600519',
    'stock_name': '贵州茅台',
    'buyer_name': '机构专用',
    'buy_amount': 150000000.0,  # 买入金额
    'sell_amount': 50000000.0,  # 卖出金额
    'net_amount': 100000000.0    # 净买入
}
```

---

## 5. 涨停原因与主线扩散分析 ⭐⭐⭐

### 5.1 什么是主线扩散效应？

主线扩散是指：当某个板块成为热点后，资金会向该板块的上下游、相关概念蔓延的过程。

**核心功能：**
- 识别涨停原因
- 分析概念板块联动
- 检测主线扩散效应
- 构建概念热度层级

### 5.2 模块位置

```
/workspace/mainline_quant_v3/strategy_engine/main_line_analysis.py
```

### 5.3 核心函数详解

#### 5.3.1 `identify_limit_up_reason()` - 识别涨停原因

```python
from strategy_engine.main_line_analysis import identify_limit_up_reason

# 识别涨停原因
reasons = identify_limit_up_reason(limit_up_df, concept_stocks_dict)

for stock in reasons:
    print(f"{stock['stock_code']}: {stock['reason']}")
```

#### 5.3.2 `analyze_concept_co_movement()` - 分析概念板块联动

```python
from strategy_engine.main_line_analysis import analyze_concept_co_movement

# 分析概念联动
co_movement = analyze_concept_co_movement(concept_stocks_dict, limit_up_df)

for concept, perf in co_movement.items():
    print(f"{concept}: 涨停占比 {perf['limit_up_ratio']*100:.1f}%")
```

#### 5.3.3 `detect_main_line_diffusion()` - 检测主线扩散效应

```python
from strategy_engine.main_line_analysis import detect_main_line_diffusion

# 检测主线扩散
diffusion = detect_main_line_diffusion(co_movement, concept_stocks_dict)

print(f"热门概念: {diffusion['hot_concepts']}")
print(f"主线强度: {diffusion['main_line_strength']:.1f}/100")
```

#### 5.3.4 `build_concept_hierarchy()` - 构建概念热度层级

```python
from strategy_engine.main_line_analysis import build_concept_hierarchy

# 构建概念层级
hierarchy = build_concept_hierarchy(concept_stocks_dict, limit_up_df)

print(f"核心概念: {hierarchy['core_concepts']}")
print(f"主要概念: {hierarchy['major_concepts']}")
print(f"是否为主线行情: {'是' if hierarchy['is_main_line'] else '否'}")
```

### 5.4 概念热度层级

```
┌─────────────────────────────────────────────────────────┐
│                     概念热度层级                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  核心概念（涨停占比 >= 50%）                     │   │
│  │  - 最强的主线，资金最集中                         │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  主要概念（涨停占比 >= 20%）                     │   │
│  │  - 次要主线，资金开始扩散                         │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  次要概念（涨停占比 < 20%）                      │   │
│  │  - 非主流，资金关注度低                          │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 6. 回测引擎

### 6.1 什么是回测？

**回测** = 用历史数据测试策略表现

```
┌─────────────────────────────────────────────────────────────────┐
│                        回测原理                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  假设：2024年1月1日，我用策略选出了股票A                        │
│                                                                 │
│  回测会：                                                       │
│  1. 假装在2024年1月1日买入股票A                                 │
│  2. 看着它在2024年一整年的走势                                   │
│  3. 计算我最终是赚钱还是亏钱                                     │
│                                                                 │
│  这样就能知道策略在过去表现如何                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 回测运行方法

```bash
# 进入项目目录
cd /workspace/mainline_quant_v3

# 运行回测
python run_backtest.py --concept BK0891 --start 2024-01-01 --end 2024-12-31 --capital 1000000
```

**参数说明：**
- `--concept`：概念板块代码，如 BK0891（白酒）
- `--start`：回测开始日期
- `--end`：回测结束日期
- `--capital`：初始资金（元）

### 3.3 回测报告解读

```
======================================================================
   主线量化交易系统 V3  -  回测报告
======================================================================

  回测概念板块: BK0891（白酒概念）
  回测区间: 2024-01-01 ~ 2024-12-31
  初始资金: 1,000,000 元

----------------------------------------------------------------------
  【核心收益指标】
----------------------------------------------------------------------
  最终权益:     1,094,209.83 元      ← 回测结束时的总资产
  累计收益:     +9.42%               ← 一年赚了9.42%
  年化收益:     +67.11%              ← 折算成年化收益率

----------------------------------------------------------------------
  【风险指标】
----------------------------------------------------------------------
  夏普比率:     2.05                 ← 风险调整后收益，越高越好
  索提诺比率:   4.08                 ← 只考虑下跌风险
  卡玛比率:     9.79                 ← 收益/最大回撤，越高越好
  最大回撤:     -6.85%               ← 曾经从高点跌了多少
  年化波动率:   25.62%               ← 收益波动程度

----------------------------------------------------------------------
  【交易统计】
----------------------------------------------------------------------
  总交易次数:   13                   ← 一年交易了13次
  盈利次数:     7                    ← 盈利7次
  亏损次数:     6                    ← 亏损6次
  胜率:         53.85%              ← 盈利次数/总次数
  盈亏比:       2.60                ← 平均盈利/平均亏损
  平均持仓天数: 10.8 天              ← 平均持仓时间
  最大连胜:     5                    ← 最多连续盈利5次
  最大连亏:     3                    ← 最多连续亏损3次

======================================================================
```

### 3.4 回测指标解释

| 指标 | 含义 | 怎么算好 |
|------|------|----------|
| 累计收益 | 总共赚了多少 | 越高越好 |
| 夏普比率 | 承担1份风险能赚多少收益 | >1.5 很好，>2 优秀 |
| 最大回撤 | 从最高点跌了多少 | 越低越好，<10% 不错 |
| 胜率 | 盈利交易占比 | >50% 就行 |
| 盈亏比 | 赚一次能抵几次亏 | >1.5 不错 |
| 卡玛比率 | 年化收益/最大回撤 | >3 很好 |

---

## 7. 策略引擎

### 4.1 主线评分策略（核心）

**主线策略** = 给每只股票打分，选择分数最高的买

```python
class MainlineBacktestStrategy:
    """
    主线评分策略
    
    每天给候选股票打分，分数高的买入
    
    评分维度：
    1. 涨跌幅（30分）：涨停板最强
    2. 成交额（20分）：资金关注度高
    3. 换手率（15分）：交易活跃度
    4. 股票板块（10分）：主板加分
    """
    
    def __init__(self):
        self.entry_score_threshold = 50  # 入场门槛：50分才能买
        self.max_positions = 5            # 最多同时持有5只
        self.position_pct = 0.18          # 每只股票最多18%仓位
        self.stop_loss_pct = -0.06        # 亏6%止损
        self.take_profit_pct = 0.12       # 赚12%止盈
    
    def _score_stock(self, code, row, daily_data):
        """给单只股票打分"""
        score = 0
        
        # 1. 涨跌幅评分（0-30分）
        change_pct = float(row.get("change_pct", 0))
        if change_pct > 9:      # 涨停
            score += 30
        elif change_pct > 6:    # 涨幅>6%
            score += 25
        elif change_pct > 3:    # 涨幅>3%
            score += 20
        elif change_pct > 1:    # 涨幅>1%
            score += 15
        elif change_pct > 0:    # 上涨
            score += 10
        else:                    # 下跌
            score += 0
        
        # 2. 成交额评分（0-20分）
        amount = float(row.get("amount", 0))
        if amount > 10e8:       # 成交额>10亿
            score += 20
        elif amount > 5e8:       # 成交额>5亿
            score += 15
        elif amount > 2e8:       # 成交额>2亿
            score += 10
        elif amount > 1e8:       # 成交额>1亿
            score += 5
        
        # 3. 换手率评分（0-15分）
        turnover_ratio = float(row.get("turnover_ratio", 0))
        if turnover_ratio > 5:
            score += 15
        elif turnover_ratio > 3:
            score += 12
        elif turnover_ratio > 1.5:
            score += 8
        elif turnover_ratio > 0.8:
            score += 5
        
        # 4. 板块评分（0-10分）
        if code.startswith("60") or code.startswith("000"):
            score += 10  # 主板加分
        elif code.startswith("688") or code.startswith("30"):
            score += 8   # 科创/创业板
        
        return score
```

### 4.2 出场条件（何时卖）

```python
def generate_signals(self, daily_data, current_date, positions):
    """
    生成交易信号（买/卖）
    
    出场条件（满足任一就卖）：
    1. 止损：亏了6%以上
    2. 止盈：赚了12%以上
    3. 时间止损：持仓超过30天
    4. 评分下降：分数低于35分且持仓>5天
    """
    signals = []
    holding_codes = list(positions.keys())
    
    for code in holding_codes:
        if code in daily_data:
            row = daily_data[code]
            cost = positions[code]["avg_cost"]  # 买入成本
            current_price = float(row.get("close", 0))
            ret = (current_price - cost) / cost  # 收益率
            
            # 1. 止损
            if ret <= self.stop_loss_pct:
                signals.append({
                    "stock_code": code,
                    "direction": "SELL",
                    "reason": f"止损 {ret:.2%}"
                })
            
            # 2. 止盈
            elif ret >= self.take_profit_pct:
                signals.append({
                    "stock_code": code,
                    "direction": "SELL",
                    "reason": f"止盈 {ret:.2%}"
                })
            
            # 3. 时间止损
            elif self.position_hold_days[code] > 30:
                signals.append({
                    "stock_code": code,
                    "direction": "SELL",
                    "reason": f"时间止损 {self.position_hold_days[code]}天"
                })
    
    return signals
```

---

## 8. 风控系统

### 5.1 五层风控体系

```
┌─────────────────────────────────────────────────────────────────┐
│                      五层风控体系                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  第1层：仓位控制                                                │
│  ─────────────────────────────────────────────                  │
│  单只股票 ≤ 20%仓位                                             │
│  总仓位 ≤ 90%                                                   │
│                                                                 │
│  第2层：止损保护                                                │
│  ─────────────────────────────────────────────                  │
│  单笔亏损 ≤ 6%                                                  │
│  日内亏损 ≤ 10%                                                 │
│                                                                 │
│  第3层：分散投资                                                │
│  ─────────────────────────────────────────────                  │
│  同时持有 3-5 只股票                                            │
│  不同板块分散                                                   │
│                                                                 │
│  第4层：流动性管理                                              │
│  ─────────────────────────────────────────────                  │
│  只买日成交额 > 1亿 的股票                                       │
│  避免小盘股流动性风险                                           │
│                                                                 │
│  第5层：压力测试                                                │
│  ─────────────────────────────────────────────                  │
│  模拟极端行情                                                   │
│  确保极端情况下不会爆仓                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Kelly公式仓位计算

```python
def calculate_kelly_position(win_rate, profit_loss_ratio, total_capital):
    """
    Kelly公式计算最优仓位
    
    Kelly公式：f = (bp - q) / b
    其中：
        f = 仓位比例
        b = 盈亏比
        p = 胜率
        q = 1 - p
    
    例如：
        胜率50%，盈亏比2
        Kelly = (2 * 0.5 - 0.5) / 2 = 25%
        最优仓位是25%
    """
    b = profit_loss_ratio
    p = win_rate
    q = 1 - p
    
    kelly = (b * p - q) / b
    
    # 实际使用一半Kelly（更保守）
    actual_position = kelly * 0.5
    
    # 限制最大仓位20%
    actual_position = min(actual_position, 0.20)
    
    return actual_position
```

---

## 9. AI分析模块

### 6.1 四大AI智能体

```python
# AI分析模块包含4个智能体

┌─────────────────────────────────────────────────────────────────┐
│                      AI智能体团队                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐                         │
│  │  技术分析师  │     │  资金分析师  │                         │
│  │ Tech Analyst │     │Fund Analyst  │                         │
│  └──────────────┘     └──────────────┘                         │
│        │                    │                                   │
│        ▼                    ▼                                   │
│  分析K线形态          分析主力资金流向                          │
│  识别技术信号          判断机构动向                            │
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐                         │
│  │  流向分析师  │     │  情绪分析师  │                         │
│  │ Flow Analyst │     │Sentiment AI  │                         │
│  └──────────────┘     └──────────────┘                         │
│        │                    │                                   │
│        ▼                    ▼                                   │
│  分析板块轮动          分析市场情绪                            │
│  判断资金偏好          识别热点概念                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 AI决策流程

```
用户问：今天买什么股票？

    │
    ▼
┌─────────────────────────────────────┐
│  协调器接收请求                      │
└─────────────────────────────────────┘
    │
    ├───────────────────────────────┐
    │                               │
    ▼                               ▼
┌───────────┐               ┌───────────┐
│ 技术分析  │               │ 资金分析  │
│ 分析K线   │               │ 分析主力  │
└───────────┘               └───────────┘
    │                               │
    │ 各自输出分析报告               │
    │                               │
    ▼                               ▼
┌───────────┐               ┌───────────┐
│ 流向分析  │               │ 情绪分析  │
│ 分析轮动  │               │ 分析热点  │
└───────────┘               └───────────┘
    │                               │
    └───────────┬───────────────────┘
                │
                ▼
        ┌───────────────┐
        │  决策引擎     │
        │ 综合所有分析  │
        │ 给出建议     │
        └───────────────┘
                │
                ▼
        ┌───────────────┐
        │  最终建议     │
        │ "建议买入XXX" │
        └───────────────┘
```

---

## 10. 交易执行

### 7.1 模拟交易 vs 实盘交易

```
┌─────────────────────────────────────────────────────────────────┐
│                      交易模式对比                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  模拟交易（Simulator）                                          │
│  ─────────────────────────────────────────────                  │
│  ✓ 不花真钱                                                    │
│  ✓ 可以测试策略                                                │
│  ✓ 无风险                                                      │
│  ✗ 不反映真实成交价格                                          │
│                                                                 │
│  实盘交易（Broker）                                             │
│  ─────────────────────────────────────────────                  │
│  ✓ 真金白银                                                    │
│  ✓ 真实成交价格                                                │
│  ✓ 可以赚钱（也可能亏钱）                                      │
│  ✗ 有风险                                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 订单类型

```python
# 支持的订单类型

OrderType = {
    'MARKET': '市价单',        # 以市场价立即成交
    'LIMIT': '限价单',          # 指定价格成交
    'STOP': '止损单',           # 触发止损
    'STOP_LIMIT': '止损限价单'  # 触发止损后限价成交
}

# 订单状态
OrderStatus = {
    'PENDING': '待成交',       # 刚下单
    'PARTIAL': '部分成交',     # 成交了一部分
    'FILLED': '全部成交',      # 全部成交
    'CANCELLED': '已取消',     # 撤单
    'REJECTED': '已拒绝'       # 被拒绝
}
```

---

## 11. 快速开始

### 8.1 环境要求

```bash
# Python版本
Python >= 3.8

# 安装依赖
pip install pandas numpy requests duckdb pyarrow openai loguru toml python-dotenv
```

### 8.2 运行回测

```bash
# 1. 进入项目目录
cd /workspace/mainline_quant_v3

# 2. 运行回测
python run_backtest.py --concept BK0891 --start 2024-01-01 --end 2024-12-31 --capital 1000000

# 3. 查看报告
cat backtest_report.txt
```

### 8.3 查看回测JSON数据

```bash
# 查看JSON格式的详细数据
cat backtest_report.json | python -m json.tool
```

---

## 12. 常见问题与故障排查

### 9.1 数据获取问题

#### 问题1：所有API都返回空数据

**可能原因：**
1. 网络无法访问
2. 代理设置错误
3. API地址失效

**解决方法：**

```python
# 1. 检查代理
import os
print("代理设置：", os.environ.get('HTTP_PROXY'))

# 2. 手动测试API
import requests
url = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData?symbol=sh600519&scale=240&datalen=5"
resp = requests.get(url, timeout=10)
print(resp.status_code, resp.text[:200])

# 3. 清除代理重试
for key in list(os.environ.keys()):
    if key.lower().endswith('proxy'):
        del os.environ[key]
```

#### 问题2：部分股票获取失败

**可能原因：**
1. 股票代码错误
2. 股票已退市
3. 网络波动

**解决方法：**

```python
# 逐个获取，失败跳过
stocks = ['600519', '000858', '000568', '000000', '600809']
all_data = {}

for code in stocks:
    try:
        df = collector.get_stock_kline(code, count=100)
        if not df.empty:
            all_data[code] = df
            print(f"✓ {code} 成功")
        else:
            print(f"✗ {code} 无数据（可能已退市）")
    except Exception as e:
        print(f"✗ {code} 获取失败: {e}")
```

#### 问题3：请求超时

**解决方法：**

```python
# 增加超时时间
def _stock_market_sina(stock_code, count=250):
    _setup_proxy()
    try:
        url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData?symbol={symbol}&scale=240&datalen={count}"
        
        # 超时设为60秒
        resp = requests.get(url, headers=_SINA_HEADERS, timeout=60)
        
        # 或者使用retry
        for attempt in range(3):
            try:
                resp = requests.get(url, timeout=30)
                break
            except Timeout:
                print(f"超时，重试第{attempt+1}次")
                time.sleep(5)
        
    except Exception as e:
        print(f"获取失败: {e}")
        return pd.DataFrame()
```

### 9.2 回测问题

#### 问题1：回测报告没有交易

**可能原因：**
1. 入场评分阈值太高
2. 概念成分股数据为空
3. 没有满足条件的股票

**解决方法：**

```python
# 降低入场门槛
class MainlineBacktestStrategy:
    def __init__(self):
        self.entry_score_threshold = 45  # 从65降到45
```

#### 问题2：收益为负

**可能原因：**
1. 策略参数不合适
2. 测试时间段行情不好
3. 止损太紧

**解决方法：**

```python
# 调整止损止盈
self.stop_loss_pct = -0.08     # 放宽止损到8%
self.take_profit_pct = 0.15    # 提高止盈到15%
```

### 9.3 网络问题

#### 检查网络连通性

```bash
# 测试是否能访问新浪
curl -I https://quotes.sina.cn --max-time 10

# 测试是否能访问腾讯
curl -I https://web.ifzq.gtimg.cn --max-time 10

# 测试是否能访问东方财富
curl -I https://push2.eastmoney.com --max-time 10
```

#### 设置代理

```python
# 在collector.py开头添加
import os

# 取消所有代理
for key in list(os.environ.keys()):
    if key.lower().endswith('proxy'):
        del os.environ[key]

# 设置代理（如果有）
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:18080'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:18080'
```

---

## 附录：常用股票代码

### A股主要指数

| 指数 | 代码 | 说明 |
|------|------|------|
| 上证指数 | 000001 | 上海证券交易所综合指数 |
| 深证成指 | 399001 | 深圳证券交易所成分指数 |
| 创业板指 | 399006 | 创业板综合指数 |
| 科创50 | 000688 | 科创板50指数 |

### 白酒板块成分股

| 股票 | 代码 | 名称 |
|------|------|------|
| 600519 | 贵州茅台 | 白酒龙头 |
| 000858 | 五粮液 | 白酒龙头 |
| 000568 | 泸州老窖 | 白酒 |
| 002304 | 洋河股份 | 白酒 |
| 600809 | 山西汾酒 | 白酒 |

### 常用概念板块代码

| 概念 | 代码 |
|------|------|
| 白酒 | BK0891 |
| 芯片 | BK0901 |
| 人工智能 | BK0891 |
| 新能源车 | BK0900 |
| 光伏 | BK0902 |

---

## 文档版本

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| 1.0 | 2024-01-01 | 初始版本 |
| 1.1 | 2024-12-31 | 增加数据获取详解 |
| 2.0 | 2026-05-16 | 重大更新，增加故障排查 |

---

**如果文档中有任何不明白的地方，请随时提问！** 🙋‍♂️
