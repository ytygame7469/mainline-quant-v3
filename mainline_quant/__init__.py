# -*- coding: utf-8 -*-
"""
主线量化交易系统
LLM子代理团队协作开发
"""
__version__ = "2.0.0"
__author__ = "LLM Subagent Team"

from .data import (
    DataProviderV2,
    get_data_provider,
    ConceptData,
    get_concept_data,
)
from .strategy import (
    SimplifiedMainlineStrategy,
    ConceptScoring,
    get_scoring,
    LeaderSelector,
    get_leader_selector,
)
from .risk import (
    PositionConfig,
    PositionManager,
    StopLoss,
    get_position_manager,
    get_stop_loss,
)
from .backtest import (
    BacktestEngine,
)

__all__ = [
    # Data
    'DataProviderV2',
    'get_data_provider',
    'ConceptData',
    'get_concept_data',
    
    # Strategy
    'SimplifiedMainlineStrategy',
    'ConceptScoring',
    'get_scoring',
    'LeaderSelector',
    'get_leader_selector',
    
    # Risk
    'PositionConfig',
    'PositionManager',
    'StopLoss',
    'get_position_manager',
    'get_stop_loss',
    
    # Backtest
    'BacktestEngine',
]

