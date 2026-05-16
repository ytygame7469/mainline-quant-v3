# -*- coding: utf-8 -*-
"""
龙头股选择系统（LLM小组设计）
4个维度评分，选择前3-5只
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class LeaderSelector:
    """
    龙头股选择器
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
        print("✅ LeaderSelector 初始化成功")
    
    def select_leaders(self, concept_code: str, num_leaders: int = 5) -> pd.DataFrame:
        """
        选择概念板块的龙头股
        
        Args:
            concept_code: 概念代码
            num_leaders: 返回前N只龙头股
        
        Returns:
            DataFrame: 龙头股列表
        """
        print(f"\n🔍 开始选择概念板块 {concept_code} 的龙头股...")
        
        # 1. 获取成分股
        constituents = self.concept_data.get_concept_constituent(concept_code)
        if constituents.empty:
            print("❌ 没有成分股数据")
            return pd.DataFrame()
        
        print(f"✅ 共 {len(constituents)} 只成分股")
        
        # 2. 获取实时行情
        stock_codes = constituents['stock_code'].tolist()
        realtime_data = self.stock_data.get_realtime_sina(stock_codes[:100])  # 先取前100只避免请求过多
        
        if realtime_data.empty:
            print("❌ 没有实时行情数据")
            return pd.DataFrame()
        
        # 3. 计算每只股票的龙头评分
        results = []
        
        for idx, row in realtime_data.iterrows():
            stock_code = row['stock_code']
            
            # 计算该股票的龙头评分
            score_result = self._calculate_leader_score(stock_code, row)
            
            # 获取股票名称
            stock_info = constituents[constituents['stock_code'] == stock_code]
            if not stock_info.empty:
                stock_name = stock_info.iloc[0]['stock_name']
                score_result['stock_name'] = stock_name
            else:
                score_result['stock_name'] = ""
            
            results.append(score_result)
        
        # 4. 转换为DataFrame并排序
        df = pd.DataFrame(results)
        df = df.sort_values('total_score', ascending=False).reset_index(drop=True)
        
        print(f"\n🏆 前{num_leaders}只龙头股:")
        print(df.head(num_leaders).to_string(index=False))
        
        return df.head(num_leaders)
    
    def _calculate_leader_score(self, stock_code: str, realtime_row: pd.Series) -> Dict:
        """
        计算单只股票的龙头评分（4个维度）
        
        Args:
            stock_code: 股票代码
            realtime_row: 实时行情数据
        
        Returns:
            Dict: 评分结果
        """
        score_result = {
            'stock_code': stock_code,
            'total_score': 0,
            'components': {}
        }
        
        # 维度1: 成交额排名 (40分)
        amount_score = self._score_amount(stock_code, realtime_row)
        score_result['components']['amount'] = amount_score
        score_result['total_score'] += amount_score
        
        # 维度2: 涨跌幅 (30分)
        change_pct_score = self._score_change_pct(stock_code, realtime_row)
        score_result['components']['change_pct'] = change_pct_score
        score_result['total_score'] += change_pct_score
        
        # 维度3: 技术形态 (20分)
        technical_score = self._score_technical(stock_code)
        score_result['components']['technical'] = technical_score
        score_result['total_score'] += technical_score
        
        # 维度4: 历史地位 (10分)
        history_score = self._score_history(stock_code)
        score_result['components']['history'] = history_score
        score_result['total_score'] += history_score
        
        return score_result
    
    def _score_amount(self, stock_code: str, realtime_row: pd.Series) -> float:
        """
        维度1: 成交额排名 (40分)
        
        规则:
        - >50亿: 40分
        - >20亿: 35分
        - >10亿: 28分
        - >5亿: 20分
        - >1亿: 12分
        - <1亿: 5分
        """
        try:
            amount = realtime_row.get('amount', 0)
            if amount > 5000000000:
                return 40
            elif amount > 2000000000:
                return 35
            elif amount > 1000000000:
                return 28
            elif amount > 500000000:
                return 20
            elif amount > 100000000:
                return 12
            else:
                return 5
        except Exception:
            pass
        
        return 20  # 默认分数
    
    def _score_change_pct(self, stock_code: str, realtime_row: pd.Series) -> float:
        """
        维度2: 涨跌幅 (30分)
        
        规则:
        - 涨停: 30分
        - >7%: 25分
        - >5%: 20分
        - >3%: 15分
        - >0%: 10分
        - <0%: 5分
        """
        try:
            current = realtime_row.get('current', 0)
            pre_close = realtime_row.get('pre_close', 0)
            
            if pre_close > 0:
                change_pct = (current - pre_close) / pre_close * 100
                
                # 简化版涨停判断
                if change_pct >= 9.9:
                    return 30
                elif change_pct > 7:
                    return 25
                elif change_pct > 5:
                    return 20
                elif change_pct > 3:
                    return 15
                elif change_pct > 0:
                    return 10
                else:
                    return 5
        except Exception:
            pass
        
        return 15  # 默认分数
    
    def _score_technical(self, stock_code: str) -> float:
        """
        维度3: 技术形态 (20分)
        
        规则:
        - 均线多头+MACD金叉: 20分
        - 均线多头: 15分
        - 5日>10日: 10分
        - 其他: 5分
        """
        try:
            kline = self.stock_data.get_stock_kline(stock_code, count=30)
            if kline.empty or len(kline) < 20:
                return 5
            
            closes = kline['close'].values
            
            # 计算均线
            ma5 = np.mean(closes[-5:])
            ma10 = np.mean(closes[-10:])
            ma20 = np.mean(closes[-20:])
            
            if ma5 > ma10 > ma20:
                return 15  # 简化版，暂时不算MACD
            elif ma5 > ma10:
                return 10
            else:
                return 5
        except Exception:
            pass
        
        return 10  # 默认分数
    
    def _score_history(self, stock_code: str) -> float:
        """
        维度4: 历史地位 (10分)
        
        规则:
        - 历史龙头股: 10分
        - 大盘股: 8分
        - 中盘股: 5分
        - 小盘股: 3分
        """
        try:
            # 简化版: 根据股票代码判断
            # 600xxx, 000xxx开头的通常是大盘股/老股
            if stock_code.startswith('600') or stock_code.startswith('000'):
                return 8
            elif stock_code.startswith('60') or stock_code.startswith('00'):
                return 5
            else:
                return 3
        except Exception:
            pass
        
        return 5  # 默认分数


# ===============================
# 快捷入口
# ===============================

def get_leader_selector(concept_data, stock_data) -> LeaderSelector:
    """获取龙头选择器实例"""
    return LeaderSelector(concept_data, stock_data)

