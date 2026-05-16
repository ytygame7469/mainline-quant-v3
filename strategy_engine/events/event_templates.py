from strategy_engine.events.event_engine import Event, Operate


MAINLINE_START_EVENT = Event(
    name="主线启动",
    operate=Operate.OPEN_LONG,
    signals_all=[
        "trend_consecutive_up_level_3",
        "volume_vol_status_blowout",
        "trend_ma_bullish_alignment_1",
    ],
    signals_any=[
        "momentum_macd_cross_golden",
        "momentum_boll_break_1",
    ],
    signals_not=[
        "momentum_rsi_zone_overbought",
    ],
    description="主线启动事件：连续上涨3天以上+放量+均线多头+MACD金叉或布林突破+非超买",
)

LEADER_CONFIRM_EVENT = Event(
    name="龙头确认",
    operate=Operate.OPEN_LONG,
    signals_all=[
        "trend_consecutive_up_level_3",
        "fund_main_inflow_level_3",
        "volume_vol_status_blowout",
    ],
    signals_any=[
        "trend_ma5_golden_cross_1",
    ],
    signals_not=[],
    description="龙头确认事件：连续上涨+主力大幅流入+放量",
)

TREND_BREAKOUT_EVENT = Event(
    name="趋势突破",
    operate=Operate.OPEN_LONG,
    signals_all=[
        "trend_ma_bullish_alignment_1",
        "trend_adx_trend_strong_1",
        "momentum_macd_above_zero_1",
    ],
    signals_any=[
        "momentum_boll_break_1",
        "trend_ma20_golden_cross_1",
    ],
    signals_not=[
        "momentum_rsi_zone_overbought",
        "volume_vol_shrink_1",
    ],
    description="趋势突破事件：均线多头+ADX趋势强+MACD零轴上+布林突破或均线金叉",
)

OVERSOLD_REBOUND_EVENT = Event(
    name="超跌反弹",
    operate=Operate.OPEN_LONG,
    signals_all=[
        "momentum_rsi_zone_oversold",
        "volume_vol_shrink_1",
    ],
    signals_any=[
        "momentum_kdj_signal_1",
        "volume_obv_divergence_1",
    ],
    signals_not=[
        "trend_adx_trend_strong_-1",
    ],
    description="超跌反弹事件：RSI超卖+缩量+KDJ金叉或OBV底背离",
)

STOP_LOSS_EVENT = Event(
    name="止损",
    operate=Operate.CLOSE_LONG,
    signals_all=[],
    signals_any=[
        "trend_ma5_dead_cross_-1",
        "momentum_macd_cross_dead",
        "momentum_boll_break_-1",
        "trend_adx_trend_strong_-1",
    ],
    signals_not=[],
    description="止损事件：任一死叉或趋势转空触发",
)

TAKE_PROFIT_EVENT = Event(
    name="止盈",
    operate=Operate.CLOSE_LONG,
    signals_all=[
        "momentum_rsi_zone_overbought",
    ],
    signals_any=[
        "momentum_macd_cross_dead",
        "volume_obv_divergence_-1",
    ],
    signals_not=[],
    description="止盈事件：RSI超买+MACD死叉或OBV顶背离",
)

MAINLINE_FADE_EVENT = Event(
    name="主线退潮",
    operate=Operate.CLOSE_LONG,
    signals_all=[
        "trend_consecutive_up_level_0",
        "volume_vol_shrink_1",
    ],
    signals_any=[
        "fund_main_inflow_level_-1",
        "fund_main_inflow_level_-2",
        "fund_main_inflow_level_-3",
    ],
    signals_not=[],
    description="主线退潮事件：不再连续上涨+缩量+主力流出",
)

ALL_TEMPLATES = {
    "mainline_start": MAINLINE_START_EVENT,
    "leader_confirm": LEADER_CONFIRM_EVENT,
    "trend_breakout": TREND_BREAKOUT_EVENT,
    "oversold_rebound": OVERSOLD_REBOUND_EVENT,
    "stop_loss": STOP_LOSS_EVENT,
    "take_profit": TAKE_PROFIT_EVENT,
    "mainline_fade": MAINLINE_FADE_EVENT,
}


def get_event_template(name: str) -> Event:
    return ALL_TEMPLATES.get(name)


def list_event_templates():
    return list(ALL_TEMPLATES.keys())


def create_custom_event(name: str, operate: str, signals_all=None,
                        signals_any=None, signals_not=None,
                        description: str = "") -> Event:
    operate_map = {
        "开多": Operate.OPEN_LONG,
        "平多": Operate.CLOSE_LONG,
        "开空": Operate.OPEN_SHORT,
        "平空": Operate.CLOSE_SHORT,
    }
    return Event(
        name=name,
        operate=operate_map.get(operate, Operate.OPEN_LONG),
        signals_all=signals_all or [],
        signals_any=signals_any or [],
        signals_not=signals_not or [],
        description=description,
    )