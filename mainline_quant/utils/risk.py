# -*- coding: utf-8 -*-
"""
风险控制模块
包含止损止盈、仓位管理等功能
"""
import pandas as pd
from typing import Dict, List, Optional, Tuple


class RiskControl:
    """
    风险控制器
    """
    
    def __init__(self):
        self.stop_loss_pct = -8.0  # 止损百分比
        self.take_profit_pct = 30.0  # 止盈百分比
        self.partial_take_profit_pct = 15.0  # 部分止盈百分比
        self.max_position_pct = 60.0  # 最大总仓位
        self.single_position_pct = 20.0  # 单只股票仓位
        self.max_holding_days = 7  # 最大持仓天数
        self.positions: Dict[str, Dict] = {}  # 当前持仓
    
    def set_stop_loss(self, pct: float):
        """设置止损比例"""
        self.stop_loss_pct = pct
    
    def set_take_profit(self, pct: float):
        """设置止盈比例"""
        self.take_profit_pct = pct
    
    def add_position(self, stock_code: str, entry_price: float, position_size: float, 
                     entry_date: Optional[str] = None):
        """
        添加持仓
        :param stock_code: 股票代码
        :param entry_price: 入场价格
        :param position_size: 仓位大小
        :param entry_date: 入场日期
        """
        import datetime
        if entry_date is None:
            entry_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        self.positions[stock_code] = {
            'entry_price': entry_price,
            'position_size': position_size,
            'entry_date': entry_date,
            'highest_price': entry_price,
            'partial_taken': False
        }
    
    def remove_position(self, stock_code: str):
        """移除持仓"""
        if stock_code in self.positions:
            del self.positions[stock_code]
    
    def check_stop_loss(self, stock_code: str, current_price: float) -> Tuple[bool, str]:
        """
        检查是否需要止损
        :param stock_code: 股票代码
        :param current_price: 当前价格
        :return: (是否止损, 原因)
        """
        if stock_code not in self.positions:
            return False, ""
        
        pos = self.positions[stock_code]
        pct = (current_price - pos['entry_price']) / pos['entry_price'] * 100
        
        if pct <= self.stop_loss_pct:
            return True, f"止损触发: 亏损{pct:.2f}%"
        
        return False, ""
    
    def check_take_profit(self, stock_code: str, current_price: float) -> Tuple[bool, str, str]:
        """
        检查是否需要止盈
        :param stock_code: 股票代码
        :param current_price: 当前价格
        :return: (是否止盈, 类型[full/partial], 原因)
        """
        if stock_code not in self.positions:
            return False, "", ""
        
        pos = self.positions[stock_code]
        pct = (current_price - pos['entry_price']) / pos['entry_price'] * 100
        
        # 更新最高价
        if current_price > pos['highest_price']:
            pos['highest_price'] = current_price
        
        # 完全止盈
        if pct >= self.take_profit_pct:
            return True, "full", f"完全止盈: 盈利{pct:.2f}%"
        
        # 部分止盈
        if pct >= self.partial_take_profit_pct and not pos['partial_taken']:
            pos['partial_taken'] = True
            return True, "partial", f"部分止盈: 盈利{pct:.2f}%"
        
        return False, "", ""
    
    def check_time_stop(self, stock_code: str, current_date: Optional[str] = None) -> Tuple[bool, str]:
        """
        检查时间止损
        :param stock_code: 股票代码
        :param current_date: 当前日期
        :return: (是否止损, 原因)
        """
        if stock_code not in self.positions:
            return False, ""
        
        import datetime
        if current_date is None:
            current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        pos = self.positions[stock_code]
        entry = pd.to_datetime(pos['entry_date'])
        current = pd.to_datetime(current_date)
        days_held = (current - entry).days
        
        if days_held >= self.max_holding_days:
            return True, f"时间止损: 持仓{days_held}天"
        
        return False, ""
    
    def calculate_position_size(self, total_capital: float, risk_per_trade: float = 2.0) -> float:
        """
        计算单笔交易仓位大小（基于风险）
        :param total_capital: 总资金
        :param risk_per_trade: 单笔交易风险百分比
        :return: 建议仓位大小
        """
        risk_amount = total_capital * risk_per_trade / 100
        position_size = risk_amount / abs(self.stop_loss_pct) * 100
        position_size = min(position_size, self.single_position_pct)
        return position_size
    
    def get_position_summary(self) -> pd.DataFrame:
        """获取持仓汇总"""
        data = []
        for code, pos in self.positions.items():
            data.append({
                'stock_code': code,
                'entry_price': pos['entry_price'],
                'position_size': pos['position_size'],
                'entry_date': pos['entry_date'],
                'highest_price': pos['highest_price']
            })
        return pd.DataFrame(data)
    
    def reset(self):
        """重置所有持仓"""
        self.positions.clear()
