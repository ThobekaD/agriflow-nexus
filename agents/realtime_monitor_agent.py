# agriflow-nexus/agents/realtime_monitor_agent.py
# RealTimeMonitorAgent – fires alerts & can trigger re-planning
from __future__ import annotations
from datetime import datetime
from random import random
from typing import Dict, Any, List

from agents.base_agent import BaseAgent


class RealTimeMonitorAgent(BaseAgent):
    """
    Periodically inspects external feeds (placeholder) and
    injects alerts into the pipeline.  Hook into Pub/Sub or
    a cron in production – here we run once synchronously.
    """
    def __init__(self, orchestrator_callback):
        super().__init__("realtime_monitor", "Real-time Monitor")
        self.alert_thresholds = {'weather': 0.8, 'security': 0.7}
        self.orchestrator_callback = orchestrator_callback

    # ---------- BaseAgent ----------
    def communicate_with_agent(self, tgt: str, message: Dict[str, Any]) -> bool:
        print(f"RealTimeMonitorAgent → {tgt}: alert sent")
        return True

    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        routes = data.get("routes", [])
        alerts = self._check_alerts(routes)
        payload = {**data, "realtime_alerts": alerts}

        # optional: immediately call back into orchestrator
        if alerts:
            self.orchestrator_callback(payload)

        return payload

    # ---------- helpers ----------
    def _check_alerts(self, routes: List[Dict]) -> List[Dict]:
        alerts = []
        for r in routes:
            # dummy weather alert: 20 % chance, higher for T1 every 10th minute
            risk = 0.9 if (r['truck'] == 'T1' and datetime.utcnow().minute % 10 == 0) else random()
            if risk > self.alert_thresholds['weather']:
                alerts.append({
                    "type": "weather",
                    "truck": r['truck'],
                    "risk_level": round(risk, 2),
                    "message": "Severe thunderstorm on route"
                })
        return alerts
