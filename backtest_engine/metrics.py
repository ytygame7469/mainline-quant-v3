# -*- coding: utf-8 -*-
from typing import Dict, List, Any
import numpy as np
import pandas as pd


class MetricsCalculator:

    @staticmethod
    def calculate_all(
        equity_curve: pd.DataFrame,
        trades: List[Any],
        risk_free_rate: float = 0.025,
    ) -> Dict[str, Any]:
        metrics = {}

        metrics.update(MetricsCalculator.calculate_return_metrics(equity_curve))
        metrics.update(MetricsCalculator.calculate_risk_metrics(equity_curve, risk_free_rate))
        metrics.update(MetricsCalculator.calculate_trade_metrics(trades))
        metrics.update(MetricsCalculator.calculate_advanced_metrics(equity_curve, trades))

        return metrics

    @staticmethod
    def calculate_return_metrics(equity_curve: pd.DataFrame) -> Dict[str, Any]:
        if equity_curve.empty:
            return {}

        total_equity = equity_curve["total_equity"]
        initial = total_equity.iloc[0]
        final = total_equity.iloc[-1]

        total_return = (final - initial) / initial

        days = (equity_curve.index[-1] - equity_curve.index[0]).days
        if days > 0:
            annual_return = (1 + total_return) ** (365.0 / days) - 1
        else:
            annual_return = 0.0

        daily_returns = total_equity.pct_change().dropna()
        cumulative_return = (1 + daily_returns).cumprod() - 1

        monthly = total_equity.resample("ME").last()
        monthly_returns = monthly.pct_change().dropna()
        positive_months = (monthly_returns > 0).sum()
        total_months = len(monthly_returns)
        monthly_win_rate = positive_months / total_months if total_months > 0 else 0

        return {
            "total_return": total_return,
            "annual_return": annual_return,
            "cumulative_return": cumulative_return.iloc[-1] if len(cumulative_return) > 0 else 0,
            "monthly_win_rate": monthly_win_rate,
            "positive_months": int(positive_months),
            "total_months": total_months,
        }

    @staticmethod
    def calculate_risk_metrics(equity_curve: pd.DataFrame, risk_free_rate: float = 0.025) -> Dict[str, Any]:
        if equity_curve.empty:
            return {}

        total_equity = equity_curve["total_equity"]
        daily_returns = total_equity.pct_change().dropna()

        if len(daily_returns) < 2:
            return {
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "calmar_ratio": 0.0,
                "max_drawdown": 0.0,
                "max_drawdown_duration": 0,
                "volatility": 0.0,
                "downside_volatility": 0.0,
                "var_95": 0.0,
                "cvar_95": 0.0,
            }

        volatility = daily_returns.std() * np.sqrt(252)

        excess_returns = daily_returns - risk_free_rate / 252
        if volatility > 0:
            sharpe_ratio = excess_returns.mean() * 252 / volatility
        else:
            sharpe_ratio = 0.0

        downside_returns = daily_returns[daily_returns < 0]
        if len(downside_returns) > 1:
            downside_volatility = downside_returns.std() * np.sqrt(252)
        else:
            downside_volatility = 0.0

        if downside_volatility > 0:
            sortino_ratio = excess_returns.mean() * 252 / downside_volatility
        else:
            sortino_ratio = 0.0

        cumulative = total_equity / total_equity.iloc[0]
        rolling_max = cumulative.cummax()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        drawdown_periods = (drawdown < 0).astype(int)
        max_duration = 0
        current_duration = 0
        for is_dd in drawdown_periods:
            if is_dd:
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0

        annual_return = MetricsCalculator.calculate_return_metrics(equity_curve).get("annual_return", 0)
        if abs(max_drawdown) > 0:
            calmar_ratio = annual_return / abs(max_drawdown)
        else:
            calmar_ratio = 0.0

        var_95 = np.percentile(daily_returns, 5)
        cvar_95 = daily_returns[daily_returns <= var_95].mean() if len(daily_returns[daily_returns <= var_95]) > 0 else var_95

        return {
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            "max_drawdown": max_drawdown,
            "max_drawdown_duration": max_duration,
            "volatility": volatility,
            "downside_volatility": downside_volatility,
            "var_95": var_95,
            "cvar_95": cvar_95,
        }

    @staticmethod
    def calculate_trade_metrics(trades: List[Any]) -> Dict[str, Any]:
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_profit": 0.0,
                "avg_loss": 0.0,
                "profit_loss_ratio": 0.0,
                "avg_hold_days": 0.0,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
                "total_commission": 0.0,
            }

        buy_trades = [t for t in trades if hasattr(t, 'direction') and t.direction == "BUY"]
        sell_trades = [t for t in trades if hasattr(t, 'direction') and t.direction == "SELL"]

        winning_trades = 0
        losing_trades = 0
        total_profit = 0.0
        total_loss = 0.0
        total_commission = sum(getattr(t, 'commission', 0) for t in trades)
        profits_list = []
        hold_days_list = []

        for sell in sell_trades:
            matching_buys = [
                b for b in buy_trades
                if getattr(b, 'stock_code', '') == getattr(sell, 'stock_code', '')
                and getattr(b, 'date', '') <= getattr(sell, 'date', '')
            ]
            if matching_buys:
                buy = matching_buys[-1]
                pnl = (getattr(sell, 'price', 0) - getattr(buy, 'price', 0)) * min(
                    getattr(sell, 'volume', 0), getattr(buy, 'volume', 0)
                )
                if pnl > 0:
                    winning_trades += 1
                    total_profit += pnl
                else:
                    losing_trades += 1
                    total_loss += abs(pnl)

                profits_list.append(pnl)

                try:
                    buy_date = pd.Timestamp(getattr(buy, 'date', ''))
                    sell_date = pd.Timestamp(getattr(sell, 'date', ''))
                    hold_days = (sell_date - buy_date).days
                    hold_days_list.append(hold_days)
                except Exception:
                    pass

        total_trades = len(sell_trades)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        avg_profit = total_profit / winning_trades if winning_trades > 0 else 0.0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0.0
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0.0
        avg_hold_days = np.mean(hold_days_list) if hold_days_list else 0.0

        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0
        for pnl in profits_list:
            if pnl > 0:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "avg_profit": avg_profit,
            "avg_loss": avg_loss,
            "profit_loss_ratio": profit_loss_ratio,
            "avg_hold_days": avg_hold_days,
            "max_consecutive_wins": max_consecutive_wins,
            "max_consecutive_losses": max_consecutive_losses,
            "total_commission": total_commission,
        }

    @staticmethod
    def calculate_advanced_metrics(equity_curve: pd.DataFrame, trades: List[Any]) -> Dict[str, Any]:
        if equity_curve.empty:
            return {}

        total_equity = equity_curve["total_equity"]
        daily_returns = total_equity.pct_change().dropna()

        if len(daily_returns) < 2:
            return {
                "information_ratio": 0.0,
                "tracking_error": 0.0,
                "alpha": 0.0,
                "beta": 0.0,
            }

        excess_returns = daily_returns - 0.025 / 252
        tracking_error = daily_returns.std()
        if tracking_error > 0:
            information_ratio = excess_returns.mean() / tracking_error * np.sqrt(252)
        else:
            information_ratio = 0.0

        return {
            "information_ratio": information_ratio,
            "tracking_error": tracking_error,
        }

    @staticmethod
    def print_metrics(metrics: Dict[str, Any]):
        print(f"\n{'=' * 60}")
        print(f"绩效指标")
        print(f"{'=' * 60}")
        print(f"累计收益: {metrics.get('total_return', 0):+.2%}")
        print(f"年化收益: {metrics.get('annual_return', 0):+.2%}")
        print(f"夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"索提诺比率: {metrics.get('sortino_ratio', 0):.2f}")
        print(f"卡玛比率: {metrics.get('calmar_ratio', 0):.2f}")
        print(f"最大回撤: {metrics.get('max_drawdown', 0):.2%}")
        print(f"最大回撤持续: {metrics.get('max_drawdown_duration', 0)}天")
        print(f"年化波动率: {metrics.get('volatility', 0):.2%}")
        print(f"VaR(95%): {metrics.get('var_95', 0):.2%}")
        print(f"CVaR(95%): {metrics.get('cvar_95', 0):.2%}")
        print(f"交易次数: {metrics.get('total_trades', 0)}")
        print(f"胜率: {metrics.get('win_rate', 0):.2%}")
        print(f"盈亏比: {metrics.get('profit_loss_ratio', 0):.2f}")
        print(f"平均持仓天数: {metrics.get('avg_hold_days', 0):.1f}")
        print(f"最大连胜: {metrics.get('max_consecutive_wins', 0)}")
        print(f"最大连亏: {metrics.get('max_consecutive_losses', 0)}")
        print(f"总佣金: {metrics.get('total_commission', 0):.2f}")
        print(f"{'=' * 60}\n")