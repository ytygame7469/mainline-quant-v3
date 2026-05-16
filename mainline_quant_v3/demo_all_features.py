# -*- coding: utf-8 -*-
"""
主线策略V3 - 完整功能演示
包含：连板队列识别、龙虎榜分析、涨停原因分析、主线扩散效应检测
"""
import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入新创建的模块
from data_engine.collector import collector
from strategy_engine.limit_up_queue import (
    identify_limit_up_stocks,
    calculate_consecutive_limit_ups,
    build_limit_up_queue,
    identify_leader_stocks
)
from strategy_engine.billboard_analyzer import (
    get_billboard_data,
    analyze_billboard_stock,
    identify_institutional_buyers,
    get_hot_stocks_from_billboard
)
from strategy_engine.main_line_analysis import (
    identify_limit_up_reason,
    analyze_concept_co_movement,
    detect_main_line_diffusion,
    build_concept_hierarchy
)


def get_demo_stock_data():
    """获取演示用的股票数据（使用adata缓存）"""
    print("=" * 70)
    print("获取演示数据...")
    print("=" * 70)
    
    # 先从adata获取成分股列表
    try:
        adata_cache_path = os.path.join(
            os.path.dirname(__file__),
            "..", "references", "adata", "adata", "stock", "info", "cache"
        )
        stocks_csv = os.path.join(adata_cache_path, "all_code.csv")
        concepts_csv = os.path.join(adata_cache_path, "all_concept_code_east.csv")
        
        if not os.path.exists(stocks_csv) or not os.path.exists(concepts_csv):
            print("找不到adata缓存，使用演示数据")
            return {}, {}
        
        stocks_df = pd.read_csv(stocks_csv)
        concepts_df = pd.read_csv(concepts_csv)
        
        # 构建概念成分股字典
        concept_stocks = {}
        
        # 我们使用白酒概念作为演示
        demo_concept = concepts_df.sample(5).iloc[0]['concept_code'] if len(concepts_df) > 0 else 'BK0891'
        print(f"演示用概念: {demo_concept}")
        
        # 获取成分股（采样30只）
        sample_stocks = stocks_df.sample(min(30, len(stocks_df))).copy()
        
        # 为每只股票生成模拟K线
        stocks_data = {}
        for _, stock_row in sample_stocks.iterrows():
            stock_code = stock_row['stock_code']
            short_name = stock_row['short_name']
            
            # 获取真实K线（如果成功），否则生成模拟
            df_kline = collector.get_stock_kline(str(stock_code).zfill(6))
            
            if len(df_kline) < 10:
                # 生成模拟K线
                df_kline = generate_demo_kline(str(stock_code).zfill(6), short_name)
            
            stocks_data[str(stock_code).zfill(6)] = df_kline
        
        concept_stocks[demo_concept] = sample_stocks
        
        return stocks_data, concept_stocks
    
    except Exception as e:
        print(f"获取数据失败: {e}")
        return {}, {}


