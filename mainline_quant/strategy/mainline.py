# -*- coding: utf-8 -*-
"""
主线策略模块
识别主线行情，选择龙头股票
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from mainline_quant.data import DataFetcher


class MainlineStrategy:
    """
    主线策略
    专注于识别和交易主线行情中的龙头股
    """
    
    def __init__(self, data_fetcher: Optional[DataFetcher] = None):
        self.fetcher = data_fetcher or DataFetcher()
        
        # 主线识别参数
        self.min_consecutive_days = 3  # 最少连续上涨天数
        self.min_avg_change_pct = 2.0  # 平均涨幅阈值
        self.min_score = 70  # 最低入场评分
        
        # 评分权重
        self.weights = {
            'amount_rank': 25,  # 成交额排名
            'consecutive_rise': 20,  # 连续上涨
            'north_flow': 20,  # 北向资金
            'limit_up_count': 20,  # 涨停家数
            'leadership': 15  # 龙头效应
        }
    
    def scan_mainline(self) -> pd.DataFrame:
        """
        扫描所有概念板块，找出潜在主线
        :return: DataFrame [concept_code, concept_name, score, ...]
        """
        print("正在扫描主线...")
        
        # 1. 获取所有概念板块
        concepts = self.fetcher.get_all_concepts()
        if concepts.empty:
            print("未获取到概念板块数据")
            return pd.DataFrame()
        
        print(f"共扫描 {len(concepts)} 个概念板块")
        
        # 2. 逐个分析概念板块
        results = []
        for idx, row in concepts.iterrows():
            concept_code = row['concept_code']
            concept_name = row['concept_name']
            
            try:
                # 获取概念行情
                market_df = self.fetcher.get_concept_market(concept_code, days=30)
                if market_df.empty or len(market_df) < 10:
                    continue
                
                # 计算评分
                score_data = self._calculate_concept_score(concept_code, market_df)
                if score_data:
                    score_data['concept_code'] = concept_code
                    score_data['concept_name'] = concept_name
                    results.append(score_data)
                
            except Exception as e:
                continue
        
        if not results:
            print("未找到符合条件的主线")
            return pd.DataFrame()
        
        # 3. 排序并返回
        result_df = pd.DataFrame(results)
        result_df = result_df.sort_values('total_score', ascending=False).reset_index(drop=True)
        print(f"\n找到 {len(result_df)} 个潜在主线")
        
        return result_df
    
    def _calculate_concept_score(self, concept_code: str, market_df: pd.DataFrame) -> Optional[Dict]:
        """
        计算概念板块评分
        """
        if len(market_df) < 10:
            return None
        
        recent_df = market_df.tail(10).copy()
        latest = recent_df.iloc[-1]
        
        # 1. 连续上涨天数
        consecutive_days = 0
        for i in range(len(recent_df)-1, -1, -1):
            if recent_df.iloc[i]['change_pct'] > 0:
                consecutive_days += 1
            else:
                break
        
        # 2. 平均涨幅
        avg_change = recent_df['change_pct'].tail(5).mean()
        
        # 3. 获取成分股分析龙头效应
        constituents = self.fetcher.get_concept_constituents(concept_code)
        limit_up_count = 0
        if not constituents.empty:
            # 计算涨停家数
            limit_up_count = len(constituents[constituents['change_pct'] >= 9.8])
        
        # 4. 计算各项得分
        score_amount = min(25, 25)  # 简化处理，实际可结合真实成交额占比
        score_consecutive = min(20, consecutive_days * 5)
        score_avg_change = min(20, avg_change * 5)
        score_limit_up = min(20, limit_up_count * 3)
        score_leadership = 15 if consecutive_days >= 3 else 10 if consecutive_days >= 2 else 5
        
        total_score = (
            score_amount +
            score_consecutive +
            score_avg_change +
            score_limit_up +
            score_leadership
        )
        
        return {
            'consecutive_days': consecutive_days,
            'avg_change_pct': round(avg_change, 2),
            'limit_up_count': limit_up_count,
            'latest_change_pct': round(latest['change_pct'], 2),
            'latest_close': latest['close'],
            'total_score': total_score
        }
    
    def select_leaders(self, concept_code: str, top_n: int = 5) -> pd.DataFrame:
        """
        从概念板块中选择龙头股
        :param concept_code: 概念板块代码
        :param top_n: 返回前N只
        :return: DataFrame
        """
        constituents = self.fetcher.get_concept_constituents(concept_code)
        if constituents.empty:
            return pd.DataFrame()
        
        # 获取实时行情
        stock_codes = constituents['stock_code'].tolist()[:50]  # 限制数量避免请求过多
        realtime_df = self.fetcher.get_stock_realtime(stock_codes)
        
        if realtime_df.empty:
            return constituents.head(top_n)
        
        # 合并数据
        merged = pd.merge(constituents, realtime_df, on='stock_code', how='left')
        
        # 计算龙头评分（简化版）
        # 实际应用中应结合K线形态、成交量、历史表现等
        merged['leader_score'] = merged.apply(
            lambda x: self._calculate_leader_score(x), axis=1
        )
        
        # 排序
        merged = merged.sort_values('leader_score', ascending=False).reset_index(drop=True)
        
        return merged.head(top_n)
    
    def _calculate_leader_score(self, row) -> float:
        """计算个股龙头评分"""
        score = 0.0
        
        # 1. 涨幅得分
        change_pct = row.get('change_pct', 0)
        if change_pct >= 9.8:
            score += 40
        elif change_pct >= 7:
            score += 30
        elif change_pct >= 5:
            score += 20
        elif change_pct >= 3:
            score += 10
        
        # 2. 成交量/成交额（简化处理）
        score += 30  # 实际应结合历史数据分析
        
        # 3. 价格位置
        score += 30  # 实际应结合K线分析
        
        return score
    
    def generate_trading_signal(self, concept_code: str) -> Dict:
        """
        生成交易信号
        :param concept_code: 概念板块代码
        :return: 信号字典
        """
        # 1. 分析主线
        market_df = self.fetcher.get_concept_market(concept_code, days=30)
        if market_df.empty:
            return {'signal': 'NONE', 'reason': '数据不足'}
        
        score_data = self._calculate_concept_score(concept_code, market_df)
        if not score_data:
            return {'signal': 'NONE', 'reason': '评分计算失败'}
        
        total_score = score_data['total_score']
        
        # 2. 判断信号
        if total_score >= self.min_score:
            # 选择龙头
            leaders = self.select_leaders(concept_code, top_n=3)
            return {
                'signal': 'BUY',
                'concept_code': concept_code,
                'score': total_score,
                'leaders': leaders.to_dict('records') if not leaders.empty else [],
                'reason': f'主线确认，评分{total_score}'
            }
        elif total_score >= self.min_score * 0.7:
            return {
                'signal': 'WATCH',
                'concept_code': concept_code,
                'score': total_score,
                'reason': '关注中，评分有待提高'
            }
        else:
            return {
                'signal': 'SELL',
                'concept_code': concept_code,
                'score': total_score,
                'reason': '主线退潮'
            }
    
    def check_exit_signal(self, concept_code: str, entry_score: float) -> Tuple[bool, str]:
        """
        检查出场信号
        :param concept_code: 概念板块代码
        :param entry_score: 入场时评分
        :return: (是否出场, 原因)
        """
        market_df = self.fetcher.get_concept_market(concept_code, days=10)
        if market_df.empty:
            return True, "数据不足，谨慎出场"
        
        latest = market_df.iloc[-1]
        score_data = self._calculate_concept_score(concept_code, market_df)
        
        if not score_data:
            return True, "评分无法计算"
        
        current_score = score_data['total_score']
        
        # 评分大幅下降
        if current_score < entry_score * 0.6:
            return True, f"评分从{entry_score}下降到{current_score}"
        
        # 板块大跌
        if latest['change_pct'] <= -3:
            return True, f"板块大跌{latest['change_pct']:.2f}%"
        
        return False, ""
