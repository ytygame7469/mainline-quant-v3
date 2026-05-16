# -*- coding: utf-8 -*-
import os
from datetime import datetime

import duckdb
import pandas as pd

from .config import engine_config

_TABLE_SCHEMAS = {
    "daily_kline": """
        CREATE TABLE IF NOT EXISTS daily_kline (
            stock_code VARCHAR,
            trade_time TIMESTAMP,
            trade_date DATE,
            open DOUBLE,
            close DOUBLE,
            high DOUBLE,
            low DOUBLE,
            volume BIGINT,
            amount DOUBLE,
            change_pct DOUBLE,
            change DOUBLE,
            turnover_ratio DOUBLE,
            pre_close DOUBLE
        )
    """,
    "concept_kline": """
        CREATE TABLE IF NOT EXISTS concept_kline (
            trade_date DATE,
            open DOUBLE,
            close DOUBLE,
            high DOUBLE,
            low DOUBLE,
            volume DOUBLE,
            amount DOUBLE,
            change DOUBLE,
            change_pct DOUBLE,
            index_code VARCHAR,
            trade_time TIMESTAMP
        )
    """,
    "concept_constituent": """
        CREATE TABLE IF NOT EXISTS concept_constituent (
            stock_code VARCHAR,
            short_name VARCHAR,
            concept_code VARCHAR
        )
    """,
    "capital_flow": """
        CREATE TABLE IF NOT EXISTS capital_flow (
            stock_code VARCHAR,
            trade_date DATE,
            main_net_inflow DOUBLE,
            sm_net_inflow DOUBLE,
            mid_net_inflow DOUBLE,
            lg_net_inflow DOUBLE,
            max_net_inflow DOUBLE
        )
    """,
    "finance": """
        CREATE TABLE IF NOT EXISTS finance (
            stock_code VARCHAR,
            short_name VARCHAR,
            report_date DATE,
            report_type VARCHAR,
            notice_date DATE,
            basic_eps DOUBLE,
            diluted_eps DOUBLE,
            net_asset_ps DOUBLE,
            oper_cf_ps DOUBLE,
            total_rev DOUBLE,
            net_profit_attr_sh DOUBLE,
            total_rev_yoy_gr DOUBLE,
            net_profit_yoy_gr DOUBLE,
            roe_wtd DOUBLE,
            gross_margin DOUBLE,
            net_margin DOUBLE,
            asset_liab_ratio DOUBLE,
            curr_ratio DOUBLE,
            quick_ratio DOUBLE,
            total_asset_turn_rate DOUBLE
        )
    """,
    "north_flow": """
        CREATE TABLE IF NOT EXISTS north_flow (
            trade_date DATE,
            net_hgt BIGINT,
            buy_hgt BIGINT,
            sell_hgt BIGINT,
            net_sgt BIGINT,
            buy_sgt BIGINT,
            sell_sgt BIGINT,
            net_tgt BIGINT,
            buy_tgt BIGINT,
            sell_tgt BIGINT
        )
    """,
    "hot_rank": """
        CREATE TABLE IF NOT EXISTS hot_rank (
            rank INTEGER,
            stock_code VARCHAR,
            short_name VARCHAR,
            price DOUBLE,
            change DOUBLE,
            change_pct DOUBLE,
            snapshot_date DATE
        )
    """,
}

_SYNC_META_DDL = """
    CREATE TABLE IF NOT EXISTS sync_meta (
        table_name VARCHAR,
        stock_code VARCHAR,
        last_sync_date DATE,
        last_sync_time TIMESTAMP,
        status VARCHAR,
        row_count INTEGER,
        PRIMARY KEY (table_name, stock_code)
    )
"""

_PARQUET_PARTITION_TABLES = {"daily_kline", "concept_kline", "capital_flow", "finance", "north_flow"}


