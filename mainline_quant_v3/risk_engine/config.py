# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PositionLimits:
    max_total_position: float = 0.80
    max_single_stock: float = 0.05
    max_single_sector: float = 0.20
    min_cash_reserve: float = 0.20
    max_concentration_top3: float = 0.40
    single_trade_ratio: float = 0.05
    batch_build_steps: int = 3
    batch_clear_steps: int = 2


@dataclass
class StopLimits:
    fixed_stop_loss: float = -0.08
    atr_stop_multiplier: float = 2.0
    trailing_stop_drawdown: float = -0.05
    time_stop_days: int = 20
    time_stop_min_return: float = 0.01
    structural_ma_period: int = 60
    structural_support_lookback: int = 120
    take_profit_fixed: float = 0.30
    take_profit_rr_ratio: float = 3.0


@dataclass
class BudgetLimits:
    daily_max_loss: float = -0.02
    weekly_max_loss: float = -0.05
    monthly_max_loss: float = -0.10
    consecutive_loss_breaker: int = 3
    max_drawdown_forced_reduce: float = -0.15
    var_confidence: float = 0.95
    cvar_confidence: float = 0.95
    var_lookback: int = 252
    risk_free_rate: float = 0.025


@dataclass
class StressScenarios:
    crash_2015_drop: float = -0.35
    circuit_breaker_2016_drop: float = -0.25
    covid_2020_drop: float = -0.15
    black_swan_drop: float = -0.20
    liquidity_crisis_drop: float = -0.30
    monte_carlo_simulations: int = 10000
    monte_carlo_horizon: int = 252
    monte_carlo_confidence: float = 0.95


@dataclass
class RiskConfig:
    position: PositionLimits = field(default_factory=PositionLimits)
    stop: StopLimits = field(default_factory=StopLimits)
    budget: BudgetLimits = field(default_factory=BudgetLimits)
    stress: StressScenarios = field(default_factory=StressScenarios)
    market_regime_adjustment: bool = True
    bear_market_multiplier: float = 0.50
    volatile_market_multiplier: float = 0.75
    bull_market_multiplier: float = 1.00
    enable_circuit_breaker: bool = True
    enable_var_monitor: bool = True
    enable_stress_test: bool = True
    log_level: str = "INFO"
    sector_classification: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "position": {
                "max_total_position": self.position.max_total_position,
                "max_single_stock": self.position.max_single_stock,
                "max_single_sector": self.position.max_single_sector,
                "min_cash_reserve": self.position.min_cash_reserve,
            },
            "stop": {
                "fixed_stop_loss": self.stop.fixed_stop_loss,
                "atr_stop_multiplier": self.stop.atr_stop_multiplier,
                "trailing_stop_drawdown": self.stop.trailing_stop_drawdown,
                "time_stop_days": self.stop.time_stop_days,
            },
            "budget": {
                "daily_max_loss": self.budget.daily_max_loss,
                "weekly_max_loss": self.budget.weekly_max_loss,
                "consecutive_loss_breaker": self.budget.consecutive_loss_breaker,
                "max_drawdown_forced_reduce": self.budget.max_drawdown_forced_reduce,
            },
            "stress": {
                "crash_2015_drop": self.stress.crash_2015_drop,
                "circuit_breaker_2016_drop": self.stress.circuit_breaker_2016_drop,
                "covid_2020_drop": self.stress.covid_2020_drop,
                "black_swan_drop": self.stress.black_swan_drop,
            },
        }


def get_default_config() -> RiskConfig:
    return RiskConfig()


def get_conservative_config() -> RiskConfig:
    return RiskConfig(
        position=PositionLimits(
            max_total_position=0.60,
            max_single_stock=0.03,
            max_single_sector=0.15,
            single_trade_ratio=0.03,
        ),
        stop=StopLimits(
            fixed_stop_loss=-0.05,
            atr_stop_multiplier=1.5,
            trailing_stop_drawdown=-0.03,
            time_stop_days=10,
        ),
        budget=BudgetLimits(
            daily_max_loss=-0.01,
            weekly_max_loss=-0.03,
            consecutive_loss_breaker=2,
            max_drawdown_forced_reduce=-0.10,
        ),
    )


def get_aggressive_config() -> RiskConfig:
    return RiskConfig(
        position=PositionLimits(
            max_total_position=0.95,
            max_single_stock=0.10,
            max_single_sector=0.30,
            single_trade_ratio=0.10,
        ),
        stop=StopLimits(
            fixed_stop_loss=-0.12,
            atr_stop_multiplier=3.0,
            trailing_stop_drawdown=-0.08,
            time_stop_days=30,
        ),
        budget=BudgetLimits(
            daily_max_loss=-0.04,
            weekly_max_loss=-0.08,
            consecutive_loss_breaker=5,
            max_drawdown_forced_reduce=-0.25,
        ),
    )