# -*- coding: utf-8 -*-
"""
数据获取模块
整合多个数据源，确保数据稳定性
"""
import json
import requests
import datetime
import pandas as pd
from typing import Optional, Dict, List


class DataFetcher:
    """
    主数据获取器
    整合多个数据源，自动故障切换
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _request(self, url: str, params: Optional[Dict] = None, timeout: int = 10) -> Optional[Dict]:
        """发送HTTP请求"""
        try:
            response = self.session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"请求失败: {e}")
            return None
    
    # ========== 概念板块数据 ==========
    
    def get_all_concepts(self) -> pd.DataFrame:
        """
        获取所有概念板块列表（东方财富数据源）
        :return: DataFrame [index_code, name]
        """
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': 1,
                'pz': 500,
                'po': 1,
                'np': 1,
                'fields': 'f12,f13,f14,f62',
                'fid': 'f62',
                'fs': 'm:90+t:3'
            }
            res_json = self._request(url, params)
            if res_json and 'data' in res_json and 'diff' in res_json['data']:
                data = []
                for item in res_json['data']['diff']:
                    data.append({
                        'concept_code': item['f12'],
                        'concept_name': item['f14'],
                        'source': '东方财富'
                    })
                return pd.DataFrame(data)
        except Exception as e:
            print(f"获取概念板块列表失败: {e}")
        return pd.DataFrame()
    
    def get_concept_market(self, concept_code: str, days: int = 30) -> pd.DataFrame:
        """
        获取概念板块K线行情
        :param concept_code: 概念板块代码 (BK开头)
        :param days: 获取天数
        :return: DataFrame
        """
        try:
            url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            params = {
                'secid': f'90.{concept_code}',
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                'klt': 101,
                'fqt': 1,
                'end': '20500101',
                'lmt': days
            }
            res_json = self._request(url, params)
            if res_json and 'data' in res_json and 'klines' in res_json['data']:
                data = []
                for kline in res_json['data']['klines']:
                    row = kline.split(',')
                    data.append({
                        'trade_date': row[0],
                        'open': float(row[1]),
                        'close': float(row[2]),
                        'high': float(row[3]),
                        'low': float(row[4]),
                        'volume': float(row[5]),
                        'amount': float(row[6]),
                        'change_pct': float(row[8])
                    })
                df = pd.DataFrame(data)
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                return df.sort_values('trade_date').reset_index(drop=True)
        except Exception as e:
            print(f"获取概念板块行情失败: {e}")
        return pd.DataFrame()
    
    def get_concept_constituents(self, concept_code: str) -> pd.DataFrame:
        """
        获取概念板块成分股
        :param concept_code: 概念板块代码
        :return: DataFrame [stock_code, short_name]
        """
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'fid': 'f62',
                'po': 1,
                'pz': 500,
                'pn': 1,
                'np': 1,
                'fltt': 2,
                'invt': 2,
                'fs': f'b:{concept_code}',
                'fields': 'f12,f14,f3,f12,f13'
            }
            res_json = self._request(url, params)
            if res_json and 'data' in res_json and 'diff' in res_json['data']:
                data = []
                for item in res_json['data']['diff']:
                    data.append({
                        'stock_code': item['f12'],
                        'short_name': item['f14'],
                        'change_pct': item.get('f3', 0)
                    })
                return pd.DataFrame(data)
        except Exception as e:
            print(f"获取概念成分股失败: {e}")
        return pd.DataFrame()
    
    # ========== 股票行情数据 ==========
    
    def get_stock_price(self, stock_code: str, frequency: str = '1d', count: int = 100) -> pd.DataFrame:
        """
        获取股票K线数据（新浪数据源）
        :param stock_code: 股票代码
        :param frequency: K线周期 '1d','1w','1M','5m','15m','30m','60m'
        :param count: 获取数量
        :return: DataFrame
        """
        # 处理股票代码格式
        code = stock_code.replace('.SH', '').replace('.SZ', '')
        if code.startswith('6'):
            xcode = f'sh{code}'
        else:
            xcode = f'sz{code}'
        
        # 转换周期
        freq_map = {
            '1d': '240m',
            '1w': '1200m',
            '1M': '7200m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '60m': '60m'
        }
        freq = freq_map.get(frequency, '240m')
        ts = int(freq[:-1])
        
        try:
            url = "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
            params = {
                'symbol': xcode,
                'scale': ts,
                'ma': 5,
                'datalen': count
            }
            res = self.session.get(url, params=params, timeout=10)
            dstr = res.text
            dstr = dstr.replace('day', '"day"').replace('open', '"open"')
            dstr = dstr.replace('high', '"high"').replace('low', '"low"')
            dstr = dstr.replace('close', '"close"').replace('volume', '"volume"')
            data = json.loads(dstr)
            
            df = pd.DataFrame(data)
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            if 'day' in df.columns:
                df['trade_date'] = pd.to_datetime(df['day'])
                df = df.drop('day', axis=1)
            else:
                df['trade_date'] = pd.to_datetime(df.index)
            
            return df.sort_values('trade_date').reset_index(drop=True)
        except Exception as e:
            print(f"获取股票行情失败: {e}")
            # 失败后尝试腾讯数据源
            return self._get_stock_price_tx(stock_code, frequency, count)
    
    def _get_stock_price_tx(self, stock_code: str, frequency: str = '1d', count: int = 100) -> pd.DataFrame:
        """腾讯数据源备用"""
        code = stock_code.replace('.SH', '').replace('.SZ', '')
        if code.startswith('6'):
            xcode = f'sh{code}'
        else:
            xcode = f'sz{code}'
        
        try:
            if frequency in ['1d', '1w', '1M']:
                unit = 'week' if frequency == '1w' else 'month' if frequency == '1M' else 'day'
                url = f'http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={xcode},{unit},,{count},qfq'
                res = self.session.get(url, timeout=10)
                st = res.json()
                stk = st['data'][xcode]
                buf = stk.get('qfq' + unit, stk.get(unit, []))
                df = pd.DataFrame(buf, columns=['time', 'open', 'close', 'high', 'low', 'volume'])
                df['trade_date'] = pd.to_datetime(df['time'])
                df = df.drop('time', axis=1)
            else:
                ts = int(frequency[:-1])
                url = f'http://ifzq.gtimg.cn/appstock/app/kline/mkline?param={xcode},m{ts},,{count}'
                res = self.session.get(url, timeout=10)
                st = res.json()
                buf = st['data'][xcode]['m' + str(ts)]
                df = pd.DataFrame(buf, columns=['time', 'open', 'close', 'high', 'low', 'volume', 'n1', 'n2'])
                df = df[['time', 'open', 'close', 'high', 'low', 'volume']]
                df['trade_date'] = pd.to_datetime(df['time'])
                df = df.drop('time', axis=1)
            
            df[['open', 'close', 'high', 'low', 'volume']] = df[['open', 'close', 'high', 'low', 'volume']].astype(float)
            return df.sort_values('trade_date').reset_index(drop=True)
        except Exception as e:
            print(f"腾讯数据源也失败: {e}")
        return pd.DataFrame()
    
    # ========== 实时行情数据 ==========
    
    def get_stock_realtime(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        获取股票实时行情（腾讯数据源）
        :param stock_codes: 股票代码列表
        :return: DataFrame
        """
        try:
            codes = []
            for code in stock_codes:
                c = code.replace('.SH', '').replace('.SZ', '')
                if c.startswith('6'):
                    codes.append(f'sh{c}')
                else:
                    codes.append(f'sz{c}')
            
            url = f"http://qt.gtimg.cn/q={','.join(codes)}"
            res = self.session.get(url, timeout=10)
            res.encoding = 'gbk'
            text = res.text
            
            data = []
            for line in text.split(';'):
                if '=' in line:
                    name_part, value_part = line.split('=', 1)
                    if len(value_part) > 2:
                        values = value_part[1:-1].split('~')
                        if len(values) >= 32:
                            data.append({
                                'stock_code': values[2],
                                'short_name': values[1],
                                'open': float(values[5]),
                                'close': float(values[3]),
                                'high': float(values[33]),
                                'low': float(values[34]),
                                'price': float(values[3]),
                                'volume': float(values[6]),
                                'amount': float(values[37]),
                                'change_pct': float(values[32]) if values[32] else 0
                            })
            return pd.DataFrame(data)
        except Exception as e:
            print(f"获取实时行情失败: {e}")
        return pd.DataFrame()
    
    # ========== 北向资金数据 ==========
    
    def get_north_flow(self) -> pd.DataFrame:
        """
        获取北向资金实时数据
        :return: DataFrame
        """
        try:
            url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            params = {
                'secid': '1.000001',
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                'klt': 101,
                'fqt': 1,
                'end': '20500101',
                'lmt': 30
            }
            res_json = self._request(url, params)
            # 简化实现，实际可从东方财富专题接口获取
            return pd.DataFrame()
        except Exception as e:
            print(f"获取北向资金失败: {e}")
        return pd.DataFrame()
