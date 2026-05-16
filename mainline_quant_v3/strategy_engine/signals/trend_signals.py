import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


class TrendSignalDetector:

    def __init__(self):
        self.ma_periods = [5, 10, 20, 60]
        self.adx_period = 14
        self.adx_threshold = 25

    def detect_all(self, kline: pd.DataFrame) -> Dict:
        if kline.empty or len(kline) < 60:
            return {}

        closes = kline['close'].values
        highs = kline['high'].values
        lows = kline['low'].values

        signals = {}

        ma_signals = self._detect_ma_cross(closes)
        signals.update(ma_signals)

        signals['ma_bullish_alignment'] = self._detect_ma_alignment(closes)
        signals['adx_trend_strength'] = self._detect_adx(highs, lows, closes)
        signals['consecutive_up'] = self._detect_consecutive_up(kline)

        return signals

    def _detect_ma_cross(self, closes: np.ndarray) -> Dict:
        result = {}

        for period in self.ma_periods:
            ma = np.mean(closes[-period:])
            ma_prev = np.mean(closes[-(period + 1):-1])
            price = closes[-1]
            price_prev = closes[-2]

            ma_name = f'ma{period}'
            if price_prev <= ma_prev and price > ma:
                result[f'{ma_name}_golden_cross'] = 1
            elif price_prev >= ma_prev and price < ma:
                result[f'{ma_name}_dead_cross'] = -1
            else:
                above = 1 if price > ma else -1
                result[f'{ma_name}_position'] = above

        return result

    def _detect_ma_alignment(self, closes: np.ndarray) -> int:
        mas = []
        for period in self.ma_periods:
            mas.append(np.mean(closes[-period:]))

        is_bullish = all(mas[i] > mas[i + 1] for i in range(len(mas) - 1))
        is_bearish = all(mas[i] < mas[i + 1] for i in range(len(mas) - 1))

        if is_bullish:
            return 1
        elif is_bearish:
            return -1
        return 0

    def _detect_adx(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> Dict:
        n = self.adx_period
        if len(closes) < n + 1:
            return {'adx': 0, 'trend_strong': 0}

        tr_list = []
        plus_dm_list = []
        minus_dm_list = []

        for i in range(1, n + 1):
            idx = -(n + 1) + i
            high = highs[idx]
            low = lows[idx]
            high_prev = highs[idx - 1]
            low_prev = lows[idx - 1]
            close_prev = closes[idx - 1]

            tr = max(high - low, abs(high - close_prev), abs(low - close_prev))
            tr_list.append(tr)

            up_move = high - high_prev
            down_move = low_prev - low

            plus_dm = up_move if up_move > down_move and up_move > 0 else 0
            minus_dm = down_move if down_move > up_move and down_move > 0 else 0

            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)

        atr = np.mean(tr_list)
        if atr == 0:
            return {'adx': 0, 'trend_strong': 0}

        plus_di = np.mean(plus_dm_list) / atr * 100
        minus_di = np.mean(minus_dm_list) / atr * 100
        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0

        prev_dx_list = []
        for j in range(2, n + 2):
            idx_start = -(n + 1) + j - n
            idx_end = -(n + 1) + j
            prev_tr = max(highs[idx_end] - lows[idx_end],
                          abs(highs[idx_end] - closes[idx_end - 1]),
                          abs(lows[idx_end] - closes[idx_end - 1]))
            prev_atr = np.mean(tr_list[j - n - 1:j - 1]) if j > n else atr
            if prev_atr == 0:
                prev_dx_list.append(0)
                continue
            prev_plus_di = np.mean(plus_dm_list[max(0, j - n - 1):j - 1]) / prev_atr * 100 if j > 1 else plus_di
            prev_minus_di = np.mean(minus_dm_list[max(0, j - n - 1):j - 1]) / prev_atr * 100 if j > 1 else minus_di
            pdx = abs(prev_plus_di - prev_minus_di) / (prev_plus_di + prev_minus_di) * 100 if (prev_plus_di + prev_minus_di) > 0 else 0
            prev_dx_list.append(pdx)

        adx = np.mean([dx] + prev_dx_list)

        trend_strong = 1 if adx > self.adx_threshold and plus_di > minus_di else (-1 if adx > self.adx_threshold and plus_di < minus_di else 0)

        return {
            'adx': round(adx, 2),
            'plus_di': round(plus_di, 2),
            'minus_di': round(minus_di, 2),
            'trend_strong': trend_strong
        }

    def _detect_consecutive_up(self, kline: pd.DataFrame) -> Dict:
        change_pct_col = 'change_pct' if 'change_pct' in kline.columns else None

        if change_pct_col:
            changes = kline[change_pct_col].values
        else:
            closes = kline['close'].values
            changes = np.diff(closes) / closes[:-1] * 100

        consecutive = 0
        for i in range(len(changes) - 1, -1, -1):
            if changes[i] > 0:
                consecutive += 1
            else:
                break

        if consecutive >= 5:
            level = 3
        elif consecutive >= 3:
            level = 2
        elif consecutive >= 2:
            level = 1
        else:
            level = 0

        return {'days': consecutive, 'level': level}