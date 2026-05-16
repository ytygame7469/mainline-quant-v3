from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import fnmatch


class Operate(Enum):
    OPEN_LONG = "开多"
    CLOSE_LONG = "平多"
    OPEN_SHORT = "开空"
    CLOSE_SHORT = "平空"


@dataclass
class Event:
    name: str
    operate: Operate
    signals_all: List[str] = field(default_factory=list)
    signals_any: List[str] = field(default_factory=list)
    signals_not: List[str] = field(default_factory=list)
    description: str = ""

    def matches(self, signal_dict: Dict[str, Any]) -> bool:
        flat_dict = self._flatten_signals(signal_dict)
        signal_keys = set(flat_dict.keys())

        if self.signals_all:
            for sig_pattern in self.signals_all:
                if not self._match_single(sig_pattern, flat_dict, signal_keys):
                    return False

        if self.signals_any:
            any_match = False
            for sig_pattern in self.signals_any:
                if self._match_single(sig_pattern, flat_dict, signal_keys):
                    any_match = True
                    break
            if not any_match:
                return False

        if self.signals_not:
            for sig_pattern in self.signals_not:
                if self._match_single(sig_pattern, flat_dict, signal_keys):
                    return False

        return True

    @staticmethod
    def _flatten_signals(signal_dict: Dict[str, Any]) -> Dict[str, Any]:
        flat = {}
        for key, value in signal_dict.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flat[f"{key}_{sub_key}"] = sub_value
            else:
                flat[key] = value
        return flat

    def _match_single(self, pattern: str, signal_dict: Dict[str, Any], signal_keys: Set[str]) -> bool:
        parts = pattern.rsplit("_", 1)
        if len(parts) < 2:
            if "*" in pattern or "?" in pattern:
                for key in signal_keys:
                    if fnmatch.fnmatch(key, pattern):
                        return True
                return False
            return pattern in signal_dict

        key_part = parts[0]
        value_part = parts[1]

        matched_keys = []
        if "*" in key_part or "?" in key_part:
            matched_keys = [k for k in signal_keys if fnmatch.fnmatch(k, key_part)]
        else:
            if key_part in signal_dict:
                matched_keys = [key_part]

        if not matched_keys:
            return False

        if not value_part or value_part == "*":
            return True

        for key in matched_keys:
            actual_value = str(signal_dict[key])
            if fnmatch.fnmatch(actual_value, value_part):
                return True

        return False

    @classmethod
    def from_dict(cls, data: Dict) -> "Event":
        operate_raw = data.get("operate", "开多")
        if isinstance(operate_raw, Operate):
            operate = operate_raw
        else:
            operate_map = {
                "开多": Operate.OPEN_LONG,
                "平多": Operate.CLOSE_LONG,
                "开空": Operate.OPEN_SHORT,
                "平空": Operate.CLOSE_SHORT,
            }
            operate = operate_map.get(operate_raw, Operate.OPEN_LONG)

        return cls(
            name=data.get("name", ""),
            operate=operate,
            signals_all=data.get("signals_all", []),
            signals_any=data.get("signals_any", []),
            signals_not=data.get("signals_not", []),
            description=data.get("description", ""),
        )

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "operate": self.operate.value,
            "signals_all": self.signals_all,
            "signals_any": self.signals_any,
            "signals_not": self.signals_not,
            "description": self.description,
        }

    def get_required_signals(self) -> Set[str]:
        signals = set()
        for pattern in self.signals_all + self.signals_any + self.signals_not:
            if "*" not in pattern and "?" not in pattern:
                parts = pattern.rsplit("_", 1)
                if len(parts) >= 2:
                    signals.add(parts[0])
        return signals


@dataclass
class Position:
    name: str
    symbol: str
    opens: List[Event] = field(default_factory=list)
    exits: List[Event] = field(default_factory=list)
    interval: int = 0
    timeout: int = 100
    stop_loss: float = 500
    take_profit: float = 1500
    t0: bool = True
    pos: int = 0

    @property
    def unique_signals(self) -> Set[str]:
        signals = set()
        for event in self.opens + self.exits:
            signals.update(event.get_required_signals())
        return signals

    def check_open(self, signal_dict: Dict[str, Any]) -> Optional[Event]:
        if self.pos != 0:
            return None
        for event in self.opens:
            if event.matches(signal_dict):
                return event
        return None

    def check_exit(self, signal_dict: Dict[str, Any]) -> Optional[Event]:
        if self.pos == 0:
            return None
        for event in self.exits:
            if event.matches(signal_dict):
                return event
        return None

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "symbol": self.symbol,
            "opens": [e.to_dict() for e in self.opens],
            "exits": [e.to_dict() for e in self.exits],
            "interval": self.interval,
            "timeout": self.timeout,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "t0": self.t0,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Position":
        return cls(
            name=data.get("name", ""),
            symbol=data.get("symbol", ""),
            opens=[Event.from_dict(e) for e in data.get("opens", [])],
            exits=[Event.from_dict(e) for e in data.get("exits", [])],
            interval=data.get("interval", 0),
            timeout=data.get("timeout", 100),
            stop_loss=data.get("stop_loss", 500),
            take_profit=data.get("take_profit", 1500),
            t0=data.get("t0", True),
        )


class EventEngine:
    def __init__(self):
        self.events: Dict[str, Event] = {}
        self.positions: Dict[str, Position] = {}

    def register_event(self, event: Event):
        self.events[event.name] = event

    def register_position(self, position: Position):
        self.positions[position.name] = position

    def scan_events(self, signal_dict: Dict[str, Any]) -> List[Event]:
        triggered = []
        for event in self.events.values():
            if event.matches(signal_dict):
                triggered.append(event)
        return triggered

    def scan_positions(self, signal_dict: Dict[str, Any]) -> Dict[str, Any]:
        result = {
            "opens": [],
            "exits": [],
        }
        for pos in self.positions.values():
            open_event = pos.check_open(signal_dict)
            if open_event:
                result["opens"].append({"position": pos.name, "event": open_event.name, "operate": open_event.operate.value})

            exit_event = pos.check_exit(signal_dict)
            if exit_event:
                result["exits"].append({"position": pos.name, "event": exit_event.name, "operate": exit_event.operate.value})

        return result