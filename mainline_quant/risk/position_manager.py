# -*- coding: utf-8 -*-
"""
仓位管理模块（LLM小组设计）
"""
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PositionConfig:
    """
    仓位配置
    """
    # 总仓位上限（0-1）
    max_total_position: float = 0.8
    
    # 单个概念板块仓位上限（0-1）
    max_concept_position: float = 0.3
    
    # 单只股票仓位上限（0-1）
    max_single_stock_position: float = 0.1
    
    # 单笔建仓比例
    single_trade_ratio: float = 0.05


class PositionManager:
    """
    仓位管理器
    """
    
    def __init__(self, config: Optional[PositionConfig] = None):
        """
        初始化
        
        Args:
            config: 仓位配置
        """
        self.config = config or PositionConfig()
        
        # 当前持仓
        self.positions: Dict[str, float] = {}  # {stock_code: position_ratio}
        
        print("✅ PositionManager 初始化成功")
    
    def get_current_position(self) -> float:
        """
        获取当前总仓位
        """
        return sum(self.positions.values())
    
    def can_buy(self, stock_code: str, concept_code: str = "") -> bool:
        """
        检查是否可以买入
        
        Args:
            stock_code: 股票代码
            concept_code: 概念代码
        
        Returns:
            bool: 是否可以买入
        """
        # 1. 检查总仓位
        current_total = self.get_current_position()
        if current_total >= self.config.max_total_position:
            print(f"⚠️ 总仓位已满: {current_total:.2%}")
            return False
        
        # 2. 检查单只股票仓位
        if stock_code in self.positions:
            if self.positions[stock_code] >= self.config.max_single_stock_position:
                print(f"⚠️ 单只股票仓位已满: {stock_code}")
                return False
        
        # 3. 检查概念板块仓位（如果有）
        if concept_code:
            # 简化版，暂时不跟踪概念板块仓位
            pass
        
        return True
    
    def calculate_buy_amount(self, stock_code: str, total_capital: float, 
                            price: float) -> float:
        """
        计算买入数量
        
        Args:
            stock_code: 股票代码
            total_capital: 总资金
            price: 当前价格
        
        Returns:
            float: 买入数量（手）
        """
        # 计算可买入金额
        current_total = self.get_current_position()
        available_ratio = min(
            self.config.max_total_position - current_total,
            self.config.single_trade_ratio
        )
        
        if available_ratio <= 0:
            return 0
        
        buy_amount = (total_capital * available_ratio) / (price * 100)  # 1手=100股
        buy_amount = int(buy_amount) * 100  # 取整手
        
        return buy_amount
    
    def update_position(self, stock_code: str, change_ratio: float):
        """
        更新持仓
        
        Args:
            stock_code: 股票代码
            change_ratio: 仓位变化（+0.05表示增加5%，-0.05表示减少5%）
        """
        if stock_code in self.positions:
            self.positions[stock_code] += change_ratio
            if self.positions[stock_code] <= 0:
                del self.positions[stock_code]
        else:
            self.positions[stock_code] = change_ratio
    
    def get_position(self, stock_code: str) -> float:
        """
        获取某只股票的仓位
        """
        return self.positions.get(stock_code, 0)
    
    def clear_all(self):
        """
        清空所有持仓
        """
        self.positions.clear()


class StopLoss:
    """
    止损止盈管理器
    """
    
    def __init__(self, stop_loss_pct: float = -0.08, 
                 take_profit_pct: float = 0.15,
                 trailing_stop_pct: float = -0.05):
        """
        初始化
        
        Args:
            stop_loss_pct: 止损比例（如-0.08表示-8%）
            take_profit_pct: 止盈比例（如0.15表示+15%）
            trailing_stop_pct: 移动止盈回撤比例（如-0.05表示回撤5%止盈）
        """
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trailing_stop_pct = trailing_stop_pct
        
        # 持仓成本记录
        self.cost_basis: Dict[str, float] = {}  # {stock_code: cost_price}
        
        # 最高价记录（用于移动止盈）
        self.highest_price: Dict[str, float] = {}
        
        print("✅ StopLoss 初始化成功")
    
    def set_cost_basis(self, stock_code: str, cost_price: float):
        """
        设置持仓成本
        """
        self.cost_basis[stock_code] = cost_price
        self.highest_price[stock_code] = cost_price
    
    def check_signal(self, stock_code: str, current_price: float) -> Optional[str]:
        """
        检查是否触发止损或止盈
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
        
        Returns:
            str: 信号类型 ("stop_loss" | "take_profit" | None)
        """
        if stock_code not in self.cost_basis:
            return None
        
        cost_price = self.cost_basis[stock_code]
        current_return = (current_price - cost_price) / cost_price
        
        # 更新最高价
        if current_price > self.highest_price.get(stock_code, 0):
            self.highest_price[stock_code] = current_price
        
        # 1. 检查止损
        if current_return <= self.stop_loss_pct:
            print(f"🛑 触发止损: {stock_code}, 收益率: {current_return:.2%}")
            return "stop_loss"
        
        # 2. 检查止盈
        if current_return >= self.take_profit_pct:
            print(f"💰 触发止盈: {stock_code}, 收益率: {current_return:.2%}")
            return "take_profit"
        
        # 3. 检查移动止盈
        highest_price = self.highest_price.get(stock_code, cost_price)
        pullback_from_high = (current_price - highest_price) / highest_price
        
        if pullback_from_high <= self.trailing_stop_pct and current_return > 0:
            print(f"📉 触发移动止盈: {stock_code}, 回撤: {pullback_from_high:.2%}")
            return "take_profit"
        
        return None
    
    def remove_position(self, stock_code: str):
        """
        移除持仓记录
        """
        if stock_code in self.cost_basis:
            del self.cost_basis[stock_code]
        if stock_code in self.highest_price:
            del self.highest_price[stock_code]


# ===============================
# 快捷入口
# ===============================

def get_position_manager(config: Optional[PositionConfig] = None) -> PositionManager:
    """获取仓位管理器实例"""
    return PositionManager(config)

def get_stop_loss(stop_loss_pct: float = -0.08, 
                 take_profit_pct: float = 0.15,
                 trailing_stop_pct: float = -0.05) -> StopLoss:
    """获取止损止盈管理器实例"""
    return StopLoss(stop_loss_pct, take_profit_pct, trailing_stop_pct)

