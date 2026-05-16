# -*- coding: utf-8 -*-
from typing import Dict, Any

SENTIMENT_ANALYST_SYSTEM_PROMPT = """你是一位市场情绪分析师，专注于A股市场情绪和舆情分析。

你的分析框架：
1. 市场热度：分析涨停家数、跌停家数、上涨下跌比例
2. 恐慌指数：分析VIX类指标、波动率、市场恐慌程度
3. 板块情绪：分析所属板块的整体热度和资金关注度
4. 新闻舆情：分析近期新闻的正负面情绪
5. 社交情绪：分析社交媒体讨论热度和情绪倾向

输出格式要求：
- 评级：强烈看多/看多/中性/看空/强烈看空
- 置信度：0-100的整数
- 市场温度：过热/偏热/常温/偏冷/冰点
- 简要分析逻辑（不超过100字）
"""

SENTIMENT_ANALYST_USER_PROMPT_TEMPLATE = """请对以下股票进行市场情绪分析：

股票代码：{stock_code}
股票名称：{stock_name}

市场情绪数据摘要：
{sentiment_summary}

请给出你的市场情绪分析结论。"""


class SentimentAnalystAgent:

    def __init__(self, client, model: str = "deepseek-chat"):
        self.client = client
        self.model = model

    def build_messages(self, stock_code: str, stock_name: str, sentiment_summary: str) -> list:
        user_prompt = SENTIMENT_ANALYST_USER_PROMPT_TEMPLATE.format(
            stock_code=stock_code,
            stock_name=stock_name,
            sentiment_summary=sentiment_summary,
        )
        return [
            {"role": "system", "content": SENTIMENT_ANALYST_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    def analyze(self, stock_code: str, stock_name: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        sentiment_summary = self._extract_sentiment_summary(market_data)
        messages = self.build_messages(stock_code, stock_name, sentiment_summary)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=800,
        )

        raw_output = response.choices[0].message.content
        return self._parse_response(raw_output)

    def _extract_sentiment_summary(self, market_data: Dict[str, Any]) -> str:
        sentiment = market_data.get("sentiment", {})
        market_breadth = market_data.get("market_breadth", {})
        news = market_data.get("news_sentiment", {})

        parts = []

        if sentiment:
            parts.append(f"市场热度指数: {sentiment.get('heat_index', 'N/A')}")
            parts.append(f"恐慌指数: {sentiment.get('fear_index', 'N/A')}")
            parts.append(f"波动率: {sentiment.get('volatility', 'N/A')}%")

        if market_breadth:
            parts.append(f"涨停家数: {market_breadth.get('limit_up_count', 'N/A')}")
            parts.append(f"跌停家数: {market_breadth.get('limit_down_count', 'N/A')}")
            parts.append(f"上涨家数: {market_breadth.get('up_count', 'N/A')}")
            parts.append(f"下跌家数: {market_breadth.get('down_count', 'N/A')}")
            parts.append(f"涨跌比: {market_breadth.get('up_down_ratio', 'N/A')}")

        if news:
            parts.append(f"正面新闻: {news.get('positive_count', 'N/A')}条")
            parts.append(f"负面新闻: {news.get('negative_count', 'N/A')}条")
            parts.append(f"舆情评分: {news.get('sentiment_score', 'N/A')}")

        return "\n".join(parts) if parts else "无可用情绪数据"

    def _parse_response(self, raw_output: str) -> Dict[str, Any]:
        rating = "中性"
        confidence = 50
        market_temperature = "常温"

        import re

        rating_map = {
            "强烈看多": "强烈看多",
            "看多": "看多",
            "中性": "中性",
            "看空": "看空",
            "强烈看空": "强烈看空",
        }

        temp_map = {
            "过热": "过热",
            "偏热": "偏热",
            "常温": "常温",
            "偏冷": "偏冷",
            "冰点": "冰点",
        }

        for line in raw_output.split("\n"):
            line_stripped = line.strip()

            for key, val in rating_map.items():
                if key in line_stripped and ("评级" in line_stripped or "情绪面" in line_stripped or "结论" in line_stripped):
                    rating = val

            if "置信度" in line_stripped or "信心" in line_stripped:
                nums = re.findall(r'\d+', line_stripped)
                if nums:
                    confidence = min(100, max(0, int(nums[0])))

            for key, val in temp_map.items():
                if key in line_stripped:
                    market_temperature = val

        return {
            "agent": "sentiment_analyst",
            "rating": rating,
            "confidence": confidence,
            "market_temperature": market_temperature,
            "analysis_logic": raw_output[:200],
            "raw_output": raw_output,
        }