import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from enum import Enum

from strategy_engine.strategies.mainline_strategy import MainlineRotateStrategy
from strategy_engine.strategies.leader_strategy import LeaderStrategy
from strategy_engine.strategies.chan_strategy import ChanStrategy
from strategy_engine.signals.trend_signals import TrendSignalDetector
from strategy_engine.signals.momentum_signals import MomentumSignalDetector
from strategy_engine.signals.volume_signals import VolumeSignalDetector
from strategy_engine.signals.fund_flow_signals import FundFlowSignalDetector


class DecisionLevel(Enum):
    STRONG_BUY = "强烈买入"
    BUY = "买入"
    WATCH = "关注"
    HOLD = "持有"
    REDUCE = "减仓"
    SELL = "卖出"
    STRONG_SELL = "强烈卖出"


class SignalCombiner:
    def __init__(self):
        self.mainline_strategy = MainlineRotateStrategy()
        self.leader_strategy = LeaderStrategy()
        self.chan_strategy = ChanStrategy()

        self.trend_detector = TrendSignalDetector()
        self.momentum_detector = MomentumSignalDetector()
        self.volume_detector = VolumeSignalDetector()
        self.fund_detector = FundFlowSignalDetector()

        self.strategy_weights = {
            'mainline': 0.45,
            'leader': 0.30,
            'chan': 0.25,
        }

        self.signal_mapping = {
            'STRONG_BUY': 2.0,
            'BUY': 1.0,
            'WATCH': 0.3,
            'HOLD': 0.0,
            'REDUCE': -0.3,
            'SELL': -1.0,
            'STRONG_SELL': -2.0,
            'NONE': 0.0,
        }

    def combine(self, concept_code: str, concept_name: str,
                kline: pd.DataFrame,
                stocks_data: Optional[List[Dict]] = None,
                fund_flow_data: Optional[Dict] = None,
                sentiment_data: Optional[Dict] = None,
                sector_data: Optional[Dict] = None,
                valuation_data: Optional[Dict] = None,
                macro_data: Optional[Dict] = None,
                institution_data: Optional[Dict] = None,
                news_data: Optional[Dict] = None) -> Dict:

        mainline_signal = self.mainline_strategy.get_trading_signal(
            concept_code, concept_name, kline,
            fund_flow_data, sentiment_data, sector_data,
            valuation_data, macro_data, institution_data, news_data
        )

        leader_signal = {'signal': 'NONE', 'score': 0, 'leaders': []}
        if stocks_data:
            leaders = self.leader_strategy.identify_true_leader(stocks_data, kline)
            if leaders:
                top_leader = leaders[0]
                leader_score = top_leader['total_score']
                if leader_score >= 75:
                    leader_signal = {'signal': 'STRONG_BUY', 'score': leader_score, 'leaders': leaders[:3]}
                elif leader_score >= 60:
                    leader_signal = {'signal': 'BUY', 'score': leader_score, 'leaders': leaders[:3]}
                elif leader_score >= 45:
                    leader_signal = {'signal': 'WATCH', 'score': leader_score, 'leaders': leaders[:3]}
                else:
                    leader_signal = {'signal': 'NONE', 'score': leader_score, 'leaders': leaders[:3]}

        chan_signal = self.chan_strategy.get_trading_signal(kline)

        mainline_value = self.signal_mapping.get(mainline_signal['signal'], 0)
        leader_value = self.signal_mapping.get(leader_signal['signal'], 0)
        chan_value = self.signal_mapping.get(chan_signal['signal'], 0)

        conflicts = self._detect_conflicts(mainline_signal, leader_signal, chan_signal)
        resolved_weights = self._resolve_conflicts(conflicts, self.strategy_weights.copy())

        weighted_score = (
            mainline_value * resolved_weights['mainline'] +
            leader_value * resolved_weights['leader'] +
            chan_value * resolved_weights['chan']
        )

        final_decision = self._score_to_decision(weighted_score)

        position_pct = self._calculate_position(
            final_decision, mainline_signal, leader_signal, chan_signal
        )

        return {
            'concept_code': concept_code,
            'concept_name': concept_name,
            'timestamp': datetime.now().isoformat(),
            'final_decision': final_decision.value,
            'weighted_score': round(weighted_score, 4),
            'position_pct': position_pct,
            'strategy_signals': {
                'mainline': {
                    'signal': mainline_signal['signal'],
                    'score': mainline_signal['score'],
                    'phase': mainline_signal['phase'],
                    'weight': resolved_weights['mainline'],
                },
                'leader': {
                    'signal': leader_signal['signal'],
                    'score': leader_signal['score'],
                    'weight': resolved_weights['leader'],
                },
                'chan': {
                    'signal': chan_signal['signal'],
                    'weight': resolved_weights['chan'],
                },
            },
            'conflicts': conflicts,
            'leaders': leader_signal.get('leaders', []),
            'buy_points': chan_signal.get('buy_point'),
            'sell_points': chan_signal.get('sell_point'),
        }

    def _detect_conflicts(self, mainline: Dict, leader: Dict, chan: Dict) -> List[Dict]:
        conflicts = []
        signals = [
            ('mainline', mainline['signal']),
            ('leader', leader['signal']),
            ('chan', chan['signal']),
        ]

        for i, (name1, sig1) in enumerate(signals):
            for j, (name2, sig2) in enumerate(signals):
                if i >= j:
                    continue
                val1 = self.signal_mapping.get(sig1, 0)
                val2 = self.signal_mapping.get(sig2, 0)

                if val1 * val2 < 0:
                    conflicts.append({
                        'type': 'opposite',
                        'strategies': [name1, name2],
                        'signals': [sig1, sig2],
                        'severity': 'high' if abs(val1 - val2) > 2 else 'medium',
                    })
                elif val1 > 0.5 and val2 < -0.5:
                    conflicts.append({
                        'type': 'divergence',
                        'strategies': [name1, name2],
                        'signals': [sig1, sig2],
                        'severity': 'medium',
                    })

        return conflicts

    def _resolve_conflicts(self, conflicts: List[Dict],
                           weights: Dict[str, float]) -> Dict[str, float]:
        if not conflicts:
            return weights

        high_severity = any(c['severity'] == 'high' for c in conflicts)

        if high_severity:
            involved_strategies = set()
            for c in conflicts:
                involved_strategies.update(c['strategies'])

            for strategy in involved_strategies:
                weights[strategy] *= 0.5

            total = sum(weights.values())
            weights = {k: v / total for k, v in weights.items()}
        else:
            for c in conflicts:
                for strategy in c['strategies']:
                    weights[strategy] *= 0.7

            total = sum(weights.values())
            weights = {k: v / total for k, v in weights.items()}

        return weights

    def _score_to_decision(self, score: float) -> DecisionLevel:
        if score >= 1.5:
            return DecisionLevel.STRONG_BUY
        elif score >= 0.7:
            return DecisionLevel.BUY
        elif score >= 0.3:
            return DecisionLevel.WATCH
        elif score >= -0.3:
            return DecisionLevel.HOLD
        elif score >= -0.7:
            return DecisionLevel.REDUCE
        elif score >= -1.5:
            return DecisionLevel.SELL
        else:
            return DecisionLevel.STRONG_SELL

    def _calculate_position(self, decision: DecisionLevel,
                            mainline: Dict, leader: Dict, chan: Dict) -> float:
        base_position = {
            DecisionLevel.STRONG_BUY: 0.8,
            DecisionLevel.BUY: 0.5,
            DecisionLevel.WATCH: 0.15,
            DecisionLevel.HOLD: 0.0,
            DecisionLevel.REDUCE: -0.3,
            DecisionLevel.SELL: -0.5,
            DecisionLevel.STRONG_SELL: -0.8,
        }

        pct = base_position.get(decision, 0)

        mainline_pct = mainline.get('position_pct', 0)
        if mainline_pct > 0 and pct > 0:
            pct = (pct + mainline_pct / 100) / 2

        if decision in [DecisionLevel.STRONG_BUY, DecisionLevel.BUY]:
            if chan.get('buy_point'):
                pct = min(pct + 0.1, 1.0)

        if decision in [DecisionLevel.SELL, DecisionLevel.STRONG_SELL]:
            if chan.get('sell_point'):
                pct = max(pct - 0.1, -1.0)

        return round(pct, 2)

    def quick_combine(self, kline: pd.DataFrame,
                      stocks_data: Optional[List[Dict]] = None) -> Dict:
        trend_signals = self.trend_detector.detect_all(kline)
        momentum_signals = self.momentum_detector.detect_all(kline)
        volume_signals = self.volume_detector.detect_all(kline)
        fund_signals = self.fund_detector.detect_all(kline)

        score = 0.0
        components = {}

        ma_align = trend_signals.get('ma_bullish_alignment', 0)
        if ma_align == 1:
            score += 20
            components['ma_align'] = 20
        elif ma_align == 0:
            score += 5
            components['ma_align'] = 5
        else:
            components['ma_align'] = -10
            score -= 10

        consecutive = trend_signals.get('consecutive_up', {})
        if isinstance(consecutive, dict):
            level = consecutive.get('level', 0)
            consecutive_score = level * 8
            score += consecutive_score
            components['consecutive'] = consecutive_score

        macd_cross = momentum_signals.get('macd_cross', 'none')
        if macd_cross == 'golden':
            score += 20
            components['macd'] = 20
        elif momentum_signals.get('macd_above_zero', 0) == 1:
            score += 10
            components['macd'] = 10
        else:
            components['macd'] = 0

        rsi = momentum_signals.get('rsi_value', 50)
        if 30 <= rsi <= 70:
            score += 10
            components['rsi'] = 10
        elif rsi < 30:
            score += 5
            components['rsi'] = 5
        else:
            components['rsi'] = 0

        vol_status = volume_signals.get('vol_status', 'normal')
        if vol_status == 'blowout':
            score += 15
            components['volume'] = 15
        elif vol_status == 'expansion':
            score += 8
            components['volume'] = 8
        else:
            components['volume'] = 0

        fund_level = fund_signals.get('main_inflow_level', 0)
        fund_score = max(0, fund_level * 5)
        score += fund_score
        components['fund'] = fund_score

        final_signal = 'HOLD'
        if score >= 60:
            final_signal = 'STRONG_BUY'
        elif score >= 40:
            final_signal = 'BUY'
        elif score >= 20:
            final_signal = 'WATCH'
        elif score >= 0:
            final_signal = 'HOLD'
        elif score >= -10:
            final_signal = 'REDUCE'
        else:
            final_signal = 'SELL'

        return {
            'signal': final_signal,
            'score': score,
            'components': components,
            'trend_signals': trend_signals,
            'momentum_signals': momentum_signals,
            'volume_signals': volume_signals,
            'fund_signals': fund_signals,
        }