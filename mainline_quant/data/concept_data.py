# -*- coding: utf-8 -*-
"""
概念板块数据模块（LLM小组增强版）
基于东方财富API实现
功能：
1. 获取所有概念板块列表
2. 获取概念板块K线
3. 获取概念板块成分股
4. 获取概念板块实时行情和统计
"""
import os
import sqlite3
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict


class ConceptData:
    """
    概念板块数据提供者
    """
    
    def __init__(self, cache_db: str = "concept_cache.db"):
        """初始化"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        self.cache_db = cache_db
        self._init_cache()
        self._concepts_cache = None
        
        print("✅ ConceptData 初始化成功")
    
    def _init_cache(self):
        """初始化SQLite缓存"""
        if not os.path.exists(self.cache_db):
            conn = sqlite3.connect(self.cache_db)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS concept_list
                (concept_code TEXT PRIMARY KEY, concept_name TEXT, source TEXT)
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS concept_kline
                (concept_code TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, 
                 volume REAL, amount REAL, change REAL, change_pct REAL,
                 PRIMARY KEY (concept_code, date))
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS concept_constituent
                (concept_code TEXT, stock_code TEXT, stock_name TEXT,
                 PRIMARY KEY (concept_code, stock_code))
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS concept_realtime
                (concept_code TEXT, date TEXT, time TEXT, price REAL, change REAL, change_pct REAL,
                 volume REAL, amount REAL, up_count INTEGER, down_count INTEGER, 
                 limit_up_count INTEGER, limit_down_count INTEGER,
                 PRIMARY KEY (concept_code, date, time))
            ''')
            conn.commit()
            conn.close()
            print(f"✅ 概念板块缓存数据库 {self.cache_db} 初始化成功")
    
    def get_all_concepts(self, use_cache: bool = True) -> pd.DataFrame:
        """
        获取所有概念板块列表
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            DataFrame: 概念板块列表
        """
        if use_cache and self._concepts_cache is not None:
            return self._concepts_cache
        
        # 1. 先尝试从缓存数据库
        if use_cache:
            try:
                conn = sqlite3.connect(self.cache_db)
                df = pd.read_sql('SELECT * FROM concept_list', conn)
                conn.close()
                if not df.empty:
                    print(f"✅ 从缓存加载 {len(df)} 个概念板块")
                    self._concepts_cache = df
                    return df
            except Exception as e:
                pass
        
        # 2. 尝试从adata的缓存文件
        cache_file = '/workspace/references/adata/adata/stock/info/cache/all_concept_code_east.csv'
        if os.path.exists(cache_file):
            try:
                df = pd.read_csv(cache_file)
                if not df.empty:
                    print(f"✅ 从文件加载 {len(df)} 个概念板块")
                    # 保存到缓存数据库
                    conn = sqlite3.connect(self.cache_db)
                    df.to_sql('concept_list', conn, if_exists='replace', index=False)
                    conn.close()
                    self._concepts_cache = df
                    return df
            except Exception as e:
                print(f"⚠️  文件加载失败: {e}")
        
        # 3. 从东方财富API获取
        print("🌐 从东方财富API获取概念板块列表...")
        try:
            curr_page = 1
            page_size = 100
            data = []
            
            while curr_page < 50:
                url = (f"https://push2.eastmoney.com/api/qt/clist/get"
                      f"?pn={curr_page}&pz={page_size}&po=1&np=1"
                      f"&fields=f12,f13,f14,f62&fid=f62&fs=m:90+t:3")
                
                response = self.session.get(url, timeout=10)
                res_json = response.json()
                
                if not res_json or 'data' not in res_json or 'diff' not in res_json['data']:
                    break
                
                res_data = res_json['data']['diff']
                if not res_data:
                    break
                
                for item in res_data:
                    data.append({
                        'concept_code': item['f12'],
                        'concept_name': item['f14'],
                        'source': '东方财富'
                    })
                
                if len(res_data) < page_size:
                    break
                
                curr_page += 1
            
            if data:
                df = pd.DataFrame(data)
                # 保存到缓存
                conn = sqlite3.connect(self.cache_db)
                df.to_sql('concept_list', conn, if_exists='replace', index=False)
                conn.close()
                
                print(f"✅ 从API获取 {len(df)} 个概念板块")
                self._concepts_cache = df
                return df
            
        except Exception as e:
            print(f"❌ API获取失败: {e}")
        
        return pd.DataFrame()
    
    def get_concept_kline(self, concept_code: str, count: int = 100, 
                         use_cache: bool = True) -> pd.DataFrame:
        """
        获取概念板块K线
        
        Args:
            concept_code: 概念代码（BK开头）
            count: K线数量
            use_cache: 是否使用缓存
            
        Returns:
            DataFrame: K线数据
        """
        # 1. 尝试从缓存获取
        if use_cache:
            try:
                conn = sqlite3.connect(self.cache_db)
                df = pd.read_sql(
                    f'SELECT * FROM concept_kline WHERE concept_code = "{concept_code}" '
                    f'ORDER BY date DESC LIMIT {count}',
                    conn
                )
                conn.close()
                if not df.empty:
                    df = df.sort_values('date').reset_index(drop=True)
                    print(f"✅ 从缓存加载 {concept_code} K线，{len(df)} 条")
                    return df
            except Exception as e:
                pass
        
        # 2. 从东方财富API获取
        print(f"🌐 从API获取 {concept_code} K线...")
        try:
            url = (f"https://push2his.eastmoney.com/api/qt/stock/kline/get?"
                  f"secid=90.{concept_code}&"
                  f"fields1=f1,f2,f3,f4,f5,f6&"
                  f"fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&"
                  f"klt=101&fqt=1&end=20500101&lmt={count}")
            
            response = self.session.get(url, timeout=10)
            res_json = response.json()
            
            if not res_json or 'data' not in res_json or 'klines' not in res_json['data']:
                return pd.DataFrame()
            
            klines = res_json['data']['klines']
            data = []
            
            for kline in klines:
                parts = kline.split(',')
                if len(parts) >= 11:
                    data.append({
                        'concept_code': concept_code,
                        'date': parts[0],
                        'open': float(parts[1]),
                        'close': float(parts[2]),
                        'high': float(parts[3]),
                        'low': float(parts[4]),
                        'volume': float(parts[5]),
                        'amount': float(parts[6]),
                        'change': float(parts[9]),
                        'change_pct': float(parts[8])
                    })
            
            if data:
                df = pd.DataFrame(data)
                df = df.sort_values('date').reset_index(drop=True)
                
                # 保存到缓存
                conn = sqlite3.connect(self.cache_db)
                for _, row in df.iterrows():
                    try:
                        conn.execute('''
                            INSERT OR REPLACE INTO concept_kline 
                            (concept_code, date, open, high, low, close, volume, amount, change, change_pct)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            row['concept_code'], row['date'], row['open'], row['high'],
                            row['low'], row['close'], row['volume'], row['amount'],
                            row['change'], row['change_pct']
                        ))
                    except Exception as e:
                        pass
                conn.commit()
                conn.close()
                
                print(f"✅ 获取 {concept_code} K线成功，{len(df)} 条")
                return df
            
        except Exception as e:
            print(f"❌ 获取 {concept_code} K线失败: {e}")
        
        return pd.DataFrame()
    
    def get_concept_constituent(self, concept_code: str, 
                               use_cache: bool = True) -> pd.DataFrame:
        """
        获取概念板块成分股
        
        Args:
            concept_code: 概念代码（BK开头）
            use_cache: 是否使用缓存
            
        Returns:
            DataFrame: 成分股列表
        """
        # 1. 尝试从缓存获取
        if use_cache:
            try:
                conn = sqlite3.connect(self.cache_db)
                df = pd.read_sql(
                    f'SELECT * FROM concept_constituent WHERE concept_code = "{concept_code}"',
                    conn
                )
                conn.close()
                if not df.empty:
                    print(f"✅ 从缓存加载 {concept_code} 成分股，{len(df)} 只")
                    return df
            except Exception as e:
                pass
        
        # 2. 从东方财富API获取
        print(f"🌐 从API获取 {concept_code} 成分股...")
        try:
            curr_page = 1
            page_size = 200
            data = []
            
            while curr_page < 100:
                url = (f"https://push2.eastmoney.com/api/qt/clist/get?"
                      f"fid=f62&po=1&pz={page_size}&pn={curr_page}&np=1&"
                      f"fltt=2&invt=2&fs=b:{concept_code}&fields=f12,f14")
                
                response = self.session.get(url, timeout=10)
                res_json = response.json()
                
                if not res_json or 'data' not in res_json or 'diff' not in res_json['data']:
                    break
                
                res_data = res_json['data']['diff']
                if not res_data:
                    break
                
                for item in res_data:
                    data.append({
                        'concept_code': concept_code,
                        'stock_code': item['f12'],
                        'stock_name': item['f14']
                    })
                
                curr_page += 1
            
            if data:
                df = pd.DataFrame(data)
                
                # 保存到缓存
                conn = sqlite3.connect(self.cache_db)
                for _, row in df.iterrows():
                    try:
                        conn.execute('''
                            INSERT OR REPLACE INTO concept_constituent 
                            (concept_code, stock_code, stock_name)
                            VALUES (?, ?, ?)
                        ''', (row['concept_code'], row['stock_code'], row['stock_name']))
                    except Exception as e:
                        pass
                conn.commit()
                conn.close()
                
                print(f"✅ 获取 {concept_code} 成分股成功，{len(df)} 只")
                return df
            
        except Exception as e:
            print(f"❌ 获取 {concept_code} 成分股失败: {e}")
        
        return pd.DataFrame()
    
    def get_concept_realtime(self, concept_code: str) -> Optional[Dict]:
        """
        获取概念板块实时行情（简化版）
        
        Args:
            concept_code: 概念代码（BK开头）
            
        Returns:
            Dict: 实时行情数据
        """
        try:
            url = (f"https://push2.eastmoney.com/api/qt/stock/get?"
                  f"secid=90.{concept_code}&"
                  f"fields=f57,f58,f106,f59,f43,f46,f60,f44,f45,f47,f48,f49")
            
            response = self.session.get(url, timeout=10)
            res_json = response.json()
            
            if not res_json or 'data' not in res_json:
                return None
            
            data = res_json['data']
            pre_close = data.get('f60', 0)
            price = data.get('f43', 0)
            change = price - pre_close if pre_close else 0
            change_pct = (change / pre_close * 100) if pre_close else 0
            
            result = {
                'concept_code': concept_code,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'time': datetime.now().strftime('%H:%M:%S'),
                'open': data.get('f46', 0),
                'high': data.get('f44', 0),
                'low': data.get('f45', 0),
                'price': price,
                'pre_close': pre_close,
                'change': change,
                'change_pct': change_pct,
                'volume': data.get('f47', 0),
                'amount': data.get('f48', 0)
            }
            
            print(f"✅ 获取 {concept_code} 实时行情: {change_pct:+.2f}%")
            return result
            
        except Exception as e:
            print(f"❌ 获取 {concept_code} 实时行情失败: {e}")
            return None
    
    def get_all_concepts_realtime(self, concept_codes: List[str]) -> pd.DataFrame:
        """
        批量获取概念板块实时行情
        
        Args:
            concept_codes: 概念代码列表
            
        Returns:
            DataFrame: 实时行情数据
        """
        data_list = []
        for code in concept_codes:
            data = self.get_concept_realtime(code)
            if data:
                data_list.append(data)
        
        if data_list:
            return pd.DataFrame(data_list)
        
        return pd.DataFrame()
    
    def calculate_concept_stats(self, concept_code: str, 
                               stock_data_provider) -> Optional[Dict]:
        """
        计算概念板块统计数据（需要股票数据支持）
        
        Args:
            concept_code: 概念代码
            stock_data_provider: 股票数据提供者
            
        Returns:
            Dict: 统计数据
        """
        constituents = self.get_concept_constituent(concept_code)
        if constituents.empty:
            return None
        
        stock_codes = constituents['stock_code'].tolist()
        realtime_data = stock_data_provider.get_realtime_sina(stock_codes)
        
        if realtime_data.empty:
            return None
        
        total = len(realtime_data)
        up_count = len(realtime_data[realtime_data['current'] > realtime_data['pre_close']])
        down_count = len(realtime_data[realtime_data['current'] < realtime_data['pre_close']])
        
        # 简单估算涨停跌停（需要更精确的涨跌幅数据）
        limit_up_count = 0
        limit_down_count = 0
        
        result = {
            'concept_code': concept_code,
            'total_count': total,
            'up_count': up_count,
            'down_count': down_count,
            'limit_up_count': limit_up_count,
            'limit_down_count': limit_down_count,
            'up_down_ratio': up_count / down_count if down_count > 0 else up_count
        }
        
        return result


# ===============================
# 快捷入口
# ===============================

def get_concept_data() -> ConceptData:
    """获取概念板块数据提供者实例"""
    return ConceptData()


if __name__ == "__main__":
    print("=" * 80)
    print("ConceptData 测试")
    print("=" * 80)
    
    concept_data = get_concept_data()
    
    # 1. 获取概念板块列表
    print("\n[1] 概念板块列表...")
    concepts = concept_data.get_all_concepts()
    if not concepts.empty:
        print(f"✅ {len(concepts)} 个概念板块")
        print(concepts.head(10))
    
    # 2. 测试获取K线
    if not concepts.empty:
        sample_code = concepts.iloc[0]['concept_code']
        sample_name = concepts.iloc[0]['concept_name']
        print(f"\n[2] 概念板块K线: {sample_name} ({sample_code})...")
        kline = concept_data.get_concept_kline(sample_code, count=10)
        if not kline.empty:
            print(kline)
    
    # 3. 测试获取成分股
    if not concepts.empty:
        sample_code = concepts.iloc[0]['concept_code']
        sample_name = concepts.iloc[0]['concept_name']
        print(f"\n[3] 概念板块成分股: {sample_name} ({sample_code})...")
        constituent = concept_data.get_concept_constituent(sample_code)
        if not constituent.empty:
            print(f"✅ {len(constituent)} 只成分股")
            print(constituent.head(10))
    
    print("\n" + "=" * 80)
    print("✅ ConceptData 测试完成！")
    print("=" * 80)

