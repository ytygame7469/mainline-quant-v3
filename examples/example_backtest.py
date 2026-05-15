# -*- coding: utf-8 -*-
"""
示例3: 回测框架示例
"""
import sys
import os

sys.path.insert(0, '/workspace')


def example_backtest():
    """回测示例"""
    print("=" * 80)
    print("示例3: 回测框架")
    print("=" * 80)
    
    from mainline_quant.backtest.simple_backtest import BacktestEngine
    
    # 初始化
    engine = BacktestEngine(initial_capital=100000)
    
    print("\n[1] 模拟交易...")
    # 模拟一些交易
    engine.buy('600000', 10.0, 1000, '2025-01-01')
    engine.buy('000001', 15.0, 500, '2025-01-02')
    
    print("\n[2] 记录每日资产...")
    # 模拟一些日期
    engine.record_daily_value('2025-01-01', {'600000': 10.0, '000001': 15.0})
    engine.record_daily_value('2025-01-02', {'600000': 10.5, '000001': 15.2})
    engine.record_daily_value('2025-01-03', {'600000': 11.0, '000001': 15.8})
    
    print("\n[3] 卖出...")
    engine.sell('600000', 11.0, 1000, '2025-01-04')
    engine.sell('000001', 15.8, 500, '2025-01-04')
    
    print("\n[4] 回测报告...")
    engine.print_report()
    
    print("\n" + "=" * 80)
    print("✅ 示例3完成！")
    print("=" * 80)


if __name__ == "__main__":
    example_backtest()
