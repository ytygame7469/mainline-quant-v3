# -*- coding: utf-8 -*-
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import numpy as np

from .config import RiskConfig, StopLimits, get_default_config


class StopSignal(Enum):
    NONE = "none"
    FIXED_STOP_LOSS = "fixed_stop_loss"
    ATR_STOP = "atr_stop"
    TRAILING_STOP = "trailing_stop"
    TIME_STOP = "time_stop"
    STRUCTURAL_STOP = "structural_stop"
    TAKE_PROFIT_FIXED = "take_profit_fixed"
    TAKE_PROFIT_RR = "take_profit_rr"
    TRAILING_TAKE_PROFIT = "trailing_take_profit"


@dataclass
class StopRecord:
    stock_code: str
    entry_price: float
    entry_date: str
    highest_price: float
    lowest_price: float
    atr_value: float
    stop_price: float
    take_profit_price: float


class StopManager:

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or get_default_config()
        self.records: Dict[str, StopRecord] = {}
        self.stop_history: List[Dict] = []

        print("StopManager")

    def register_position(
        self,
        stock_code: str,
        entry_price: float,
        entry_date: str = "",
        atr_value: float = 0.0,
    ):
        stop_cfg = self.config.stop
        stop_price = entry_price * (1 + stop_cfg.fixed_stop_loss)
        take_profit_price = entry_price * (1 + stop_cfg.take_profit_fixed)

        if atr_value > 0:
            atr_stop_price = entry_price - stop_cfg.atr_stop_multiplier * atr_value
            stop_price = min(stop_price, atr_stop_price)

        self.records[stock_code] = StopRecord(
            stock_code=stock_code,
            entry_price=entry_price,
            entry_date=entry_date or datetime.now().strftime("%Y-%m-%d"),
            highest_price=entry_price,
            lowest_price=entry_price,
            atr_value=atr_value,
            stop_price=stop_price,
            take_profit_price=take_profit_price,
        )

        print(f"StopRegister  {stock_code}  stop={stop_price:.2f}  tp={take_profit_price:.2f}")

    def update_price(self, stock_code: str, current_price: float):
        if stock_code not in self.records:
            return

        rec = self.records[stock_code]
        if current_price > rec.highest_price:
            rec.highest_price = current_price

        if current_price < rec.lowest_price:
            rec.lowest_price = current_price

    def update_atr(self, stock_code: str, atr_value: float):
        if stock_code not in self.records:
            return

        rec = self.records[stock_code]
        rec.atr_value = atr_value

        stop_cfg = self.config.stop
        atr_stop = rec.entry_price - stop_cfg.atr_stop_multiplier * atr_value
        fixed_stop = rec.entry_price * (1 + stop_cfg.fixed_stop_loss)
        rec.stop_price = min(fixed_stop, atr_stop)

    def check_fixed_stop_loss(self, stock_code: str, current_price: float) -> bool:
        if stock_code not in self.records:
            return False

        rec = self.records[stock_code]
        pnl = (current_price - rec.entry_price) / rec.entry_price
        return pnl <= self.config.stop.fixed_stop_loss

    def check_atr_stop(self, stock_code: str, current_price: float) -> bool:
        if stock_code not in self.records:
            return False

        rec = self.records[stock_code]
        if rec.atr_value <= 0:
            return False

        atr_stop_price = rec.entry_price - self.config.stop.atr_stop_multiplier * rec.atr_value
        return current_price <= atr_stop_price

    def check_trailing_stop(self, stock_code: str, current_price: float) -> bool:
        if stock_code not in self.records:
            return False

        rec = self.records[stock_code]
        if rec.highest_price <= rec.entry_price:
            return False

        drawdown = (current_price - rec.highest_price) / rec.highest_price
        return drawdown <= self.config.stop.trailing_stop_drawdown

    def check_time_stop(self, stock_code: str, current_price: float) -> bool:
        if stock_code not in self.records:
            return False

        rec = self.records[stock_code]
        try:
            entry_dt = datetime.strptime(rec.entry_date, "%Y-%m-%d")
        except ValueError:
            return False

        days_held = (datetime.now() - entry_dt).days
        if days_held < self.config.stop.time_stop_days:
            return False

        pnl = (current_price - rec.entry_price) / rec.entry_price
        return pnl < self.config.stop.time_stop_min_return

    def check_structural_stop(
        self,
        stock_code: str,
        current_price: float,
        ma_price: float = 0.0,
        support_price: float = 0.0,
    ) -> bool:
        if stock_code not in self.records:
            return False

        if ma_price > 0 and current_price < ma_price:
            return True

        if support_price > 0 and current_price < support_price:
            return True

        return False

    def check_take_profit_fixed(self, stock_code: str, current_price: float) -> bool:
        if stock_code not in self.records:
            return False

        rec = self.records[stock_code]
        pnl = (current_price - rec.entry_price) / rec.entry_price
        return pnl >= self.config.stop.take_profit_fixed

    def check_take_profit_rr(
        self, stock_code: str, current_price: float, risk_amount: float = 0.0
    ) -> bool:
        if stock_code not in self.records:
            return False

        rec = self.records[stock_code]
        pnl = (current_price - rec.entry_price) / rec.entry_price

        if risk_amount <= 0:
            risk_amount = abs(self.config.stop.fixed_stop_loss)

        rr_ratio = pnl / risk_amount if risk_amount > 0 else 0
        return rr_ratio >= self.config.stop.take_profit_rr_ratio

    def check_trailing_take_profit(self, stock_code: str, current_price: float) -> bool:
        if stock_code not in self.records:
            return False

        rec = self.records[stock_code]
        if rec.highest_price <= rec.entry_price:
            return False

        profit_from_entry = (rec.highest_price - rec.entry_price) / rec.entry_price
        if profit_from_entry <= 0:
            return False

        drawdown = (current_price - rec.highest_price) / rec.highest_price
        return drawdown <= self.config.stop.trailing_stop_drawdown

    def check_all(
        self,
        stock_code: str,
        current_price: float,
        ma_price: float = 0.0,
        support_price: float = 0.0,
        risk_amount: float = 0.0,
    ) -> Tuple[StopSignal, str]:
        if stock_code not in self.records:
            return StopSignal.NONE, ""

        self.update_price(stock_code, current_price)

        if self.check_fixed_stop_loss(stock_code, current_price):
            pnl = (current_price - self.records[stock_code].entry_price) / self.records[stock_code].entry_price
            return StopSignal.FIXED_STOP_LOSS, f"fixed stop: {pnl:.2%}"

        if self.check_atr_stop(stock_code, current_price):
            return StopSignal.ATR_STOP, "ATR stop triggered"

        if self.check_trailing_stop(stock_code, current_price):
            drawdown = (current_price - self.records[stock_code].highest_price) / self.records[stock_code].highest_price
            return StopSignal.TRAILING_STOP, f"trailing stop: {drawdown:.2%}"

        if self.check_time_stop(stock_code, current_price):
            pnl = (current_price - self.records[stock_code].entry_price) / self.records[stock_code].entry_price
            return StopSignal.TIME_STOP, f"time stop: held {self.config.stop.time_stop_days}d, pnl {pnl:.2%}"

        if self.check_structural_stop(stock_code, current_price, ma_price, support_price):
            return StopSignal.STRUCTURAL_STOP, "structural stop: below MA/support"

        if self.check_take_profit_fixed(stock_code, current_price):
            pnl = (current_price - self.records[stock_code].entry_price) / self.records[stock_code].entry_price
            return StopSignal.TAKE_PROFIT_FIXED, f"take profit: {pnl:.2%}"

        if self.check_take_profit_rr(stock_code, current_price, risk_amount):
            pnl = (current_price - self.records[stock_code].entry_price) / self.records[stock_code].entry_price
            return StopSignal.TAKE_PROFIT_RR, f"RR take profit: {pnl:.2%}"

        if self.check_trailing_take_profit(stock_code, current_price):
            return StopSignal.TRAILING_TAKE_PROFIT, "trailing take profit"

        return StopSignal.NONE, ""

    def get_stop_price(self, stock_code: str) -> Optional[float]:
        if stock_code not in self.records:
            return None
        return self.records[stock_code].stop_price

    def get_take_profit_price(self, stock_code: str) -> Optional[float]:
        if stock_code not in self.records:
            return None
        return self.records[stock_code].take_profit_price

    def get_unrealized_pnl(self, stock_code: str, current_price: float) -> float:
        if stock_code not in self.records:
            return 0.0
        rec = self.records[stock_code]
        return (current_price - rec.entry_price) / rec.entry_price

    def get_highest_price(self, stock_code: str) -> Optional[float]:
        if stock_code not in self.records:
            return None
        return self.records[stock_code].highest_price

    def remove_position(self, stock_code: str):
        if stock_code in self.records:
            del self.records[stock_code]
            print(f"StopRecord removed: {stock_code}")

    def get_active_stops(self) -> List[Dict]:
        result = []
        for code, rec in self.records.items():
            result.append({
                "stock_code": code,
                "entry_price": rec.entry_price,
                "stop_price": rec.stop_price,
                "take_profit_price": rec.take_profit_price,
                "highest_price": rec.highest_price,
                "atr_value": rec.atr_value,
                "entry_date": rec.entry_date,
            })
        return result

    def calculate_atr(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 14,
    ) -> float:
        if len(high) < 2:
            return 0.0

        high = np.asarray(high[-period - 1:])
        low = np.asarray(low[-period - 1:])
        close = np.asarray(close[-period - 1:])

        prev_close = np.roll(close, 1)
        prev_close[0] = close[0]

        tr = np.maximum(
            high - low,
            np.maximum(
                np.abs(high - prev_close),
                np.abs(low - prev_close),
            ),
        )

        return float(np.mean(tr[-period:]))

    def clear_all(self):
        self.records.clear()
        self.stop_history.clear()
        print("all stop records cleared")


def get_stop_manager(config: Optional[RiskConfig] = None) -> StopManager:
    return StopManager(config=config)