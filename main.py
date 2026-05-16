# -*- coding: utf-8 -*-
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import setup_logger, get_logger
from data_engine.config import engine_config as data_config
from risk_engine.config import get_default_config as get_risk_config
from ai_engine import AgentOrchestrator, AIDecisionEngine
from trade_engine import SimulatorBroker, OrderManager
from monitor_engine import MarketMonitor, PositionMonitor, Notifier
from backtest_engine import BacktestEngine, MetricsCalculator


def cmd_collect(args):
    logger = get_logger()
    logger.info("数据采集")

    from data_engine.collector import DataCollector

    collector = DataCollector(data_config)

    if args.type == "daily":
        collector.sync_daily_kline(args.start, args.end)
    elif args.type == "concept":
        collector.sync_concept_kline(args.start, args.end)
    elif args.type == "finance":
        collector.sync_finance()
    elif args.type == "all":
        collector.sync_all()
    else:
        logger.error(f"未知采集类型: {args.type}")

    logger.info("数据采集完成")


def cmd_scan(args):
    logger = get_logger()
    logger.info("主线扫描")

    from strategy_engine.strategies.mainline_strategy import MainlineStrategy

    strategy = MainlineStrategy()
    results = strategy.scan(args.date)

    for r in results:
        logger.info(f"  {r.get('stock_code')} {r.get('stock_name')} score={r.get('score')}")

    logger.info(f"扫描完成 共{len(results)}只")


def cmd_trade(args):
    logger = get_logger()
    logger.info("交易模式")

    broker = SimulatorBroker(initial_capital=args.capital)
    order_mgr = OrderManager(broker)

    if args.ai:
        api_key = args.api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        orchestrator = AgentOrchestrator(api_key=api_key, model=args.model)
        decision_engine = AIDecisionEngine(orchestrator)
        logger.info(f"AI引擎已启动 model={args.model}")

    logger.info(f"交易引擎已启动 capital={args.capital}")


def cmd_monitor(args):
    logger = get_logger()
    logger.info("监控模式")

    notifier = Notifier()

    if args.dingtalk:
        notifier.add_dingtalk(args.dingtalk)

    if args.feishu:
        notifier.add_feishu(args.feishu)

    notifier.info("监控系统启动", f"启动时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    logger.info("监控引擎已启动")


def cmd_backtest(args):
    logger = get_logger()
    logger.info("回测模式")

    engine = BacktestEngine(
        initial_capital=args.capital,
        commission=args.commission,
        slippage=args.slippage,
    )

    logger.info(f"回测引擎已启动 capital={args.capital} commission={args.commission} slippage={args.slippage}")


def main():
    parser = argparse.ArgumentParser(description="mainline_quant_v3 量化交易系统")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    parser_collect = subparsers.add_parser("collect", help="数据采集")
    parser_collect.add_argument("--type", choices=["daily", "concept", "finance", "all"], default="all")
    parser_collect.add_argument("--start", default="2020-01-01")
    parser_collect.add_argument("--end", default=None)

    parser_scan = subparsers.add_parser("scan", help="主线扫描")
    parser_scan.add_argument("--date", default=None)
    parser_scan.add_argument("--strategy", default="mainline")

    parser_trade = subparsers.add_parser("trade", help="交易")
    parser_trade.add_argument("--capital", type=float, default=1000000.0)
    parser_trade.add_argument("--ai", action="store_true", default=False)
    parser_trade.add_argument("--api-key", default=None)
    parser_trade.add_argument("--model", default="deepseek-chat")

    parser_monitor = subparsers.add_parser("monitor", help="监控")
    parser_monitor.add_argument("--dingtalk")
    parser_monitor.add_argument("--feishu")
    parser_monitor.add_argument("--interval", type=int, default=60)

    parser_backtest = subparsers.add_parser("backtest", help="回测")
    parser_backtest.add_argument("--capital", type=float, default=100000.0)
    parser_backtest.add_argument("--commission", type=float, default=0.0003)
    parser_backtest.add_argument("--slippage", type=float, default=0.001)
    parser_backtest.add_argument("--start", default="2024-01-01")
    parser_backtest.add_argument("--end", default="2024-12-31")
    parser_backtest.add_argument("--strategy", default="mainline")

    parser_collect.add_argument("--log-level", default="INFO")
    parser_scan.add_argument("--log-level", default="INFO")
    parser_trade.add_argument("--log-level", default="INFO")
    parser_monitor.add_argument("--log-level", default="INFO")
    parser_backtest.add_argument("--log-level", default="INFO")

    args = parser.parse_args()

    log_level = getattr(args, "log_level", "INFO")
    setup_logger(level=log_level)

    if args.command == "collect":
        cmd_collect(args)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "trade":
        cmd_trade(args)
    elif args.command == "monitor":
        cmd_monitor(args)
    elif args.command == "backtest":
        cmd_backtest(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()