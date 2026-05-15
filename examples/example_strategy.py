# -*- coding: utf-8 -*-
"""
示例2: 主线策略示例
"""
import sys
import os

sys.path.insert(0, '/workspace')


def example_strategy():
    """策略示例"""
    print("=" * 80)
    print("示例2: 主线策略")
    print("=" * 80)
    
    from mainline_quant.data.fetcher_v2 import get_data_provider
    from mainline_quant.strategy.mainline_v2 import SimplifiedMainlineStrategy
    
    # 初始化
    provider = get_data_provider()
    strategy = SimplifiedMainlineStrategy(provider)
    
    # 扫描主线
    print("\n[1] 主线扫描...")
    mainlines = strategy.scan_mainline_simplified()
    
    if not mainlines.empty:
        print(f"\n✅ 找到 {len(mainlines)} 个潜在主线")
        
        # 选龙头
        best = mainlines.iloc[0]
        print(f"\n[2] 最佳主线: {best['concept_name']} (评分: {best['score']})")
        
        leaders = strategy.select_leaders_simplified(best['concept_code'])
        print(f"   龙头股: {leaders}")
    
    print("\n" + "=" * 80)
    print("✅ 示例2完成！")
    print("=" * 80)


if __name__ == "__main__":
    example_strategy()
