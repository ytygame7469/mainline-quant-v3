# -*- coding: utf-8 -*-
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import numpy as np

from .config import RiskConfig, BudgetLimits, get_default_config


class CircuitBreakerStatus(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    TRIGGERED = "triggered"
    COOLDOWN = "cooldown"


@dataclass
class DailyRecord:
    date: str
    pnl: float
    pnl_pct: float
    trades: int
    winning_trades: int
    losing_trades: int


class RiskBudget:

    def __init__(self, config: Optional[RiskConfig] = None, initial_capital: float = 1_000_000.0):
        self.config = config or get_default_config()
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital

        self.daily_records: List[DailyRecord] = []
        self.consecutive_losses: int = 0
        self.consecutive_wins: int = 0

        self.circuit_breaker: CircuitBreakerStatus = CircuitBreakerStatus.NORMAL
        self.breaker_triggered_at: Optional[str] = None
        self.breaker_cooldown_until: Optional[str] = None

        self.daily_pnl: float = 0.0
        self.weekly_pnl: float = 0.0
        self.monthly_pnl: float = 0.0
        self.today_trades: int = 0
        self.today_wins: int = 0
        self.today_losses: int = 0

        self.returns_history: List[float] = []

        print("RiskBudget")

    def start_day(self):
        self.daily_pnl = 0.0
        self.today_trades = 0
        self.today_wins = 0
        self.today_losses = 0

    def record_trade(self, pnl: float, pnl_pct: float):
        self.daily_pnl += pnl
        self.today_trades += 1
        self.current_capital += pnl

        if pnl > 0:
            self.today_wins += 1
            self.consecutive_losses = 0
            self.consecutive_wins += 1
        elif pnl < 0:
            self.today_losses += 1
            self.consecutive_losses += 1
            self.consecutive_wins = 0

        self.returns_history.append(pnl_pct)

        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital

        self._check_circuit_breaker()

    def end_day(self, date_str: str = ""):
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        daily_pnl_pct = self.daily_pnl / self.initial_capital

        record = DailyRecord(
            date=date_str,
            pnl=self.daily_pnl,
            pnl_pct=daily_pnl_pct,
            trades=self.today_trades,
            winning_trades=self.today_wins,
            losing_trades=self.today_losses,
        )
        self.daily_records.append(record)

        self.weekly_pnl += daily_pnl_pct
        self.monthly_pnl += daily_pnl_pct

    def _check_circuit_breaker(self):
        if not self.config.enable_circuit_breaker:
            return

        budget = self.config.budget

        daily_pnl_pct = self.daily_pnl / self.initial_capital
        if daily_pnl_pct <= budget.daily_max_loss:
            self.circuit_breaker = CircuitBreakerStatus.TRIGGERED
            self.breaker_triggered_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"CircuitBreaker TRIGGERED  daily loss={daily_pnl_pct:.2%} > {budget.daily_max_loss:.2%}")

        if self.consecutive_losses >= budget.consecutive_loss_breaker:
            self.circuit_breaker = CircuitBreakerStatus.TRIGGERED
            self.breaker_triggered_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"CircuitBreaker TRIGGERED  consecutive losses={self.consecutive_losses}")

        current_drawdown = self.get_current_drawdown()
        if current_drawdown <= budget.max_drawdown_forced_reduce:
            if self.circuit_breaker != CircuitBreakerStatus.TRIGGERED:
                self.circuit_breaker = CircuitBreakerStatus.WARNING
            print(f"MaxDrawdown WARNING  drawdown={current_drawdown:.2%} > {budget.max_drawdown_forced_reduce:.2%}")

    def is_trading_allowed(self) -> Tuple[bool, str]:
        if self.circuit_breaker == CircuitBreakerStatus.TRIGGERED:
            return False, "circuit breaker triggered"

        if self.circuit_breaker == CircuitBreakerStatus.COOLDOWN:
            if self.breaker_cooldown_until:
                cooldown_dt = datetime.strptime(self.breaker_cooldown_until, "%Y-%m-%d")
                if datetime.now() < cooldown_dt:
                    return False, f"cooldown until {self.breaker_cooldown_until}"
            self.circuit_breaker = CircuitBreakerStatus.NORMAL

        return True, "OK"

    def reset_circuit_breaker(self, cooldown_days: int = 1):
        self.circuit_breaker = CircuitBreakerStatus.COOLDOWN
        cooldown_date = datetime.now() + timedelta(days=cooldown_days)
        self.breaker_cooldown_until = cooldown_date.strftime("%Y-%m-%d")
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        print(f"CircuitBreaker reset  cooldown until {self.breaker_cooldown_until}")

    def get_current_drawdown(self) -> float:
        if self.peak_capital <= 0:
            return 0.0
        return (self.current_capital - self.peak_capital) / self.peak_capital

    def get_max_drawdown(self) -> float:
        if not self.daily_records:
            return 0.0

        cumulative = self.initial_capital
        peak = self.initial_capital
        max_dd = 0.0

        for rec in self.daily_records:
            cumulative += rec.pnl
            if cumulative > peak:
                peak = cumulative
            dd = (cumulative - peak) / peak if peak > 0 else 0.0
            if dd < max_dd:
                max_dd = dd

        return max_dd

    def calculate_var(self, confidence: Optional[float] = None) -> float:
        if confidence is None:
            confidence = self.config.budget.var_confidence

        if len(self.returns_history) < 30:
            return 0.0

        returns = np.array(self.returns_history[-self.config.budget.var_lookback:])
        var = np.percentile(returns, (1 - confidence) * 100)
        return float(var)

    def calculate_cvar(self, confidence: Optional[float] = None) -> float:
        if confidence is None:
            confidence = self.config.budget.cvar_confidence

        if len(self.returns_history) < 30:
            return 0.0

        returns = np.array(self.returns_history[-self.config.budget.var_lookback:])
        var = np.percentile(returns, (1 - confidence) * 100)
        cvar = returns[returns <= var].mean()
        return float(cvar) if not np.isnan(cvar) else float(var)

    def calculate_sharpe_ratio(self) -> float:
        if len(self.returns_history) < 2:
            return 0.0

        returns = np.array(self.returns_history)
        excess = returns.mean() - self.config.budget.risk_free_rate / 252
        std = returns.std()
        if std == 0:
            return 0.0

        return float(excess / std * np.sqrt(252))

    def calculate_sortino_ratio(self) -> float:
        if len(self.returns_history) < 2:
            return 0.0

        returns = np.array(self.returns_history)
        excess = returns.mean() - self.config.budget.risk_free_rate / 252
        downside = returns[returns < 0]
        if len(downside) == 0:
            return 999.0

        downside_std = downside.std()
        if downside_std == 0:
            return 0.0

        return float(excess / downside_std * np.sqrt(252))

    def calculate_calmar_ratio(self) -> float:
        if len(self.returns_history) < 30:
            return 0.0

        returns = np.array(self.returns_history)
        annual_return = returns.mean() * 252
        max_dd = abs(self.get_max_drawdown())
        if max_dd == 0:
            return 999.0

        return float(annual_return / max_dd)

    def get_weekly_pnl_pct(self) -> float:
        return self.weekly_pnl

    def get_monthly_pnl_pct(self) -> float:
        return self.monthly_pnl

    def get_win_rate(self) -> float:
        total = sum(r.trades for r in self.daily_records)
        wins = sum(r.winning_trades for r in self.daily_records)
        return wins / total if total > 0 else 0.0

    def get_profit_factor(self) -> float:
        total_profit = 0.0
        total_loss = 0.0
        for rec in self.daily_records:
            if rec.pnl > 0:
                total_profit += rec.pnl
            else:
                total_loss += abs(rec.pnl)

        if total_loss == 0:
            return 999.0 if total_profit > 0 else 0.0
        return total_profit / total_loss

    def get_risk_report(self) -> Dict:
        return {
            "current_capital": self.current_capital,
            "peak_capital": self.peak_capital,
            "current_drawdown": self.get_current_drawdown(),
            "max_drawdown": self.get_max_drawdown(),
            "daily_pnl": self.daily_pnl,
            "daily_pnl_pct": self.daily_pnl / self.initial_capital if self.initial_capital > 0 else 0.0,
            "weekly_pnl_pct": self.weekly_pnl,
            "monthly_pnl_pct": self.monthly_pnl,
            "consecutive_losses": self.consecutive_losses,
            "consecutive_wins": self.consecutive_wins,
            "circuit_breaker": self.circuit_breaker.value,
            "var_95": self.calculate_var(0.95),
            "cvar_95": self.calculate_cvar(0.95),
            "var_99": self.calculate_var(0.99),
            "cvar_99": self.calculate_cvar(0.99),
            "sharpe_ratio": self.calculate_sharpe_ratio(),
            "sortino_ratio": self.calculate_sortino_ratio(),
            "calmar_ratio": self.calculate_calmar_ratio(),
            "win_rate": self.get_win_rate(),
            "profit_factor": self.get_profit_factor(),
            "total_trades": sum(r.trades for r in self.daily_records),
            "today_trades": self.today_trades,
        }

    def reset_weekly(self):
        self.weekly_pnl = 0.0

    def reset_monthly(self):
        self.monthly_pnl = 0.0

    def clear_all(self):
        self.daily_records.clear()
        self.returns_history.clear()
        self.current_capital = self.initial_capital
        self.peak_capital = self.initial_capital
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.circuit_breaker = CircuitBreakerStatus.NORMAL
        self.start_day()
        print("RiskBudget cleared")


def get_risk_budget(
    config: Optional[RiskConfig] = None,
    initial_capital: float = 1_000_000.0,
) -> RiskBudget:
    return RiskBudget(config=config, initial_capital=initial_capital)