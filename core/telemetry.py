from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional


class TelemetryLogger:
    def __init__(self, metrics_path: str = "logs/metrics.jsonl", incidents_path: str = "logs/incidents.jsonl"):
        self.metrics_path = metrics_path
        self.incidents_path = incidents_path
        os.makedirs(os.path.dirname(metrics_path), exist_ok=True)

    def log_metric(self, record: Dict[str, Any]) -> None:
        record = {"ts": time.time(), **record}
        with open(self.metrics_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def log_incident(self, record: Dict[str, Any]) -> None:
        record = {"ts": time.time(), **record}
        with open(self.incidents_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")