# -*- coding: utf-8 -*-
"""
主线量化交易系统
专注A股主线行情识别和龙头股交易
"""

__version__ = '1.0.0'

from mainline_quant.data import DataFetcher
from mainline_quant.strategy import MainlineStrategy
from mainline_quant.utils import risk_control

__all__ = ['DataFetcher', 'MainlineStrategy', 'risk_control']
