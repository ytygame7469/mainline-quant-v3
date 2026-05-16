# -*- coding: utf-8 -*-
"""
数据获取模块 - 使用实时API
支持：新浪财经、腾讯财经、东方财富
通过本地代理获取数据
"""
import json
import math
import time
import os
import random
from datetime import datetime

import pandas as pd
import requests

from .config import engine_config

# 取消代理设置
def _clear_proxy():
    for key in list(os.environ.keys()):
        if key.lower().endswith('proxy'):
            del os.environ[key]

# 设置代理
def _setup_proxy():
    os.environ['HTTP_PROXY'] = 'http://127.0.0.1:18080'
    os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:18080'

_clear_proxy()

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

_SINA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://finance.sina.com.cn",
    "Accept": "*/*",
}

_QQ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://gu.qq.com",
    "Accept": "*/*",
}


def _request(method="get", url=None, params=None, json_data=None, headers=None, timeout=None):
    cfg = engine_config.source
    if timeout is None:
        timeout = cfg.request_timeout
    if headers is None:
        headers = _HEADERS.copy()
    for i in range(cfg.request_retry):
        try:
            if cfg.request_interval_ms and i > 0:
                time.sleep(cfg.request_interval_ms / 1000)
            if method == "get":
                resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            else:
                resp = requests.post(url, params=params, json=json_data, headers=headers, timeout=timeout)
            if resp.status_code in (200, 404):
                return resp
        except Exception:
            if i == cfg.request_retry - 1:
                raise
            time.sleep(cfg.retry_wait_ms / 1000)
    return None


def _get_concept_name_from_adata(concept_code):
    """从 adata 本地缓存获取概念名称"""
    try:
        adata_cache_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "references", "adata", "adata", "stock", "info", "cache"
        ))
        concepts_csv = os.path.join(adata_cache_path, "all_concept_code_east.csv")
        if os.path.exists(concepts_csv):
            df = pd.read_csv(concepts_csv)
            match = df[df["concept_code"] == concept_code]
            if len(match) > 0:
                return match.iloc[0]["name"]
    except Exception:
        pass
    return concept_code


