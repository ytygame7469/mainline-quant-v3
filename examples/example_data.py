# -*- coding: utf-8 -*-
"""
示例1: 数据获取示例
"""
import sys
import os

# 清除代理
for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    if var in os.environ:
        del os.environ[var]

sys.path.insert(0, '/workspace')


def example_data():
    """数据获取示例"""
    print("=" * 80)
    print("示例1: 数据获取")
    print("=" * 80)
    
    from mainline_quant.data.fetcher_v2 import get_data_provider
    
    # 初始化
    provider = get_data_provider()
    
    # 1. 获取概念板块
    print("\n[1] 概念板块...")
    concepts = provider.get_all_concepts()
    if not concepts.empty:
        print(f"✅ {len(concepts)} 个概念板块")
        print(concepts.head())
    
    # 2. 获取股票K线
    print("\n[2] 股票K线（600000）...")
    kline = provider.get_stock_kline('600000', count=5)
    if not kline.empty:
        print("✅ 获取成功！")
        print(kline)
    
    # 3. 获取实时行情（直接用curl方式测试
    print("\n[3] 实时行情...")
    try:
        import requests
        url = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData?symbol=sh600000&scale=240&datalen=5"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            print("✅ 新浪API连接正常！")
    except Exception as e:
        print(f"⚠️  测试跳过: {e}")
    
    print("\n" + "=" * 80)
    print("✅ 示例1完成！")
    print("=" * 80)


if __name__ == "__main__":
    example_data()
