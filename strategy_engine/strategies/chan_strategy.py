import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from enum import Enum

from strategy_engine.signals.trend_signals import TrendSignalDetector
from strategy_engine.signals.momentum_signals import MomentumSignalDetector
from strategy_engine.signals.volume_signals import VolumeSignalDetector


class ChanBuyPoint(Enum):
    BUY1 = "一买"
    BUY2 = "二买"
    BUY3 = "三买"
    SELL1 = "一卖"
    SELL2 = "二卖"
    SELL3 = "三卖"
    NONE = "无"


class ChanStrategy:
    def __init__(self):
        self.trend_detector = TrendSignalDetector()
        self.momentum_detector = MomentumSignalDetector()
        self.volume_detector = VolumeSignalDetector()

        self.min_bi_len = 6
        self.max_bi_num = 50

    def detect_fenxing(self, kline: pd.DataFrame) -> Dict:
        if kline.empty or len(kline) < 6:
            return {'top_fx': [], 'bottom_fx': [], 'latest_fx': ChanBuyPoint.NONE.value}

        highs = kline['high'].values
        lows = kline['low'].values

        top_fx = self._find_top_fenxing(highs)
        bottom_fx = self._find_bottom_fenxing(lows)

        latest_fx = ChanBuyPoint.NONE.value
        if top_fx and bottom_fx:
            if top_fx[-1]['index'] > bottom_fx[-1]['index']:
                latest_fx = 'top'
            else:
                latest_fx = 'bottom'

        return {
            'top_fx': top_fx,
            'bottom_fx': bottom_fx,
            'latest_fx': latest_fx,
            'top_count': len(top_fx),
            'bottom_count': len(bottom_fx),
        }

    def _find_top_fenxing(self, highs: np.ndarray) -> List[Dict]:
        fx_list = []
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i - 1] and highs[i] > highs[i - 2] and \
               highs[i] > highs[i + 1] and highs[i] > highs[i + 2]:
                fx_list.append({'index': i, 'price': float(highs[i])})
        return fx_list

    def _find_bottom_fenxing(self, lows: np.ndarray) -> List[Dict]:
        fx_list = []
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i - 1] and lows[i] < lows[i - 2] and \
               lows[i] < lows[i + 1] and lows[i] < lows[i + 2]:
                fx_list.append({'index': i, 'price': float(lows[i])})
        return fx_list

    def detect_bi(self, kline: pd.DataFrame) -> Dict:
        fx_result = self.detect_fenxing(kline)
        top_fx = fx_result['top_fx']
        bottom_fx = fx_result['bottom_fx']

        bi_list = []
        all_fx = sorted(
            [('top', f) for f in top_fx] + [('bottom', f) for f in bottom_fx],
            key=lambda x: x[1]['index']
        )

        if len(all_fx) < 2:
            return {'bi_list': [], 'latest_bi_direction': 'unknown'}

        prev_type, prev_fx = all_fx[0]
        for i in range(1, len(all_fx)):
            curr_type, curr_fx = all_fx[i]
            if curr_type != prev_type:
                bi_len = curr_fx['index'] - prev_fx['index']
                if bi_len >= self.min_bi_len:
                    direction = 'down' if prev_type == 'top' else 'up'
                    bi_list.append({
                        'start_idx': prev_fx['index'],
                        'end_idx': curr_fx['index'],
                        'start_price': prev_fx['price'],
                        'end_price': curr_fx['price'],
                        'direction': direction,
                        'length': bi_len,
                        'change_pct': round((curr_fx['price'] - prev_fx['price']) / prev_fx['price'] * 100, 2),
                    })
                    prev_type, prev_fx = curr_type, curr_fx

        latest_direction = bi_list[-1]['direction'] if bi_list else 'unknown'

        return {
            'bi_list': bi_list[-self.max_bi_num:],
            'bi_count': len(bi_list),
            'latest_bi_direction': latest_direction,
        }

    def detect_zhongshu(self, kline: pd.DataFrame) -> Dict:
        bi_result = self.detect_bi(kline)
        bi_list = bi_result['bi_list']

        if len(bi_list) < 3:
            return {'zhongshu_list': [], 'latest_zs': None}

        zhongshu_list = []
        i = 0
        while i < len(bi_list) - 2:
            bi1 = bi_list[i]
            bi2 = bi_list[i + 1]
            bi3 = bi_list[i + 2]

            if bi1['direction'] == 'up' and bi2['direction'] == 'down' and bi3['direction'] == 'up':
                zs_high = min(bi1['end_price'], bi3['start_price'])
                zs_low = max(bi2['end_price'], bi3['start_price']) if bi2['end_price'] > bi3['start_price'] else max(bi1['start_price'], bi2['start_price'])

                if zs_high > zs_low:
                    zhongshu_list.append({
                        'start_idx': bi1['end_idx'],
                        'end_idx': bi3['start_idx'],
                        'zg': round(zs_high, 2),
                        'zd': round(zs_low, 2),
                        'zz': round((zs_high + zs_low) / 2, 2),
                        'width': round((zs_high - zs_low) / zs_low * 100, 2),
                        'bi_range': [bi1, bi2, bi3],
                    })
                    i += 2
                    continue

            if bi1['direction'] == 'down' and bi2['direction'] == 'up' and bi3['direction'] == 'down':
                zs_low = max(bi1['end_price'], bi3['start_price'])
                zs_high = min(bi2['end_price'], bi3['start_price']) if bi2['end_price'] < bi3['start_price'] else min(bi1['start_price'], bi2['start_price'])

                if zs_high > zs_low:
                    zhongshu_list.append({
                        'start_idx': bi1['end_idx'],
                        'end_idx': bi3['start_idx'],
                        'zg': round(zs_high, 2),
                        'zd': round(zs_low, 2),
                        'zz': round((zs_high + zs_low) / 2, 2),
                        'width': round((zs_high - zs_low) / zs_low * 100, 2),
                        'bi_range': [bi1, bi2, bi3],
                    })
                    i += 2
                    continue

            i += 1

        latest_zs = zhongshu_list[-1] if zhongshu_list else None

        return {
            'zhongshu_list': zhongshu_list,
            'zs_count': len(zhongshu_list),
            'latest_zs': latest_zs,
        }

    def detect_buy_sell_points(self, kline: pd.DataFrame) -> Dict:
        zs_result = self.detect_zhongshu(kline)
        zhongshu_list = zs_result['zhongshu_list']
        bi_result = self.detect_bi(kline)
        bi_list = bi_result['bi_list']

        buy_points = []
        sell_points = []

        if len(zhongshu_list) >= 1 and len(bi_list) >= 5:
            latest_zs = zhongshu_list[-1]
            zg = latest_zs['zg']
            zd = latest_zs['zd']

            last_bi = bi_list[-1]
            prev_bi = bi_list[-2] if len(bi_list) >= 2 else None

            if last_bi['direction'] == 'down':
                if len(zhongshu_list) >= 2:
                    prev_zs = zhongshu_list[-2]
                    if last_bi['end_price'] < prev_zs['zd']:
                        momentum = self.momentum_detector.detect_all(kline)
                        rsi = momentum.get('rsi_value', 50)
                        macd_cross = momentum.get('macd_cross', 'none')

                        if rsi < 30 or macd_cross == 'golden':
                            buy_points.append({
                                'type': ChanBuyPoint.BUY1.value,
                                'price': last_bi['end_price'],
                                'index': last_bi['end_idx'],
                                'description': '一买：趋势背驰，离开第二个中枢后底背驰',
                            })

                if last_bi['end_price'] <= zg and last_bi['end_price'] >= zd:
                    if prev_bi and prev_bi['direction'] == 'up' and prev_bi['end_price'] >= zg:
                        buy_points.append({
                            'type': ChanBuyPoint.BUY3.value,
                            'price': last_bi['end_price'],
                            'index': last_bi['end_idx'],
                            'description': '三买：回调不进中枢',
                        })

                if last_bi['end_price'] < zd:
                    momentum = self.momentum_detector.detect_all(kline)
                    if momentum.get('kdj_signal', 0) == 1:
                        buy_points.append({
                            'type': ChanBuyPoint.BUY2.value,
                            'price': last_bi['end_price'],
                            'index': last_bi['end_idx'],
                            'description': '二买：回调跌破中枢后回升',
                        })

            if last_bi['direction'] == 'up':
                if len(zhongshu_list) >= 2:
                    prev_zs = zhongshu_list[-2]
                    if last_bi['end_price'] > prev_zs['zg']:
                        momentum = self.momentum_detector.detect_all(kline)
                        rsi = momentum.get('rsi_value', 50)
                        macd_cross = momentum.get('macd_cross', 'none')

                        if rsi > 70 or macd_cross == 'dead':
                            sell_points.append({
                                'type': ChanBuyPoint.SELL1.value,
                                'price': last_bi['end_price'],
                                'index': last_bi['end_idx'],
                                'description': '一卖：趋势背驰，离开第二个中枢后顶背驰',
                            })

                if last_bi['end_price'] >= zd and last_bi['end_price'] <= zg:
                    if prev_bi and prev_bi['direction'] == 'down' and prev_bi['end_price'] <= zd:
                        sell_points.append({
                            'type': ChanBuyPoint.SELL3.value,
                            'price': last_bi['end_price'],
                            'index': last_bi['end_idx'],
                            'description': '三卖：反弹不进中枢',
                        })

                if last_bi['end_price'] > zg:
                    momentum = self.momentum_detector.detect_all(kline)
                    if momentum.get('kdj_signal', 0) == -1:
                        sell_points.append({
                            'type': ChanBuyPoint.SELL2.value,
                            'price': last_bi['end_price'],
                            'index': last_bi['end_idx'],
                            'description': '二卖：反弹突破中枢后回落',
                        })

        latest_buy = buy_points[-1] if buy_points else None
        latest_sell = sell_points[-1] if sell_points else None

        return {
            'buy_points': buy_points,
            'sell_points': sell_points,
            'latest_buy': latest_buy,
            'latest_sell': latest_sell,
        }

    def zhongshu_oscillation_trade(self, kline: pd.DataFrame) -> Dict:
        zs_result = self.detect_zhongshu(kline)
        latest_zs = zs_result.get('latest_zs')

        if not latest_zs:
            return {'signal': 'NONE', 'reason': '无中枢'}

        zg = latest_zs['zg']
        zd = latest_zs['zd']
        zz = latest_zs['zz']
        current_price = kline['close'].iloc[-1]

        if current_price <= zd * 1.02:
            momentum = self.momentum_detector.detect_all(kline)
            volume = self.volume_detector.detect_all(kline)

            rsi = momentum.get('rsi_value', 50)
            vol_shrink = volume.get('vol_shrink', 0)

            if rsi < 40 and vol_shrink == 1:
                return {
                    'signal': 'BUY',
                    'price': current_price,
                    'target': zg,
                    'stop_loss': zd * 0.97,
                    'reason': f'中枢下沿买入: ZD={zd}, 缩量+RSI低位',
                }

        if current_price >= zg * 0.98:
            momentum = self.momentum_detector.detect_all(kline)
            rsi = momentum.get('rsi_value', 50)

            if rsi > 60:
                return {
                    'signal': 'SELL',
                    'price': current_price,
                    'target': zd,
                    'reason': f'中枢上沿卖出: ZG={zg}, RSI高位',
                }

        return {
            'signal': 'HOLD',
            'price': current_price,
            'zg': zg,
            'zd': zd,
            'zz': zz,
            'reason': '中枢内震荡，观望',
        }

    def get_trading_signal(self, kline: pd.DataFrame) -> Dict:
        if kline.empty or len(kline) < 60:
            return {'signal': 'NONE', 'reason': '数据不足'}

        bsp_result = self.detect_buy_sell_points(kline)
        zs_trade = self.zhongshu_oscillation_trade(kline)

        latest_buy = bsp_result.get('latest_buy')
        latest_sell = bsp_result.get('latest_sell')

        if latest_buy and latest_sell:
            if latest_buy['index'] > latest_sell['index']:
                primary = 'buy'
            else:
                primary = 'sell'
        elif latest_buy:
            primary = 'buy'
        elif latest_sell:
            primary = 'sell'
        else:
            primary = 'neutral'

        momentum = self.momentum_detector.detect_all(kline)
        trend = self.trend_detector.detect_all(kline)
        volume = self.volume_detector.detect_all(kline)

        if primary == 'buy':
            confirm_count = 0
            if momentum.get('macd_cross') == 'golden' or momentum.get('macd_above_zero') == 1:
                confirm_count += 1
            if trend.get('ma_bullish_alignment') == 1:
                confirm_count += 1
            if volume.get('vol_status') in ['blowout', 'expansion']:
                confirm_count += 1

            if confirm_count >= 2:
                signal = 'STRONG_BUY'
            elif confirm_count >= 1:
                signal = 'BUY'
            else:
                signal = 'WATCH'

            return {
                'signal': signal,
                'buy_point': latest_buy,
                'zs_trade': zs_trade,
                'confirm_count': confirm_count,
            }

        elif primary == 'sell':
            confirm_count = 0
            if momentum.get('macd_cross') == 'dead':
                confirm_count += 1
            if momentum.get('rsi_value', 50) > 70:
                confirm_count += 1
            if trend.get('ma_bullish_alignment') == -1:
                confirm_count += 1

            if confirm_count >= 2:
                signal = 'STRONG_SELL'
            elif confirm_count >= 1:
                signal = 'SELL'
            else:
                signal = 'REDUCE'

            return {
                'signal': signal,
                'sell_point': latest_sell,
                'zs_trade': zs_trade,
                'confirm_count': confirm_count,
            }

        else:
            return {
                'signal': zs_trade.get('signal', 'HOLD'),
                'zs_trade': zs_trade,
                'reason': '无明确买卖点，按中枢震荡处理',
            }