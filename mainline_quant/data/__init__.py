# -*- coding: utf-8 -*-
"""
数据模块
"""
from .fetcher_v2 import DataProviderV2, get_data_provider
from .concept_data import ConceptData, get_concept_data

__all__ = [
    'DataProviderV2',
    'get_data_provider',
    'ConceptData',
    'get_concept_data',
]

