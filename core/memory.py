from __future__ import annotations
import json, os, time
from typing import Any, Dict, List, Tuple, Optional


class MemoryStore:
    """
    JSONL memory:
    each line: {ts, signature, action, success, outcome, metadata}
    used to bias future decisions (reinforcement-ish)
    """

    def __init__(self, path: str = "memory/aiops_memory.jsonl"):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def append(
        self,
        signature: str,
        action: str,
        success: bool,
        outcome: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        row = {
            "ts": time.time(),
            "signature": signature,
            "action": action,
            "success": bool(success),
            "outcome": outcome,
            "metadata": metadata or {},
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

    def _load(self, limit: int = 5000) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        rows: List[Dict[str, Any]] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= limit:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    def success_rate(self, signature: str, action: str) -> Tuple[int, int, float]:
        rows = self._load()
        total = 0
        succ = 0
        for r in rows:
            if r.get("signature") == signature and r.get("action") == action:
                total += 1
                succ += 1 if r.get("success") else 0
        rate = (succ / total) if total else 0.0
        return succ, total, rate

    def bias(self, signature: str, action: str, base: float, max_boost: float = 0.25) -> float:
        succ, total, rate = self.success_rate(signature, action)
        if total < 2:
            return base
        confidence = min(1.0, total / 10.0)
        boosted = base + max_boost * rate * confidence
        return min(1.0, max(0.0, boosted))