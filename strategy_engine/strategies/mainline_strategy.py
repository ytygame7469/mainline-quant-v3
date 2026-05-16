import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from enum import Enum

from strategy_engine.signals.trend_signals import TrendSignalDetector
from strategy_engine.signals.momentum_signals import MomentumSignalDetector
from strategy_engine.signals.volume_signals import VolumeSignalDetector
from strategy_engine.signals.fund_flow_signals import FundFlowSignalDetector


class MainlinePhase(Enum):
    GERMINATION = "萌芽"
    ERUPTION = "爆发"
    CLIMAX = "高潮"
    RECESSION = "退潮"
    DORMANT = "休眠"


class MainlineRotateStrategy:
    def __init__(self):
        self.trend_detector = TrendSignalDetector()
        self.momentum_detector = MomentumSignalDetector()
        self.volume_detector = VolumeSignalDetector()
        self.fund_detector = FundFlowSignalDetector()

        self.min_score = 70
        self.confirm_days = 3
        self.phase_history: Dict[str, List[Dict]] = {}

        self.weights = {
            'trend_momentum': 12,
            'consecutive_strength': 10,
            'volume_energy': 8,
            'fund_flow': 8,
            'market_sentiment': 7,
            'sector_rotation': 7,
            'technical_pattern': 7,
            'valuation_support': 6,
            'macro_resonance': 6,
            'institutional_position': 6,
            'news_catalyst': 5,
            'risk_adjustment': 5,
        }

    def calculate_concept_score(self, concept_code: str, concept_name: str,
                                 kline: pd.DataFrame,
                                 fund_flow_data: Optional[Dict] = None,
                                 sentiment_data: Optional[Dict] = None,
                                 sector_data: Optional[Dict] = None,
                                 valuation_data: Optional[Dict] = None,
                                 macro_data: Optional[Dict] = None,
                                 institution_data: Optional[Dict] = None,
                                 news_data: Optional[Dict] = None) -> Dict:

        if kline.empty or len(kline) < 60:
            return {'concept_code': concept_code, 'concept_name': concept_name, 'total_score': 0, 'phase': MainlinePhase.DORMANT.value}

        trend_signals = self.trend_detector.detect_all(kline)
        momentum_signals = self.momentum_detector.detect_all(kline)
        volume_signals = self.volume_detector.detect_all(kline)
        fund_signals = self.fund_detector.detect_all(kline, fund_flow_data)

        scores = {}

        scores['trend_momentum'] = self._score_trend_momentum(trend_signals, momentum_signals)
        scores['consecutive_strength'] = self._score_consecutive_strength(trend_signals, kline)
        scores['volume_energy'] = self._score_volume_energy(volume_signals)
        scores['fund_flow'] = self._score_fund_flow(fund_signals)
        scores['market_sentiment'] = self._score_market_sentiment(sentiment_data, kline)
        scores['sector_rotation'] = self._score_sector_rotation(sector_data, kline)
        scores['technical_pattern'] = self._score_technical_pattern(trend_signals, momentum_signals, volume_signals)
        scores['valuation_support'] = self._score_valuation_support(valuation_data)
        scores['macro_resonance'] = self._score_macro_resonance(macro_data)
        scores['institutional_position'] = self._score_institutional_position(institution_data)
        scores['news_catalyst'] = self._score_news_catalyst(news_data)
        scores['risk_adjustment'] = self._score_risk_adjustment(kline, trend_signals)

        total_score = sum(
            scores[k] * self.weights[k] / 100 for k in scores
        ) * 100 / sum(self.weights.values())

        phase = self._determine_phase(concept_code, total_score, trend_signals, volume_signals)

        return {
            'concept_code': concept_code,
            'concept_name': concept_name,
            'total_score': round(total_score, 2),
            'phase': phase.value,
            'components': scores,
            'trend_signals': trend_signals,
            'momentum_signals': momentum_signals,
            'volume_signals': volume_signals,
            'fund_signals': fund_signals,
        }

    def _score_trend_momentum(self, trend: Dict, momentum: Dict) -> float:
        score = 0.0

        if trend.get('ma_bullish_alignment', 0) == 1:
            score += 30
        elif trend.get('ma_bullish_alignment', 0) == 0:
            score += 15

        adx_data = trend.get('adx_trend_strength', {})
        if isinstance(adx_data, dict):
            if adx_data.get('trend_strong', 0) == 1:
                score += 25
            elif adx_data.get('adx', 0) > 20:
                score += 10

        macd_cross = momentum.get('macd_cross', 'none')
        if macd_cross == 'golden':
            score += 25
        elif momentum.get('macd_above_zero', 0) == 1:
            score += 15

        boll_pos = momentum.get('boll_position', 0)
        if boll_pos == 2:
            score += 20
        elif boll_pos == 1:
            score += 10

        return min(score, 100)

    def _score_consecutive_strength(self, trend: Dict, kline: pd.DataFrame) -> float:
        consecutive = trend.get('consecutive_up', {})
        if isinstance(consecutive, dict):
            level = consecutive.get('level', 0)
            days = consecutive.get('days', 0)
        else:
            level = 0
            days = 0

        score = level * 20

        if len(kline) >= 10:
            changes = kline['close'].pct_change().tail(10)
            avg_change = changes[changes > 0].mean() * 100 if len(changes[changes > 0]) > 0 else 0
            if avg_change > 5:
                score += 25
            elif avg_change > 3:
                score += 15
            elif avg_change > 1:
                score += 5

        if len(kline) >= 20:
            close_20d_ago = kline['close'].iloc[-20]
            current = kline['close'].iloc[-1]
            momentum_20d = (current - close_20d_ago) / close_20d_ago * 100
            if momentum_20d > 20:
                score += 25
            elif momentum_20d > 10:
                score += 15
            elif momentum_20d > 5:
                score += 5

        return min(score, 100)

    def _score_volume_energy(self, volume: Dict) -> float:
        score = 0.0

        vol_status = volume.get('vol_status', 'normal')
        if vol_status == 'blowout':
            score += 40
        elif vol_status == 'expansion':
            score += 25
        elif vol_status == 'normal':
            score += 10

        pv_coordination = volume.get('pv_coordination', 'neutral')
        if pv_coordination == 'bullish_sync':
            score += 30
        elif pv_coordination == 'bullish_diverge':
            score += 10

        obv_trend = volume.get('obv_trend', 'below_ma')
        if obv_trend == 'breakout_up':
            score += 20
        elif obv_trend == 'above_ma':
            score += 10

        obv_div = volume.get('obv_divergence', 0)
        if obv_div == 1:
            score += 10

        return min(score, 100)

    def _score_fund_flow(self, fund: Dict) -> float:
        score = 0.0

        level = fund.get('main_inflow_level', 0)
        if level >= 3:
            score += 50
        elif level >= 2:
            score += 35
        elif level >= 1:
            score += 20
        elif level >= 0:
            score += 10

        if fund.get('main_dominant', 0) == 1:
            score += 20

        north_direction = fund.get('north_direction', 0)
        if north_direction == 1:
            north_strength = fund.get('north_strength', 'weak')
            if north_strength == 'strong':
                score += 20
            elif north_strength == 'moderate':
                score += 10

        big_order_bias = fund.get('big_order_bias', 'neutral')
        if big_order_bias == 'buy':
            score += 10

        return min(score, 100)

    def _score_market_sentiment(self, sentiment_data: Optional[Dict], kline: pd.DataFrame) -> float:
        score = 50.0

        if sentiment_data:
            limit_up_ratio = sentiment_data.get('limit_up_ratio', 0)
            if limit_up_ratio > 5:
                score += 30
            elif limit_up_ratio > 2:
                score += 15

            fear_greed = sentiment_data.get('fear_greed_index', 50)
            if fear_greed > 70:
                score += 10
            elif fear_greed < 30:
                score -= 10

        if len(kline) >= 5:
            up_days = sum(1 for i in range(len(kline) - 5, len(kline)) if kline['close'].iloc[i] > kline['open'].iloc[i])
            score += up_days * 2

        return min(max(score, 0), 100)

    def _score_sector_rotation(self, sector_data: Optional[Dict], kline: pd.DataFrame) -> float:
        score = 50.0

        if sector_data:
            rank_pct = sector_data.get('rank_percentile', 50)
            score += (100 - rank_pct) * 0.3

            turnover_rank = sector_data.get('turnover_rank', 50)
            score += (100 - turnover_rank) * 0.2

        return min(max(score, 0), 100)

    def _score_technical_pattern(self, trend: Dict, momentum: Dict, volume: Dict) -> float:
        score = 0.0

        if trend.get('ma_bullish_alignment', 0) == 1:
            score += 25

        macd_bar_dir = momentum.get('macd_bar_direction', 0)
        if macd_bar_dir == 1:
            score += 15

        rsi_value = momentum.get('rsi_value', 50)
        if 40 <= rsi_value <= 70:
            score += 20
        elif rsi_value < 30:
            score += 10

        boll_width = momentum.get('boll_width', 5)
        if boll_width > 10:
            score += 15
        elif boll_width > 5:
            score += 10

        kdj_signal = momentum.get('kdj_signal', 0)
        if kdj_signal == 1:
            score += 15

        if volume.get('bullish_volume', 0) == 1:
            score += 10

        return min(score, 100)

    def _score_valuation_support(self, valuation_data: Optional[Dict]) -> float:
        if not valuation_data:
            return 50.0

        score = 50.0

        pe_percentile = valuation_data.get('pe_percentile', 50)
        if pe_percentile < 30:
            score += 30
        elif pe_percentile < 50:
            score += 15

        pb_percentile = valuation_data.get('pb_percentile', 50)
        if pb_percentile < 20:
            score += 20
        elif pb_percentile < 50:
            score += 10

        return min(score, 100)

    def _score_macro_resonance(self, macro_data: Optional[Dict]) -> float:
        if not macro_data:
            return 50.0

        score = 50.0

        policy_direction = macro_data.get('policy_direction', 0)
        score += policy_direction * 15

        liquidity = macro_data.get('liquidity_index', 50)
        if liquidity > 70:
            score += 20
        elif liquidity > 50:
            score += 10

        industry_cycle = macro_data.get('industry_cycle', 'neutral')
        if industry_cycle == 'upswing':
            score += 15
        elif industry_cycle == 'downswing':
            score -= 10

        return min(max(score, 0), 100)

    def _score_institutional_position(self, institution_data: Optional[Dict]) -> float:
        if not institution_data:
            return 50.0

        score = 50.0

        position_change = institution_data.get('position_change_pct', 0)
        score += position_change * 5

        fund_count = institution_data.get('fund_count_change', 0)
        if fund_count > 5:
            score += 20
        elif fund_count > 0:
            score += 10

        top10_concentration = institution_data.get('top10_concentration', 50)
        if top10_concentration > 70:
            score += 10

        return min(max(score, 0), 100)

    def _score_news_catalyst(self, news_data: Optional[Dict]) -> float:
        if not news_data:
            return 50.0

        score = 50.0

        sentiment = news_data.get('sentiment_score', 0)
        score += sentiment * 10

        heat_index = news_data.get('heat_index', 50)
        if heat_index > 80:
            score += 20
        elif heat_index > 60:
            score += 10

        freshness = news_data.get('freshness_hours', 24)
        if freshness < 6:
            score += 15
        elif freshness < 24:
            score += 5

        return min(max(score, 0), 100)

    def _score_risk_adjustment(self, kline: pd.DataFrame, trend: Dict) -> float:
        score = 50.0

        if len(kline) >= 20:
            close = kline['close'].values
            returns = np.diff(close) / close[:-1]
            volatility = np.std(returns[-20:]) * np.sqrt(252) * 100

            if volatility < 20:
                score += 20
            elif volatility < 30:
                score += 10
            elif volatility > 50:
                score -= 15

        if len(kline) >= 60:
            high_60 = kline['high'].max()
            low_60 = kline['low'].max()
            current = kline['close'].iloc[-1]
            if low_60 > 0:
                position_in_range = (current - low_60) / (high_60 - low_60) * 100
                if 30 <= position_in_range <= 70:
                    score += 15
                elif position_in_range > 90:
                    score -= 10

        adx_data = trend.get('adx_trend_strength', {})
        if isinstance(adx_data, dict):
            adx = adx_data.get('adx', 0)
            if adx > 40:
                score -= 10

        return min(max(score, 0), 100)

    def _determine_phase(self, concept_code: str, score: float,
                         trend: Dict, volume: Dict) -> MainlinePhase:
        if concept_code not in self.phase_history:
            self.phase_history[concept_code] = []

        self.phase_history[concept_code].append({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'score': score,
        })

        history = self.phase_history[concept_code]
        if len(history) > 20:
            history = history[-20:]

        recent_scores = [h['score'] for h in history[-self.confirm_days:]]

        if len(recent_scores) < self.confirm_days:
            if score >= self.min_score:
                return MainlinePhase.GERMINATION
            return MainlinePhase.DORMANT

        all_above_threshold = all(s >= self.min_score for s in recent_scores)

        if not all_above_threshold:
            if score >= self.min_score:
                return MainlinePhase.GERMINATION
            if len(history) >= 5:
                recent_5 = [h['score'] for h in history[-5:]]
                if all(s < self.min_score * 0.7 for s in recent_5):
                    return MainlinePhase.DORMANT
            return MainlinePhase.RECESSION

        if score >= 85:
            vol_status = volume.get('vol_status', 'normal')
            if vol_status == 'blowout':
                return MainlinePhase.CLIMAX
            return MainlinePhase.ERUPTION

        if score >= 75:
            return MainlinePhase.ERUPTION

        return MainlinePhase.GERMINATION

    def check_mainline_confirmed(self, concept_code: str) -> bool:
        if concept_code not in self.phase_history:
            return False

        history = self.phase_history[concept_code]
        if len(history) < self.confirm_days:
            return False

        recent_scores = [h['score'] for h in history[-self.confirm_days:]]
        return all(s >= self.min_score for s in recent_scores)

    def detect_sector_rotation(self, all_concept_scores: List[Dict]) -> List[Dict]:
        if len(all_concept_scores) < 2:
            return []

        sorted_scores = sorted(all_concept_scores, key=lambda x: x['total_score'], reverse=True)
        rotations = []

        for i, current in enumerate(sorted_scores):
            concept_code = current['concept_code']
            if concept_code not in self.phase_history or len(self.phase_history[concept_code]) < 5:
                continue

            recent_history = self.phase_history[concept_code][-5:]
            trend = np.polyfit(range(5), [h['score'] for h in recent_history], 1)[0]

            rotation_signal = {
                'concept_code': concept_code,
                'concept_name': current['concept_name'],
                'current_score': current['total_score'],
                'score_trend': round(trend, 2),
                'direction': 'up' if trend > 2 else ('down' if trend < -2 else 'flat'),
                'phase': current.get('phase', MainlinePhase.DORMANT.value),
            }
            rotations.append(rotation_signal)

        return rotations

    def get_trading_signal(self, concept_code: str, concept_name: str,
                           kline: pd.DataFrame,
                           fund_flow_data: Optional[Dict] = None,
                           sentiment_data: Optional[Dict] = None,
                           sector_data: Optional[Dict] = None,
                           valuation_data: Optional[Dict] = None,
                           macro_data: Optional[Dict] = None,
                           institution_data: Optional[Dict] = None,
                           news_data: Optional[Dict] = None) -> Dict:

        score_result = self.calculate_concept_score(
            concept_code, concept_name, kline,
            fund_flow_data, sentiment_data, sector_data,
            valuation_data, macro_data, institution_data, news_data
        )

        total_score = score_result['total_score']
        phase = score_result['phase']
        confirmed = self.check_mainline_confirmed(concept_code)

        if confirmed and phase in [MainlinePhase.ERUPTION.value, MainlinePhase.GERMINATION.value]:
            signal = 'STRONG_BUY'
            position_pct = 30 if phase == MainlinePhase.ERUPTION.value else 20
        elif confirmed and phase == MainlinePhase.CLIMAX.value:
            signal = 'HOLD'
            position_pct = 10
        elif not confirmed and total_score >= self.min_score:
            signal = 'BUY'
            position_pct = 10
        elif phase == MainlinePhase.RECESSION.value:
            signal = 'SELL'
            position_pct = 0
        elif phase == MainlinePhase.DORMANT.value:
            signal = 'NONE'
            position_pct = 0
        else:
            signal = 'WATCH'
            position_pct = 0

        return {
            'concept_code': concept_code,
            'concept_name': concept_name,
            'signal': signal,
            'score': total_score,
            'phase': phase,
            'confirmed': confirmed,
            'position_pct': position_pct,
            'components': score_result['components'],
        }