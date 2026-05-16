# -*- coding: utf-8 -*-
"""
龙虎榜分析模块
获取和分析龙虎榜数据、识别游资席位、分析龙虎榜上榜后次日表现
"""
import pandas as pd
import requests
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional


def _setup_proxy():
    os.environ['HTTP_PROXY'] = 'http://127.0.0.1:18080'
    os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:18080'


def _clear_proxy():
    for key in list(os.environ.keys()):
        if key.lower().endswith('proxy'):
            del os.environ[key]


def get_billboard_data(date: Optional[str] = None, page: int = 1, page_size: int = 100) -> pd.DataFrame:
    """
    获取指定日期的龙虎榜数据
    
    参数:
        date: 日期，格式 YYYY-MM-DD
        page: 页码
        page_size: 每页条数
    
    返回:
        龙虎榜数据
    """
    _setup_proxy()
    
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        start_date_str = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
        
        params = {
            "sortColumns": "TRADE_DATE,SECURITY_CODE",
            "sortTypes": "-1,-1",
            "pageSize": page_size,
            "pageNumber": page,
            "reportName": "RPT_DRAGON_LIST",
            "columns": "ALL",
            "filter": f'(TRADE_DATE>="{start_date_str}")(TRADE_DATE<="{date}")',
        }
        
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            return pd.DataFrame()
        
        res = resp.json()
        if res.get('result') is None:
            return pd.DataFrame()
        
        data = res['result'].get('data', [])
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        rename = {
            "TRADE_DATE": "trade_date",
            "SECURITY_CODE": "stock_code",
            "SECURITY_NAME_ABBR": "stock_name",
            "CLOSE_PRICE": "close_price",
            "CHANGE_RATE": "change_pct",
            "TURNOVER_RATE": "turnover_rate",
            "BUYER_NAME": "buyer_name",
            "SELLER_NAME": "seller_name",
            "NET_AMOUNT": "net_amount",
            "EXPLANATION": "explanation",
            "BUY_AMOUNT": "buy_amount",
            "SELL_AMOUNT": "sell_amount",
        }
        df = df.rename(columns=rename)
        
        for col in ["close_price", "change_pct", "net_amount", "buy_amount", "sell_amount"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        return df
    
    except Exception as e:
        print(f"获取龙虎榜失败: {e}")
        return pd.DataFrame()


def analyze_billboard_stock(billboard_df: pd.DataFrame, stock_code: str) -> Dict:
    """
    分析单只股票的龙虎榜数据
    
    参数:
        billboard_df: 龙虎榜数据
        stock_code: 股票代码
    
    返回:
        分析结果
    """
    if billboard_df.empty:
        return {'status': 'no_data'}
    
    stock_data = billboard_df[billboard_df['stock_code'] == stock_code]
    
    if stock_data.empty:
        return {'status': 'not_on_list'}
    
    # 分析买方席位
    buyer_stats = []
    for _, row in stock_data.iterrows():
        buyer_name = row.get('buyer_name', '')
        if buyer_name:
            buyer_stats.append({
                'buyer_name': buyer_name,
                'buy_amount': row.get('buy_amount', 0),
                'net_amount': row.get('net_amount', 0)
            })
    
    return {
        'stock_code': stock_code,
        'stock_name': stock_data['stock_name'].iloc[0] if len(stock_data) > 0 else '',
        'on_list_count': len(stock_data),
        'total_net_amount': stock_data['net_amount'].sum(),
        'buyer_stats': buyer_stats,
        'status': 'success'
    }


def identify_institutional_buyers(billboard_df: pd.DataFrame) -> List[Dict]:
    """
    识别机构专用席位
    
    参数:
        billboard_df: 龙虎榜数据
    
    返回:
        机构买入列表
    """
    institutional_keywords = ['机构专用', '机构', 'QFII']
    
    institutional_buys = []
    
    for _, row in billboard_df.iterrows():
        buyer_name = row.get('buyer_name', '')
        if any(keyword in buyer_name for keyword in institutional_keywords):
            institutional_buys.append({
                'stock_code': row['stock_code'],
                'stock_name': row.get('stock_name', ''),
                'buyer_name': buyer_name,
                'buy_amount': row.get('buy_amount', 0),
                'net_amount': row.get('net_amount', 0),
                'is_institutional': True
            })
    
    return institutional_buys


def analyze_next_day_performance(billboard_date: str, stock_kline: pd.DataFrame, stock_code: str) -> Dict:
    """
    分析龙虎榜上榜后的次日表现
    
    参数:
        billboard_date: 上榜日期
        stock_kline: 股票K线数据
        stock_code: 股票代码
    
    返回:
        次日表现分析
    """
    if len(stock_kline) < 2:
        return {'status': 'insufficient_data'}
    
    # 找到上榜日期的位置
    stock_kline_sorted = stock_kline.sort_values('trade_date', ascending=True).copy()
    
    try:
        billboard_idx = stock_kline_sorted[stock_kline_sorted['trade_date'] == billboard_date].index
        if len(billboard_idx) == 0:
            return {'status': 'date_not_found'}
        
        billboard_idx = billboard_idx[0]
        
        if billboard_idx + 1 < len(stock_kline_sorted):
            next_day_row = stock_kline_sorted.iloc[billboard_idx + 1]
            
            return {
                'status': 'success',
                'billboard_date': billboard_date,
                'next_date': next_day_row['trade_date'],
                'next_open': next_day_row['open'],
                'next_close': next_day_row['close'],
                'next_change_pct': next_day_row['change_pct'],
                'billboard_close': stock_kline_sorted.iloc[billboard_idx]['close']
            }
        else:
            return {'status': 'no_next_day_data'}
    
    except Exception as e:
        print(f"分析次日表现失败: {e}")
        return {'status': 'error', 'error': str(e)}


def get_hot_stocks_from_billboard(billboard_df: pd.DataFrame, top_n: int = 10) -> List[Dict]:
    """
    从龙虎榜中提取热门股
    
    参数:
        billboard_df: 龙虎榜数据
        top_n: 返回前n只
    
    返回:
        热门股列表
    """
    if billboard_df.empty:
        return []
    
    # 按股票代码分组统计
    grouped = billboard_df.groupby('stock_code').agg({
        'stock_name': 'first',
        'net_amount': 'sum',
        'close_price': 'first',
        'change_pct': 'first'
    }).reset_index()
    
    # 按净买入排序
    grouped_sorted = grouped.sort_values('net_amount', ascending=False).head(top_n)
    
    return grouped_sorted.to_dict('records')


if __name__ == '__main__':
    print("龙虎榜分析模块加载成功！")