def generate_demo_kline(stock_code: str, short_name: str) -> pd.DataFrame:
    """生成演示用的K线"""
    import numpy as np
    
    # 生成20天数据
    dates = pd.date_range(end=datetime.now(), periods=20, freq='B').strftime('%Y-%m-%d')
    
    # 生成模拟价格
    base_price = 10.0 + np.random.randn(1)[0] * 2
    prices = [base_price]
    
    for i in range(19):
        change = np.random.normal(0, 0.03)
        
        # 模拟一些涨停
        if i > 10 and i < 16:
            change = 0.10  # 涨停
        
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    # 构建DataFrame
    data = []
    for i, date in enumerate(dates):
        open_price = prices[i] * (1 + np.random.normal(0, 0.01))
        close = prices[i]
        high = max(open_price, close) * (1 + abs(np.random.normal(0, 0.02)))
        low = min(open_price, close) * (1 - abs(np.random.normal(0, 0.02)))
        volume = int(np.random.normal(1000000, 200000))
        prev_close = prices[i - 1] if i > 0 else prices[i]
        change_pct = (close - prev_close) / prev_close * 100
        
        data.append({
            'trade_date': date,
            'stock_code': stock_code,
            'open': round(open_price, 2),
            'close': round(close, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'volume': volume,
            'amount': volume * close,
            'change_pct': round(change_pct, 2),
            'change': close - prev_close,
            'turnover_ratio': round(np.random.uniform(0.5, 3.0), 2),
            'pre_close': round(prev_close, 2)
        })
    
    return pd.DataFrame(data)


def main():
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "主线量化交易系统 V3 - 完整功能演示" + " " * 20 + "║")
    print("╚" + "=" * 68 + "╝")
    
    # 1. 获取数据
    stocks_data, concept_stocks = get_demo_stock_data()
    
    if not stocks_data:
        print("\n无法获取数据，演示将使用完全模拟数据")
        return
    
    print(f"\n成功获取 {len(stocks_data)} 只股票数据\n")
    
    # 2. 识别涨停股票
    print("=" * 70)
    print("1. 连板队列识别")
    print("=" * 70)
    
    all_limit_up = []
    for stock_code, kline_df in stocks_data.items():
        limit_up_list = identify_limit_up_stocks(kline_df)
        all_limit_up.extend(limit_up_list)
    
    limit_up_df = pd.DataFrame(all_limit_up)
    
    if not limit_up_df.empty:
        print(f"发现 {len(limit_up_df)} 只涨停股")
        
        # 构建连板队列
        print("\n构建连板队列...")
        limit_queue = build_limit_up_queue(stocks_data)
        
        if not limit_queue.empty:
            print("\n" + "连板队列（按高度排序）:")
            print(limit_queue[['stock_code', 'consecutive_days', 'is_leader']].to_string(index=False))
        
        # 识别龙头
        print("\n识别龙头股...")
        leaders = identify_leader_stocks(limit_queue)
        
        if leaders:
            print(f"\n发现 {len(leaders)} 只龙头股（>=3板）:")
            for leader in leaders:
                print(f"  {leader['stock_code']}: {leader['consecutive_days']}板")
        else:
            print("\n今日无龙头股（<3板）")
    else:
        print("今日无涨停股")
    
    # 3. 分析概念联动和主线扩散
    print("\n" + "=" * 70)
    print("2. 概念联动与主线扩散分析")
    print("=" * 70)
    
    if not limit_up_df.empty:
        # 构建概念层级
        print("\n构建概念热度层级...")
        hierarchy = build_concept_hierarchy(concept_stocks, limit_up_df)
        
        print(f"\n核心概念: {hierarchy['core_concepts']}")
        print(f"主要概念: {hierarchy['major_concepts']}")
        print(f"是否为主线行情: {'是' if hierarchy['is_main_line'] else '否'}")
        
        # 分析主线扩散
        print("\n检测主线扩散效应...")
        diffusion = detect_main_line_diffusion(hierarchy['concept_performance'], concept_stocks)
        
        print(f"\n热门概念数量: {diffusion['hot_concept_count']}")
        print(f"主线强度: {diffusion['main_line_strength']:.1f}/100")
        
        # 识别涨停原因
        print("\n分析涨停原因...")
        limit_up_with_reason = identify_limit_up_reason(limit_up_df, concept_stocks)
        
        if limit_up_with_reason:
            print(f"\n已分析 {len(limit_up_with_reason)} 只涨停股的原因")
            for stock in limit_up_with_reason[:5]:  # 显示前5只
                concepts = ', '.join(stock['possible_concepts']) if stock['possible_concepts'] else '无'
                print(f"  {stock['stock_code']}: {stock['reason']} ({concepts})")
    
    # 4. 龙虎榜分析
    print("\n" + "=" * 70)
    print("3. 龙虎榜分析")
    print("=" * 70)
    
    print("\n获取龙虎榜数据...")
    billboard_df = get_billboard_data(page=1, page_size=30)
    
    if not billboard_df.empty:
        print(f"获取到 {len(billboard_df)} 条龙虎榜数据")
        
        # 机构识别
        print("\n识别机构专用席位...")
        institutional = identify_institutional_buyers(billboard_df)
        
        if institutional:
            print(f"发现 {len(institutional)} 个机构买入")
            for ins in institutional[:5]:
                print(f"  {ins['stock_code']}: {ins['buyer_name']}")
        
        # 热门股提取
        print("\n提取龙虎榜热门股...")
        hot_stocks = get_hot_stocks_from_billboard(billboard_df, top_n=5)
        
        if hot_stocks:
            print("\n龙虎榜热门股前5:")
            for hs in hot_stocks:
                print(f"  {hs['stock_name']} ({hs['stock_code']}): 净买入 {hs['net_amount']/100000000:.1f}亿")
    else:
        print("暂未获取到今日龙虎榜数据（可能是网络问题）")
    
    # 5. 总结
    print("\n" + "=" * 70)
    print("演示总结")
    print("=" * 70)
    
    print("\n系统已包含以下功能:")
    print("  ✓ 连板队列识别")
    print("  ✓ 龙头股识别")
    print("  ✓ 龙虎榜数据获取")
    print("  ✓ 机构席位识别")
    print("  ✓ 涨停原因分析")
    print("  ✓ 概念联动分析")
    print("  ✓ 主线扩散效应检测")
    print("  ✓ 概念热度层级")
    
    print("\n文件位置:")
    print("  /workspace/mainline_quant_v3/strategy_engine/")
    print("    - limit_up_queue.py     # 连板队列模块")
    print("    - billboard_analyzer.py  # 龙虎榜分析模块")
    print("    - main_line_analysis.py  # 主线扩散分析模块")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
