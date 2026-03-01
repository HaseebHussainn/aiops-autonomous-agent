from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import math


@dataclass
class AnomalyReport:
    is_anomaly: bool
    anomaly_score: float
    abnormal_metrics: Dict[str, float]  # metric -> z-score
    reason: str  # warming_up | ok | threshold


class RollingWindow:
    """
    Minimal rolling window stats (mean/std) per metric.
    Keeps last N values for each metric key.
    """

    def __init__(self, size: int):
        self.size = max(3, int(size))
        self._values: Dict[str, List[float]] = {}

    def add(self, metrics: Dict[str, float]) -> None:
        for k, v in metrics.items():
            arr = self._values.setdefault(k, [])
            arr.append(float(v))
            if len(arr) > self.size:
                arr.pop(0)

    def count(self) -> int:
        # Count is min length across keys present; good enough for warmup gating
        if not self._values:
            return 0
        return min(len(v) for v in self._values.values())

    def mean_std(self, key: str) -> tuple[float, float]:
        arr = self._values.get(key, [])
        if not arr:
            return 0.0, 0.0
        m = sum(arr) / len(arr)
        var = sum((x - m) ** 2 for x in arr) / max(1, (len(arr) - 1))
        sd = math.sqrt(var)
        return m, sd


class MonitorAgent:
    """
    Observe + Detect.
    Uses rolling window stats and z-score anomaly detection.
    """

    def __init__(self, cfg: Any):
        self.cfg = cfg
        self.window = RollingWindow(size=getattr(cfg, "window_size", 30))

    def observe(self, point: Any) -> None:
        # supports both point.metrics dict OR point.cpu fields via adapter property
        metrics = getattr(point, "metrics", None)
        if callable(metrics):
            metrics = metrics()
        if not isinstance(metrics, dict):
            # try field-based fallback
            metrics = {
                "cpu": float(getattr(point, "cpu")),
                "mem": float(getattr(point, "mem")),
                "lat_ms": float(getattr(point, "lat_ms")),
                "err": float(getattr(point, "err")),
            }
        self.window.add(metrics)

    def detect(self, point: Any) -> AnomalyReport:
        # Warmup
        if self.window.count() < int(getattr(self.cfg, "window_size", 30)):
            return AnomalyReport(
                is_anomaly=False,
                anomaly_score=0.0,
                abnormal_metrics={},
                reason="warming_up",
            )

        metrics = getattr(point, "metrics", None)
        if callable(metrics):
            metrics = metrics()
        if not isinstance(metrics, dict):
            metrics = {
                "cpu": float(getattr(point, "cpu")),
                "mem": float(getattr(point, "mem")),
                "lat_ms": float(getattr(point, "lat_ms")),
                "err": float(getattr(point, "err")),
            }

        z_threshold = float(getattr(self.cfg, "z_threshold", 3.0))
        score_threshold = float(getattr(self.cfg, "score_threshold", 3.5))
        min_abnormal = int(getattr(self.cfg, "min_abnormal_metrics", 1))

        abnormal: Dict[str, float] = {}
        max_abs_z = 0.0

        for k, v in metrics.items():
            mean, sd = self.window.mean_std(k)

            # If sd is too small, z-score becomes unstable; treat as non-abnormal unless far off
            if sd < 1e-9:
                z = 0.0
            else:
                z = (float(v) - mean) / sd

            abs_z = abs(z)
            max_abs_z = max(max_abs_z, abs_z)

            if abs_z >= z_threshold:
                abnormal[k] = float(z)

        is_anomaly = (len(abnormal) >= min_abnormal) and (max_abs_z >= score_threshold)

        return AnomalyReport(
            is_anomaly=is_anomaly,
            anomaly_score=float(max_abs_z),
            abnormal_metrics=abnormal,
            reason="threshold" if is_anomaly else "ok",
        )