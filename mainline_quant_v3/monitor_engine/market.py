# -*- coding: utf-8 -*-
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConceptAnomaly:
    concept_name: str
    pct_change: float
    volume_ratio: float
    anomaly_type: str
    detect_time: str


@dataclass
class LeaderAnomaly:
    stock_code: str
    stock_name: str
    pct_change: float
    volume_ratio: float
    anomaly_type: str
    detect_time: str


class MarketMonitor:

    CONCEPT_PCT_THRESHOLD = 3.0
    CONCEPT_VOLUME_RATIO_THRESHOLD = 2.0
    LEADER_PCT_THRESHOLD = 5.0
    LEADER_VOLUME_RATIO_THRESHOLD = 1.5

    def __init__(self, data_collector, risk_engine=None, notifier=None):
        self.data_collector = data_collector
        self.risk_engine = risk_engine
        self.notifier = notifier
        self.concept_alerts: List[ConceptAnomaly] = []
        self.leader_alerts: List[LeaderAnomaly] = []

        print(f"MarketMonitor concept_threshold={self.CONCEPT_PCT_THRESHOLD}% volume_ratio={self.CONCEPT_VOLUME_RATIO_THRESHOLD}x")

    def check_concept_anomaly(self, concept_data: Optional[Dict[str, Any]] = None) -> List[ConceptAnomaly]:
        if concept_data is None and self.data_collector:
            try:
                concept_data = self.data_collector.get_concept_data()
            except Exception as e:
                print(f"获取概念数据失败: {e}")
                return []

        if not concept_data:
            return []

        anomalies = []
        detect_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        concepts = concept_data.get("concepts", [])
        for concept in concepts:
            name = concept.get("name", "")
            pct_change = concept.get("pct_change", 0)
            volume_ratio = concept.get("volume_ratio", 1.0)

            if abs(pct_change) >= self.CONCEPT_PCT_THRESHOLD:
                anomaly_type = "涨幅异动" if pct_change > 0 else "跌幅异动"
                anomaly = ConceptAnomaly(
                    concept_name=name,
                    pct_change=pct_change,
                    volume_ratio=volume_ratio,
                    anomaly_type=anomaly_type,
                    detect_time=detect_time,
                )
                anomalies.append(anomaly)

            elif volume_ratio >= self.CONCEPT_VOLUME_RATIO_THRESHOLD:
                anomaly = ConceptAnomaly(
                    concept_name=name,
                    pct_change=pct_change,
                    volume_ratio=volume_ratio,
                    anomaly_type="放量异动",
                    detect_time=detect_time,
                )
                anomalies.append(anomaly)

        self.concept_alerts = anomalies

        if anomalies and self.notifier:
            self._notify_concept_anomalies(anomalies)

        return anomalies

    def check_leader_anomaly(self, leaders: Optional[List[Dict[str, Any]]] = None) -> List[LeaderAnomaly]:
        if leaders is None and self.data_collector:
            try:
                leaders = self.data_collector.get_leader_data()
            except Exception as e:
                print(f"获取龙头数据失败: {e}")
                return []

        if not leaders:
            return []

        anomalies = []
        detect_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for leader in leaders:
            code = leader.get("code", "")
            name = leader.get("name", "")
            pct_change = leader.get("pct_change", 0)
            volume_ratio = leader.get("volume_ratio", 1.0)

            if abs(pct_change) >= self.LEADER_PCT_THRESHOLD:
                anomaly_type = "涨幅异动" if pct_change > 0 else "跌幅异动"
                anomaly = LeaderAnomaly(
                    stock_code=code,
                    stock_name=name,
                    pct_change=pct_change,
                    volume_ratio=volume_ratio,
                    anomaly_type=anomaly_type,
                    detect_time=detect_time,
                )
                anomalies.append(anomaly)

            elif volume_ratio >= self.LEADER_VOLUME_RATIO_THRESHOLD:
                anomaly = LeaderAnomaly(
                    stock_code=code,
                    stock_name=name,
                    pct_change=pct_change,
                    volume_ratio=volume_ratio,
                    anomaly_type="放量异动",
                    detect_time=detect_time,
                )
                anomalies.append(anomaly)

        self.leader_alerts = anomalies

        if anomalies and self.notifier:
            self._notify_leader_anomalies(anomalies)

        return anomalies

    def _notify_concept_anomalies(self, anomalies: List[ConceptAnomaly]):
        content_lines = []
        for a in anomalies:
            content_lines.append(
                f"概念: {a.concept_name} | {a.anomaly_type} | "
                f"涨跌幅: {a.pct_change:+.2f}% | 量比: {a.volume_ratio:.2f}x"
            )
        self.notifier.send(
            title=f"概念板块异动 ({len(anomalies)}个)",
            content="\n".join(content_lines),
            level="WARNING",
        )

    def _notify_leader_anomalies(self, anomalies: List[LeaderAnomaly]):
        content_lines = []
        for a in anomalies:
            content_lines.append(
                f"{a.stock_name}({a.stock_code}) | {a.anomaly_type} | "
                f"涨跌幅: {a.pct_change:+.2f}% | 量比: {a.volume_ratio:.2f}x"
            )
        self.notifier.send(
            title=f"龙头股异动 ({len(anomalies)}个)",
            content="\n".join(content_lines),
            level="WARNING",
        )

    def run_check(self, concept_data=None, leaders=None) -> Dict[str, Any]:
        concept_anomalies = self.check_concept_anomaly(concept_data)
        leader_anomalies = self.check_leader_anomaly(leaders)

        return {
            "check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "concept_anomalies": [
                {
                    "name": a.concept_name,
                    "pct_change": a.pct_change,
                    "volume_ratio": a.volume_ratio,
                    "type": a.anomaly_type,
                }
                for a in concept_anomalies
            ],
            "leader_anomalies": [
                {
                    "code": a.stock_code,
                    "name": a.stock_name,
                    "pct_change": a.pct_change,
                    "volume_ratio": a.volume_ratio,
                    "type": a.anomaly_type,
                }
                for a in leader_anomalies
            ],
            "total_anomalies": len(concept_anomalies) + len(leader_anomalies),
        }