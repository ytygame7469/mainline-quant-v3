# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DataSourceConfig:
    eastmoney: bool = True
    sina: bool = True
    tencent: bool = True
    request_timeout: int = 30
    request_retry: int = 3
    retry_wait_ms: int = 1588
    request_interval_ms: int = 200


@dataclass
class StorageConfig:
    base_path: str = "data"
    parquet_engine: str = "pyarrow"
    parquet_compression: str = "snappy"
    duckdb_path: str = "data/meta.duckdb"
    partition_col: str = "trade_date"
    partition_fmt: str = "%Y%m%d"


@dataclass
class SyncConfig:
    daily_kline_start: str = "2020-01-01"
    concept_kline_start: str = "2020-01-01"
    capital_flow_start: str = "2024-01-01"
    finance_start: str = "2019-01-01"
    north_flow_start: str = "2017-01-01"
    batch_size: int = 50
    max_batch_retry: int = 3


@dataclass
class FactorConfig:
    ma_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 60, 120, 250])
    ema_periods: List[int] = field(default_factory=lambda: [12, 26])
    macd_params: Dict = field(default_factory=lambda: {"fast": 12, "slow": 26, "signal": 9})
    rsi_periods: List[int] = field(default_factory=lambda: [6, 14, 24])
    kdj_params: Dict = field(default_factory=lambda: {"n": 9, "m1": 3, "m2": 3})
    boll_params: Dict = field(default_factory=lambda: {"n": 20, "k": 2})
    atr_period: int = 14
    volume_ma_periods: List[int] = field(default_factory=lambda: [5, 20])
    momentum_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 60])


@dataclass
class DataEngineConfig:
    source: DataSourceConfig = field(default_factory=DataSourceConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    sync: SyncConfig = field(default_factory=SyncConfig)
    factor: FactorConfig = field(default_factory=FactorConfig)


engine_config = DataEngineConfig()