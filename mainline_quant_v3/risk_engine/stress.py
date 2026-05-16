# -*- coding: utf-8 -*-
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np

from .config import RiskConfig, StressScenarios, get_default_config


@dataclass
class StressResult:
    scenario_name: str
    portfolio_loss: float
    portfolio_loss_pct: float
    max_drawdown: float
    var_95: float
    var_99: float
    cvar_95: float
    recovery_days_estimate: int
    survived: bool


class StressTester:

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or get_default_config()
        self.results: List[StressResult] = []
        self.portfolio_weights: Dict[str, float] = {}
        self.historical_betas: Dict[str, float] = {}
        self.stock_volatilities: Dict[str, float] = {}

        print("StressTester")

    def set_portfolio(
        self,
        weights: Dict[str, float],
        betas: Optional[Dict[str, float]] = None,
        volatilities: Optional[Dict[str, float]] = None,
    ):
        self.portfolio_weights = weights
        if betas:
            self.historical_betas = betas
        if volatilities:
            self.stock_volatilities = volatilities

    def _estimate_portfolio_loss(self, market_drop: float) -> float:
        if not self.portfolio_weights:
            return market_drop

        if self.historical_betas:
            weighted_beta = sum(
                self.portfolio_weights.get(code, 0.0) * self.historical_betas.get(code, 1.0)
                for code in set(list(self.portfolio_weights.keys()) + list(self.historical_betas.keys()))
            )
            total_weight = sum(self.portfolio_weights.values())
            weighted_beta = weighted_beta / total_weight if total_weight > 0 else 1.0
        else:
            weighted_beta = 1.0

        return market_drop * weighted_beta

    def run_historical_scenario(
        self,
        name: str,
        market_drop: float,
        volatility_spike: float = 1.0,
        recovery_days: int = 60,
    ) -> StressResult:
        portfolio_loss_pct = self._estimate_portfolio_loss(market_drop)

        portfolio_loss = sum(
            self.portfolio_weights.get(code, 0.0) * portfolio_loss_pct
            for code in self.portfolio_weights
        )

        max_dd = portfolio_loss_pct * 1.2

        var_95 = portfolio_loss_pct * 0.7
        var_99 = portfolio_loss_pct * 0.9
        cvar_95 = portfolio_loss_pct * 0.85

        survived = abs(portfolio_loss_pct) < 0.50

        result = StressResult(
            scenario_name=name,
            portfolio_loss=portfolio_loss,
            portfolio_loss_pct=portfolio_loss_pct,
            max_drawdown=max_dd,
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            recovery_days_estimate=recovery_days,
            survived=survived,
        )

        self.results.append(result)
        return result

    def run_all_historical(self) -> List[StressResult]:
        scenarios = [
            ("2015_crash", self.config.stress.crash_2015_drop, 90),
            ("2016_circuit_breaker", self.config.stress.circuit_breaker_2016_drop, 45),
            ("2020_covid", self.config.stress.covid_2020_drop, 30),
            ("black_swan", self.config.stress.black_swan_drop, 120),
            ("liquidity_crisis", self.config.stress.liquidity_crisis_drop, 180),
        ]

        results = []
        for name, drop, recovery in scenarios:
            result = self.run_historical_scenario(name, drop, recovery_days=recovery)
            results.append(result)

        return results

    def monte_carlo_simulation(
        self,
        initial_capital: float = 1_000_000.0,
        num_simulations: Optional[int] = None,
        horizon: Optional[int] = None,
    ) -> Dict:
        if num_simulations is None:
            num_simulations = self.config.stress.monte_carlo_simulations
        if horizon is None:
            horizon = self.config.stress.monte_carlo_horizon

        if not self.portfolio_weights:
            return self._monte_carlo_simple(initial_capital, num_simulations, horizon)

        return self._monte_carlo_portfolio(initial_capital, num_simulations, horizon)

    def _monte_carlo_simple(
        self,
        initial_capital: float,
        num_simulations: int,
        horizon: int,
    ) -> Dict:
        daily_return = 0.0004
        daily_vol = 0.015

        np.random.seed(42)
        random_returns = np.random.normal(daily_return, daily_vol, (horizon, num_simulations))
        paths = initial_capital * np.exp(np.cumsum(random_returns, axis=0))

        final_values = paths[-1, :]
        max_drawdowns = np.zeros(num_simulations)

        for i in range(num_simulations):
            path = paths[:, i]
            peak = np.maximum.accumulate(path)
            drawdown = (path - peak) / peak
            max_drawdowns[i] = drawdown.min()

        return {
            "simulations": num_simulations,
            "horizon_days": horizon,
            "initial_capital": initial_capital,
            "mean_final_value": float(np.mean(final_values)),
            "median_final_value": float(np.median(final_values)),
            "std_final_value": float(np.std(final_values)),
            "var_95_final": float(np.percentile(final_values, 5)),
            "var_99_final": float(np.percentile(final_values, 1)),
            "mean_max_drawdown": float(np.mean(max_drawdowns)),
            "median_max_drawdown": float(np.median(max_drawdowns)),
            "var_95_max_drawdown": float(np.percentile(max_drawdowns, 5)),
            "var_99_max_drawdown": float(np.percentile(max_drawdowns, 1)),
            "prob_profit": float(np.mean(final_values > initial_capital)),
            "prob_ruin_50pct": float(np.mean(max_drawdowns < -0.50)),
            "prob_ruin_30pct": float(np.mean(max_drawdowns < -0.30)),
            "prob_ruin_15pct": float(np.mean(max_drawdowns < -0.15)),
        }

    def _monte_carlo_portfolio(
        self,
        initial_capital: float,
        num_simulations: int,
        horizon: int,
    ) -> Dict:
        codes = list(self.portfolio_weights.keys())
        weights = np.array([self.portfolio_weights[c] for c in codes])
        n_stocks = len(codes)

        daily_returns = np.full(n_stocks, 0.0004)

        if self.stock_volatilities:
            vols = np.array([self.stock_volatilities.get(c, 0.02) for c in codes])
        else:
            vols = np.full(n_stocks, 0.02)

        np.random.seed(42)

        all_paths = np.zeros((num_simulations, horizon + 1))
        all_paths[:, 0] = initial_capital

        for t in range(horizon):
            shocks = np.random.normal(0, 1, (num_simulations, n_stocks))
            stock_returns = daily_returns + vols * shocks
            portfolio_returns = np.dot(stock_returns, weights) / weights.sum()
            all_paths[:, t + 1] = all_paths[:, t] * (1 + portfolio_returns)

        final_values = all_paths[:, -1]
        max_drawdowns = np.zeros(num_simulations)

        for i in range(num_simulations):
            path = all_paths[i, :]
            peak = np.maximum.accumulate(path)
            drawdown = (path - peak) / peak
            max_drawdowns[i] = drawdown.min()

        return {
            "simulations": num_simulations,
            "horizon_days": horizon,
            "n_stocks": n_stocks,
            "initial_capital": initial_capital,
            "mean_final_value": float(np.mean(final_values)),
            "median_final_value": float(np.median(final_values)),
            "std_final_value": float(np.std(final_values)),
            "var_95_final": float(np.percentile(final_values, 5)),
            "var_99_final": float(np.percentile(final_values, 1)),
            "mean_max_drawdown": float(np.mean(max_drawdowns)),
            "median_max_drawdown": float(np.median(max_drawdowns)),
            "var_95_max_drawdown": float(np.percentile(max_drawdowns, 5)),
            "var_99_max_drawdown": float(np.percentile(max_drawdowns, 1)),
            "prob_profit": float(np.mean(final_values > initial_capital)),
            "prob_ruin_50pct": float(np.mean(max_drawdowns < -0.50)),
            "prob_ruin_30pct": float(np.mean(max_drawdowns < -0.30)),
            "prob_ruin_15pct": float(np.mean(max_drawdowns < -0.15)),
        }

    def black_swan_test(
        self,
        initial_capital: float = 1_000_000.0,
        num_events: int = 5,
        event_magnitude: float = -0.07,
    ) -> Dict:
        daily_return = 0.0004
        daily_vol = 0.015
        horizon = 252

        np.random.seed(42)
        base_returns = np.random.normal(daily_return, daily_vol, horizon)
        event_days = np.sort(np.random.choice(horizon, num_events, replace=False))
        black_swan_returns = base_returns.copy()
        black_swan_returns[event_days] = event_magnitude

        path = initial_capital * np.exp(np.cumsum(black_swan_returns))
        peak = np.maximum.accumulate(path)
        drawdown = (path - peak) / peak

        return {
            "num_events": num_events,
            "event_magnitude": event_magnitude,
            "final_value": float(path[-1]),
            "total_return": float(path[-1] / initial_capital - 1),
            "max_drawdown": float(drawdown.min()),
            "event_days": event_days.tolist(),
            "max_single_day_loss": float(black_swan_returns.min()),
        }

    def correlation_stress_test(
        self,
        normal_correlation: float = 0.3,
        stressed_correlation: float = 0.8,
        num_simulations: int = 5000,
    ) -> Dict:
        n_stocks = len(self.portfolio_weights) if self.portfolio_weights else 5
        weights = (
            np.array(list(self.portfolio_weights.values()))
            if self.portfolio_weights
            else np.ones(n_stocks) / n_stocks
        )

        normal_cov = np.ones((n_stocks, n_stocks)) * normal_correlation
        np.fill_diagonal(normal_cov, 1.0)

        stressed_cov = np.ones((n_stocks, n_stocks)) * stressed_correlation
        np.fill_diagonal(stressed_cov, 1.0)

        vols = np.full(n_stocks, 0.02)

        normal_cov_scaled = np.outer(vols, vols) * normal_cov
        stressed_cov_scaled = np.outer(vols, vols) * stressed_cov

        np.random.seed(42)
        normal_returns = np.random.multivariate_normal(
            np.full(n_stocks, 0.0004), normal_cov_scaled, num_simulations
        )
        stressed_returns = np.random.multivariate_normal(
            np.full(n_stocks, 0.0004), stressed_cov_scaled, num_simulations
        )

        normal_portfolio = np.dot(normal_returns, weights) / weights.sum()
        stressed_portfolio = np.dot(stressed_returns, weights) / weights.sum()

        return {
            "normal_correlation": normal_correlation,
            "stressed_correlation": stressed_correlation,
            "normal_var_95": float(np.percentile(normal_portfolio, 5)),
            "normal_var_99": float(np.percentile(normal_portfolio, 1)),
            "normal_cvar_95": float(normal_portfolio[normal_portfolio <= np.percentile(normal_portfolio, 5)].mean()),
            "stressed_var_95": float(np.percentile(stressed_portfolio, 5)),
            "stressed_var_99": float(np.percentile(stressed_portfolio, 1)),
            "stressed_cvar_95": float(stressed_portfolio[stressed_portfolio <= np.percentile(stressed_portfolio, 5)].mean()),
            "var_amplification": float(np.percentile(stressed_portfolio, 5) / np.percentile(normal_portfolio, 5)),
        }

    def get_report(self) -> Dict:
        historical = []
        for r in self.results:
            historical.append({
                "scenario": r.scenario_name,
                "portfolio_loss_pct": r.portfolio_loss_pct,
                "max_drawdown": r.max_drawdown,
                "var_95": r.var_95,
                "var_99": r.var_99,
                "cvar_95": r.cvar_95,
                "recovery_days": r.recovery_days_estimate,
                "survived": r.survived,
            })

        return {
            "historical_scenarios": historical,
            "portfolio_weights": self.portfolio_weights,
            "stock_betas": self.historical_betas,
            "stock_volatilities": self.stock_volatilities,
        }

    def clear_all(self):
        self.results.clear()
        self.portfolio_weights.clear()
        self.historical_betas.clear()
        self.stock_volatilities.clear()
        print("StressTester cleared")


def get_stress_tester(config: Optional[RiskConfig] = None) -> StressTester:
    return StressTester(config=config)