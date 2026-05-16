# -*- coding: utf-8 -*-
import json
import math
import time
from datetime import datetime

import pandas as pd
import requests

from .config import engine_config

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
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


def _stock_market_east(stock_code, start_date=None, end_date=None, k_type=1, adjust_type=1):
    se_cid = 1 if stock_code.startswith("6") else 0
    start_date = (start_date or "19900101").replace("-", "")
    end_date = (end_date or datetime.now().strftime("%Y%m%d")).replace("-", "")
    klt = f"10{k_type}" if int(k_type) < 5 else k_type
    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "klt": klt,
        "fqt": adjust_type,
        "secid": f"{se_cid}.{stock_code}",
        "beg": start_date,
        "end": end_date,
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
    numeric_cols = ["open", "close", "volume", "high", "low", "amount", "change", "change_pct",
                    "turnover_ratio", "pre_close"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
    df.reset_index(inplace=True, drop=True)
    return df[["stock_code", "trade_time", "trade_date", "open", "close", "high", "low",
               "volume", "amount", "change_pct", "change", "turnover_ratio", "pre_close"]]


def _concept_kline_east(index_code, k_type=1):
    url = (
        f"https://push2his.eastmoney.com/api/qt/stock/kline/get?"
        f"secid=90.{index_code}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
        f"&klt=10{k_type}&fqt=1&end=20500101&lmt=1000000"
    )
    r = _request("get", url)
    if r is None:
        return pd.DataFrame()
    res_json = r.json()
    code = res_json["data"]["code"]
    if code != index_code:
        return pd.DataFrame()
    res_data = res_json["data"]["klines"]
    data = []
    for _ in res_data:
        row = str(_).split(",")
        data.append({
            "trade_date": row[0], "open": row[1], "close": row[2], "high": row[3],
            "low": row[4], "volume": row[5], "amount": row[6], "change": row[9],
            "change_pct": row[8], "index_code": index_code,
        })
    columns = ["trade_date", "open", "close", "high", "low", "volume", "amount",
               "change", "change_pct", "index_code"]
    result_df = pd.DataFrame(data=data, columns=columns)
    numeric_cols = ["open", "high", "low", "close", "volume", "amount", "change", "change_pct"]
    result_df[numeric_cols] = result_df[numeric_cols].astype(float)
    result_df["trade_time"] = pd.to_datetime(result_df["trade_date"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    result_df = result_df.round(2)
    return result_df


def _all_concept_code_east():
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
        for _ in res_data:
            data.append({"index_code": _["f12"], "concept_code": _["f12"], "name": _["f14"], "source": "东方财富"})
        if len(res_data) < page_size:
            break
        curr_page += 1
    return pd.DataFrame(data=data, columns=["index_code", "concept_code", "name", "source"])


def _concept_constituent_east(concept_code):
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
        for _ in res_data:
            data.append({"stock_code": _["f12"], "short_name": _["f14"]})
        curr_page += 1
    result_df = pd.DataFrame(data=data, columns=["stock_code", "short_name"])
    if not result_df.empty:
        result_df["concept_code"] = concept_code
    return result_df


def _capital_flow_east(stock_code, start_date=None, end_date=None):
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
    data = [[stock_code] + line.split(",")[0:6] for line in lines]
    flow_cols = ["stock_code", "trade_date", "main_net_inflow", "sm_net_inflow",
                 "mid_net_inflow", "lg_net_inflow", "max_net_inflow"]
    df = pd.DataFrame(data, columns=flow_cols)
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


def _concept_capital_flow_east(days_type=1):
    fid_map = {1: "f62", 5: "f164", 10: "f174"}
    fields_map = {
        1: "f12,f14,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205",
        5: "f12,f14,f109,f164,f165,f166,f167,f168,f169,f170,f171,f172,f173,f257,f258",
        10: "f12,f14,f160,f174,f175,f176,f177,f178,f179,f180,f181,f182,f183,f260,f261",
    }
    fid = fid_map.get(days_type, "f62")
    fields = fields_map.get(days_type, fields_map[1])
    flow_cols = [
        "index_code", "index_name", "change_pct", "main_net_inflow", "main_net_inflow_rate",
        "max_net_inflow", "max_net_inflow_rate", "lg_net_inflow", "lg_net_inflow_rate",
        "mid_net_inflow", "mid_net_inflow_rate", "sm_net_inflow", "sm_net_inflow_rate",
        "stock_code", "stock_name",
    ]
    curr_page = 1
    res_data = []
    while curr_page < 50:
        url = (
            f"https://push2.eastmoney.com/api/qt/clist/get?"
            f"cb=jQuery112309367957412610306_1735123926723&fid={fid}&po=1&pz=50&pn={curr_page}"
            f"&np=1&fltt=2&invt=2&fs=m:90 t:3&fields={fields}"
        )
        res = _request("get", url)
        if res is None:
            break
        text = res.text
        text = text[text.index("(") + 1:-2]
        data = json.loads(text)["data"]
        if not data:
            break
        data = data["diff"]
        field_list = fields.split(",")
        for item in data:
            dt = {}
            for i, col in enumerate(flow_cols):
                if item.get(field_list[i], "-") != "-":
                    dt[col] = item[field_list[i]]
            if len(dt) == len(flow_cols):
                res_data.append(dt)
        curr_page += 1
    df = pd.DataFrame(res_data, columns=flow_cols)
    numeric_cols = [c for c in flow_cols if c not in ("index_code", "index_name", "stock_code", "stock_name")]
    df[numeric_cols] = df[numeric_cols].astype(float)
    return df


def _finance_core_east(stock_code):
    report_types = ["年报", "中报", "三季报", "一季报"]
    exchange_code = stock_code + (".SH" if stock_code.startswith("6") else ".SZ")
    data = []
    for rtype in report_types:
        url = (
            f"https://datacenter.eastmoney.com/securities/api/data/get?type=RPT_F10_FINANCE_MAINFINADATA&"
            f'sty=APP_F10_MAINFINADATA&quoteColumns=&filter=(SECUCODE="{exchange_code}")(REPORT_TYPE="{rtype}")&'
            f"p=1&ps=100&sr=-1&st=REPORT_DATE&source=HSF10&client=PC&v=03890754131799983"
        )
        r = _request("get", url, timeout=30)
        if r is None:
            continue
        data_json = r.json()
        if data_json.get("code") == 0:
            res = data_json["result"]["data"]
            data.extend(res)
    if not data:
        return pd.DataFrame()
    rename = {
        "SECURITY_CODE": "stock_code",
        "SECURITY_NAME_ABBR": "short_name",
        "REPORT_DATE": "report_date",
        "REPORT_TYPE": "report_type",
        "NOTICE_DATE": "notice_date",
        "EPSJB": "basic_eps",
        "EPSKCJB": "diluted_eps",
        "BPS": "net_asset_ps",
        "MGJYXJJE": "oper_cf_ps",
        "TOTALOPERATEREVE": "total_rev",
        "PARENTNETPROFIT": "net_profit_attr_sh",
        "TOTALOPERATEREVETZ": "total_rev_yoy_gr",
        "PARENTNETPROFITTZ": "net_profit_yoy_gr",
        "ROEJQ": "roe_wtd",
        "XSMLL": "gross_margin",
        "XSJLL": "net_margin",
        "ZCFZL": "asset_liab_ratio",
        "LD": "curr_ratio",
        "SD": "quick_ratio",
        "TOAZZL": "total_asset_turn_rate",
    }
    df = pd.DataFrame(data).rename(columns=rename)
    avail_cols = [v for v in rename.values() if v in df.columns]
    df = df[avail_cols]
    df["report_date"] = pd.to_datetime(df["report_date"]).dt.strftime("%Y-%m-%d")
    df["notice_date"] = pd.to_datetime(df["notice_date"]).dt.strftime("%Y-%m-%d")
    df = df.sort_values(by="report_date", ascending=False)
    return df


def _north_flow_east(start_date=None):
    columns = [
        "trade_date", "net_hgt", "buy_hgt", "sell_hgt",
        "net_sgt", "buy_sgt", "sell_sgt", "net_tgt", "buy_tgt", "sell_tgt",
    ]
    if start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        date_min = datetime.strptime("2017-01-01", "%Y-%m-%d")
        start_date = max(start_date, date_min)
    curr_page = 1
    data = []
    while curr_page < 18:
        base_url = (
            f"https://datacenter-web.eastmoney.com/api/data/v1/get?"
            f"sortColumns=TRADE_DATE&sortTypes=-1&pageSize=1000&pageNumber={curr_page}&"
            f"reportName=RPT_MUTUAL_DEAL_HISTORY&columns=ALL&source=WEB&client=WEB&"
        )
        sgt_url = f'{base_url}filter=(MUTUAL_TYPE="001")'
        hgt_url = f'{base_url}filter=(MUTUAL_TYPE="003")'
        sgt_resp = _request("get", sgt_url)
        hgt_resp = _request("get", hgt_url)
        if sgt_resp is None or hgt_resp is None:
            break
        sgt_text = sgt_resp.text.replace("null", "0")
        hgt_text = hgt_resp.text.replace("null", "0")
        sgt_json = json.loads(sgt_text[sgt_text.index("{"):-2])
        hgt_json = json.loads(hgt_text[hgt_text.index("{"):-2])
        sgt_items = sgt_json["result"]["data"]
        hgt_items = hgt_json["result"]["data"]
        if not sgt_items:
            break
        is_end = False
        for hgt_item, sgt_item in zip(hgt_items, sgt_items):
            if start_date:
                item_date = datetime.strptime(hgt_item["TRADE_DATE"], "%Y-%m-%d %H:%M:%S")
                if start_date > item_date:
                    is_end = True
                    break
            data.append({
                "trade_date": hgt_item["TRADE_DATE"],
                "net_hgt": math.ceil(hgt_item["NET_DEAL_AMT"] * 1000000),
                "buy_hgt": math.ceil(hgt_item["BUY_AMT"] * 1000000),
                "sell_hgt": math.ceil(hgt_item["SELL_AMT"] * 1000000),
                "net_sgt": math.ceil(sgt_item["NET_DEAL_AMT"] * 1000000),
                "buy_sgt": math.ceil(sgt_item["BUY_AMT"] * 1000000),
                "sell_sgt": math.ceil(sgt_item["SELL_AMT"] * 1000000),
                "net_tgt": math.ceil((hgt_item["NET_DEAL_AMT"] + sgt_item["NET_DEAL_AMT"]) * 1000000),
                "buy_tgt": math.ceil((hgt_item["BUY_AMT"] + sgt_item["BUY_AMT"]) * 1000000),
                "sell_tgt": math.ceil((hgt_item["SELL_AMT"] + sgt_item["SELL_AMT"]) * 1000000),
            })
        if is_end:
            break
        curr_page += 1
    result_df = pd.DataFrame(data=data, columns=columns)
    result_df["trade_date"] = pd.to_datetime(result_df["trade_date"]).dt.strftime("%Y-%m-%d")
    return result_df[columns]


def _hot_rank_east():
    url = "https://emappdata.eastmoney.com/stockrank/getAllCurrentList"
    params = {
        "appId": "appId01",
        "globalId": "786e4c21-70dc-435a-93bb-38",
        "marketType": "",
        "pageNo": 1,
        "pageSize": 100,
    }
    r = _request("post", url, json_data=params)
    if r is None:
        return pd.DataFrame()
    res = r.json()
    df = pd.DataFrame(res["data"])
    df["mark"] = ["0." + item[2:] if "SZ" in item else "1." + item[2:] for item in df["sc"]]
    params2 = {
        "ut": "f057cbcbce2a86e2866ab8877db1d059",
        "fltt": "2",
        "invt": "2",
        "fields": "f14,f3,f12,f2",
        "secids": ",".join(df["mark"]) + ",?v=08926209912590994",
    }
    url2 = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    r2 = _request("get", url2, params=params2)
    if r2 is None:
        return pd.DataFrame()
    data2 = r2.json()["data"]["diff"]
    rename = {"f2": "price", "f3": "change_pct", "f12": "stock_code", "f14": "short_name"}
    rank_df = pd.DataFrame(data2).rename(columns=rename)
    rank_df["change_pct"] = pd.to_numeric(rank_df["change_pct"], errors="coerce")
    rank_df["price"] = pd.to_numeric(rank_df["price"], errors="coerce")
    rank_df["change"] = rank_df["price"] * rank_df["change_pct"] / 100
    rank_df["rank"] = range(1, len(rank_df) + 1)
    return rank_df[["rank", "stock_code", "short_name", "price", "change", "change_pct"]]


class Collector:

    def __init__(self):
        self.cfg = engine_config

    def get_stock_kline(self, stock_code, start_date=None, end_date=None, k_type=1, adjust_type=1):
        return _stock_market_east(stock_code, start_date, end_date, k_type, adjust_type)

    def get_concept_kline(self, index_code, k_type=1):
        return _concept_kline_east(index_code, k_type)

    def get_all_concept_codes(self):
        return _all_concept_code_east()

    def get_concept_constituent(self, concept_code):
        return _concept_constituent_east(concept_code)

    def get_capital_flow(self, stock_code, start_date=None, end_date=None):
        return _capital_flow_east(stock_code, start_date, end_date)

    def get_concept_capital_flow(self, days_type=1):
        return _concept_capital_flow_east(days_type)

    def get_finance(self, stock_code):
        return _finance_core_east(stock_code)

    def get_north_flow(self, start_date=None):
        return _north_flow_east(start_date)

    def get_hot_rank(self):
        return _hot_rank_east()

    def get_billboard(self):
        return pd.DataFrame()


collector = Collector()