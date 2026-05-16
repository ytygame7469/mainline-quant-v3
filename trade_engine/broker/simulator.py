# -*- coding: utf-8 -*-
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Position:
    stock_code: str
    stock_name: str
    volume: int
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


@dataclass
class Order:
    order_id: str
    stock_code: str
    stock_name: str
    direction: str
    order_type: str
    price: float
    volume: int
    filled_volume: int
    status: str
    create_time: str
    update_time: str


class SimulatorBroker:

    def __init__(self, initial_capital: float = 1_000_000.0, commission_rate: float = 0.0003, slippage: float = 0.001):
        self.initial_capital = initial_capital
        self.available_cash = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.min_stamp_tax = 0.001

        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.trade_history: List[Dict] = []
        self._order_counter = 0

        print(f"SimulatorBroker initial_capital={initial_capital:.2f} commission={commission_rate:.4f} slippage={slippage:.3f}")

    def _next_order_id(self) -> str:
        self._order_counter += 1
        return f"SIM_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._order_counter:06d}"

    def _apply_slippage(self, price: float, direction: str) -> float:
        if direction == "BUY":
            return price * (1 + self.slippage)
        else:
            return price * (1 - self.slippage)

    def _calc_commission(self, amount: float, direction: str) -> float:
        commission = amount * self.commission_rate
        if commission < 5.0:
            commission = 5.0
        if direction == "SELL":
            stamp_tax = amount * self.min_stamp_tax
            commission += stamp_tax
        return commission

    def submit_order(
        self,
        stock_code: str,
        stock_name: str,
        direction: str,
        price: float,
        volume: int,
        order_type: str = "limit",
    ) -> Order:
        order_id = self._next_order_id()
        exec_price = self._apply_slippage(price, direction)
        amount = exec_price * volume
        commission = self._calc_commission(amount, direction)

        if direction == "BUY":
            required_cash = amount + commission
            if required_cash > self.available_cash:
                max_vol = int((self.available_cash - commission) / exec_price / 100) * 100
                if max_vol <= 0:
                    order = Order(
                        order_id=order_id,
                        stock_code=stock_code,
                        stock_name=stock_name,
                        direction=direction,
                        order_type=order_type,
                        price=price,
                        volume=volume,
                        filled_volume=0,
                        status="REJECTED",
                        create_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    )
                    self.orders[order_id] = order
                    print(f"REJECTED {stock_code} {direction} vol={volume} 资金不足")
                    return order
                volume = max_vol
                amount = exec_price * volume
                commission = self._calc_commission(amount, direction)

        if direction == "SELL":
            if stock_code not in self.positions:
                order = Order(
                    order_id=order_id,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    direction=direction,
                    order_type=order_type,
                    price=price,
                    volume=volume,
                    filled_volume=0,
                    status="REJECTED",
                    create_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                self.orders[order_id] = order
                print(f"REJECTED {stock_code} {direction} 无持仓")
                return order

            pos = self.positions[stock_code]
            if volume > pos.volume:
                volume = pos.volume
                amount = exec_price * volume
                commission = self._calc_commission(amount, direction)

        order = Order(
            order_id=order_id,
            stock_code=stock_code,
            stock_name=stock_name,
            direction=direction,
            order_type=order_type,
            price=exec_price,
            volume=volume,
            filled_volume=volume,
            status="FILLED",
            create_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        if direction == "BUY":
            self.available_cash -= (amount + commission)
            if stock_code in self.positions:
                pos = self.positions[stock_code]
                total_cost = pos.avg_cost * pos.volume + amount + commission
                pos.volume += volume
                pos.avg_cost = total_cost / pos.volume
                pos.current_price = exec_price
                pos.market_value = pos.current_price * pos.volume
                pos.unrealized_pnl = pos.market_value - pos.avg_cost * pos.volume
                pos.unrealized_pnl_pct = pos.unrealized_pnl / (pos.avg_cost * pos.volume) if pos.avg_cost > 0 else 0
            else:
                self.positions[stock_code] = Position(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    volume=volume,
                    avg_cost=exec_price,
                    current_price=exec_price,
                    market_value=amount,
                    unrealized_pnl=0.0,
                    unrealized_pnl_pct=0.0,
                )

        elif direction == "SELL":
            self.available_cash += (amount - commission)
            pos = self.positions[stock_code]
            pos.volume -= volume
            if pos.volume <= 0:
                del self.positions[stock_code]
            else:
                pos.market_value = pos.current_price * pos.volume

        self.orders[order_id] = order

        self.trade_history.append({
            "order_id": order_id,
            "stock_code": stock_code,
            "direction": direction,
            "price": exec_price,
            "volume": volume,
            "amount": amount,
            "commission": commission,
            "time": order.create_time,
        })

        print(f"FILLED {stock_code} {direction} vol={volume} price={exec_price:.2f} amount={amount:.2f} comm={commission:.2f}")
        return order

    def buy(self, stock_code: str, stock_name: str, price: float, volume: int, order_type: str = "limit") -> Order:
        return self.submit_order(stock_code, stock_name, "BUY", price, volume, order_type)

    def sell(self, stock_code: str, stock_name: str, price: float, volume: int, order_type: str = "limit") -> Order:
        return self.submit_order(stock_code, stock_name, "SELL", price, volume, order_type)

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status in ("PENDING", "PARTIAL"):
                order.status = "CANCELLED"
                order.update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"CANCELLED {order_id}")
                return True
        print(f"cancel failed: {order_id}")
        return False

    def get_positions(self) -> Dict[str, Position]:
        return self.positions

    def get_position(self, stock_code: str) -> Optional[Position]:
        return self.positions.get(stock_code)

    def get_orders(self) -> Dict[str, Order]:
        return self.orders

    def get_available_cash(self) -> float:
        return self.available_cash

    def get_total_assets(self) -> float:
        market_value = sum(p.market_value for p in self.positions.values())
        return self.available_cash + market_value

    def get_total_pnl(self) -> float:
        total = self.get_total_assets()
        return total - self.initial_capital

    def get_total_pnl_pct(self) -> float:
        total = self.get_total_assets()
        return (total - self.initial_capital) / self.initial_capital

    def update_market_price(self, stock_code: str, price: float):
        if stock_code in self.positions:
            pos = self.positions[stock_code]
            pos.current_price = price
            pos.market_value = price * pos.volume
            pos.unrealized_pnl = pos.market_value - pos.avg_cost * pos.volume
            pos.unrealized_pnl_pct = pos.unrealized_pnl / (pos.avg_cost * pos.volume) if pos.avg_cost > 0 else 0

    def update_market_prices(self, prices: Dict[str, float]):
        for code, price in prices.items():
            self.update_market_price(code, price)

    def reset(self):
        self.available_cash = self.initial_capital
        self.positions.clear()
        self.orders.clear()
        self.trade_history.clear()
        self._order_counter = 0
        print("SimulatorBroker reset")

    def get_summary(self) -> Dict:
        return {
            "initial_capital": self.initial_capital,
            "available_cash": self.available_cash,
            "total_assets": self.get_total_assets(),
            "total_pnl": self.get_total_pnl(),
            "total_pnl_pct": self.get_total_pnl_pct(),
            "position_count": len(self.positions),
            "trade_count": len(self.trade_history),
        }