import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta


class FundFlowSignalDetector:

    def __init__(self):
        self.main_force_threshold = 0.3
        self.north_flow_threshold = 0.5
        self.big_order_threshold = 1000000

    def detect_all(self, kline: pd.DataFrame,
                   fund_flow_data: Optional[Dict] = None,
                   north_flow_data: Optional[Dict] = None,
                   big_order_data: Optional[Dict] = None) -> Dict:

        signals = {}

        if fund_flow_data:
            signals.update(self._detect_main_force(fund_flow_data, kline))
        else:
            signals.update(self._detect_main_force_from_kline(kline))

        if north_flow_data:
            signals.update(self._detect_north_flow(north_flow_data))

        if big_order_data:
            signals.update(self._detect_big_order(big_order_data))

        return signals

    def _detect_main_force(self, fund_data: Dict, kline: pd.DataFrame) -> Dict:
        net_inflow = fund_data.get('main_net_inflow', 0)
        total_amount = fund_data.get('total_amount', 1)

        if total_amount == 0:
            total_amount = 1

        inflow_ratio = net_inflow / total_amount

        if inflow_ratio > 0.15:
            level = 3
        elif inflow_ratio > 0.08:
            level = 2
        elif inflow_ratio > 0.03:
            level = 1
        elif inflow_ratio > -0.03:
            level = 0
        elif inflow_ratio > -0.08:
            level = -1
        elif inflow_ratio > -0.15:
            level = -2
        else:
            level = -3

        super_large = fund_data.get('super_large_net', 0)
        large = fund_data.get('large_net', 0)
        medium = fund_data.get('medium_net', 0)
        small = fund_data.get('small_net', 0)

        main_dominant = 1 if (super_large + large) > abs(medium + small) * 0.5 else 0

        return {
            'main_inflow_ratio': round(inflow_ratio, 4),
            'main_inflow_level': level,
            'main_dominant': main_dominant,
            'super_large_net': super_large,
            'large_net': large
        }

    def _detect_main_force_from_kline(self, kline: pd.DataFrame) -> Dict:
        if kline.empty or len(kline) < 5:
            return {'main_inflow_ratio': 0, 'main_inflow_level': 0, 'main_dominant': 0}

        closes = kline['close'].values
        volumes = kline['volume'].values
        opens = kline['open'].values

        up_volume = 0
        down_volume = 0

        for i in range(len(kline)):
            if closes[i] > opens[i]:
                up_volume += volumes[i] * (closes[i] - opens[i]) / opens[i]
            elif closes[i] < opens[i]:
                down_volume += volumes[i] * (opens[i] - closes[i]) / opens[i]

        total = up_volume + down_volume
        if total == 0:
            ratio = 0
        else:
            ratio = (up_volume - down_volume) / total

        if ratio > 0.15:
            level = 3
        elif ratio > 0.08:
            level = 2
        elif ratio > 0.03:
            level = 1
        elif ratio > -0.03:
            level = 0
        elif ratio > -0.08:
            level = -1
        elif ratio > -0.15:
            level = -2
        else:
            level = -3

        return {
            'main_inflow_ratio': round(ratio, 4),
            'main_inflow_level': level,
            'main_dominant': 1 if ratio > 0.05 else 0
        }

    def _detect_north_flow(self, north_data: Dict) -> Dict:
        net_buy = north_data.get('net_buy', 0)
        buy_amount = north_data.get('buy_amount', 0)
        sell_amount = north_data.get('sell_amount', 0)

        if buy_amount == 0:
            buy_amount = 1

        buy_ratio = net_buy / buy_amount

        if net_buy > 0:
            direction = 1
            if buy_ratio > 0.3:
                strength = 'strong'
            elif buy_ratio > 0.1:
                strength = 'moderate'
            else:
                strength = 'weak'
        else:
            direction = -1
            if buy_ratio < -0.3:
                strength = 'strong_sell'
            elif buy_ratio < -0.1:
                strength = 'moderate_sell'
            else:
                strength = 'weak_sell'

        consecutive = north_data.get('consecutive_days', 0)

        return {
            'north_net_buy': net_buy,
            'north_direction': direction,
            'north_strength': strength,
            'north_consecutive': consecutive
        }

    def _detect_big_order(self, order_data: Dict) -> Dict:
        big_buy_count = order_data.get('big_buy_count', 0)
        big_sell_count = order_data.get('big_sell_count', 0)
        big_buy_amount = order_data.get('big_buy_amount', 0)
        big_sell_amount = order_data.get('big_sell_amount', 0)

        net_count = big_buy_count - big_sell_count
        net_amount = big_buy_amount - big_sell_amount

        if big_buy_count + big_sell_count > 0:
            count_ratio = net_count / (big_buy_count + big_sell_count)
        else:
            count_ratio = 0

        if net_amount > 0:
            bias = 'buy'
        elif net_amount < 0:
            bias = 'sell'
        else:
            bias = 'neutral'

        return {
            'big_order_net_count': net_count,
            'big_order_net_amount': net_amount,
            'big_order_count_ratio': round(count_ratio, 4),
            'big_order_bias': bias
        }