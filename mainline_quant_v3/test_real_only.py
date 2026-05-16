#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
严格使用真实数据的测试 - 2026年5月15日
绝对不使用任何模拟数据！
"""
import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_engine.collector import Collector

TEST_DATE = "2026-05-15"


def main():
    print("\n" + "="*70)
    print("主线量化交易系统 V3 - 真实数据测试 (2026-05-15)")
    print("="*70)
    print("⚠️ 严格使用真实数据，不使用任何模拟数据！")
    print("="*70)
    
    collector = Collector()
    
    # 1. 尝试获取龙虎榜真实数据（多次尝试不同的数据源）
    print("\n[1/3] 尝试获取龙虎榜真实数据...")
    billboard_df = None
    
    # 尝试东方财富龙虎榜API
    try:
        billboard_df = collector.get_billboard(date=TEST_DATE, page=1, page_size=100)
        if not billboard_df.empty:
            print(f"  ✓ 东方财富龙虎榜API成功: {len(billboard_df)} 条数据")
    except Exception as e:
        print(f"  ✗ 东方财富龙虎榜API失败: {e}")
    
    # 如果失败，尝试其他日期范围
    if billboard_df is None or billboard_df.empty:
        print("\n  尝试获取最近几个交易日的龙虎榜...")
        dates_to_try = [
            "2026-05-14",
            "2026-05-13", 
            "2026-05-12",
            "2026-05-09",
            "2026-05-08"
        ]
        
        for date in dates_to_try:
            try:
                test_df = collector.get_billboard(date=date, page=1, page_size=100)
                if not test_df.empty:
                    print(f"  ✓ 找到 {date} 的龙虎榜数据: {len(test_df)} 条")
                    billboard_df = test_df
                    break
            except Exception as e:
                print(f"  ✗ {date} 获取失败: {e}")
                continue
    
    # 2. 尝试获取真实K线数据
    print("\n[2/3] 获取真实K线数据...")
    stocks_data = {}
    
    # 选取一些热门股票获取真实K线
    sample_stocks = [
        ('600519', '贵州茅台'),
        ('000858', '五粮液'),
        ('300750', '宁德时代'),
        ('002594', '比亚迪'),
        ('601318', '中国平安'),
        ('600036', '招商银行'),
        ('000651', '格力电器'),
        ('000333', '美的集团'),
        ('300033', '同花顺'),
        ('002487', '大金重工'),
    ]
    
    success_count = 0
    fail_count = 0
    
    for code, name in sample_stocks:
        print(f"  获取 {code} {name}...")
        df_kline = collector.get_stock_kline(code, 
                                            start_date="2026-04-01", 
                                            end_date=TEST_DATE)
        
        if not df_kline.empty:
            stocks_data[code] = df_kline
            success_count += 1
            print(f"    ✓ 成功: {len(df_kline)} 条K线")
        else:
            fail_count += 1
            print(f"    ✗ 失败: 无法获取K线")
    
    print(f"\n  统计: 成功 {success_count} 只, 失败 {fail_count} 只")
    
    # 3. 生成真实数据报告
    print("\n[3/3] 生成真实数据报告...")
    generate_real_report(stocks_data, billboard_df, TEST_DATE)
    
    print("\n" + "="*70)
    print("✓ 测试完成！")
    print("="*70)


def generate_real_report(stocks_data, billboard_df, test_date):
    """生成真实数据报告"""
    
    report_path = os.path.join(
        os.path.dirname(__file__), 
        f"REAL_ONLY_TEST_REPORT_{test_date.replace('-', '')}.md"
    )
    
    report = []
    
    report.append("# 主线量化交易系统 V3 - 真实数据测试报告")
    report.append("")
    report.append(f"**测试日期**: {test_date}")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("> ⚠️ **重要说明**：本报告严格使用真实数据，不包含任何模拟数据")
    report.append("")
    
    # 1. 数据获取情况
    report.append("---")
    report.append("## 1. 数据获取情况")
    report.append("")
    
    report.append(f"- **成功获取K线数据的股票**: {len(stocks_data)} 只")
    report.append(f"- **龙虎榜数据**: {'有数据' if billboard_df is not None and not billboard_df.empty else '无数据'}")
    
    if stocks_data:
        report.append("")
        report.append("### 成功获取的股票K线:")
        report.append("")
        report.append("| 股票代码 | 股票名称 | K线数量 | 最新日期 | 最新收盘价 | 最新涨跌幅 |")
        report.append("|---------|---------|---------|---------|-----------|-----------|")
        
        stock_names = {
            '600519': '贵州茅台', '000858': '五粮液', '300750': '宁德时代',
            '002594': '比亚迪', '601318': '中国平安', '600036': '招商银行',
            '000651': '格力电器', '000333': '美的集团', '300033': '同花顺',
            '002487': '大金重工'
        }
        
        for code, df in stocks_data.items():
            if not df.empty:
                name = stock_names.get(code, code)
                kline_count = len(df)
                latest = df.iloc[-1]
                latest_date = latest.get('trade_date', 'N/A')
                close = latest.get('close', 0)
                change_pct = latest.get('change_pct', 0)
                report.append(f"| {code} | {name} | {kline_count} | {latest_date} | {close:.2f} | {change_pct:+.2f}% |")
    
    # 2. 龙虎榜数据
    if billboard_df is not None and not billboard_df.empty:
        report.append("")
        report.append("---")
        report.append("## 2. 龙虎榜真实数据")
        report.append("")
        report.append(f"- **数据条数**: {len(billboard_df)} 条")
        report.append("")
        
        # 显示列名
        report.append("### 数据字段:")
        report.append("")
        report.append(f"可用字段: {list(billboard_df.columns)}")
        report.append("")
        
        # 显示前20条数据
        report.append("### 龙虎榜数据（前20条）:")
        report.append("")
        
        # 选择关键列显示
        display_cols = ['trade_date', 'stock_code', 'stock_name', 'net_amount']
        available_cols = [col for col in display_cols if col in billboard_df.columns]
        
        if available_cols:
            report.append("| " + " | ".join(available_cols) + " |")
            report.append("|" + "|".join(["---"] * len(available_cols)) + "|")
            
            for _, row in billboard_df.head(20).iterrows():
                values = [str(row.get(col, 'N/A')) for col in available_cols]
                report.append("| " + " | ".join(values) + " |")
    else:
        report.append("")
        report.append("---")
        report.append("## 2. 龙虎榜数据")
        report.append("")
        report.append("⚠️ **无法获取龙虎榜真实数据**")
        report.append("")
        report.append("可能原因:")
        report.append("- 网络限制")
        report.append("- 5月15日可能不是交易日")
        report.append("- API访问限制")
    
    # 3. 真实K线分析
    if stocks_data:
        report.append("")
        report.append("---")
        report.append("## 3. 真实K线数据分析")
        report.append("")
        
        # 识别真实涨停股
        all_limit_up = []
        for stock_code, df in stocks_data.items():
            if not df.empty and 'change_pct' in df.columns:
                latest = df.iloc[-1]
                if latest['change_pct'] >= 9.5:  # 真实涨停（接近10%）
                    all_limit_up.append({
                        'stock_code': stock_code,
                        'change_pct': latest['change_pct'],
                        'close': latest['close']
                    })
        
        if all_limit_up:
            report.append(f"- **真实涨停股数量**: {len(all_limit_up)} 只")
            report.append("")
            report.append("### 真实涨停股票:")
            report.append("")
            report.append("| 股票代码 | 股票名称 | 涨跌幅 | 收盘价 |")
            report.append("|---------|---------|--------|--------|")
            
            stock_names = {
                '600519': '贵州茅台', '000858': '五粮液', '300750': '宁德时代',
                '002594': '比亚迪', '601318': '中国平安', '600036': '招商银行',
                '000651': '格力电器', '000333': '美的集团', '300033': '同花顺',
                '002487': '大金重工'
            }
            
            for stock in all_limit_up:
                name = stock_names.get(stock['stock_code'], stock['stock_code'])
                report.append(f"| {stock['stock_code']} | {name} | {stock['change_pct']:.2f}% | {stock['close']:.2f} |")
        else:
            report.append("- **真实涨停股数量**: 0 只")
            report.append("")
            report.append("说明: 这些股票在测试日期未达到涨停")
    
    # 4. 总结
    report.append("")
    report.append("---")
    report.append("## 4. 测试总结")
    report.append("")
    report.append("### 数据质量评估:")
    report.append("")
    
    if len(stocks_data) > 0:
        report.append("✓ K线数据: **真实数据**")
    else:
        report.append("✗ K线数据: 无数据")
    
    if billboard_df is not None and not billboard_df.empty:
        report.append("✓ 龙虎榜数据: **真实数据**")
    else:
        report.append("⚠ 龙虎榜数据: 无法获取")
    
    report.append("")
    report.append("### 诚实说明:")
    report.append("")
    report.append("- 本报告严格使用从API获取的真实数据")
    report.append("- 没有使用任何模拟涨停、连板或概念数据")
    report.append("- 如果数据显示未涨停，说明实际市场情况就是如此")
    report.append("- 数据获取可能受网络、API限制等因素影响")
    report.append("")
    report.append("### 文件位置:")
    report.append("")
    report.append("  - 测试程序: test_real_only.py")
    report.append("  - 数据采集器: data_engine/collector.py")
    report.append("  - 连板队列模块: strategy_engine/limit_up_queue.py")
    report.append("  - 龙虎榜分析: strategy_engine/billboard_analyzer.py")
    
    # 保存报告
    report_text = "\n".join(report)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print(f"\n✓ 报告已保存: {report_path}")
    print("\n" + "="*70)
    print(report_text)
    print("="*70)
    
    return report_path


if __name__ == '__main__':
    main()
