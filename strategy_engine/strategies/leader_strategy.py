import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from enum import Enum

from strategy_engine.signals.trend_signals import TrendSignalDetector
from strategy_engine.signals.momentum_signals import MomentumSignalDetector
from strategy_engine.signals.volume_signals import VolumeSignalDetector
from strategy_engine.signals.fund_flow_signals import FundFlowSignalDetector


class LeaderTier(Enum):
    TRUE_LEADER = "真龙头"
    TIER1 = "第一梯队"
    TIER2 = "第二梯队"
    CATCHUP = "补涨龙头"
    FOLLOWER = "跟风股"


class LeaderStrategy:
    def __init__(self):
        self.trend_detector = TrendSignalDetector()
        self.momentum_detector = MomentumSignalDetector()
        self.volume_detector = VolumeSignalDetector()
        self.fund_detector = FundFlowSignalDetector()

        self.leader_history: Dict[str, List[Dict]] = {}

    def identify_true_leader(self, stocks_data: List[Dict],
                             concept_kline: pd.DataFrame) -> List[Dict]:
        if not stocks_data:
            return []

        scored_stocks = []
        for stock in stocks_data:
            score_result = self._score_leader_candidate(stock, concept_kline)
            scored_stocks.append(score_result)

        scored_stocks.sort(key=lambda x: x['total_score'], reverse=True)

        if scored_stocks:
            self._assign_tiers(scored_stocks)

        return scored_stocks

    def _score_leader_candidate(self, stock: Dict,
                                concept_kline: pd.DataFrame) -> Dict:
        stock_code = stock.get('stock_code', '')
        stock_name = stock.get('stock_name', '')
        kline = stock.get('kline', pd.DataFrame())

        score = 0.0

        first_limit_score = self._score_first_limit_up(stock)
        score += first_limit_score

        seal_score = self._score_seal_volume(stock, kline)
        score += seal_score

        drive_score = self._score_drive_effect(stock, concept_kline)
        score += drive_score

        momentum_score = self._score_leader_momentum(stock, kline)
        score += momentum_score

        fund_score = self._score_leader_fund(stock)
        score += fund_score

        market_cap_score = self._score_market_cap_fit(stock)
        score += market_cap_score

        return {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'total_score': round(score, 2),
            'components': {
                'first_limit': first_limit_score,
                'seal_volume': seal_score,
                'drive_effect': drive_score,
                'momentum': momentum_score,
                'fund_flow': fund_score,
                'market_cap': market_cap_score,
            },
            'tier': None,
        }

    def _score_first_limit_up(self, stock: Dict) -> float:
        score = 0.0

        limit_time = stock.get('first_limit_time', '')
        if limit_time:
            hour = int(limit_time.split(':')[0]) if ':' in limit_time else 10
            minute = int(limit_time.split(':')[1]) if ':' in limit_time else 0
            minutes_from_open = (hour - 9) * 60 + minute - 30

            if minutes_from_open <= 30:
                score += 40
            elif minutes_from_open <= 60:
                score += 30
            elif minutes_from_open <= 120:
                score += 20
            else:
                score += 10

        consecutive_limits = stock.get('consecutive_limit_up', 0)
        if consecutive_limits >= 5:
            score += 30
        elif consecutive_limits >= 3:
            score += 25
        elif consecutive_limits >= 2:
            score += 15
        elif consecutive_limits == 1:
            score += 5

        is_first_in_sector = stock.get('is_first_in_sector', False)
        if is_first_in_sector:
            score += 20

        return min(score, 100)

    def _score_seal_volume(self, stock: Dict, kline: pd.DataFrame) -> float:
        score = 0.0

        seal_ratio = stock.get('seal_volume_ratio', 0)
        if seal_ratio > 5:
            score += 35
        elif seal_ratio > 3:
            score += 25
        elif seal_ratio > 1.5:
            score += 15
        elif seal_ratio > 1:
            score += 5

        seal_stability = stock.get('seal_stability', 0)
        if seal_stability > 0.9:
            score += 35
        elif seal_stability > 0.7:
            score += 25
        elif seal_stability > 0.5:
            score += 15
        else:
            score += 5

        if not kline.empty:
            volume_detector = VolumeSignalDetector()
            vol_signals = volume_detector.detect_all(kline)
            if vol_signals.get('vol_status') == 'blowout':
                score += 20

        return min(score, 100)

    def _score_drive_effect(self, stock: Dict, concept_kline: pd.DataFrame) -> float:
        score = 0.0

        driven_stocks = stock.get('driven_stocks_count', 0)
        if driven_stocks >= 10:
            score += 40
        elif driven_stocks >= 5:
            score += 30
        elif driven_stocks >= 3:
            score += 20
        elif driven_stocks >= 1:
            score += 10

        sector_boost = stock.get('sector_boost_pct', 0)
        if sector_boost > 3:
            score += 30
        elif sector_boost > 1.5:
            score += 20
        elif sector_boost > 0.5:
            score += 10

        correlation = stock.get('concept_correlation', 0)
        if correlation > 0.8:
            score += 20
        elif correlation > 0.6:
            score += 10

        return min(score, 100)

    def _score_leader_momentum(self, stock: Dict, kline: pd.DataFrame) -> float:
        score = 0.0

        if not kline.empty and len(kline) >= 30:
            momentum_detector = MomentumSignalDetector()
            trend_detector = TrendSignalDetector()

            mom_signals = momentum_detector.detect_all(kline)
            trend_signals = trend_detector.detect_all(kline)

            if mom_signals.get('macd_cross') == 'golden':
                score += 20
            elif mom_signals.get('macd_above_zero') == 1:
                score += 10

            if trend_signals.get('ma_bullish_alignment') == 1:
                score += 20

            consecutive = trend_signals.get('consecutive_up', {})
            if isinstance(consecutive, dict):
                level = consecutive.get('level', 0)
                score += level * 10

            boll_pos = mom_signals.get('boll_position', 0)
            if boll_pos == 2:
                score += 15

            rsi = mom_signals.get('rsi_value', 50)
            if 50 <= rsi <= 75:
                score += 10

        return min(score, 100)

    def _score_leader_fund(self, stock: Dict) -> float:
        score = 0.0

        main_inflow = stock.get('main_net_inflow', 0)
        if main_inflow > 500000000:
            score += 40
        elif main_inflow > 100000000:
            score += 30
        elif main_inflow > 50000000:
            score += 20
        elif main_inflow > 0:
            score += 10

        big_order_buy = stock.get('big_order_buy_ratio', 0)
        if big_order_buy > 0.3:
            score += 30
        elif big_order_buy > 0.2:
            score += 20
        elif big_order_buy > 0.1:
            score += 10

        institution_holding = stock.get('institution_holding_pct', 0)
        if institution_holding > 10:
            score += 20
        elif institution_holding > 5:
            score += 10

        return min(score, 100)

    def _score_market_cap_fit(self, stock: Dict) -> float:
        score = 0.0

        market_cap = stock.get('market_cap', 0)
        if 5000000000 <= market_cap <= 50000000000:
            score += 30
        elif 50000000000 < market_cap <= 100000000000:
            score += 25
        elif 100000000000 < market_cap <= 300000000000:
            score += 15
        elif market_cap > 300000000000:
            score += 5
        else:
            score += 10

        float_cap = stock.get('float_market_cap', 0)
        if market_cap > 0:
            float_ratio = float_cap / market_cap
            if 0.3 <= float_ratio <= 0.7:
                score += 20
            elif float_ratio > 0.2:
                score += 10

        price = stock.get('price', 0)
        if 5 <= price <= 50:
            score += 20
        elif 50 < price <= 100:
            score += 15
        elif price < 5:
            score += 5

        return min(score, 100)

    def _assign_tiers(self, scored_stocks: List[Dict]):
        if not scored_stocks:
            return

        if scored_stocks[0]['total_score'] >= 75:
            scored_stocks[0]['tier'] = LeaderTier.TRUE_LEADER.value

        tier1_count = 0
        for stock in scored_stocks:
            if stock['tier'] is not None:
                continue
            if stock['total_score'] >= 65 and tier1_count < 3:
                stock['tier'] = LeaderTier.TIER1.value
                tier1_count += 1

        tier2_count = 0
        for stock in scored_stocks:
            if stock['tier'] is not None:
                continue
            if stock['total_score'] >= 50 and tier2_count < 5:
                stock['tier'] = LeaderTier.TIER2.value
                tier2_count += 1

        for stock in scored_stocks:
            if stock['tier'] is not None:
                continue
            if stock['total_score'] >= 35:
                stock['tier'] = LeaderTier.CATCHUP.value
            else:
                stock['tier'] = LeaderTier.FOLLOWER.value

    def identify_catchup_leader(self, stocks_data: List[Dict],
                                current_leader_code: str) -> List[Dict]:
        candidates = []

        for stock in stocks_data:
            if stock.get('stock_code') == current_leader_code:
                continue

            kline = stock.get('kline', pd.DataFrame())
            if kline.empty or len(kline) < 20:
                continue

            momentum_detector = MomentumSignalDetector()
            trend_detector = TrendSignalDetector()
            volume_detector = VolumeSignalDetector()

            mom_signals = momentum_detector.detect_all(kline)
            trend_signals = trend_detector.detect_all(kline)
            vol_signals = volume_detector.detect_all(kline)

            catchup_score = 0.0

            if mom_signals.get('macd_cross') == 'golden':
                catchup_score += 30

            if trend_signals.get('ma_bullish_alignment') == 1:
                catchup_score += 20

            consecutive = trend_signals.get('consecutive_up', {})
            if isinstance(consecutive, dict):
                days = consecutive.get('days', 0)
                if days >= 2:
                    catchup_score += 15

            if vol_signals.get('vol_status') in ['blowout', 'expansion']:
                catchup_score += 20

            change_pct = stock.get('change_pct', 0)
            if 3 <= change_pct <= 8:
                catchup_score += 15

            if catchup_score >= 60:
                candidates.append({
                    'stock_code': stock.get('stock_code', ''),
                    'stock_name': stock.get('stock_name', ''),
                    'catchup_score': catchup_score,
                    'change_pct': change_pct,
                })

        candidates.sort(key=lambda x: x['catchup_score'], reverse=True)
        return candidates[:5]

    def manage_leader_rotation(self, current_leaders: List[Dict],
                               new_candidates: List[Dict]) -> Dict:
        rotation_signal = {
            'hold_leaders': [],
            'add_leaders': [],
            'remove_leaders': [],
            'promote_catchup': [],
        }

        current_codes = {l['stock_code'] for l in current_leaders}

        for leader in current_leaders:
            code = leader['stock_code']
            score = leader.get('total_score', 0)
            tier = leader.get('tier', '')

            if tier == LeaderTier.TRUE_LEADER.value and score >= 70:
                rotation_signal['hold_leaders'].append(code)
            elif tier in [LeaderTier.TRUE_LEADER.value, LeaderTier.TIER1.value] and score >= 55:
                rotation_signal['hold_leaders'].append(code)
            else:
                rotation_signal['remove_leaders'].append(code)

        for candidate in new_candidates:
            code = candidate['stock_code']
            if code in current_codes:
                continue
            score = candidate.get('total_score', 0)
            tier = candidate.get('tier', '')

            if tier == LeaderTier.TRUE_LEADER.value and score >= 80:
                rotation_signal['add_leaders'].append(code)
            elif tier == LeaderTier.CATCHUP.value and score >= 60:
                rotation_signal['promote_catchup'].append(code)

        return rotation_signal