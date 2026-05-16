# -*- coding: utf-8 -*-
"""
涨停原因分析模块
识别涨停原因、分析概念板块联动、判断主线扩散效应
"""
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict


def identify_limit_up_reason(limit_up_df: pd.DataFrame, concept_stocks: Dict[str, pd.DataFrame]) -> List[Dict]:
    """
    识别涨停股票的原因
    
    参数:
        limit_up_df: 涨停股票列表
        concept_stocks: 概念板块成分股字典，key是概念代码，value是成分股
    
    返回:
        带涨停原因的股票列表
    """
    if limit_up_df.empty or not concept_stocks:
        return []
    
    stocks_with_reason = []
    
    for _, limit_stock in limit_up_df.iterrows():
        stock_code = limit_stock['stock_code']
        
        # 查找属于哪个概念
        possible_concepts = []
        for concept_code, constituent_df in concept_stocks.items():
            if 'stock_code' in constituent_df.columns:
                if stock_code in constituent_df['stock_code'].values:
                    possible_concepts.append(concept_code)
        
        stocks_with_reason.append({
            'stock_code': stock_code,
            'stock_name': limit_stock.get('short_name', stock_code),
            'possible_concepts': possible_concepts,
            'reason': '概念联动' if len(possible_concepts) > 0 else '其他',
            'close': limit_stock.get('close', 0),
            'change_pct': limit_stock.get('change_pct', 0)
        })
    
    return stocks_with_reason


def analyze_concept_co_movement(concept_stocks: Dict[str, pd.DataFrame], stock_limit_up: pd.DataFrame) -> Dict:
    """
    分析概念板块联动效应
    
    参数:
        concept_stocks: 概念板块成分股
        stock_limit_up: 涨停股票列表
    
    返回:
        概念联动分析
    """
    concept_performance = {}
    
    for concept_code, constituent_df in concept_stocks.items():
        if constituent_df.empty:
            continue
        
        if 'stock_code' not in constituent_df.columns:
            continue
        
        # 统计该概念内涨停股数量
        limit_up_in_concept = 0
        for _, limit_stock in stock_limit_up.iterrows():
            if limit_stock['stock_code'] in constituent_df['stock_code'].values:
                limit_up_in_concept += 1
        
        # 计算涨停占比
        total_stocks = len(constituent_df)
        limit_up_ratio = limit_up_in_concept / total_stocks if total_stocks > 0 else 0
        
        concept_performance[concept_code] = {
            'concept_code': concept_code,
            'total_stocks': total_stocks,
            'limit_up_count': limit_up_in_concept,
            'limit_up_ratio': limit_up_ratio,
            'is_hot': limit_up_ratio >= 0.2 or limit_up_in_concept >= 3
        }
    
    return concept_performance


def detect_main_line_diffusion(concept_performance: Dict, concept_stocks: Dict[str, pd.DataFrame]) -> Dict:
    """
    检测主线扩散效应
    
    参数:
        concept_performance: 概念板块联动分析结果
        concept_stocks: 概念板块成分股
    
    返回:
        主线扩散分析
    """
    # 找出热门概念
    hot_concepts = []
    for concept_code, perf in concept_performance.items():
        if perf['is_hot']:
            hot_concepts.append(concept_code)
    
    # 分析热点扩散
    diffusion_analysis = {
        'hot_concepts': hot_concepts,
        'hot_concept_count': len(hot_concepts),
        'is_multi_hot': len(hot_concepts) > 1,
        'main_line_strength': calculate_main_line_strength(concept_performance, hot_concepts)
    }
    
    return diffusion_analysis


def calculate_main_line_strength(concept_performance: Dict, hot_concepts: List[str]) -> float:
    """
    计算主线强度
    
    参数:
        concept_performance: 概念板块联动分析
        hot_concepts: 热门概念列表
    
    返回:
        主线强度分数 0-100
    """
    if not hot_concepts:
        return 0.0
    
    # 简单计算：热门概念的平均涨停占比
    total_ratio = 0.0
    for concept_code in hot_concepts:
        total_ratio += concept_performance[concept_code]['limit_up_ratio']
    
    avg_ratio = total_ratio / len(hot_concepts)
    
    return min(100.0, avg_ratio * 100)


def find_related_concepts(stock_code: str, concept_stocks: Dict[str, pd.DataFrame]) -> List[str]:
    """
    查找股票相关概念
    
    参数:
        stock_code: 股票代码
        concept_stocks: 概念板块成分股
    
    返回:
        相关概念列表
    """
    related = []
    
    for concept_code, constituent_df in concept_stocks.items():
        if 'stock_code' in constituent_df.columns:
            if stock_code in constituent_df['stock_code'].values:
                related.append(concept_code)
    
    return related


def build_concept_hierarchy(concept_stocks: Dict[str, pd.DataFrame], stock_limit_up: pd.DataFrame) -> Dict:
    """
    构建概念热度层级
    
    参数:
        concept_stocks: 概念板块成分股
        stock_limit_up: 涨停股票
    
    返回:
        概念热度层级
    """
    # 先分析联动
    co_movement = analyze_concept_co_movement(concept_stocks, stock_limit_up)
    
    # 分热度层级
    core = []    # 核心：涨停占比 >=50%
    major = []   # 主要：涨停占比 >=20%
    minor = []   # 次要：涨停占比 <20%
    
    for concept_code, perf in co_movement.items():
        ratio = perf['limit_up_ratio']
        if ratio >= 0.5:
            core.append(concept_code)
        elif ratio >= 0.2:
            major.append(concept_code)
        else:
            minor.append(concept_code)
    
    return {
        'core_concepts': core,
        'major_concepts': major,
        'minor_concepts': minor,
        'is_main_line': len(core) > 0 or len(major) > 1,
        'concept_performance': co_movement
    }


if __name__ == '__main__':
    print("涨停原因与主线扩散分析模块加载成功！")
