# -*- coding: utf-8 -*-
from typing import Dict, Any

TECH_ANALYST_SYSTEM_PROMPT = """你是一位拥有10年实战经验的技术分析专家，精通A股市场技术分析。

你的分析框架：
1. 均线系统：分析MA5/MA10/MA20/MA60/MA120/MA250的多空排列关系，识别金叉死叉信号
2. MACD指标：分析DIF/DEA/MACD柱状线，判断趋势强度和背离信号
3. RSI指标：分析超买超卖区域（RSI>80超买，RSI<20超卖），识别背离
4. 布林带：分析价格与上下轨关系，识别突破和回归信号
5. 成交量：分析量价配合关系，识别放量突破和缩量调整

输出格式要求：
- 评级：强烈看多/看多/中性/看空/强烈看空
- 置信度：0-100的整数
- 关键支撑位：2-3个价格点位
- 关键阻力位：2-3个价格点位
- 简要分析逻辑（不超过100字）
"""

TECH_ANALYST_USER_PROMPT_TEMPLATE = """请对以下股票进行技术分析：

股票代码：{stock_code}
股票名称：{stock_name}

技术指标摘要：
{tech_summary}

请给出你的技术面分析结论。"""


class TechAnalystAgent:

    def __init__(self, client, model: str = "deepseek-chat"):
        self.client = client
        self.model = model

    def build_messages(self, stock_code: str, stock_name: str, tech_summary: str) -> list:
        user_prompt = TECH_ANALYST_USER_PROMPT_TEMPLATE.format(
            stock_code=stock_code,
            stock_name=stock_name,
            tech_summary=tech_summary,
        )
        return [
            {"role": "system", "content": TECH_ANALYST_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    def analyze(self, stock_code: str, stock_name: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        tech_summary = self._extract_tech_summary(market_data)
        messages = self.build_messages(stock_code, stock_name, tech_summary)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=800,
        )

        raw_output = response.choices[0].message.content
        return self._parse_response(raw_output)

    def _extract_tech_summary(self, market_data: Dict[str, Any]) -> str:
        kline = market_data.get("kline", {})
        indicators = market_data.get("indicators", {})

        parts = []

        if kline:
            parts.append(f"最新价: {kline.get('close', 'N/A')}")
            parts.append(f"涨跌幅: {kline.get('pct_change', 'N/A')}%")
            parts.append(f"成交量: {kline.get('volume', 'N/A')}")
            parts.append(f"换手率: {kline.get('turnover_rate', 'N/A')}%")

        if indicators:
            ma = indicators.get("ma", {})
            if ma:
                parts.append(f"均线: MA5={ma.get('ma5','N/A')}, MA10={ma.get('ma10','N/A')}, MA20={ma.get('ma20','N/A')}, MA60={ma.get('ma60','N/A')}")

            macd = indicators.get("macd", {})
            if macd:
                parts.append(f"MACD: DIF={macd.get('dif','N/A')}, DEA={macd.get('dea','N/A')}, MACD={macd.get('macd','N/A')}")

            rsi = indicators.get("rsi", {})
            if rsi:
                parts.append(f"RSI: RSI6={rsi.get('rsi6','N/A')}, RSI14={rsi.get('rsi14','N/A')}, RSI24={rsi.get('rsi24','N/A')}")

            boll = indicators.get("boll", {})
            if boll:
                parts.append(f"布林带: 上轨={boll.get('upper','N/A')}, 中轨={boll.get('mid','N/A')}, 下轨={boll.get('lower','N/A')}")

            vol = indicators.get("volume_ratio", {})
            if vol:
                parts.append(f"量比: {vol.get('volume_ratio', 'N/A')}")

        return "\n".join(parts) if parts else "无可用技术指标数据"

    def _parse_response(self, raw_output: str) -> Dict[str, Any]:
        rating = "中性"
        confidence = 50
        support_levels = []
        resistance_levels = []
        analysis_logic = ""

        rating_map = {
            "强烈看多": "强烈看多",
            "看多": "看多",
            "中性": "中性",
            "看空": "看空",
            "强烈看空": "强烈看空",
        }

        for line in raw_output.split("\n"):
            line_stripped = line.strip()

            for key, val in rating_map.items():
                if key in line_stripped and ("评级" in line_stripped or "技术面" in line_stripped or "结论" in line_stripped):
                    rating = val

            if "置信度" in line_stripped or "信心" in line_stripped:
                import re
                nums = re.findall(r'\d+', line_stripped)
                if nums:
                    confidence = min(100, max(0, int(nums[0])))

            if "支撑" in line_stripped:
                import re
                nums = re.findall(r'\d+\.?\d*', line_stripped)
                support_levels = [float(n) for n in nums[:3]]

            if "阻力" in line_stripped:
                import re
                nums = re.findall(r'\d+\.?\d*', line_stripped)
                resistance_levels = [float(n) for n in nums[:3]]

        analysis_logic = raw_output[:200]

        return {
            "agent": "tech_analyst",
            "rating": rating,
            "confidence": confidence,
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
            "analysis_logic": analysis_logic,
            "raw_output": raw_output,
        }