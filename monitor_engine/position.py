# -*- coding: utf-8 -*-
from typing import Dict, List, Any, Optional
from datetime import datetime


class PositionMonitor:

    def __init__(self, position_manager=None, stop_manager=None, notifier=None):
        self.position_manager = position_manager
        self.stop_manager = stop_manager
        self.notifier = notifier
        self.alert_history: List[Dict] = []

        print("PositionMonitor")

    def check_positions(self, market_prices: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        alerts = []

        if market_prices and self.position_manager:
            self.position_manager.update_market_prices(market_prices)

        if self.stop_manager:
            stop_alerts = self._check_stop_conditions()
            alerts.extend(stop_alerts)

        if self.position_manager:
            position_alerts = self._check_position_deviation()
            alerts.extend(position_alerts)

        self.alert_history.extend(alerts)

        if alerts and self.notifier:
            self._notify_alerts(alerts)

        return alerts

    def _check_stop_conditions(self) -> List[Dict[str, Any]]:
        alerts = []
        try:
            triggered = self.stop_manager.check_all_stops()
            for trigger in triggered:
                alert = {
                    "type": "STOP",
                    "stock_code": trigger.get("stock_code", ""),
                    "stock_name": trigger.get("stock_name", ""),
                    "stop_type": trigger.get("stop_type", ""),
                    "current_price": trigger.get("current_price", 0),
                    "stop_price": trigger.get("stop_price", 0),
                    "pnl_pct": trigger.get("pnl_pct", 0),
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                alerts.append(alert)
        except Exception as e:
            print(f"止损检查异常: {e}")

        return alerts

    def _check_position_deviation(self) -> List[Dict[str, Any]]:
        alerts = []
        try:
            positions = self.position_manager.get_position_report()
            total_position = self.position_manager.get_total_position()

            max_total = self.position_manager.config.position.max_total_position
            if total_position > max_total:
                alerts.append({
                    "type": "DEVIATION",
                    "stock_code": "",
                    "stock_name": "",
                    "deviation_type": "总仓位超标",
                    "current": total_position,
                    "limit": max_total,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })

            for pos in positions:
                single_ratio = pos.get("allocated_ratio", 0)
                max_single = self.position_manager.config.position.max_single_stock
                if single_ratio > max_single:
                    alerts.append({
                        "type": "DEVIATION",
                        "stock_code": pos.get("stock_code", ""),
                        "stock_name": "",
                        "deviation_type": "单票仓位超标",
                        "current": single_ratio,
                        "limit": max_single,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })

        except Exception as e:
            print(f"仓位偏离检查异常: {e}")

        return alerts

    def _notify_alerts(self, alerts: List[Dict[str, Any]]):
        stop_alerts = [a for a in alerts if a["type"] == "STOP"]
        dev_alerts = [a for a in alerts if a["type"] == "DEVIATION"]

        if stop_alerts:
            content_lines = []
            for a in stop_alerts:
                content_lines.append(
                    f"{a['stock_name']}({a['stock_code']}) | "
                    f"{a['stop_type']} | "
                    f"当前价: {a['current_price']} | "
                    f"止损价: {a['stop_price']} | "
                    f"盈亏: {a['pnl_pct']:+.2%}"
                )
            self.notifier.send(
                title=f"止损触发 ({len(stop_alerts)}个)",
                content="\n".join(content_lines),
                level="ERROR",
            )

        if dev_alerts:
            content_lines = []
            for a in dev_alerts:
                content_lines.append(
                    f"{a.get('stock_code', '组合')} | {a['deviation_type']} | "
                    f"当前: {a['current']:.2%} | 上限: {a['limit']:.2%}"
                )
            self.notifier.send(
                title=f"仓位偏离警告 ({len(dev_alerts)}个)",
                content="\n".join(content_lines),
                level="WARNING",
            )

    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.alert_history[-limit:]

    def clear_alert_history(self):
        self.alert_history.clear()