# -*- coding: utf-8 -*-
"""
连板队列识别模块
识别连续涨停、统计连板高度、判断龙头股
"""
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Tuple


def identify_limit_up_stocks(stock_data: pd.DataFrame, date: Optional[str] = None) -> List[Dict]:
    """
    识别指定日期的涨停股票
    
    参数:
        stock_data: K线数据，包含 trade_date, close, change_pct 等列
        date: 日期，格式 YYYY-MM-DD，默认为最新日期
    
    返回:
        涨停股票列表
    """
    if date is None:
        if len(stock_data) > 0:
            date = stock_data['trade_date'].max()
        else:
            return []
    
    # 筛选日期
    df_date = stock_data[stock_data['trade_date'] == date].copy()
    
    if df_date.empty:
        return []
    
    # 识别涨停：涨跌幅 >=9.8%
    limit_up_threshold = 9.8  # 主板
    limit_up_threshold_gem = 19.8  # 创业板/科创板
    
    # 判断每只股票是否涨停
    limit_up_stocks = []
    for _, row in df_date.iterrows():
        stock_code = row['stock_code']
        change_pct = row['change_pct']
        
        # 判断板块
        is_gem = stock_code.startswith('30') or stock_code.startswith('68')
        threshold = limit_up_threshold_gem if is_gem else limit_up_threshold
        
        if change_pct >= threshold:
            limit_up_stocks.append({
                'stock_code': stock_code,
                'trade_date': date,
                'close': row['close'],
                'change_pct': change_pct,
                'is_limit_up': True,
                'board': 'GEM' if is_gem else 'MAIN'
            })
    
    return limit_up_stocks


def calculate_consecutive_limit_ups(stock_kline: pd.DataFrame) -> Tuple[int, List[str]]:
    """
    计算单只股票的连板高度
    
    参数:
        stock_kline: 单只股票的K线数据
    
    返回:
        (连续涨停天数, 涨停日期列表)
    """
    if len(stock_kline) < 1:
        return 0, []
    
    # 按日期排序
    df_sorted = stock_kline.sort_values('trade_date', ascending=False).copy()
    
    consecutive_count = 0
    limit_up_dates = []
    
    # 从最新日期向前遍历
    for _, row in df_sorted.iterrows():
        stock_code = row['stock_code']
        change_pct = row['change_pct']
        
        # 判断板块
        is_gem = stock_code.startswith('30') or stock_code.startswith('68')
        threshold = 19.8 if is_gem else 9.8
        
        if change_pct >= threshold:
            consecutive_count += 1
            limit_up_dates.append(row['trade_date'])
        else:
            break
    
    return consecutive_count, limit_up_dates


def build_limit_up_queue(stocks_data: Dict[str, pd.DataFrame], date: Optional[str] = None) -> pd.DataFrame:
    """
    构建连板队列
    
    参数:
        stocks_data: 股票数据字典，key是股票代码，value是K线DataFrame
        date: 日期
    
    返回:
        连板队列DataFrame
    """
    queue_data = []
    
    for stock_code, kline_df in stocks_data.items():
        # 计算连板高度
        con_count, limit_up_dates = calculate_consecutive_limit_ups(kline_df)
        
        if con_count > 0:
            # 获取最新日期的涨停信息
            if len(kline_df) > 0:
                latest_row = kline_df.iloc[0]
                queue_data.append({
                    'stock_code': stock_code,
                    'short_name': latest_row.get('short_name', stock_code),
                    'consecutive_days': con_count,
                    'limit_up_dates': limit_up_dates,
                    'close': latest_row.get('close', 0),
                    'change_pct': latest_row.get('change_pct', 0),
                    'is_leader': con_count >= 3
                })
    
    # 按连板高度排序
    queue_df = pd.DataFrame(queue_data)
    if not queue_df.empty:
        queue_df = queue_df.sort_values(
            ['consecutive_days', 'change_pct'],
            ascending=[False, False]
        ).reset_index(drop=True)
    
    return queue_df


def identify_leader_stocks(limit_up_queue: pd.DataFrame, leader_threshold: int = 3) -> List[Dict]:
    """
    识别龙头股
    
    参数:
        limit_up_queue: 连板队列
        leader_threshold: 龙头阈值，默认3板
    
    返回:
        龙头股列表
    """
    if limit_up_queue.empty:
        return []
    
    # 筛选连板高度>=threshold的股票
    leader_df = limit_up_queue[limit_up_queue['consecutive_days'] >= leader_threshold]
    
    return leader_df.to_dict('records')


def analyze_limit_up_pattern(stock_kline: pd.DataFrame) -> Dict:
    """
    分析涨停股的走势模式
    
    参数:
        stock_kline: 股票K线
    
    返回:
        分析结果
    """
    if len(stock_kline) < 5:
        return {'status': 'insufficient_data'}
    
    # 计算连板
    con_count, _ = calculate_consecutive_limit_ups(stock_kline)
    
    # 计算成交量变化
    recent_volume = stock_kline['volume'].tail(5)
    avg_volume = recent_volume.mean()
    latest_volume = recent_volume.iloc[-1]
    volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 1
    
    return {
        'consecutive_days': con_count,
        'volume_ratio': volume_ratio,
        'avg_volume': avg_volume,
        'latest_volume': latest_volume,
        'status': 'normal'
    }


if __name__ == '__main__':
    print("连板队列识别模块加载成功！")
