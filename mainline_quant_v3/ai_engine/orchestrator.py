# -*- coding: utf-8 -*-
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from .agents.tech_analyst import TechAnalystAgent
from .agents.fund_analyst import FundAnalystAgent
from .agents.flow_analyst import FlowAnalystAgent
from .agents.sentiment_analyst import SentimentAnalystAgent


@dataclass
class AgentResult:
    agent: str
    rating: str
    confidence: int
    analysis_logic: str
    extra: Dict[str, Any] = field(default_factory=dict)


class AgentOrchestrator:

    RATING_SCORES = {
        "强烈看多": 100,
        "看多": 75,
        "中性": 50,
        "看空": 25,
        "强烈看空": 0,
    }

    AGENT_WEIGHTS = {
        "tech_analyst": 0.30,
        "fund_analyst": 0.30,
        "flow_analyst": 0.25,
        "sentiment_analyst": 0.15,
    }

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "deepseek-chat"):
        from openai import OpenAI

        if api_key is None:
            import os
            api_key = os.environ.get("DEEPSEEK_API_KEY", os.environ.get("OPENAI_API_KEY", ""))

        if base_url is None:
            base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

        self.tech_agent = TechAnalystAgent(self.client, model)
        self.fund_agent = FundAnalystAgent(self.client, model)
        self.flow_agent = FlowAnalystAgent(self.client, model)
        self.sentiment_agent = SentimentAnalystAgent(self.client, model)

    def analyze(
        self,
        stock_code: str,
        stock_name: str,
        market_data: Dict[str, Any],
        parallel: bool = True,
    ) -> Dict[str, Any]:
        agents = [
            ("tech_analyst", self.tech_agent),
            ("fund_analyst", self.fund_agent),
            ("flow_analyst", self.flow_agent),
            ("sentiment_analyst", self.sentiment_agent),
        ]

        results: Dict[str, Dict[str, Any]] = {}

        if parallel:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(agent.analyze, stock_code, stock_name, market_data): name
                    for name, agent in agents
                }
                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        results[name] = future.result(timeout=60)
                    except Exception as e:
                        results[name] = {
                            "agent": name,
                            "rating": "中性",
                            "confidence": 0,
                            "error": str(e),
                            "analysis_logic": f"分析异常: {e}",
                        }
        else:
            for name, agent in agents:
                try:
                    results[name] = agent.analyze(stock_code, stock_name, market_data)
                except Exception as e:
                    results[name] = {
                        "agent": name,
                        "rating": "中性",
                        "confidence": 0,
                        "error": str(e),
                        "analysis_logic": f"分析异常: {e}",
                    }

        aggregated = self._aggregate(results)
        return {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "aggregated": aggregated,
            "details": results,
        }

    def _aggregate(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        weighted_score = 0.0
        total_weight = 0.0
        total_confidence = 0
        agent_count = 0

        ratings_detail = {}
        buy_count = 0
        sell_count = 0

        for agent_name, result in results.items():
            rating = result.get("rating", "中性")
            confidence = result.get("confidence", 50)
            weight = self.AGENT_WEIGHTS.get(agent_name, 0.25)

            score = self.RATING_SCORES.get(rating, 50)
            weighted_score += score * weight
            total_weight += weight
            total_confidence += confidence
            agent_count += 1

            ratings_detail[agent_name] = {
                "rating": rating,
                "confidence": confidence,
                "weight": weight,
            }

            if rating in ("强烈看多", "看多"):
                buy_count += 1
            elif rating in ("强烈看空", "看空"):
                sell_count += 1

        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = 50

        avg_confidence = total_confidence // agent_count if agent_count > 0 else 50

        if final_score >= 85:
            overall_rating = "强烈看多"
        elif final_score >= 65:
            overall_rating = "看多"
        elif final_score >= 40:
            overall_rating = "中性"
        elif final_score >= 20:
            overall_rating = "看空"
        else:
            overall_rating = "强烈看空"

        if buy_count >= 3:
            suggestion = "多数分析师看多，建议关注买入机会"
            action = "BUY"
        elif sell_count >= 3:
            suggestion = "多数分析师看空，建议回避或减仓"
            action = "SELL"
        elif buy_count >= 2:
            suggestion = "部分分析师看多，可轻仓试探"
            action = "BUY_LIGHT"
        elif sell_count >= 2:
            suggestion = "部分分析师看空，建议谨慎持有"
            action = "REDUCE"
        else:
            suggestion = "分析师意见分歧，建议观望"
            action = "HOLD"

        return {
            "overall_rating": overall_rating,
            "overall_score": round(final_score, 1),
            "avg_confidence": avg_confidence,
            "suggestion": suggestion,
            "action": action,
            "ratings_detail": ratings_detail,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "neutral_count": agent_count - buy_count - sell_count,
        }