# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

from .config import engine_config


def _ensure_ohlc(df):
    required = ["open", "high", "low", "close"]
    if "volume" in df.columns:
        required.append("volume")
    for col in required:
        if col not in df.columns:
            raise ValueError(f"缺少必要列: {col}")


def _sort_by_date(df):
    if "trade_date" in df.columns:
        return df.sort_values("trade_date").reset_index(drop=True)
    return df.reset_index(drop=True)


class FactorEngine:

    def __init__(self):
        self.cfg = engine_config.factor

    def ma(self, df, periods=None):
        if periods is None:
            periods = self.cfg.ma_periods
        _ensure_ohlc(df)
        df = _sort_by_date(df)
        result = df[["trade_date", "stock_code"]].copy() if "stock_code" in df.columns else df[["trade_date"]].copy()
        result["close"] = df["close"]
        for p in periods:
            result[f"ma{p}"] = df["close"].rolling(window=p).mean()
        return result

    def ema(self, df, periods=None):
        if periods is None:
            periods = self.cfg.ema_periods
        _ensure_ohlc(df)
        df = _sort_by_date(df)
        result = df[["trade_date", "stock_code"]].copy() if "stock_code" in df.columns else df[["trade_date"]].copy()
        result["close"] = df["close"]
        for p in periods:
            result[f"ema{p}"] = df["close"].ewm(span=p, adjust=False).mean()
        return result

    def macd(self, df, fast=None, slow=None, signal=None):
        if fast is None:
            fast = self.cfg.macd_params["fast"]
        if slow is None:
            slow = self.cfg.macd_params["slow"]
        if signal is None:
            signal = self.cfg.macd_params["signal"]
        _ensure_ohlc(df)
        df = _sort_by_date(df)
        base_cols = ["trade_date"]
        if "stock_code" in df.columns:
            base_cols.append("stock_code")
        result = df[base_cols].copy()
        result["close"] = df["close"]
        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
        result["dif"] = ema_fast - ema_slow
        result["dea"] = result["dif"].ewm(span=signal, adjust=False).mean()
        result["macd"] = 2 * (result["dif"] - result["dea"])
        return result

    def rsi(self, df, periods=None):
        if periods is None:
            periods = self.cfg.rsi_periods
        _ensure_ohlc(df)
        df = _sort_by_date(df)
        base_cols = ["trade_date"]
        if "stock_code" in df.columns:
            base_cols.append("stock_code")
        result = df[base_cols].copy()
        result["close"] = df["close"]
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        for p in periods:
            avg_gain = gain.ewm(alpha=1 / p, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1 / p, adjust=False).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            result[f"rsi{p}"] = 100 - (100 / (1 + rs))
        return result

    def kdj(self, df, n=None, m1=None, m2=None):
        if n is None:
            n = self.cfg.kdj_params["n"]
        if m1 is None:
            m1 = self.cfg.kdj_params["m1"]
        if m2 is None:
            m2 = self.cfg.kdj_params["m2"]
        _ensure_ohlc(df)
        df = _sort_by_date(df)
        base_cols = ["trade_date"]
        if "stock_code" in df.columns:
            base_cols.append("stock_code")
        result = df[base_cols].copy()
        low_n = df["low"].rolling(window=n).min()
        high_n = df["high"].rolling(window=n).max()
        rsv = (df["close"] - low_n) / (high_n - low_n).replace(0, np.nan) * 100
        k = rsv.ewm(alpha=1 / m1, adjust=False).mean()
        d = k.ewm(alpha=1 / m2, adjust=False).mean()
        result["k"] = k
        result["d"] = d
        result["j"] = 3 * k - 2 * d
        return result

    def boll(self, df, n=None, k=None):
        if n is None:
            n = self.cfg.boll_params["n"]
        if k is None:
            k = self.cfg.boll_params["k"]
        _ensure_ohlc(df)
        df = _sort_by_date(df)
        base_cols = ["trade_date"]
        if "stock_code" in df.columns:
            base_cols.append("stock_code")
        result = df[base_cols].copy()
        result["close"] = df["close"]
        ma = df["close"].rolling(window=n).mean()
        std = df["close"].rolling(window=n).std()
        result["boll_mid"] = ma
        result["boll_up"] = ma + k * std
        result["boll_low"] = ma - k * std
        result["boll_width"] = (result["boll_up"] - result["boll_low"]) / result["boll_mid"].replace(0, np.nan)
        return result

    def atr(self, df, period=None):
        if period is None:
            period = self.cfg.atr_period
        _ensure_ohlc(df)
        df = _sort_by_date(df)
        base_cols = ["trade_date"]
        if "stock_code" in df.columns:
            base_cols.append("stock_code")
        result = df[base_cols].copy()
        high, low, close = df["high"], df["low"], df["close"]
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        result[f"atr{period}"] = tr.ewm(alpha=1 / period, adjust=False).mean()
        return result

    def ma_bullish_alignment(self, df, periods=None):
        if periods is None:
            periods = self.cfg.ma_periods
        ma_df = self.ma(df, periods=periods)
        ma_cols = [f"ma{p}" for p in sorted(periods)]
        valid = ma_df[ma_cols].notna().all(axis=1)
        alignment = True
        for i in range(len(ma_cols) - 1):
            alignment = alignment & (ma_df[ma_cols[i]] > ma_df[ma_cols[i + 1]])
        result = ma_df[["trade_date"]].copy()
        if "stock_code" in ma_df.columns:
            result["stock_code"] = ma_df["stock_code"]
        result["bullish_alignment"] = alignment & valid
        result["alignment_count"] = sum(
            (ma_df[c] > ma_df[ma_cols[i + 1]]) for i, c in enumerate(ma_cols[:-1])
        )
        return result

    def volume_factor(self, df, periods=None):
        if periods is None:
            periods = self.cfg.volume_ma_periods
        if "volume" not in df.columns:
            raise ValueError("缺少 volume 列")
        df = _sort_by_date(df)
        base_cols = ["trade_date"]
        if "stock_code" in df.columns:
            base_cols.append("stock_code")
        result = df[base_cols].copy()
        result["volume"] = df["volume"]
        for p in periods:
            result[f"vol_ma{p}"] = df["volume"].rolling(window=p).mean()
        for p in periods:
            ma_col = f"vol_ma{p}"
            result[f"vol_ratio{p}"] = df["volume"] / result[ma_col].replace(0, np.nan)
        result["volume_std20"] = df["volume"].rolling(window=20).std()
        result["vol_breakout"] = df["volume"] > result["vol_ma5"] * 1.5
        return result

    def momentum(self, df, periods=None):
        if periods is None:
            periods = self.cfg.momentum_periods
        _ensure_ohlc(df)
        df = _sort_by_date(df)
        base_cols = ["trade_date"]
        if "stock_code" in df.columns:
            base_cols.append("stock_code")
        result = df[base_cols].copy()
        result["close"] = df["close"]
        for p in periods:
            result[f"mom{p}"] = df["close"] - df["close"].shift(p)
            result[f"roc{p}"] = df["close"].pct_change(periods=p) * 100
        return result

    def compute_all(self, df):
        _ensure_ohlc(df)
        df = _sort_by_date(df)
        base_cols = ["trade_date"]
        if "stock_code" in df.columns:
            base_cols.append("stock_code")
        result = df[base_cols].copy()

        ma_df = self.ma(df)
        result = result.merge(ma_df.drop(columns=["close"], errors="ignore"), on=base_cols, how="left")

        macd_df = self.macd(df)
        result = result.merge(macd_df.drop(columns=["close"], errors="ignore"), on=base_cols, how="left")

        rsi_df = self.rsi(df)
        result = result.merge(rsi_df.drop(columns=["close"], errors="ignore"), on=base_cols, how="left")

        kdj_df = self.kdj(df)
        result = result.merge(kdj_df, on=base_cols, how="left")

        boll_df = self.boll(df)
        result = result.merge(boll_df.drop(columns=["close"], errors="ignore"), on=base_cols, how="left")

        atr_df = self.atr(df)
        result = result.merge(atr_df, on=base_cols, how="left")

        align_df = self.ma_bullish_alignment(df)
        result = result.merge(align_df, on=base_cols, how="left")

        if "volume" in df.columns:
            vol_df = self.volume_factor(df)
            result = result.merge(vol_df.drop(columns=["volume"], errors="ignore"), on=base_cols, how="left")

        mom_df = self.momentum(df)
        result = result.merge(mom_df.drop(columns=["close"], errors="ignore"), on=base_cols, how="left")

        return result


factors = FactorEngine()