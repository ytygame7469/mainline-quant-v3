import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


class MomentumSignalDetector:

    def __init__(self):
        self.rsi_period = 14
        self.rsi_overbought = 80
        self.rsi_oversold = 20
        self.kdj_n = 9
        self.kdj_m1 = 3
        self.kdj_m2 = 3
        self.bb_period = 20
        self.bb_std = 2

    def detect_all(self, kline: pd.DataFrame) -> Dict:
        if kline.empty or len(kline) < 30:
            return {}

        closes = kline['close'].values
        highs = kline['high'].values
        lows = kline['low'].values
        volumes = kline['volume'].values if 'volume' in kline.columns else None

        signals = {}
        signals.update(self._detect_macd(closes))
        signals.update(self._detect_rsi(closes))
        signals.update(self._detect_kdj(highs, lows, closes))
        signals.update(self._detect_bollinger(closes))

        return signals

    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        result = np.zeros_like(data)
        multiplier = 2 / (period + 1)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = (data[i] - result[i - 1]) * multiplier + result[i - 1]
        return result

    def _detect_macd(self, closes: np.ndarray) -> Dict:
        fast = 12
        slow = 26
        signal_period = 9

        ema_fast = self._ema(closes, fast)
        ema_slow = self._ema(closes, slow)
        dif = ema_fast - ema_slow
        dea = self._ema(dif, signal_period)
        macd_bar = 2 * (dif - dea)

        current_dif = dif[-1]
        current_dea = dea[-1]
        prev_dif = dif[-2]
        prev_dea = dea[-2]
        current_bar = macd_bar[-1]
        prev_bar = macd_bar[-2]

        if prev_dif <= prev_dea and current_dif > current_dea:
            cross = 'golden'
        elif prev_dif >= prev_dea and current_dif < current_dea:
            cross = 'dead'
        else:
            cross = 'none'

        bar_direction = 1 if current_bar > prev_bar else (-1 if current_bar < prev_bar else 0)

        return {
            'macd_dif': round(current_dif, 4),
            'macd_dea': round(current_dea, 4),
            'macd_bar': round(current_bar, 4),
            'macd_cross': cross,
            'macd_bar_direction': bar_direction,
            'macd_above_zero': 1 if current_dif > 0 else -1
        }

    def _detect_rsi(self, closes: np.ndarray) -> Dict:
        n = self.rsi_period
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-n:])
        avg_loss = np.mean(losses[-n:])

        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))

        prev_deltas = deltas[-(n + 1):-1]
        prev_gains = np.where(prev_deltas > 0, prev_deltas, 0)
        prev_losses = np.where(prev_deltas < 0, -prev_deltas, 0)
        prev_avg_gain = np.mean(prev_gains)
        prev_avg_loss = np.mean(prev_losses)

        if prev_avg_loss == 0:
            prev_rsi = 100.0
        else:
            prev_rs = prev_avg_gain / prev_avg_loss
            prev_rsi = 100.0 - (100.0 / (1.0 + prev_rs))

        signal = 0
        if prev_rsi < self.rsi_oversold and rsi > self.rsi_oversold:
            signal = 1
        elif prev_rsi > self.rsi_overbought and rsi < self.rsi_overbought:
            signal = -1

        zone = 'overbought' if rsi > self.rsi_overbought else ('oversold' if rsi < self.rsi_oversold else 'neutral')

        return {
            'rsi_value': round(rsi, 2),
            'rsi_signal': signal,
            'rsi_zone': zone
        }

    def _detect_kdj(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> Dict:
        n = self.kdj_n
        if len(closes) < n:
            return {'kdj_k': 50, 'kdj_d': 50, 'kdj_j': 50, 'kdj_signal': 0}

        low_n = np.min(lows[-n:])
        high_n = np.max(highs[-n:])

        if high_n == low_n:
            rsv = 50.0
        else:
            rsv = (closes[-1] - low_n) / (high_n - low_n) * 100

        prev_low = np.min(lows[-(n + 1):-1])
        prev_high = np.max(highs[-(n + 1):-1])
        if prev_high == prev_low:
            prev_rsv = 50.0
        else:
            prev_rsv = (closes[-2] - prev_low) / (prev_high - prev_low) * 100

        m1 = self.kdj_m1
        m2 = self.kdj_m2

        k = (rsv + (m1 - 1) * 50) / m1
        d = (k + (m2 - 1) * 50) / m2
        j = 3 * k - 2 * d

        prev_k = (prev_rsv + (m1 - 1) * 50) / m1
        prev_d = (prev_k + (m2 - 1) * 50) / m2

        signal = 0
        if prev_k <= prev_d and k > d and k < 30:
            signal = 1
        elif prev_k >= prev_d and k < d and k > 70:
            signal = -1

        return {
            'kdj_k': round(k, 2),
            'kdj_d': round(d, 2),
            'kdj_j': round(j, 2),
            'kdj_signal': signal
        }

    def _detect_bollinger(self, closes: np.ndarray) -> Dict:
        n = self.bb_period
        if len(closes) < n:
            return {'boll_upper': 0, 'boll_mid': 0, 'boll_lower': 0, 'boll_position': 0, 'boll_break': 0}

        mid = np.mean(closes[-n:])
        std = np.std(closes[-n:], ddof=1)
        upper = mid + self.bb_std * std
        lower = mid - self.bb_std * std
        price = closes[-1]
        price_prev = closes[-2]

        prev_mid = np.mean(closes[-(n + 1):-1])
        prev_std = np.std(closes[-(n + 1):-1], ddof=1)
        prev_upper = prev_mid + self.bb_std * prev_std
        prev_lower = prev_mid - self.bb_std * prev_std

        if price > upper:
            position = 2
        elif price > mid:
            position = 1
        elif price > lower:
            position = -1
        else:
            position = -2

        break_signal = 0
        if price_prev <= prev_upper and price > upper:
            break_signal = 1
        elif price_prev >= prev_lower and price < lower:
            break_signal = -1

        width_pct = (upper - lower) / mid * 100

        return {
            'boll_upper': round(upper, 2),
            'boll_mid': round(mid, 2),
            'boll_lower': round(lower, 2),
            'boll_position': position,
            'boll_break': break_signal,
            'boll_width': round(width_pct, 2)
        }