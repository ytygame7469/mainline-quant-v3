# -*- coding: utf-8 -*-
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


class TradeLogger:

    def __init__(self, log_dir: str = "logs", trade_log_file: str = "trade.log", level: str = "INFO"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        self.logger = logging.getLogger("mainline_quant_v3")
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self.logger.handlers.clear()

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        app_log_file = os.path.join(log_dir, "app.log")
        app_handler = RotatingFileHandler(
            app_log_file,
            maxBytes=100 * 1024 * 1024,
            backupCount=10,
            encoding="utf-8",
        )
        app_handler.setLevel(logging.DEBUG)
        app_handler.setFormatter(formatter)
        self.logger.addHandler(app_handler)

        self.trade_logger = logging.getLogger("trade")
        self.trade_logger.setLevel(logging.INFO)
        self.trade_logger.handlers.clear()
        self.trade_logger.propagate = False

        trade_path = os.path.join(log_dir, trade_log_file)
        trade_handler = RotatingFileHandler(
            trade_path,
            maxBytes=100 * 1024 * 1024,
            backupCount=10,
            encoding="utf-8",
        )
        trade_formatter = logging.Formatter(
            "%(asctime)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        trade_handler.setFormatter(trade_formatter)
        self.trade_logger.addHandler(trade_handler)

    def debug(self, msg: str):
        self.logger.debug(msg)

    def info(self, msg: str):
        self.logger.info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def trade(self, msg: str):
        self.trade_logger.info(msg)

    def trade_buy(self, stock_code: str, stock_name: str, price: float, volume: int, reason: str = ""):
        self.trade(f"BUY | {stock_code} | {stock_name} | price={price:.2f} | vol={volume} | {reason}")

    def trade_sell(self, stock_code: str, stock_name: str, price: float, volume: int, reason: str = ""):
        self.trade(f"SELL | {stock_code} | {stock_name} | price={price:.2f} | vol={volume} | {reason}")

    def trade_signal(self, stock_code: str, signal: str, score: float, reason: str = ""):
        self.trade(f"SIGNAL | {stock_code} | {signal} | score={score:.1f} | {reason}")

    def trade_result(self, stock_code: str, pnl: float, pnl_pct: float):
        self.trade(f"RESULT | {stock_code} | pnl={pnl:.2f} | pnl_pct={pnl_pct:+.2%}")


_logger_instance = None


def get_logger(
    log_dir: str = "logs",
    trade_log_file: str = "trade.log",
    level: str = "INFO",
) -> TradeLogger:
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = TradeLogger(
            log_dir=log_dir,
            trade_log_file=trade_log_file,
            level=level,
        )
    return _logger_instance


def setup_logger(
    log_dir: str = "logs",
    trade_log_file: str = "trade.log",
    level: str = "INFO",
) -> TradeLogger:
    global _logger_instance
    _logger_instance = TradeLogger(
        log_dir=log_dir,
        trade_log_file=trade_log_file,
        level=level,
    )
    return _logger_instance