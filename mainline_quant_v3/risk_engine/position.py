# -*- coding: utf-8 -*-
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
from enum import Enum

from .config import RiskConfig, PositionLimits, get_default_config


class MarketRegime(Enum):
    BULL = "bull"
    BEAR = "bear"
    VOLATILE = "volatile"
    NEUTRAL = "neutral"


@dataclass
class PositionRecord:
    stock_code: str
    allocated_ratio: float
    entry_price: float
    current_price: float
    sector: str
    entry_date: str
    unrealized_pnl: float = 0.0


class PositionManager:

    def __init__(self, config: Optional[RiskConfig] = None, total_capital: float = 1_000_000.0):
        self.config = config or get_default_config()
        self.total_capital = total_capital
        self.positions: Dict[str, PositionRecord] = {}
        self.sector_positions: Dict[str, float] = {}
        self.market_regime: MarketRegime = MarketRegime.NEUTRAL
        self.trade_history: List[Dict] = []

        print("PositionManager")

    def get_total_position(self) -> float:
        return sum(p.allocated_ratio for p in self.positions.values())

    def get_available_capital(self) -> float:
        total_pos = self.get_total_position()
        regime_mult = self._get_regime_multiplier()
        max_allowed = self.config.position.max_total_position * regime_mult
        available_ratio = max(0.0, max_allowed - total_pos)
        return self.total_capital * available_ratio

    def get_cash_reserve(self) -> float:
        return self.total_capital * (1.0 - self.get_total_position())

    def _get_regime_multiplier(self) -> float:
        if not self.config.market_regime_adjustment:
            return 1.0
        return {
            MarketRegime.BULL: self.config.bull_market_multiplier,
            MarketRegime.BEAR: self.config.bear_market_multiplier,
            MarketRegime.VOLATILE: self.config.volatile_market_multiplier,
            MarketRegime.NEUTRAL: 1.0,
        }.get(self.market_regime, 1.0)

    def set_market_regime(self, regime: MarketRegime):
        self.market_regime = regime
        print(f"MarketRegime -> {regime.value}  multiplier={self._get_regime_multiplier():.2f}")

    def set_sector_classification(self, sector_map: Dict[str, List[str]]):
        self.config.sector_classification = sector_map

    def _get_stock_sector(self, stock_code: str) -> str:
        for sector, stocks in self.config.sector_classification.items():
            if stock_code in stocks:
                return sector
        return "default"

    def get_sector_position(self, sector: str) -> float:
        return sum(
            p.allocated_ratio
            for p in self.positions.values()
            if p.sector == sector
        )

    def kelly_fraction(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        if avg_loss == 0 or win_rate <= 0:
            return 0.0
        b = abs(avg_win / avg_loss) if avg_loss != 0 else 1.0
        f = (win_rate * b - (1 - win_rate)) / b
        return max(0.0, min(f, self.config.position.max_single_stock))

    def kelly_half(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        return self.kelly_fraction(win_rate, avg_win, avg_loss) * 0.5

    def risk_parity_weights(
        self,
        stock_codes: List[str],
        volatility: np.ndarray,
        max_weight: float = 0.05,
    ) -> Dict[str, float]:
        n = len(stock_codes)
        if n == 0:
            return {}

        inv_vol = 1.0 / np.maximum(volatility, 1e-8)
        raw_weights = inv_vol / inv_vol.sum()

        regime_mult = self._get_regime_multiplier()
        max_allowed = self.config.position.max_total_position * regime_mult
        weights = raw_weights * max_allowed

        weights = np.minimum(weights, max_weight)
        excess = weights.sum() - max_allowed
        if excess > 0:
            weights = weights - excess / n
            weights = np.maximum(weights, 0.0)

        return {code: float(w) for code, w in zip(stock_codes, weights)}

    def equal_risk_contribution(
        self,
        cov_matrix: np.ndarray,
        stock_codes: List[str],
        max_iter: int = 100,
    ) -> Dict[str, float]:
        n = len(stock_codes)
        if n == 0:
            return {}

        w = np.ones(n) / n
        regime_mult = self._get_regime_multiplier()
        max_allowed = self.config.position.max_total_position * regime_mult

        for _ in range(max_iter):
            sigma = np.sqrt(w @ cov_matrix @ w)
            mrc = cov_matrix @ w
            rc = w * mrc
            rc = rc / sigma if sigma > 0 else rc
            target_rc = sigma * sigma / n
            w = w * (target_rc / np.maximum(rc, 1e-8))
            w = np.maximum(w, 0.0)
            w = w / w.sum() * max_allowed

        w = np.minimum(w, self.config.position.max_single_stock)

        return {code: float(w) for code, w in zip(stock_codes, w)}

    def check_position_limits(
        self, stock_code: str, sector: str, proposed_ratio: float
    ) -> Tuple[bool, str]:
        current_total = self.get_total_position()

        regime_mult = self._get_regime_multiplier()
        max_total = self.config.position.max_total_position * regime_mult

        if current_total + proposed_ratio > max_total:
            return False, f"total position overflow: {current_total + proposed_ratio:.2%} > {max_total:.2%}"

        if stock_code in self.positions:
            new_stock_ratio = self.positions[stock_code].allocated_ratio + proposed_ratio
        else:
            new_stock_ratio = proposed_ratio

        if new_stock_ratio > self.config.position.max_single_stock:
            return False, f"single stock overflow: {new_stock_ratio:.2%} > {self.config.position.max_single_stock:.2%}"

        current_sector = self.get_sector_position(sector)
        if current_sector + proposed_ratio > self.config.position.max_single_sector:
            return False, f"sector overflow [{sector}]: {current_sector + proposed_ratio:.2%} > {self.config.position.max_single_sector:.2%}"

        top3 = sorted(
            [(code, p.allocated_ratio) for code, p in self.positions.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:3]
        if top3:
            top3_ratio = sum(r for _, r in top3)
            new_top3 = top3_ratio + proposed_ratio
            if len(top3) >= 3 and new_stock_ratio <= top3[-1][1]:
                pass
            elif new_top3 > self.config.position.max_concentration_top3:
                return False, f"top3 concentration overflow: {new_top3:.2%} > {self.config.position.max_concentration_top3:.2%}"

        return True, "OK"

    def calculate_buy_ratio(
        self,
        stock_code: str,
        sector: str,
        kelly_f: float,
        risk_parity_w: float = 0.0,
        confidence: float = 1.0,
    ) -> float:
        base_ratio = kelly_f * 0.6 + risk_parity_w * 0.4
        adjusted = base_ratio * confidence

        regime_mult = self._get_regime_multiplier()
        adjusted = adjusted * regime_mult

        single_trade_max = self.config.position.single_trade_ratio * regime_mult
        adjusted = min(adjusted, single_trade_max)

        ok, msg = self.check_position_limits(stock_code, sector, adjusted)
        if not ok:
            print(f"PositionLimit  {stock_code}: {msg}")
            return 0.0

        return round(adjusted, 6)

    def batch_build_plan(self, target_ratio: float) -> List[float]:
        steps = self.config.position.batch_build_steps
        if steps <= 1:
            return [target_ratio]

        ratios = []
        for i in range(steps):
            progress = (i + 1) / steps
            ratio = target_ratio * (progress**0.5)
            ratio = round(ratio, 6)
            ratios.append(ratio)

        return ratios

    def batch_clear_plan(self, current_ratio: float) -> List[float]:
        steps = self.config.position.batch_clear_steps
        if steps <= 1:
            return [-current_ratio]

        ratios = []
        for i in range(steps):
            remaining_steps = steps - i
            ratio = -current_ratio / remaining_steps
            ratio = round(ratio, 6)
            ratios.append(ratio)

        return ratios

    def open_position(
        self,
        stock_code: str,
        ratio: float,
        entry_price: float,
        sector: str = "",
        entry_date: str = "",
    ) -> bool:
        if not sector:
            sector = self._get_stock_sector(stock_code)

        ok, msg = self.check_position_limits(stock_code, sector, ratio)
        if not ok:
            print(f"Cannot open {stock_code}: {msg}")
            return False

        if stock_code in self.positions:
            existing = self.positions[stock_code]
            new_ratio = existing.allocated_ratio + ratio
            existing.allocated_ratio = new_ratio
            existing.entry_price = (
                existing.entry_price * existing.allocated_ratio
                + entry_price * ratio
            ) / new_ratio if new_ratio > 0 else entry_price
        else:
            self.positions[stock_code] = PositionRecord(
                stock_code=stock_code,
                allocated_ratio=ratio,
                entry_price=entry_price,
                current_price=entry_price,
                sector=sector,
                entry_date=entry_date,
            )

        self.sector_positions[sector] = self.get_sector_position(sector)

        self.trade_history.append({
            "action": "open",
            "stock_code": stock_code,
            "ratio": ratio,
            "price": entry_price,
            "sector": sector,
        })

        print(f"open  {stock_code}  {ratio:.4%}  @{entry_price:.2f}  [{sector}]")
        return True

    def close_position(self, stock_code: str, ratio: Optional[float] = None) -> bool:
        if stock_code not in self.positions:
            print(f"position not found: {stock_code}")
            return False

        pos = self.positions[stock_code]
        close_ratio = ratio if ratio is not None else pos.allocated_ratio

        if close_ratio >= pos.allocated_ratio:
            sector = pos.sector
            del self.positions[stock_code]
            self.sector_positions[sector] = self.get_sector_position(sector)
        else:
            pos.allocated_ratio -= close_ratio
            sector = pos.sector
            self.sector_positions[sector] = self.get_sector_position(sector)

        self.trade_history.append({
            "action": "close",
            "stock_code": stock_code,
            "ratio": close_ratio,
            "price": pos.current_price,
            "sector": pos.sector,
        })

        print(f"close  {stock_code}  {close_ratio:.4%}")
        return True

    def update_market_prices(self, prices: Dict[str, float]):
        for code, price in prices.items():
            if code in self.positions:
                old_price = self.positions[code].current_price
                self.positions[code].current_price = price
                self.positions[code].unrealized_pnl = (
                    (price - self.positions[code].entry_price)
                    / self.positions[code].entry_price
                )

    def get_position_report(self) -> List[Dict]:
        report = []
        for code, pos in self.positions.items():
            report.append({
                "stock_code": code,
                "allocated_ratio": pos.allocated_ratio,
                "entry_price": pos.entry_price,
                "current_price": pos.current_price,
                "unrealized_pnl": pos.unrealized_pnl,
                "sector": pos.sector,
                "entry_date": pos.entry_date,
                "market_value": self.total_capital * pos.allocated_ratio,
            })
        return report

    def get_sector_report(self) -> Dict[str, float]:
        return {
            sector: self.get_sector_position(sector)
            for sector in set(p.sector for p in self.positions.values())
        }

    def dynamic_adjust(self, new_weights: Dict[str, float]) -> Dict[str, float]:
        adjustments = {}
        current_codes = set(self.positions.keys())
        target_codes = set(new_weights.keys())

        for code in current_codes - target_codes:
            adjustments[code] = -self.positions[code].allocated_ratio

        for code in target_codes - current_codes:
            adjustments[code] = new_weights[code]

        for code in current_codes & target_codes:
            diff = new_weights[code] - self.positions[code].allocated_ratio
            if abs(diff) > 0.001:
                adjustments[code] = round(diff, 6)

        return adjustments

    def clear_all(self):
        self.positions.clear()
        self.sector_positions.clear()
        self.trade_history.clear()
        print("all positions cleared")

    @property
    def total_pnl(self) -> float:
        if not self.positions:
            return 0.0
        total = sum(
            p.unrealized_pnl * p.allocated_ratio
            for p in self.positions.values()
        )
        total_ratio = sum(p.allocated_ratio for p in self.positions.values())
        return total / total_ratio if total_ratio > 0 else 0.0


def get_position_manager(
    config: Optional[RiskConfig] = None,
    total_capital: float = 1_000_000.0,
) -> PositionManager:
    return PositionManager(config=config, total_capital=total_capital)