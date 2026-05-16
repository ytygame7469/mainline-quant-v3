# -*- coding: utf-8 -*-
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DecisionResult:
    stock_code: str
    stock_name: str
    final_decision: str
    position_advice: float
    stop_loss: float
    take_profit: float
    confidence: int
    ai_rating: str
    strategy_signal: str
    reason: str


class AIDecisionEngine:

    AI_WEIGHT = 0.30
    STRATEGY_WEIGHT = 0.70

    RATING_SCORES = {
        "强烈看多": 100,
        "看多": 75,
        "中性": 50,
        "看空": 25,
        "强烈看空": 0,
    }

    SIGNAL_SCORES = {
        "STRONG_BUY": 100,
        "BUY": 80,
        "WEAK_BUY": 60,
        "HOLD": 50,
        "WEAK_SELL": 40,
        "SELL": 20,
        "STRONG_SELL": 0,
    }

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def make_decision(
        self,
        stock_code: str,
        stock_name: str,
        market_data: Dict[str, Any],
        strategy_signals: Dict[str, Any],
    ) -> DecisionResult:
        ai_analysis = self.orchestrator.analyze(stock_code, stock_name, market_data, parallel=True)

        aggregated = ai_analysis.get("aggregated", {})
        ai_rating = aggregated.get("overall_rating", "中性")
        ai_score = self.RATING_SCORES.get(ai_rating, 50)
        ai_confidence = aggregated.get("avg_confidence", 50)

        strategy_signal = strategy_signals.get("signal", "HOLD")
        strategy_score = self.SIGNAL_SCORES.get(strategy_signal, 50)
        strategy_confidence = strategy_signals.get("confidence", 70)

        final_score = ai_score * self.AI_WEIGHT + strategy_score * self.STRATEGY_WEIGHT

        if final_score >= 80:
            final_decision = "BUY"
            position_advice = 0.05
        elif final_score >= 65:
            final_decision = "BUY_LIGHT"
            position_advice = 0.03
        elif final_score >= 45:
            final_decision = "HOLD"
            position_advice = 0.0
        elif final_score >= 25:
            final_decision = "REDUCE"
            position_advice = -0.02
        else:
            final_decision = "SELL"
            position_advice = -0.05

        stop_loss, take_profit = self._calculate_stop_profit(
            market_data, strategy_signals, final_decision
        )

        combined_confidence = int(ai_confidence * self.AI_WEIGHT + strategy_confidence * self.STRATEGY_WEIGHT)

        reason = self._build_reason(
            ai_rating, ai_score, ai_confidence,
            strategy_signal, strategy_score, strategy_confidence,
            final_score, final_decision,
        )

        return DecisionResult(
            stock_code=stock_code,
            stock_name=stock_name,
            final_decision=final_decision,
            position_advice=position_advice,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=combined_confidence,
            ai_rating=ai_rating,
            strategy_signal=strategy_signal,
            reason=reason,
        )

    def _calculate_stop_profit(
        self,
        market_data: Dict[str, Any],
        strategy_signals: Dict[str, Any],
        decision: str,
    ) -> Tuple[float, float]:
        kline = market_data.get("kline", {})
        current_price = kline.get("close", 0)
        atr = market_data.get("indicators", {}).get("atr", current_price * 0.03)

        strategy_stop = strategy_signals.get("stop_loss", 0)
        strategy_profit = strategy_signals.get("take_profit", 0)

        if current_price > 0:
            if strategy_stop <= 0:
                stop_loss_pct = -0.08 if decision in ("BUY", "BUY_LIGHT") else -0.05
                stop_loss = current_price * (1 + stop_loss_pct)
            else:
                stop_loss = strategy_stop

            if strategy_profit <= 0:
                take_profit_pct = 0.30 if decision in ("BUY", "BUY_LIGHT") else 0.15
                take_profit = current_price * (1 + take_profit_pct)
            else:
                take_profit = strategy_profit
        else:
            stop_loss = 0
            take_profit = 0

        return round(stop_loss, 2), round(take_profit, 2)

    def _build_reason(
        self,
        ai_rating: str,
        ai_score: int,
        ai_confidence: int,
        strategy_signal: str,
        strategy_score: int,
        strategy_confidence: int,
        final_score: float,
        final_decision: str,
    ) -> str:
        return (
            f"AI分析: {ai_rating}(得分{ai_score},置信度{ai_confidence}%) | "
            f"策略信号: {strategy_signal}(得分{strategy_score},置信度{strategy_confidence}%) | "
            f"综合得分: {final_score:.1f} | "
            f"最终决策: {final_decision}"
        )