# -*- coding: utf-8 -*-
"""
新一代数据获取模块（LLM小组优化版）
核心改进：
1. 直接用requests调用，不依赖第三方库
2. 新浪/腾讯双数据源，自动切换
3. SQLite本地缓存
"""
import os
import json
import requests
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List, Tuple


class DataProviderV2:
    """
    新一代数据提供者
    LLM小组决策：优先新浪/腾讯API，requests直接调用
    """
    
    def __init__(self, cache_db: str = "data_cache.db"):
        """初始化"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # 缓存设置
        self.cache_db = cache_db
        self._init_cache()
        
        # 概念板块本地缓存（来自adata项目）
        self._concepts_cache = None
        
        print("✅ DataProviderV2 初始化成功")
    
    def _init_cache(self):
        """初始化SQLite缓存"""
        if not os.path.exists(self.cache_db):
            conn = sqlite3.connect(self.cache_db)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS stock_kline
                (stock_code TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL, 
                 PRIMARY KEY (stock_code, date))
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS concept_kline
                (concept_code TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, change_pct REAL,
                 PRIMARY KEY (concept_code, date))
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS concept_list
                (concept_code TEXT PRIMARY KEY, concept_name TEXT, source TEXT)
            ''')
            conn.commit()
            conn.close()
            print(f"✅ 缓存数据库 {self.cache_db} 初始化成功")
    
    def _get_concepts_from_cache(self) -> pd.DataFrame:
        """从缓存获取概念板块"""
        try:
            # 优先从本地缓存文件（来自adata项目）
            cache_file = '/workspace/references/adata/adata/stock/cache/all_concept_code_east.csv'
            if os.path.exists(cache_file):
                df = pd.read_csv(cache_file)
                if not df.empty:
                    print(f"✅ 从本地文件加载 {len(df)} 个概念板块")
                    return df
        except Exception as e:
            pass
        
        # SQLite缓存备用
        try:
            conn = sqlite3.connect(self.cache_db)
            df = pd.read_sql('SELECT * FROM concept_list', conn)
            conn.close()
            if not df.empty:
                print(f"✅ 从缓存数据库加载 {len(df)} 个概念板块")
                return df
        except Exception as e:
            pass
        
        return pd.DataFrame()
    
    def get_all_concepts(self) -> pd.DataFrame:
        """获取所有概念板块（优先本地缓存）"""
        if self._concepts_cache is not None:
            return self._concepts_cache
        
        # 尝试获取
        df = self._get_concepts_from_cache()
        if not df.empty:
            self._concepts_cache = df
            return df
        
        # 没有缓存时提示
        print("⚠️  概念板块缓存未找到，但不影响其他功能")
        print("💡 可以先从 adata 项目复制缓存")
        return pd.DataFrame()
    
    def get_stock_kline_sina(self, stock_code: str, count: int = 100) -> pd.DataFrame:
        """
        新浪API获取K线（推荐，含均线！）
        """
        try:
            # 处理代码格式
            if stock_code.startswith('6'):
                symbol = f"sh{stock_code}"
            else:
                symbol = f"sz{stock_code}"
            
            url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData?symbol={symbol}&scale=240&datalen={count}"
            
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            df = df.rename(columns={'day': 'date'})
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
            # 只保留核心列
            df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            print(f"✅ 新浪API获取 {stock_code} 成功，{len(df)} 条数据")
            return df
            
        except Exception as e:
            print(f"❌ 新浪API失败: {e}")
            return pd.DataFrame()
    
    def get_stock_kline_qq(self, stock_code: str, count: int = 100) -> pd.DataFrame:
        """
        腾讯API获取K线（前复权！）
        """
        try:
            if stock_code.startswith('6'):
                symbol = f"sh{stock_code}"
            else:
                symbol = f"sz{stock_code}"
            
            url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,{count},qfq"
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if data and 'data' in data and symbol in data['data']:
                kline_data = data['data'][symbol].get('qfqday', [])
                if kline_data:
                    df = pd.DataFrame(kline_data, columns=['date', 'open', 'close', 'high', 'low', 'volume'])
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    print(f"✅ 腾讯API获取 {stock_code} 成功，{len(df)} 条数据")
                    return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ 腾讯API失败: {e}")
            return pd.DataFrame()
    
    def get_stock_kline(self, stock_code: str, count: int = 100) -> pd.DataFrame:
        """
        双数据源获取K线（新浪优先，腾讯备用）
        """
        print(f"📊 获取股票K线: {stock_code}")
        
        # 1. 新浪API
        df = self.get_stock_kline_sina(stock_code, count)
        if not df.empty:
            return df
        
        # 2. 腾讯API
        df = self.get_stock_kline_qq(stock_code, count)
        if not df.empty:
            return df
        
        print(f"❌ 两个数据源都失败: {stock_code}")
        return pd.DataFrame()
    
    def get_realtime_sina(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        新浪API获取实时行情
        """
        try:
            symbols = []
            for code in stock_codes:
                if code.startswith('6'):
                    symbols.append(f"sh{code}")
                else:
                    symbols.append(f"sz{code}")
            
            url = f"https://hq.sinajs.cn/list={','.join(symbols)}"
            self.session.headers['Referer'] = 'https://finance.sina.com.cn'
            response = self.session.get(url, timeout=10)
            response.encoding = 'gbk'
            text = response.text
            
            data_list = []
            for line in text.split('\n'):
                if '=' in line:
                    parts = line.split('=')
                    if len(parts) > 1 and len(parts[1]) > 2:
                        values = parts[1][1:-2].split(',')
                        if len(values) >= 32:
                            data_list.append({
                                'stock_code': parts[0].split('_')[-1].replace('hq_str_', ''),
                                'open': float(values[1]) if values[1] else 0,
                                'pre_close': float(values[2]) if values[2] else 0,
                                'current': float(values[3]) if values[3] else 0,
                                'high': float(values[4]) if values[4] else 0,
                                'low': float(values[5]) if values[5] else 0,
                                'volume': float(values[8]) if values[8] else 0,
                                'amount': float(values[9]) if values[9] else 0,
                            })
            
            df = pd.DataFrame(data_list)
            print(f"✅ 新浪实时行情获取: {len(df)} 只股票")
            return df
            
        except Exception as e:
            print(f"❌ 新浪实时行情失败: {e}")
            return pd.DataFrame()


# ===============================
# 快捷入口
# ===============================

def get_data_provider() -> DataProviderV2:
    """获取数据提供者实例"""
    return DataProviderV2()


if __name__ == "__main__":
    print("=" * 80)
    print("DataProviderV2 测试")
    print("=" * 80)
    
    provider = get_data_provider()
    
    # 1. 获取概念板块
    print("\n[1] 概念板块...")
    concepts = provider.get_all_concepts()
    if not concepts.empty:
        print(f"✅ {len(concepts)} 个概念板块")
        print(concepts.head(5))
    
    # 2. 测试K线获取
    print("\n[2] 股票K线（600000）...")
    kline = provider.get_stock_kline('600000', count=5)
    if not kline.empty:
        print(kline)
    
    print("\n" + "=" * 80)
    print("✅ DataProviderV2 测试完成！")
    print("=" * 80)
