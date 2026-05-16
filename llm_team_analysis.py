#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import json
from openai import OpenAI

# 取消代理设置
for key in list(os.environ.keys()):
    if key.lower().endswith('proxy'):
        del os.environ[key]

api_key = "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"
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=api_key
)

call_model_priorities = [
    "deepseek-ai/deepseek-v4-pro",
    "z-ai/glm-5.1",
    "deepseek-ai/deepseek-v4-flash"
]

def chat_completion(messages, model_idx=0, temperature=0.7):
    for attempt in range(3):
        try:
            model_name = call_model_priorities[model_idx % len(call_model_priorities)]
            completion = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=2048
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Model {call_model_priorities[model_idx]} failed (attempt {attempt+1}): {e}")
            model_idx += 1
            time.sleep(3)
    return None

def main():
    print("="*70)
    print("LLM 小组分析回测报告")
    print("="*70)
    
    with open("backtest_report.txt", "r", encoding="utf8") as f:
        backtest_text = f.read()
    
    with open("backtest_report.json", "r", encoding="utf8") as f:
        backtest_json = json.load(f)
    
    # LLM 角色设置
    team_roles = [
        {
            "role": "组长",
            "prompt": """你是 LLM 小组的组长，负责统筹全局、任务规划、流程管控、最终终审。根据回测报告，你需要指出最大的问题是什么，以及给出总体改进方向。""",
        },
        {
            "role": "规划员",
            "prompt": """你是 LLM 小组的规划员，负责拆解需求、制定执行方案。根据回测结果，分析为什么只有2次交易，胜率只有50%，问题出在哪里？提出优化方案。"""
        },
        {
            "role": "执行员",
            "prompt": """你是 LLM 小组的执行员，负责落地具体事务、输出工作成果。根据回测报告和策略，给出具体的修改代码和修改建议，参数调整等具体措施。"""
        },
        {
            "role": "评审员",
            "prompt": """你是 LLM 小组的评审员，交叉核验、查找问题、给出优化建议。从风险控制、策略逻辑、参数设置角度分析现有策略，找出缺陷。"""
        }
    ]
    
    discussion_history = []
    all_responses = {}
    
    for member in team_roles:
        role_name = member["role"]
        print(f"\n--- 正在邀请 {role_name} 分析...")
        
        messages = [
            {
                "role": "system",
                "content": "你是量化交易系统的专家，精通 A 股市场，主线策略，回测分析。用中文回复。"
            },
            {
                "role": "user",
                "content": f"""{member["prompt"]}

回测报告：
{backtest_text}

回测 JSON 数据：
{json.dumps(backtest_json, ensure_ascii=False, indent=2)}
"""
            }
        ]
        
        response = chat_completion(messages)
        all_responses[role_name] = response
        
        print(f"\n{role_name} 回复：")
        print(response)
        discussion_history.append(f"--- {role_name}：\n{response}")
        time.sleep(1)
    
    # 最终总结
    print("\n"*2)
    print("="*70)
    print("组长终审总结")
    print("="*70)
    final_summary_prompt = "\n".join(discussion_history) + "\n\n请根据以上所有LLM成员的讨论，给出最终的改进方案，包括具体的代码修改建议、策略逻辑优化、参数调整。"
    final_messages = [
        {
            "role": "system",
            "content": "你是量化交易专家，负责终审总结，给出具体可执行的改进方案。用中文回复。"
        },
        {
            "role": "user",
            "content": final_summary_prompt
        }
    ]
    final_summary = chat_completion(final_messages)
    all_responses["组长终审"] = final_summary
    
    print(final_summary)
    
    # 保存结果
    with open("LLM_TEAM_ANALYSIS_REPORT.md", "w", encoding="utf8") as f:
        f.write("# LLM 小组分析报告\n\n")
        for role, resp in all_responses.items():
            f.write(f"## {role}\n\n{resp}\n\n")
    
    print("\n\n报告已保存为 LLM_TEAM_ANALYSIS_REPORT.md")
    print("\n")
    print("="*70)
    return all_responses

if __name__ == "__main__":
    main()
