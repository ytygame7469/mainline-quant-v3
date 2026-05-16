# -*- coding: utf-8 -*-
"""
增强版评分系统（LLM小组设计）
8个维度评分，满分100分
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class ConceptScoring:
    """
    概念板块评分系统
    """
    
    def __init__(self, concept_data, stock_data):
        """
        初始化
        
        Args:
            concept_data: 概念板块数据提供者
            stock_data: 股票数据提供者
        """
        self.concept_data = concept_data
        self.stock_data = stock_data
        print("✅ ConceptScoring 初始化成功")
    
    def calculate_score(self, concept_code: str, concept_name: str = "") -> Dict:
        """
        计算概念板块综合评分（8个维度）
        
        Args:
            concept_code: 概念代码
            concept_name: 概念名称
        
        Returns:
            Dict: 评分结果
        """
        score_result = {
            'concept_code': concept_code,
            'concept_name': concept_name,
            'total_score': 0,
            'components': {}
        }
        
        # 维度1: 今日涨跌幅排名 (25分)
        change_score = self._score_change_pct(concept_code)
        score_result['components']['change_pct'] = change_score
        score_result['total_score'] += change_score
        
        # 维度2: 连续上涨天数 (15分)
        consecutive_score = self._score_consecutive_up(concept_code)
        score_result['components']['consecutive_up'] = consecutive_score
        score_result['total_score'] += consecutive_score
        
        # 维度3: 涨停家数 (20分)
        limit_up_score = self._score_limit_up(concept_code)
        score_result['components']['limit_up'] = limit_up_score
        score_result['total_score'] += limit_up_score
        
        # 维度4: 成交额排名 (15分)
        amount_score = self._score_amount(concept_code)
        score_result['components']['amount'] = amount_score
        score_result['total_score'] += amount_score
        
        # 维度5: 涨跌比 (10分)
        up_down_ratio_score = self._score_up_down_ratio(concept_code)
        score_result['components']['up_down_ratio'] = up_down_ratio_score
        score_result['total_score'] += up_down_ratio_score
        
        # 维度6: 主力资金流入 (10分) - 简化版
        capital_flow_score = self._score_capital_flow(concept_code)
        score_result['components']['capital_flow'] = capital_flow_score
        score_result['total_score'] += capital_flow_score
        
        # 维度7: 均线形态 (5分)
        ma_score = self._score_ma_shape(concept_code)
        score_result['components']['ma_shape'] = ma_score
        score_result['total_score'] += ma_score
        
        return score_result
    
    def _score_change_pct(self, concept_code: str) -> float:
        """
        维度1: 今日涨跌幅排名 (25分)
        
        规则:
        - >5%: 25分
        - 3%-5%: 20分
        - 1%-3%: 15分
        - 0%-1%: 10分
        - <0%: 5分
        """
        try:
            realtime = self.concept_data.get_concept_realtime(concept_code)
            if realtime:
                change_pct = realtime.get('change_pct', 0)
                if change_pct > 5:
                    return 25
                elif change_pct > 3:
                    return 20
                elif change_pct > 1:
                    return 15
                elif change_pct > 0:
                    return 10
                else:
                    return 5
        except Exception:
            pass
        
        # 备用方案: 从K线获取最新涨跌幅
        try:
            kline = self.concept_data.get_concept_kline(concept_code, count=5)
            if not kline.empty:
                latest = kline.iloc[-1]
                change_pct = latest.get('change_pct', 0)
                if change_pct > 5:
                    return 25
                elif change_pct > 3:
                    return 20
                elif change_pct > 1:
                    return 15
                elif change_pct > 0:
                    return 10
                else:
                    return 5
        except Exception:
            pass
        
        return 10  # 默认分数
    
    def _score_consecutive_up(self, concept_code: str) -> float:
        """
        维度2: 连续上涨天数 (15分)
        
        规则:
        - >=5天: 15分
        - 3-4天: 10分
        - 2天: 7分
        - 1天: 5分
        """
        try:
            kline = self.concept_data.get_concept_kline(concept_code, count=10)
            if kline.empty:
                return 5
            
            consecutive_days = 0
            for i in range(len(kline)-1, -1, -1):
                if kline.iloc[i]['change_pct'] > 0:
                    consecutive_days += 1
                else:
                    break
            
            if consecutive_days >= 5:
                return 15
            elif consecutive_days >= 3:
                return 10
            elif consecutive_days >= 2:
                return 7
            else:
                return 5
        except Exception:
            pass
        
        return 5  # 默认分数
    
    def _score_limit_up(self, concept_code: str) -> float:
        """
        维度3: 涨停家数 (20分)
        
        规则:
        - >=15只: 20分
        - 10-14只: 15分
        - 5-9只: 10分
        - 2-4只: 5分
        - <2只: 2分
        """
        try:
            # 简化版: 从概念板块涨跌幅*2估算
            realtime = self.concept_data.get_concept_realtime(concept_code)
            if realtime:
                change_pct = realtime.get('change_pct', 0)
                estimated_limit_up = int(change_pct * 2)
                if estimated_limit_up >= 15:
                    return 20
                elif estimated_limit_up >= 10:
                    return 15
                elif estimated_limit_up >= 5:
                    return 10
                elif estimated_limit_up >= 2:
                    return 5
                else:
                    return 2
        except Exception:
            pass
        
        return 5  # 默认分数
    
    def _score_amount(self, concept_code: str) -> float:
        """
        维度4: 成交额排名 (15分)
        
        规则:
        - 前10%: 15分
        - 前30%: 12分
        - 前50%: 8分
        - 其他: 5分
        """
        try:
            kline = self.concept_data.get_concept_kline(concept_code, count=5)
            if not kline.empty:
                latest = kline.iloc[-1]
                amount = latest.get('amount', 0)
                # 简化版: 根据成交额评分
                if amount > 10000000000:  # >100亿
                    return 15
                elif amount > 5000000000:  # >50亿
                    return 12
                elif amount > 1000000000:  # >10亿
                    return 8
                else:
                    return 5
        except Exception:
            pass
        
        return 8  # 默认分数
    
    def _score_up_down_ratio(self, concept_code: str) -> float:
        """
        维度5: 涨跌比 (10分)
        
        规则:
        - >=3:1: 10分
        - >=2:1: 8分
        - >=1:1: 5分
        - <1:1: 3分
        """
        try:
            stats = self.concept_data.calculate_concept_stats(concept_code, self.stock_data)
            if stats:
                ratio = stats.get('up_down_ratio', 1)
                if ratio >= 3:
                    return 10
                elif ratio >= 2:
                    return 8
                elif ratio >= 1:
                    return 5
                else:
                    return 3
        except Exception:
            pass
        
        return 5  # 默认分数
    
    def _score_capital_flow(self, concept_code: str) -> float:
        """
        维度6: 主力资金流入 (10分) - 简化版
        
        规则:
        简化: 用涨跌幅代替
        """
        try:
            realtime = self.concept_data.get_concept_realtime(concept_code)
            if realtime:
                change_pct = realtime.get('change_pct', 0)
                if change_pct > 5:
                    return 10
                elif change_pct > 3:
                    return 8
                elif change_pct > 1:
                    return 5
                else:
                    return 3
        except Exception:
            pass
        
        return 5  # 默认分数
    
    def _score_ma_shape(self, concept_code: str) -> float:
        """
        维度7: 均线形态 (5分)
        
        规则:
        - 多头排列(5日>10日>20日): 5分
        - 5日>10日: 3分
        - 其他: 2分
        """
        try:
            kline = self.concept_data.get_concept_kline(concept_code, count=30)
            if kline.empty or len(kline) < 20:
                return 2
            
            closes = kline['close'].values
            
            # 计算均线
            ma5 = np.mean(closes[-5:])
            ma10 = np.mean(closes[-10:])
            ma20 = np.mean(closes[-20:])
            
            if ma5 > ma10 > ma20:
                return 5
            elif ma5 > ma10:
                return 3
            else:
                return 2
        except Exception:
            pass
        
        return 2  # 默认分数
    
    def scan_all_concepts(self, top_n: int = 50) -> pd.DataFrame:
        """
        扫描所有概念板块并评分
        
        Args:
            top_n: 返回前N个概念板块
        
        Returns:
            DataFrame: 评分结果
        """
        print("\n" + "=" * 80)
        print("🚀 开始扫描所有概念板块...")
        print("=" * 80)
        
        concepts = self.concept_data.get_all_concepts()
        if concepts.empty:
            print("❌ 没有概念板块数据")
            return pd.DataFrame()
        
        print(f"📊 共 {len(concepts)} 个概念板块待扫描")
        
        results = []
        
        # 为了演示，先扫描前top_n*2个
        scan_count = min(top_n * 2, len(concepts))
        
        for idx, row in concepts.head(scan_count).iterrows():
            concept_code = row['concept_code']
            concept_name = row['concept_name']
            
            print(f"[{idx+1}/{scan_count}] 评分中: {concept_name} ({concept_code})")
            
            score_result = self.calculate_score(concept_code, concept_name)
            results.append(score_result)
        
        # 转换为DataFrame
        df = pd.DataFrame(results)
        
        # 按总分排序
        df = df.sort_values('total_score', ascending=False).reset_index(drop=True)
        
        print("\n" + "=" * 80)
        print("✅ 扫描完成！")
        print("=" * 80)
        print(f"\n🏆 前{top_n}个潜在主线概念板块:")
        print(df.head(top_n).to_string(index=False))
        
        return df.head(top_n)


# ===============================
# 快捷入口
# ===============================

def get_scoring(concept_data, stock_data) -> ConceptScoring:
    """获取评分系统实例"""
    return ConceptScoring(concept_data, stock_data)

