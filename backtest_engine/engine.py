# -*- coding: utf-8 -*-
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
import pandas as pd

from .metrics import MetricsCalculator


@dataclass
class BacktestConfig:
    initial_capital: float = 100_000.0
    commission_rate: float = 0.0003
    slippage: float = 0.001
    stamp_tax: float = 0.001
    min_commission: float = 5.0


@dataclass
class TradeRecord:
    date: str
    stock_code: str
    direction: str
    price: float
    volume: int
    amount: float
    commission: float
    reason: str = ""


@dataclass
class BacktestResult:
    config: BacktestConfig
    start_date: str
    end_date: str
    initial_capital: float
    final_equity: float
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_loss_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    equity_curve: pd.DataFrame
    trades: List[TradeRecord]
    monthly_returns: pd.DataFrame
    yearly_returns: pd.DataFrame


class BacktestEngine:

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        commission: float = 0.0003,
        slippage: float = 0.001,
    ):
        self.config = BacktestConfig(
            initial_capital=initial_capital,
            commission_rate=commission,
            slippage=slippage,
        )
        self.cash = initial_capital
        self.positions: Dict[str, Dict] = {}
        self.trades: List[TradeRecord] = []
        self.equity_curve: List[Dict] = []
        self._current_date = ""

        print(f"BacktestEngine capital={initial_capital:.2f} commission={commission:.4f} slippage={slippage:.3f}")

    def run(
        self,
        strategy,
        start_date: str,
        end_date: str,
        stocks: List[str],
        data_provider: Optional[Callable] = None,
    ) -> BacktestResult:
        self.reset()

        if data_provider is None:
            raise ValueError("data_provider is required")

        all_data = {}
        for stock_code in stocks:
            df = data_provider(stock_code, start_date, end_date)
            if df is not None and not df.empty:
                all_data[stock_code] = df

        if not all_data:
            raise ValueError("无可用行情数据")

        sample_df = list(all_data.values())[0]
        if "trade_date" in sample_df.columns:
            trading_dates = sorted(sample_df["trade_date"].unique())
        else:
            trading_dates = sorted(sample_df.index.unique())

        trading_dates = [d for d in trading_dates if start_date <= str(d)[:10] <= end_date]

        for date in trading_dates:
            self._current_date = str(date)[:10]

            daily_data = {}
            for code, df in all_data.items():
                if "trade_date" in df.columns:
                    row = df[df["trade_date"] == date]
                else:
                    row = df[df.index == date]

                if not row.empty:
                    daily_data[code] = row.iloc[0].to_dict()

            signals = strategy.generate_signals(daily_data, self._current_date, self.positions)

            for signal in signals:
                self._execute_signal(signal, daily_data)

            self._update_equity(daily_data)

        return self._build_result(start_date, end_date)

    def _execute_signal(self, signal: Dict, daily_data: Dict):
        stock_code = signal.get("stock_code", "")
        direction = signal.get("direction", "")
        price = signal.get("price", 0)
        volume = signal.get("volume", 0)
        reason = signal.get("reason", "")

        if stock_code not in daily_data:
            return

        if direction == "BUY":
            self._buy(stock_code, price, volume, reason)
        elif direction == "SELL":
            self._sell(stock_code, price, volume, reason)

    def _buy(self, stock_code: str, price: float, volume: int, reason: str = ""):
        if volume <= 0:
            return

        exec_price = price * (1 + self.config.slippage)
        amount = exec_price * volume
        commission = max(amount * self.config.commission_rate, self.config.min_commission)
        total_cost = amount + commission

        if total_cost > self.cash:
            max_vol = int((self.cash - self.config.min_commission) / exec_price / 100) * 100
            if max_vol <= 0:
                return
            volume = max_vol
            amount = exec_price * volume
            commission = max(amount * self.config.commission_rate, self.config.min_commission)
            total_cost = amount + commission

        self.cash -= total_cost

        if stock_code in self.positions:
            pos = self.positions[stock_code]
            total_cost_basis = pos["avg_cost"] * pos["volume"] + total_cost
            pos["volume"] += volume
            pos["avg_cost"] = total_cost_basis / pos["volume"]
        else:
            self.positions[stock_code] = {
                "volume": volume,
                "avg_cost": exec_price,
            }

        self.trades.append(TradeRecord(
            date=self._current_date,
            stock_code=stock_code,
            direction="BUY",
            price=exec_price,
            volume=volume,
            amount=amount,
            commission=commission,
            reason=reason,
        ))

    def _sell(self, stock_code: str, price: float, volume: int, reason: str = ""):
        if stock_code not in self.positions:
            return

        pos = self.positions[stock_code]
        if volume <= 0 or volume > pos["volume"]:
            volume = pos["volume"]

        exec_price = price * (1 - self.config.slippage)
        amount = exec_price * volume
        commission = max(amount * self.config.commission_rate, self.config.min_commission)
        stamp_tax = amount * self.config.stamp_tax
        total_fee = commission + stamp_tax

        self.cash += (amount - total_fee)

        pos["volume"] -= volume
        if pos["volume"] <= 0:
            del self.positions[stock_code]

        self.trades.append(TradeRecord(
            date=self._current_date,
            stock_code=stock_code,
            direction="SELL",
            price=exec_price,
            volume=volume,
            amount=amount,
            commission=total_fee,
            reason=reason,
        ))

    def _update_equity(self, daily_data: Dict):
        position_value = 0.0
        for code, pos in self.positions.items():
            if code in daily_data:
                close_price = daily_data[code].get("close", 0)
                if close_price > 0:
                    position_value += close_price * pos["volume"]
            else:
                position_value += pos["avg_cost"] * pos["volume"]

        total_equity = self.cash + position_value

        self.equity_curve.append({
            "date": self._current_date,
            "cash": self.cash,
            "position_value": position_value,
            "total_equity": total_equity,
        })

    def _build_result(self, start_date: str, end_date: str) -> BacktestResult:
        if not self.equity_curve:
            raise ValueError("无回测数据")

        eq_df = pd.DataFrame(self.equity_curve)
        eq_df["date"] = pd.to_datetime(eq_df["date"])
        eq_df.set_index("date", inplace=True)

        final_equity = eq_df["total_equity"].iloc[-1]
        total_return = (final_equity - self.config.initial_capital) / self.config.initial_capital

        days = (eq_df.index[-1] - eq_df.index[0]).days
        if days > 0:
            annual_return = (1 + total_return) ** (365 / days) - 1
        else:
            annual_return = 0.0

        daily_returns = eq_df["total_equity"].pct_change().dropna()
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252)
        else:
            sharpe_ratio = 0.0

        cumulative = eq_df["total_equity"] / eq_df["total_equity"].iloc[0]
        rolling_max = cumulative.cummax()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        buy_trades = [t for t in self.trades if t.direction == "BUY"]
        sell_trades = [t for t in self.trades if t.direction == "SELL"]

        winning_trades = 0
        losing_trades = 0
        total_profit = 0.0
        total_loss = 0.0

        for i, sell in enumerate(sell_trades):
            matching_buys = [
                b for b in buy_trades
                if b.stock_code == sell.stock_code and b.date <= sell.date
            ]
            if matching_buys:
                buy = matching_buys[-1]
                pnl = (sell.price - buy.price) * min(sell.volume, buy.volume)
                if pnl > 0:
                    winning_trades += 1
                    total_profit += pnl
                else:
                    losing_trades += 1
                    total_loss += abs(pnl)

        total_trades = len(sell_trades)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        avg_profit = total_profit / winning_trades if winning_trades > 0 else 0.0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0.0
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0.0

        monthly = eq_df["total_equity"].resample("ME").last()
        monthly_returns = monthly.pct_change().dropna()

        yearly = eq_df["total_equity"].resample("YE").last()
        yearly_returns = yearly.pct_change().dropna()

        return BacktestResult(
            config=self.config,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.config.initial_capital,
            final_equity=final_equity,
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_loss_ratio=profit_loss_ratio,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            equity_curve=eq_df,
            trades=self.trades,
            monthly_returns=monthly_returns,
            yearly_returns=yearly_returns,
        )

    def print_report(self, result: Optional[BacktestResult] = None):
        if result is None:
            if not self.trades:
                print("无回测数据")
                return
            result = self._build_result("", "")

        print(f"\n{'=' * 60}")
        print(f"回测报告")
        print(f"{'=' * 60}")
        print(f"回测区间: {result.start_date} ~ {result.end_date}")
        print(f"初始资金: {result.initial_capital:,.2f}")
        print(f"最终权益: {result.final_equity:,.2f}")
        print(f"累计收益: {result.total_return:+.2%}")
        print(f"年化收益: {result.annual_return:+.2%}")
        print(f"夏普比率: {result.sharpe_ratio:.2f}")
        print(f"最大回撤: {result.max_drawdown:.2%}")
        print(f"交易次数: {result.total_trades}")
        print(f"胜率: {result.win_rate:.2%}")
        print(f"盈亏比: {result.profit_loss_ratio:.2f}")
        print(f"盈利次数: {result.winning_trades}")
        print(f"亏损次数: {result.losing_trades}")
        print(f"{'=' * 60}\n")

        if len(result.monthly_returns) > 0:
            print("月度收益:")
            for date, ret in result.monthly_returns.items():
                print(f"  {date.strftime('%Y-%m')}: {ret:+.2%}")

        print()

    def reset(self):
        self.cash = self.config.initial_capital
        self.positions.clear()
        self.trades.clear()
        self.equity_curve.clear()
        self._current_date = ""