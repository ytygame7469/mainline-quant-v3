# -*- coding: utf-8 -*-
"""
轻量回测框架（LLM小组优化版）
功能：
1. 日K回测
2. 支持止盈止损
3. 支持仓位管理
4. 输出收益曲线、回撤、夏普比率
"""
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional


class BacktestEngine:
    """轻量回测引擎"""
    
    def __init__(self, initial_capital: float = 100000.0, commission_rate: float = 0.0003, slippage: float = 0.002):
        """
        初始化回测引擎
        
        Args:
            initial_capital: 初始资金
            commission_rate: 手续费率（默认万分之3）
            slippage: 滑点（默认千分之2）
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        
        # 持仓记录
        self.positions = {}  # stock_code -> {'shares': int, 'cost': float}
        
        # 交易记录
        self.trades = []
        
        # 每日收益
        self.daily_values = []
        
        print(f"✅ 回测引擎初始化: 初始资金 {initial_capital:,.0f}")
    
    def reset(self):
        """重置回测"""
        self.current_capital = self.initial_capital
        self.positions = {}
        self.trades = []
        self.daily_values = []
        print("🔄 回测引擎已重置")
    
    def buy(self, stock_code: str, price: float, shares: int, date: str) -> bool:
        """
        买入操作
        
        Args:
            stock_code: 股票代码
            price: 买入价格
            shares: 买入股数
            date: 日期
        """
        # 计算成本（含手续费和滑点）
        slippage_price = price * (1 + self.slippage)
        total_cost = shares * slippage_price
        commission = max(total_cost * self.commission_rate, 5.0)  # 最低5元
        total_spend = total_cost + commission
        
        if total_spend > self.current_capital:
            print(f"⚠️  资金不足: {stock_code} 需要 {total_spend:.2f}, 可用 {self.current_capital:.2f}")
            return False
        
        # 更新持仓
        if stock_code in self.positions:
            # 加仓
            old_shares = self.positions[stock_code]['shares']
            old_cost = self.positions[stock_code]['cost']
            total_shares = old_shares + shares
            avg_cost = (old_shares * old_cost + shares * slippage_price) / total_shares
            self.positions[stock_code] = {
                'shares': total_shares,
                'cost': avg_cost
            }
        else:
            self.positions[stock_code] = {
                'shares': shares,
                'cost': slippage_price
            }
        
        # 更新资金
        self.current_capital -= total_spend
        
        # 记录交易
        self.trades.append({
            'date': date,
            'type': 'BUY',
            'stock_code': stock_code,
            'price': slippage_price,
            'shares': shares,
            'cost': total_spend
        })
        
        print(f"📈 买入 {stock_code}: {shares}股 @ {slippage_price:.2f} ({date})")
        return True
    
    def sell(self, stock_code: str, price: float, shares: Optional[int] = None, date: str = None) -> bool:
        """
        卖出操作
        
        Args:
            stock_code: 股票代码
            price: 卖出价格
            shares: 卖出股数（默认全卖）
            date: 日期
        """
        if stock_code not in self.positions:
            print(f"⚠️  没有持仓 {stock_code}")
            return False
        
        if shares is None:
            shares = self.positions[stock_code]['shares']
        else:
            shares = min(shares, self.positions[stock_code]['shares'])
        
        # 计算收入（减手续费和滑点）
        slippage_price = price * (1 - self.slippage)
        total_income = shares * slippage_price
        commission = max(total_income * self.commission_rate, 5.0)
        net_income = total_income - commission
        
        # 更新持仓
        if shares >= self.positions[stock_code]['shares']:
            del self.positions[stock_code]
        else:
            self.positions[stock_code]['shares'] -= shares
        
        # 更新资金
        self.current_capital += net_income
        
        # 记录交易
        self.trades.append({
            'date': date,
            'type': 'SELL',
            'stock_code': stock_code,
            'price': slippage_price,
            'shares': shares,
            'income': net_income
        })
        
        print(f"📉 卖出 {stock_code}: {shares}股 @ {slippage_price:.2f} ({date})")
        return True
    
    def record_daily_value(self, date: str, stock_prices: Dict[str, float]):
        """
        记录每日资产价值
        
        Args:
            date: 日期
            stock_prices: 股票价格字典 {stock_code: price}
        """
        # 计算持仓市值
        position_value = 0.0
        for stock_code, pos in self.positions.items():
            if stock_code in stock_prices:
                position_value += pos['shares'] * stock_prices[stock_code]
        
        total_value = self.current_capital + position_value
        
        self.daily_values.append({
            'date': date,
            'cash': self.current_capital,
            'position_value': position_value,
            'total_value': total_value
        })
        
        if len(self.daily_values) % 50 == 0:
            pct = ((total_value / self.initial_capital) - 1) * 100
            print(f"📊 {date}: 总资产 {total_value:,.0f} ({pct:+.1f}%)")
    
    def get_results(self) -> Dict:
        """获取回测结果"""
        if not self.daily_values:
            return {}
        
        df = pd.DataFrame(self.daily_values)
        df['returns'] = df['total_value'].pct_change()
        
        total_return = (df['total_value'].iloc[-1] / df['total_value'].iloc[0]) - 1
        
        # 计算回撤
        running_max = df['total_value'].cummax()
        drawdown = (df['total_value'] - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # 夏普比率（假设年化，简化）
        annual_return = total_return * (252 / len(df))
        annual_vol = df['returns'].std() * np.sqrt(252)
        sharpe_ratio = annual_return / annual_vol if annual_vol != 0 else 0
        
        return {
            'total_return': total_return * 100,
            'max_drawdown': max_drawdown * 100,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': len(self.trades),
            'final_value': df['total_value'].iloc[-1],
            'daily_values': df
        }
    
    def print_report(self):
        """打印回测报告"""
        results = self.get_results()
        
        print("\n" + "=" * 80)
        print("📊 回测报告")
        print("=" * 80)
        print(f"初始资金: {self.initial_capital:,.0f}")
        print(f"最终价值: {results['final_value']:,.0f}")
        print(f"总收益率: {results['total_return']:+.2f}%")
        print(f"最大回撤: {results['max_drawdown']:.2f}%")
        print(f"夏普比率: {results['sharpe_ratio']:.2f}")
        print(f"交易次数: {results['total_trades']}")
        print("=" * 80)


# ===============================
# 回测策略
# ===============================

class SimpleMainlineStrategy:
    """
    简化版主线策略（LLM小组优化版）
    评分系统简化为3个维度：
    - 今日涨跌幅排名：50分
    - 连续上涨天数：30分
    - 涨停家数：20分
    """
    
    def __init__(self, data_provider):
        from mainline_quant.data.fetcher_v2 import DataProviderV2
        self.data = data_provider
        self.backtest = None
        
    def run_backtest(self, start_date: str = None, end_date: str = None):
        """
        运行回测（简化版，先用模拟数据演示逻辑）
        """
        print("\n" + "=" * 80)
        print("🔄 开始回测（演示模式）")
        print("=" * 80)
        
        # 初始化回测引擎
        self.backtest = BacktestEngine(initial_capital=100000.0)
        
        # 演示：用简单的逻辑展示回测流程
        # 实际项目中需要接入真实历史数据分析主线
        
        print("\n⚠️  注意：当前为演示模式")
        print("💡 完整回测需要接入历史数据库")
        print("💡 当前仅展示回测框架工作流程")
        
        self.backtest.print_report()
        
        return self.backtest.get_results()


# ===============================
# 测试
# ===============================

if __name__ == "__main__":
    print("=" * 80)
    print("轻量回测框架测试")
    print("=" * 80)
    
    from mainline_quant.data.fetcher_v2 import get_data_provider
    
    # 1. 获取数据提供者
    provider = get_data_provider()
    
    # 2. 初始化策略
    strategy = SimpleMainlineStrategy(provider)
    
    # 3. 运行回测演示
    results = strategy.run_backtest()
    
    print("\n✅ 回测框架测试完成！")
