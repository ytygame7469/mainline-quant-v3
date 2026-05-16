# -*- coding: utf-8 -*-
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TradeOrder:
    order_id: str
    stock_code: str
    stock_name: str
    direction: str
    order_type: str
    price: float
    volume: int
    status: str
    create_time: str


class OrderManager:

    def __init__(self, broker):
        self.broker = broker
        self.pending_orders: Dict[str, TradeOrder] = {}
        self.filled_orders: Dict[str, TradeOrder] = {}
        self.cancelled_orders: Dict[str, TradeOrder] = {}
        self._order_seq = 0

        print(f"OrderManager broker={type(broker).__name__}")

    def _gen_order_id(self) -> str:
        self._order_seq += 1
        return f"ORD_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._order_seq:06d}"

    def submit_buy_order(
        self,
        stock_code: str,
        stock_name: str,
        price: float,
        volume: int,
        order_type: str = "limit",
    ) -> TradeOrder:
        order_id = self._gen_order_id()
        order = TradeOrder(
            order_id=order_id,
            stock_code=stock_code,
            stock_name=stock_name,
            direction="BUY",
            order_type=order_type,
            price=price,
            volume=volume,
            status="PENDING",
            create_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        self.pending_orders[order_id] = order

        broker_order = self.broker.buy(stock_code, stock_name, price, volume, order_type)

        if broker_order.status == "FILLED":
            order.status = "FILLED"
            self.filled_orders[order_id] = order
            del self.pending_orders[order_id]
        elif broker_order.status == "REJECTED":
            order.status = "REJECTED"
            self.cancelled_orders[order_id] = order
            del self.pending_orders[order_id]

        return order

    def submit_sell_order(
        self,
        stock_code: str,
        stock_name: str,
        price: float,
        volume: int,
        order_type: str = "limit",
    ) -> TradeOrder:
        order_id = self._gen_order_id()
        order = TradeOrder(
            order_id=order_id,
            stock_code=stock_code,
            stock_name=stock_name,
            direction="SELL",
            order_type=order_type,
            price=price,
            volume=volume,
            status="PENDING",
            create_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        self.pending_orders[order_id] = order

        broker_order = self.broker.sell(stock_code, stock_name, price, volume, order_type)

        if broker_order.status == "FILLED":
            order.status = "FILLED"
            self.filled_orders[order_id] = order
            del self.pending_orders[order_id]
        elif broker_order.status == "REJECTED":
            order.status = "REJECTED"
            self.cancelled_orders[order_id] = order
            del self.pending_orders[order_id]

        return order

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.pending_orders:
            order = self.pending_orders[order_id]
            if self.broker.cancel_order(order_id):
                order.status = "CANCELLED"
                self.cancelled_orders[order_id] = order
                del self.pending_orders[order_id]
                return True
        return False

    def cancel_all_orders(self) -> int:
        cancelled = 0
        for order_id in list(self.pending_orders.keys()):
            if self.cancel_order(order_id):
                cancelled += 1
        return cancelled

    def get_orders(self, status: Optional[str] = None) -> List[TradeOrder]:
        all_orders = []
        all_orders.extend(self.pending_orders.values())
        all_orders.extend(self.filled_orders.values())
        all_orders.extend(self.cancelled_orders.values())

        if status:
            return [o for o in all_orders if o.status == status]
        return all_orders

    def get_pending_orders(self) -> List[TradeOrder]:
        return list(self.pending_orders.values())

    def get_filled_orders(self) -> List[TradeOrder]:
        return list(self.filled_orders.values())

    def get_order_by_id(self, order_id: str) -> Optional[TradeOrder]:
        for odict in (self.pending_orders, self.filled_orders, self.cancelled_orders):
            if order_id in odict:
                return odict[order_id]
        return None

    def get_positions(self):
        return self.broker.get_positions()

    def get_available_cash(self) -> float:
        return self.broker.get_available_cash()

    def get_total_assets(self) -> float:
        return self.broker.get_total_assets()