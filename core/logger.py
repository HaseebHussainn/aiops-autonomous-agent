from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional


class ActionLogger:
    """
    Simple JSONL logger used by ExecutorAgent.
    Writes events like:
      {"ts": ..., "event": "execute", "payload": {...}}
    """

    def __init__(self, path: str = "logs/actions.jsonl"):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def log(self, event: str, payload: Optional[Dict[str, Any]] = None) -> None:
        row = {
            "ts": time.time(),
            "event": event,
            "payload": payload or {},
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")