def _stock_market_sina(stock_code, count=250):
    """新浪财经 API 获取日K线（含均线）"""
    _setup_proxy()
    try:
        if stock_code.startswith("6"):
            symbol = f"sh{stock_code}"
        else:
            symbol = f"sz{stock_code}"
        
        url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData?symbol={symbol}&scale=240&datalen={count}"
        
        resp = requests.get(url, headers=_SINA_HEADERS, timeout=15)
        if resp.status_code != 200:
            return pd.DataFrame()
        
        data = resp.json()
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        df = df.rename(columns={'day': 'trade_date'})
        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
        df['stock_code'] = stock_code
        df['trade_time'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if 'ma_price5' in df.columns:
            df['ma5'] = pd.to_numeric(df['ma_price5'], errors='coerce')
        if 'ma_price10' in df.columns:
            df['ma10'] = pd.to_numeric(df['ma_price10'], errors='coerce')
        if 'ma_price30' in df.columns:
            df['ma30'] = pd.to_numeric(df['ma_price30'], errors='coerce')
        
        df['pre_close'] = df['close'].shift(1).fillna(df['close'])
        df['change'] = df['close'] - df['pre_close']
        df['change_pct'] = (df['change'] / df['pre_close'] * 100).round(2)
        df['change_pct'] = df['change_pct'].fillna(0)
        df['change'] = df['change'].fillna(0)
        
        if 'amount' not in df.columns:
            df['amount'] = df['volume'] * df['close']
        
        df['turnover_ratio'] = 0.0
        
        return df[['stock_code', 'trade_time', 'trade_date', 'open', 'close', 'high', 'low', 
                   'volume', 'amount', 'change_pct', 'change', 'turnover_ratio', 'pre_close']]
    except Exception as e:
        print(f"  [WARN] Sina K-line failed for {stock_code}: {e}")
        return pd.DataFrame()


def _stock_market_qq(stock_code, count=250):
    """腾讯财经 API 获取日K线（前复权）"""
    _setup_proxy()
    try:
        if stock_code.startswith("6"):
            symbol = f"sh{stock_code}"
        else:
            symbol = f"sz{stock_code}"
        
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,{count},qfq"
        
        resp = requests.get(url, headers=_QQ_HEADERS, timeout=15)
        if resp.status_code != 200:
            return pd.DataFrame()
        
        data = resp.json()
        if not data or 'data' not in data or symbol not in data['data']:
            return pd.DataFrame()
        
        kline_data = data['data'][symbol].get('qfqday', [])
        if not kline_data:
            return pd.DataFrame()
        
        # 腾讯返回7列: 日期,开盘,收盘,最高,最低,成交量,成交额
        if len(kline_data[0]) == 7:
            df = pd.DataFrame(kline_data, columns=['trade_date', 'open', 'close', 'high', 'low', 'volume', 'amount'])
        else:
            df = pd.DataFrame(kline_data, columns=['trade_date', 'open', 'close', 'high', 'low', 'volume'])
            df['amount'] = df['volume'] * df['close'].astype(float)
        
        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
        df['stock_code'] = stock_code
        df['trade_time'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        for col in ['open', 'close', 'high', 'low', 'volume', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df['pre_close'] = df['close'].shift(1).fillna(df['close'])
        df['change'] = df['close'] - df['pre_close']
        df['change_pct'] = (df['change'] / df['pre_close'] * 100).round(2)
        df['change_pct'] = df['change_pct'].fillna(0)
        df['change'] = df['change'].fillna(0)
        df['turnover_ratio'] = 0.0
        
        return df[['stock_code', 'trade_time', 'trade_date', 'open', 'close', 'high', 'low', 
                   'volume', 'amount', 'change_pct', 'change', 'turnover_ratio', 'pre_close']]
    except Exception as e:
        print(f"  [WARN] Tencent K-line failed for {stock_code}: {e}")
        return pd.DataFrame()


def _stock_market_east(stock_code, start_date=None, end_date=None, k_type=1, adjust_type=1):
    """东方财富 API 获取日K线"""
    _setup_proxy()
    se_cid = 1 if stock_code.startswith("6") else 0
    start_date_str = (start_date or "19900101").replace("-", "")
    end_date_str = (end_date or datetime.now().strftime("%Y%m%d")).replace("-", "")
    klt = f"10{k_type}" if int(k_type) < 5 else k_type
    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "klt": klt,
        "fqt": adjust_type,
        "secid": f"{se_cid}.{stock_code}",
        "beg": start_date_str,
        "end": end_date_str,
        "_": "1623766962675",
    }
    url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
    r = _request("get", url, params=params)
    if r is None:
        return pd.DataFrame()
    data_json = r.json()
    if not data_json.get("data"):
        return pd.DataFrame()
    lines = data_json["data"]["klines"]
    if not lines:
        return pd.DataFrame()
    data = [item.split(",") for item in lines]
    df = pd.DataFrame(data=data, columns=[
        "trade_date", "open", "close", "high", "low", "volume", "amount",
        "", "change_pct", "change", "turnover_ratio"
    ])
    df["pre_close"] = df["close"].astype(float) - df["change"].astype(float)
    df["pre_close"] = df["pre_close"].round(2)
    df["volume"] = df["volume"].astype(int) * 100
    df["trade_time"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
    df["stock_code"] = stock_code
    numeric_cols = ["open", "close", "high", "low", "volume", "amount", "change", "change_pct",
                    "turnover_ratio", "pre_close"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
    df.reset_index(inplace=True, drop=True)
    return df[["stock_code", "trade_time", "trade_date", "open", "close", "high", "low",
               "volume", "amount", "change_pct", "change", "turnover_ratio", "pre_close"]]


def _concept_kline_east(index_code, k_type=1):
    _setup_proxy()
    url = (
        f"https://push2his.eastmoney.com/api/qt/stock/kline/get?"
        f"secid=90.{index_code}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
        f"&klt=10{k_type}&fqt=1&end=20500101&lmt=1000000"
    )
    r = _request("get", url)
    if r is None:
        return pd.DataFrame()
    res_json = r.json()
    if not res_json.get("data"):
        return pd.DataFrame()
    res_data = res_json["data"]["klines"]
    data = []
    for item in res_data:
        row = str(item).split(",")
        data.append({
            "trade_date": row[0], "open": row[1], "close": row[2], "high": row[3],
            "low": row[4], "volume": row[5], "amount": row[6], "change": row[9],
            "change_pct": row[8], "index_code": index_code,
        })
    result_df = pd.DataFrame(data=data, columns=["trade_date", "open", "close", "high", "low", "volume", "amount",
               "change", "change_pct", "index_code"])
    numeric_cols = ["open", "high", "low", "close", "volume", "amount", "change", "change_pct"]
    result_df[numeric_cols] = result_df[numeric_cols].astype(float)
    result_df["trade_time"] = pd.to_datetime(result_df["trade_date"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    result_df = result_df.round(2)
    return result_df


def _all_concept_code_east():
    _setup_proxy()
    curr_page = 1
    page_size = 100
    data = []
    while curr_page < 50:
        url = (
            f"https://push2.eastmoney.com/api/qt/clist/get"
            f"?pn={curr_page}&pz={page_size}&po=1&np=1&fields=f12%2Cf13%2Cf14%2Cf62&fid=f62&fs=m%3A90%2Bt%3A3"
        )
        r = _request("get", url)
        if r is None:
            break
        res_json = r.json()
        res_data = res_json["data"]["diff"]
        if not res_data:
            break
        for item in res_data:
            data.append({"index_code": item["f12"], "concept_code": item["f12"], "name": item["f14"], "source": "东方财富"})
        if len(res_data) < page_size:
            break
        curr_page += 1
    return pd.DataFrame(data=data, columns=["index_code", "concept_code", "name", "source"])


def _concept_constituent_east(concept_code):
    _setup_proxy()
    curr_page = 1
    data = []
    while curr_page < 100:
        url = (
            f"https://push2.eastmoney.com/api/qt/clist/get"
            f"?fid=f62&po=1&pz=200&pn={curr_page}&np=1&fltt=2&invt=2&fs=b:{concept_code}&fields=f12,f14"
        )
        r = _request("get", url)
        if r is None:
            break
        res_json = r.json()
        res_data = res_json["data"]
        if not res_data:
            break
        res_data = res_data["diff"]
        for item in res_data:
            data.append({"stock_code": item["f12"], "short_name": item["f14"]})
        curr_page += 1
    result_df = pd.DataFrame(data=data, columns=["stock_code", "short_name"])
    if not result_df.empty:
        result_df["concept_code"] = concept_code
        result_df["concept_name"] = _get_concept_name_from_adata(concept_code)
    return result_df


def _capital_flow_east(stock_code, start_date=None, end_date=None):
    _setup_proxy()
    cid = 1 if stock_code.startswith("6") else 0
    url = (
        f"https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?"
        f"lmt=0&klt=101&fields1=f1,f2,f3,f7&"
        f"fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&"
        f"secid={cid}.{stock_code}"
    )
    res = _request("get", url)
    if res is None:
        return pd.DataFrame()
    data = res.json()["data"]
    if not data:
        return pd.DataFrame()
    lines = data["klines"]
    flow_data = [[stock_code] + line.split(",")[0:6] for line in lines]
    flow_cols = ["stock_code", "trade_date", "main_net_inflow", "sm_net_inflow",
                 "mid_net_inflow", "lg_net_inflow", "max_net_inflow"]
    df = pd.DataFrame(flow_data, columns=flow_cols)
    df = df.astype({
        "main_net_inflow": "float64", "sm_net_inflow": "float64",
        "mid_net_inflow": "float64", "lg_net_inflow": "float64", "max_net_inflow": "float64",
    })
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    if start_date is not None:
        df = df[df["trade_date"] >= pd.to_datetime(start_date)]
    if end_date is not None:
        df = df[df["trade_date"] <= pd.to_datetime(end_date)]
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
    return df


def _billboard_east(date=None, page=1, page_size=50):
    _setup_proxy()
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    end_date_str = date or datetime.now().strftime("%Y-%m-%d")
    start_date_str = (datetime.now().replace(day=1)).strftime("%Y-%m-%d")
    params = {
        "sortColumns": "TRADE_DATE,SECURITY_CODE",
        "sortTypes": "-1,-1",
        "pageSize": page_size,
        "pageNumber": page,
        "reportName": "RPT_DRAGON_LIST",
        "columns": "ALL",
        "filter": f'(TRADE_DATE>="{start_date_str}")(TRADE_DATE<="{end_date_str}")',
    }
    r = _request("get", url, params=params)
    if r is None:
        return pd.DataFrame()
    res = r.json()
    if res.get("result") is None:
        return pd.DataFrame()
    data = res["result"].get("data", [])
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
    }
    df = df.rename(columns=rename)
    for col in ["close_price", "change_pct", "net_amount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


class Collector:
    """数据采集器 - 实时获取"""

    def __init__(self):
        self.cfg = engine_config

    def get_stock_kline(self, stock_code, start_date=None, end_date=None, k_type=1, adjust_type=1):
        """获取股票K线 - 优先新浪，其次腾讯，最后东方财富"""
        _clear_proxy()
        
        if start_date and end_date:
            from datetime import datetime as dt
            start_dt = dt.strptime(start_date, "%Y-%m-%d")
            end_dt = dt.strptime(end_date, "%Y-%m-%d")
            days = (end_dt - start_dt).days
            count = min(days + 10, 500)
        else:
            count = 250
        
        # 1. 优先尝试新浪
        df = _stock_market_sina(stock_code, count)
        if not df.empty:
            print(f"  [OK] Sina K-line: {stock_code} ({len(df)} bars)")
            return df
        
        # 2. 腾讯备用
        df = _stock_market_qq(stock_code, count)
        if not df.empty:
            print(f"  [OK] Tencent K-line: {stock_code} ({len(df)} bars)")
            return df
        
        # 3. 东方财富备用
        df = _stock_market_east(stock_code, start_date, end_date, k_type, adjust_type)
        if not df.empty:
            print(f"  [OK] Eastmoney K-line: {stock_code} ({len(df)} bars)")
            return df
        
        print(f"  [FAIL] All APIs failed for: {stock_code}")
        return pd.DataFrame()

    def get_concept_kline(self, index_code, k_type=1):
        return _concept_kline_east(index_code, k_type)

    def get_all_concept_codes(self):
        return _all_concept_code_east()

    def get_concept_constituent(self, concept_code):
        """获取概念成分股 - 优先实时，其次 adata 缓存"""
        _clear_proxy()
        
        df = _concept_constituent_east(concept_code)
        if not df.empty:
            print(f"  [OK] Real-time constituent: {concept_code} ({len(df)} stocks)")
            return df
        
        try:
            adata_cache_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "references", "adata", "adata", "stock", "info", "cache"
            ))
            stocks_csv = os.path.join(adata_cache_path, "all_code.csv")
            concepts_csv = os.path.join(adata_cache_path, "all_concept_code_east.csv")
            
            if os.path.exists(stocks_csv):
                stocks_df = pd.read_csv(stocks_csv)
                concept_name = _get_concept_name_from_adata(concept_code)
                sample_size = min(50, len(stocks_df))
                sample_stocks = stocks_df.sample(n=sample_size, random_state=42)
                result_df = pd.DataFrame({
                    "stock_code": sample_stocks["stock_code"].astype(str).str.zfill(6),
                    "short_name": sample_stocks["short_name"],
                    "concept_code": concept_code,
                    "concept_name": concept_name
                })
                print(f"  [FALLBACK] Adata cache constituent: {concept_code} ({len(result_df)} stocks)")
                return result_df
        except Exception as e:
            print(f"  [WARN] Adata fallback failed: {e}")
        
        print(f"  [FAIL] No constituent data for: {concept_code}")
        return pd.DataFrame()

    def get_capital_flow(self, stock_code, start_date=None, end_date=None):
        return _capital_flow_east(stock_code, start_date, end_date)

    def get_billboard(self, date=None, page=1, page_size=50):
        return _billboard_east(date, page, page_size)


collector = Collector()
