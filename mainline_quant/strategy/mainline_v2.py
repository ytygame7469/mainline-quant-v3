# -*- coding: utf-8 -*-
"""
简化版主线策略（LLM小组优化版）
评分系统简化为3个维度：
- 今日涨跌幅排名：50分
- 连续上涨天数：30分
- 涨停家数：20分
"""
import sys
import os
from datetime import datetime
from typing import Optional, List, Dict

import pandas as pd
import numpy as np

# 清除代理
for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    if var in os.environ:
        del os.environ[var]

sys.path.insert(0, '/workspace/references/adata')


class SimplifiedMainlineStrategy:
    """
    简化版主线策略
    """
    
    def __init__(self, data_provider):
        """
        初始化
        
        Args:
            data_provider: 数据提供者
        """
        self.data = data_provider
        self.concepts = pd.DataFrame()
        
        # 尝试加载概念板块
        self._load_concepts()
        
        print("✅ SimplifiedMainlineStrategy 初始化成功")
    
    def _load_concepts(self):
        """加载概念板块"""
        try:
            self.concepts = self.data.get_all_concepts()
            if not self.concepts.empty:
                print(f"✅ 成功加载 {len(self.concepts)} 个概念板块")
        except Exception as e:
            print(f"⚠️  加载概念板块失败: {e}")
    
    def _calculate_concept_score_simplified(self, concept_data: Dict) -> Dict:
        """
        简化版评分计算（LLM小组决策）
        
        3个维度：
        - 今日涨跌幅排名：50分
        - 连续上涨天数：30分
        - 涨停家数：20分
        
        满分100分
        """
        score = 0
        
        # 1. 今日涨跌幅排名（假设是第1名，得50分）
        # 实际应用中需要排序后给分
        # 这里先模拟简化逻辑
        if concept_data.get('change_pct_today', 0) > 5:
            score += 50
        elif concept_data.get('change_pct_today', 0) > 3:
            score += 35
        elif concept_data.get('change_pct_today', 0) > 1:
            score += 20
        else:
            score += 5
        
        # 2. 连续上涨天数（30分）
        up_days = concept_data.get('consecutive_up_days', 1)
        if up_days >= 5:
            score += 30
        elif up_days >= 3:
            score += 20
        elif up_days >= 2:
            score += 10
        else:
            score += 5
        
        # 3. 涨停家数（20分）
        limit_up_count = concept_data.get('limit_up_count', 0)
        if limit_up_count >= 15:
            score += 20
        elif limit_up_count >= 10:
            score += 15
        elif limit_up_count >= 5:
            score += 10
        elif limit_up_count >= 2:
            score += 5
        
        return {
            'score': score,
            'components': {
                'change_rank': score if score > 0 else 0,
                'consecutive_up': score if score > 0 else 0,
                'limit_up_count': score if score > 0 else 0
            }
        }
    
    def scan_mainline_simplified(self) -> pd.DataFrame:
        """
        简化版主线扫描
        
        Returns:
            DataFrame: 概念板块评分排序
        """
        print("\n" + "=" * 80)
        print("🔍 简化版主线扫描")
        print("=" * 80)
        
        if self.concepts.empty:
            print("⚠️  概念板块数据不可用")
            return pd.DataFrame()
        
        print(f"✅ 扫描 {len(self.concepts)} 个概念板块...")
        
        results = []
        
        # 遍历概念板块（简化版演示）
        for i, concept in self.concepts.head(50).iterrows():
            # 模拟数据（实际应用需要真实获取）
            concept_data = {
                'concept_code': concept.get('concept_code', ''),
                'concept_name': concept.get('name', concept.get('concept_name', '')),
                'change_pct_today': 3.5 + np.random.random() * 4.5,  # 模拟涨跌幅
                'consecutive_up_days': 2 + np.random.randint(0, 5),  # 模拟连涨
                'limit_up_count': 3 + np.random.randint(0, 12),  # 模拟涨停
            }
            
            # 计算评分
            score_result = self._calculate_concept_score_simplified(concept_data)
            
            results.append({
                'concept_code': concept_data['concept_code'],
                'concept_name': concept_data['concept_name'],
                'change_pct': concept_data['change_pct_today'],
                'consecutive_up': concept_data['consecutive_up_days'],
                'limit_up_count': concept_data['limit_up_count'],
                'score': score_result['score']
            })
        
        # 排序
        df = pd.DataFrame(results)
        df = df.sort_values('score', ascending=False)
        
        print(f"\n✅ 主线扫描完成")
        print(f"\n潜在主线（前10名）：")
        print(df.head(10).to_string(index=False))
        
        # 筛选评分≥70的
        df_mainline = df[df['score'] >= 70]
        if not df_mainline.empty:
            print(f"\n🚀 找到 {len(df_mainline)} 个潜在主线（评分≥70）")
        
        return df
    
    def select_leaders_simplified(self, concept_code: str, num_leaders: int = 3) -> List[str]:
        """
        简化版龙头选择
        
        策略：成分股成交额前3 + 涨跌幅前3
        
        Args:
            concept_code: 概念代码
            num_leaders: 龙头数量
            
        Returns:
            股票代码列表
        """
        print(f"\n🔍 筛选概念 {concept_code} 的龙头股...")
        
        # 简化演示：返回一些例子
        leaders = [
            '600000',
            '000001',
            '600519'
        ]
        
        print(f"✅ 龙头股: {leaders}")
        return leaders[:num_leaders]


# ===============================
# 测试
# ===============================

if __name__ == "__main__":
    print("=" * 80)
    print("简化版主线策略测试")
    print("=" * 80)
    
    from mainline_quant.data.fetcher_v2 import get_data_provider
    
    # 1. 获取数据提供者
    provider = get_data_provider()
    
    # 2. 初始化策略
    strategy = SimplifiedMainlineStrategy(provider)
    
    # 3. 扫描主线
    mainlines = strategy.scan_mainline_simplified()
    
    print("\n" + "=" * 80)
    print("✅ 简化版主线策略测试完成！")
    print("=" * 80)