class Storage:

    def __init__(self, base_path=None, duckdb_path=None):
        cfg = engine_config.storage
        self.base_path = base_path or cfg.base_path
        self.duckdb_path = duckdb_path or cfg.duckdb_path
        self.parquet_compression = cfg.parquet_compression
        os.makedirs(self.base_path, exist_ok=True)
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.duckdb_path), exist_ok=True)
        self.conn = duckdb.connect(self.duckdb_path)
        self.conn.execute(_SYNC_META_DDL)
        for ddl in _TABLE_SCHEMAS.values():
            self.conn.execute(ddl)

    def _parquet_partition_path(self, table_name, trade_date):
        date_str = pd.Timestamp(trade_date).strftime("%Y%m%d")
        return os.path.join(self.base_path, table_name, f"date={date_str}")

    def _write_parquet(self, table_name, df, trade_date):
        if df.empty:
            return
        partition_path = self._parquet_partition_path(table_name, trade_date)
        os.makedirs(partition_path, exist_ok=True)
        file_path = os.path.join(partition_path, "data.parquet")
        if os.path.exists(file_path):
            existing = pd.read_parquet(file_path)
            df = pd.concat([existing, df], ignore_index=True).drop_duplicates()
        df.to_parquet(file_path, index=False, compression=self.parquet_compression)

    def _read_parquet(self, table_name, start_date=None, end_date=None):
        base_dir = os.path.join(self.base_path, table_name)
        if not os.path.exists(base_dir):
            return pd.DataFrame()
        all_dfs = []
        for partition in sorted(os.listdir(base_dir)):
            if not partition.startswith("date="):
                continue
            date_str = partition.replace("date=", "")
            if start_date and date_str < start_date.replace("-", ""):
                continue
            if end_date and date_str > end_date.replace("-", ""):
                continue
            file_path = os.path.join(base_dir, partition, "data.parquet")
            if os.path.exists(file_path):
                all_dfs.append(pd.read_parquet(file_path))
        if not all_dfs:
            return pd.DataFrame()
        return pd.concat(all_dfs, ignore_index=True)

    def _update_sync_meta(self, table_name, stock_code, trade_date, row_count, status="success"):
        self.conn.execute("""
            INSERT OR REPLACE INTO sync_meta (table_name, stock_code, last_sync_date, last_sync_time, status, row_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [table_name, stock_code, str(trade_date), datetime.now(), status, row_count])

    def _get_sync_meta(self, table_name, stock_code=None):
        if stock_code:
            result = self.conn.execute(
                "SELECT * FROM sync_meta WHERE table_name=? AND stock_code=?",
                [table_name, stock_code]
            ).fetchone()
        else:
            result = self.conn.execute(
                "SELECT * FROM sync_meta WHERE table_name=?", [table_name]
            ).fetchdf()
        return result

    def save_daily_kline(self, df, stock_code):
        if df.empty:
            return
        if "trade_date" not in df.columns:
            return
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        for trade_date, group in df.groupby(df["trade_date"].dt.date):
            self._write_parquet("daily_kline", group, trade_date)
        last_date = df["trade_date"].max()
        self._update_sync_meta("daily_kline", stock_code, last_date, len(df))

    def save_concept_kline(self, df, index_code):
        if df.empty:
            return
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        for trade_date, group in df.groupby(df["trade_date"].dt.date):
            self._write_parquet("concept_kline", group, trade_date)
        last_date = df["trade_date"].max()
        self._update_sync_meta("concept_kline", index_code, last_date, len(df))

    def save_concept_constituent(self, df, concept_code):
        if df.empty:
            return
        file_path = os.path.join(self.base_path, "concept_constituent", "data.parquet")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if os.path.exists(file_path):
            existing = pd.read_parquet(file_path)
            df = pd.concat([existing, df], ignore_index=True).drop_duplicates(
                subset=["stock_code", "concept_code"]
            )
        df.to_parquet(file_path, index=False, compression=self.parquet_compression)
        self._update_sync_meta("concept_constituent", concept_code, datetime.now().date(), len(df))

    def save_capital_flow(self, df, stock_code):
        if df.empty:
            return
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        for trade_date, group in df.groupby(df["trade_date"].dt.date):
            self._write_parquet("capital_flow", group, trade_date)
        last_date = df["trade_date"].max()
        self._update_sync_meta("capital_flow", stock_code, last_date, len(df))

    def save_finance(self, df, stock_code):
        if df.empty:
            return
        file_path = os.path.join(self.base_path, "finance", "data.parquet")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if os.path.exists(file_path):
            existing = pd.read_parquet(file_path)
            df = pd.concat([existing, df], ignore_index=True).drop_duplicates(
                subset=["stock_code", "report_date"]
            )
        df.to_parquet(file_path, index=False, compression=self.parquet_compression)
        self._update_sync_meta("finance", stock_code, datetime.now().date(), len(df))

    def save_north_flow(self, df):
        if df.empty:
            return
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        for trade_date, group in df.groupby(df["trade_date"].dt.date):
            self._write_parquet("north_flow", group, trade_date)
        last_date = df["trade_date"].max()
        self._update_sync_meta("north_flow", "ALL", last_date, len(df))

    def save_hot_rank(self, df):
        if df.empty:
            return
        df["snapshot_date"] = datetime.now().date()
        file_path = os.path.join(self.base_path, "hot_rank", "data.parquet")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        df.to_parquet(file_path, index=False, compression=self.parquet_compression)
        self._update_sync_meta("hot_rank", "ALL", datetime.now().date(), len(df))

    def load_daily_kline(self, stock_code=None, start_date=None, end_date=None):
        df = self._read_parquet("daily_kline", start_date, end_date)
        if not df.empty and stock_code:
            df = df[df["stock_code"] == stock_code]
        return df

    def load_concept_kline(self, index_code=None, start_date=None, end_date=None):
        df = self._read_parquet("concept_kline", start_date, end_date)
        if not df.empty and index_code:
            df = df[df["index_code"] == index_code]
        return df

    def load_concept_constituent(self, concept_code=None):
        file_path = os.path.join(self.base_path, "concept_constituent", "data.parquet")
        if not os.path.exists(file_path):
            return pd.DataFrame()
        df = pd.read_parquet(file_path)
        if concept_code:
            df = df[df["concept_code"] == concept_code]
        return df

    def load_capital_flow(self, stock_code=None, start_date=None, end_date=None):
        df = self._read_parquet("capital_flow", start_date, end_date)
        if not df.empty and stock_code:
            df = df[df["stock_code"] == stock_code]
        return df

    def load_finance(self, stock_code=None):
        file_path = os.path.join(self.base_path, "finance", "data.parquet")
        if not os.path.exists(file_path):
            return pd.DataFrame()
        df = pd.read_parquet(file_path)
        if stock_code:
            df = df[df["stock_code"] == stock_code]
        return df

    def load_north_flow(self, start_date=None, end_date=None):
        return self._read_parquet("north_flow", start_date, end_date)

    def load_hot_rank(self):
        file_path = os.path.join(self.base_path, "hot_rank", "data.parquet")
        if not os.path.exists(file_path):
            return pd.DataFrame()
        return pd.read_parquet(file_path)

    def get_sync_status(self, table_name=None):
        if table_name:
            return self.conn.execute(
                "SELECT * FROM sync_meta WHERE table_name=?", [table_name]
            ).fetchdf()
        return self.conn.execute("SELECT * FROM sync_meta").fetchdf()

    def query_duckdb(self, sql):
        return self.conn.execute(sql).fetchdf()

    def close(self):
        self.conn.close()


storage = Storage()