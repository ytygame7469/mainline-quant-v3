# -*- coding: utf-8 -*-
from typing import Dict, Any

FUND_ANALYST_SYSTEM_PROMPT = """你是一位CFA持证基本面分析师，拥有15年A股投研经验。

你的分析框架：
1. 估值指标：PE（市盈率）、PB（市净率）、PS（市销率），结合行业均值与历史分位判断
2. 盈利能力：ROE（净资产收益率）、毛利率、净利率，评估盈利质量与可持续性
3. 成长性：营收增长率、净利润增长率，判断成长阶段与增速趋势
4. 财务健康：资产负债率、流动比率、经营现金流，评估财务风险
5. 估值区间：结合DCF和相对估值法，给出合理估值区间

输出格式要求：
- 评级：强烈看多/看多/中性/看空/强烈看空
- 置信度：0-100的整数
- 合理估值区间：下限-上限
- 当前估值判断：低估/合理/高估
- 简要分析逻辑（不超过100字）
"""

FUND_ANALYST_USER_PROMPT_TEMPLATE = """请对以下股票进行基本面分析：

股票代码：{stock_code}
股票名称：{stock_name}

基本面数据摘要：
{fund_summary}

请给出你的基本面分析结论。"""


class FundAnalystAgent:

    def __init__(self, client, model: str = "deepseek-chat"):
        self.client = client
        self.model = model

    def build_messages(self, stock_code: str, stock_name: str, fund_summary: str) -> list:
        user_prompt = FUND_ANALYST_USER_PROMPT_TEMPLATE.format(
            stock_code=stock_code,
            stock_name=stock_name,
            fund_summary=fund_summary,
        )
        return [
            {"role": "system", "content": FUND_ANALYST_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    def analyze(self, stock_code: str, stock_name: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        fund_summary = self._extract_fund_summary(market_data)
        messages = self.build_messages(stock_code, stock_name, fund_summary)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=800,
        )

        raw_output = response.choices[0].message.content
        return self._parse_response(raw_output)

    def _extract_fund_summary(self, market_data: Dict[str, Any]) -> str:
        fundamental = market_data.get("fundamental", {})
        finance = market_data.get("finance", {})

        parts = []

        if fundamental:
            parts.append(f"PE: {fundamental.get('pe', 'N/A')} (行业均值: {fundamental.get('pe_industry', 'N/A')})")
            parts.append(f"PB: {fundamental.get('pb', 'N/A')} (行业均值: {fundamental.get('pb_industry', 'N/A')})")
            parts.append(f"PS: {fundamental.get('ps', 'N/A')}")
            parts.append(f"ROE: {fundamental.get('roe', 'N/A')}%")
            parts.append(f"总市值: {fundamental.get('total_mv', 'N/A')}亿")

        if finance:
            parts.append(f"毛利率: {finance.get('gross_profit_margin', 'N/A')}%")
            parts.append(f"净利率: {finance.get('net_profit_margin', 'N/A')}%")
            parts.append(f"营收增长率: {finance.get('revenue_growth', 'N/A')}%")
            parts.append(f"净利润增长率: {finance.get('profit_growth', 'N/A')}%")
            parts.append(f"资产负债率: {finance.get('debt_ratio', 'N/A')}%")
            parts.append(f"经营现金流: {finance.get('operating_cf', 'N/A')}亿")

        return "\n".join(parts) if parts else "无可用基本面数据"

    def _parse_response(self, raw_output: str) -> Dict[str, Any]:
        rating = "中性"
        confidence = 50
        valuation_range = (0.0, 0.0)
        valuation_judgment = "合理"

        import re

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
                if key in line_stripped and ("评级" in line_stripped or "基本面" in line_stripped or "结论" in line_stripped):
                    rating = val

            if "置信度" in line_stripped or "信心" in line_stripped:
                nums = re.findall(r'\d+', line_stripped)
                if nums:
                    confidence = min(100, max(0, int(nums[0])))

            if "低估" in line_stripped:
                valuation_judgment = "低估"
            elif "高估" in line_stripped:
                valuation_judgment = "高估"

            if "估值区间" in line_stripped or "合理区间" in line_stripped:
                nums = re.findall(r'\d+\.?\d*', line_stripped)
                if len(nums) >= 2:
                    valuation_range = (float(nums[0]), float(nums[1]))

        return {
            "agent": "fund_analyst",
            "rating": rating,
            "confidence": confidence,
            "valuation_range": valuation_range,
            "valuation_judgment": valuation_judgment,
            "analysis_logic": raw_output[:200],
            "raw_output": raw_output,
        }