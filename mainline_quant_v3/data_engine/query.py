# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

import pandas as pd

from .storage import storage


class Query:

    def __init__(self):
        self.storage = storage

    def daily_kline(self, stock_code=None, start_date=None, end_date=None, fields=None):
        df = self.storage.load_daily_kline(stock_code=stock_code, start_date=start_date, end_date=end_date)
        if df.empty:
            return df
        if fields:
            avail = [f for f in fields if f in df.columns]
            df = df[avail]
        return df.reset_index(drop=True)

    def concept_kline(self, index_code=None, start_date=None, end_date=None, fields=None):
        df = self.storage.load_concept_kline(index_code=index_code, start_date=start_date, end_date=end_date)
        if df.empty:
            return df
        if fields:
            avail = [f for f in fields if f in df.columns]
            df = df[avail]
        return df.reset_index(drop=True)

    def concept_constituent(self, concept_code=None):
        return self.storage.load_concept_constituent(concept_code=concept_code)

    def capital_flow(self, stock_code=None, start_date=None, end_date=None, fields=None):
        df = self.storage.load_capital_flow(stock_code=stock_code, start_date=start_date, end_date=end_date)
        if df.empty:
            return df
        if fields:
            avail = [f for f in fields if f in df.columns]
            df = df[avail]
        return df.reset_index(drop=True)

    def finance(self, stock_code=None, fields=None):
        df = self.storage.load_finance(stock_code=stock_code)
        if df.empty:
            return df
        if fields:
            avail = [f for f in fields if f in df.columns]
            df = df[avail]
        return df.reset_index(drop=True)

    def north_flow(self, start_date=None, end_date=None, fields=None):
        df = self.storage.load_north_flow(start_date=start_date, end_date=end_date)
        if df.empty:
            return df
        if fields:
            avail = [f for f in fields if f in df.columns]
            df = df[avail]
        return df.reset_index(drop=True)

    def hot_rank(self):
        return self.storage.load_hot_rank()

    def latest_kline(self, stock_code=None, days=20):
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=days * 2)).strftime("%Y-%m-%d")
        df = self.daily_kline(stock_code=stock_code, start_date=start, end_date=end)
        if df.empty:
            return df
        if stock_code:
            df = df.sort_values("trade_date", ascending=False).head(days)
        else:
            codes = df["stock_code"].unique()
            dfs = []
            for code in codes:
                sub = df[df["stock_code"] == code].sort_values("trade_date", ascending=False).head(days)
                dfs.append(sub)
            df = pd.concat(dfs, ignore_index=True)
        return df.sort_values(["stock_code", "trade_date"]).reset_index(drop=True)

    def latest_concept_kline(self, index_code=None, days=20):
        df = self.concept_kline(index_code=index_code)
        if df.empty:
            return df
        if index_code:
            df = df.sort_values("trade_date", ascending=False).head(days)
        else:
            codes = df["index_code"].unique()
            dfs = []
            for code in codes:
                sub = df[df["index_code"] == code].sort_values("trade_date", ascending=False).head(days)
                dfs.append(sub)
            df = pd.concat(dfs, ignore_index=True)
        return df.sort_values(["index_code", "trade_date"]).reset_index(drop=True)

    def sync_status(self, table_name=None):
        return self.storage.get_sync_status(table_name=table_name)

    def raw_sql(self, sql):
        return self.storage.query_duckdb(sql)


query = Query()