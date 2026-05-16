import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


class VolumeSignalDetector:

    def __init__(self):
        self.volume_ma_period = 20
        self.blowout_ratio = 2.0
        self.shrink_ratio = 0.5
        self.obv_ma_period = 20

    def detect_all(self, kline: pd.DataFrame) -> Dict:
        if kline.empty or len(kline) < 30:
            return {}

        volumes = kline['volume'].values
        closes = kline['close'].values
        opens = kline['open'].values

        signals = {}
        signals.update(self._detect_volume_change(volumes))
        signals.update(self._detect_price_volume(closes, volumes, opens))
        signals.update(self._detect_obv(closes, volumes))

        return signals

    def _detect_volume_change(self, volumes: np.ndarray) -> Dict:
        n = self.volume_ma_period
        vol_ma = np.mean(volumes[-n:])
        current_vol = volumes[-1]

        if vol_ma == 0:
            return {
                'vol_ratio': 1.0,
                'vol_status': 'normal',
                'vol_blowout': 0,
                'vol_shrink': 0
            }

        ratio = current_vol / vol_ma

        if ratio >= self.blowout_ratio:
            status = 'blowout'
            blowout = 1
        elif ratio >= 1.5:
            status = 'expansion'
            blowout = 0
        elif ratio <= self.shrink_ratio:
            status = 'shrink'
            blowout = 0
        else:
            status = 'normal'
            blowout = 0

        shrink = 1 if ratio <= self.shrink_ratio else 0

        consecutive_low = 0
        for i in range(len(volumes) - 1, -1, -1):
            if volumes[i] < vol_ma * 0.6:
                consecutive_low += 1
            else:
                break

        return {
            'vol_ratio': round(ratio, 2),
            'vol_status': status,
            'vol_blowout': blowout,
            'vol_shrink': shrink,
            'vol_consecutive_low': consecutive_low
        }

    def _detect_price_volume(self, closes: np.ndarray, volumes: np.ndarray, opens: np.ndarray) -> Dict:
        change = closes[-1] - closes[-2]
        vol_change = volumes[-1] - volumes[-2]

        if change > 0 and vol_change > 0:
            coordination = 'bullish_sync'
        elif change < 0 and vol_change < 0:
            coordination = 'bearish_sync'
        elif change > 0 and vol_change < 0:
            coordination = 'bullish_diverge'
        elif change < 0 and vol_change > 0:
            coordination = 'bearish_diverge'
        else:
            coordination = 'neutral'

        vol_ma = np.mean(volumes[-self.volume_ma_period:])
        price_ma = np.mean(closes[-self.volume_ma_period:])

        if vol_ma > 0 and price_ma > 0:
            recent_vol_price_ratio = volumes[-5:].mean() / vol_ma / (closes[-5:].mean() / price_ma) if closes[-5:].mean() > 0 else 1
        else:
            recent_vol_price_ratio = 1

        is_bullish_vol = 0
        if closes[-1] > opens[-1] and volumes[-1] > vol_ma * 1.2:
            is_bullish_vol = 1
        elif closes[-1] < opens[-1] and volumes[-1] > vol_ma * 1.2:
            is_bullish_vol = -1

        return {
            'pv_coordination': coordination,
            'pv_ratio': round(recent_vol_price_ratio, 2),
            'bullish_volume': is_bullish_vol
        }

    def _detect_obv(self, closes: np.ndarray, volumes: np.ndarray) -> Dict:
        obv = np.zeros(len(closes))
        obv[0] = volumes[0]

        for i in range(1, len(closes)):
            if closes[i] > closes[i - 1]:
                obv[i] = obv[i - 1] + volumes[i]
            elif closes[i] < closes[i - 1]:
                obv[i] = obv[i - 1] - volumes[i]
            else:
                obv[i] = obv[i - 1]

        obv_ma = np.mean(obv[-self.obv_ma_period:])
        obv_ma_prev = np.mean(obv[-(self.obv_ma_period + 1):-1])

        current_obv = obv[-1]
        prev_obv = obv[-2]

        if current_obv > obv_ma and prev_obv <= obv_ma_prev:
            trend = 'breakout_up'
        elif current_obv < obv_ma and prev_obv >= obv_ma_prev:
            trend = 'breakout_down'
        elif current_obv > obv_ma:
            trend = 'above_ma'
        else:
            trend = 'below_ma'

        obv_divergence = 0
        price_high = np.max(closes[-10:])
        price_low = np.min(closes[-10:])
        obv_high = np.max(obv[-10:])
        obv_low = np.min(obv[-10:])

        if closes[-1] > price_high * 0.98 and obv[-1] < obv_high * 0.95:
            obv_divergence = -1
        elif closes[-1] < price_low * 1.02 and obv[-1] > obv_low * 1.05:
            obv_divergence = 1

        return {
            'obv_trend': trend,
            'obv_divergence': obv_divergence
        }