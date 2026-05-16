# -*- coding: utf-8 -*-
from typing import Dict, Any

FLOW_ANALYST_SYSTEM_PROMPT = """你是一位主力资金追踪专家，专注于A股市场资金流向分析。

你的分析框架：
1. 主力资金流向：分析超大单和大单的净流入/流出情况，判断主力意图
2. 北向资金：分析沪深股通的资金流向，外资配置动向
3. 龙虎榜数据：分析机构席位、游资席位的买卖情况
4. 资金面技术指标：分析成交量异动、资金集中度、主力控盘度
5. 筹码分布：分析筹码集中度和移动趋势

输出格式要求：
- 评级：强烈看多/看多/中性/看空/强烈看空
- 置信度：0-100的整数
- 主力动向：建仓/加仓/持仓/减仓/出货
- 简要分析逻辑（不超过100字）
"""

FLOW_ANALYST_USER_PROMPT_TEMPLATE = """请对以下股票进行资金面分析：

股票代码：{stock_code}
股票名称：{stock_name}

资金面数据摘要：
{flow_summary}

请给出你的资金面分析结论。"""


class FlowAnalystAgent:

    def __init__(self, client, model: str = "deepseek-chat"):
        self.client = client
        self.model = model

    def build_messages(self, stock_code: str, stock_name: str, flow_summary: str) -> list:
        user_prompt = FLOW_ANALYST_USER_PROMPT_TEMPLATE.format(
            stock_code=stock_code,
            stock_name=stock_name,
            flow_summary=flow_summary,
        )
        return [
            {"role": "system", "content": FLOW_ANALYST_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    def analyze(self, stock_code: str, stock_name: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        flow_summary = self._extract_flow_summary(market_data)
        messages = self.build_messages(stock_code, stock_name, flow_summary)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=800,
        )

        raw_output = response.choices[0].message.content
        return self._parse_response(raw_output)

    def _extract_flow_summary(self, market_data: Dict[str, Any]) -> str:
        capital_flow = market_data.get("capital_flow", {})
        north_flow = market_data.get("north_flow", {})
        lhb = market_data.get("lhb", {})

        parts = []

        if capital_flow:
            parts.append(f"主力净流入: {capital_flow.get('main_net_inflow', 'N/A')}万")
            parts.append(f"超大单净流入: {capital_flow.get('super_large_net', 'N/A')}万")
            parts.append(f"大单净流入: {capital_flow.get('large_net', 'N/A')}万")
            parts.append(f"中单净流入: {capital_flow.get('medium_net', 'N/A')}万")
            parts.append(f"小单净流入: {capital_flow.get('small_net', 'N/A')}万")
            parts.append(f"主力净流入占比: {capital_flow.get('main_flow_ratio', 'N/A')}%")

        if north_flow:
            parts.append(f"北向资金持股: {north_flow.get('hold_shares', 'N/A')}万股")
            parts.append(f"北向资金持股市值: {north_flow.get('hold_value', 'N/A')}亿")
            parts.append(f"北向资金占比: {north_flow.get('hold_ratio', 'N/A')}%")

        if lhb:
            parts.append(f"龙虎榜上榜日期: {lhb.get('trade_date', 'N/A')}")
            parts.append(f"买入总计: {lhb.get('total_buy', 'N/A')}万")
            parts.append(f"卖出总计: {lhb.get('total_sell', 'N/A')}万")
            parts.append(f"净买入: {lhb.get('net_buy', 'N/A')}万")

        return "\n".join(parts) if parts else "无可用资金面数据"

    def _parse_response(self, raw_output: str) -> Dict[str, Any]:
        rating = "中性"
        confidence = 50
        main_force_action = "持仓"

        import re

        rating_map = {
            "强烈看多": "强烈看多",
            "看多": "看多",
            "中性": "中性",
            "看空": "看空",
            "强烈看空": "强烈看空",
        }

        action_map = {
            "建仓": "建仓",
            "加仓": "加仓",
            "持仓": "持仓",
            "减仓": "减仓",
            "出货": "出货",
        }

        for line in raw_output.split("\n"):
            line_stripped = line.strip()

            for key, val in rating_map.items():
                if key in line_stripped and ("评级" in line_stripped or "资金面" in line_stripped or "结论" in line_stripped):
                    rating = val

            if "置信度" in line_stripped or "信心" in line_stripped:
                nums = re.findall(r'\d+', line_stripped)
                if nums:
                    confidence = min(100, max(0, int(nums[0])))

            for key, val in action_map.items():
                if key in line_stripped:
                    main_force_action = val

        return {
            "agent": "flow_analyst",
            "rating": rating,
            "confidence": confidence,
            "main_force_action": main_force_action,
            "analysis_logic": raw_output[:200],
            "raw_output": raw_output,
        }