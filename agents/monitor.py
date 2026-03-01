from __future__ import annotations

from core.types import MetricPoint, AnomalyReport
from core.rolling_window import RollingWindow
from core.config import MonitorConfig


class MonitorAgent:
    def __init__(self, cfg: MonitorConfig):
        self.cfg = cfg
        self.window = RollingWindow(cfg.window_size)

    def observe(self, point: MetricPoint) -> None:
        # push ONLY the metrics dict into the rolling window
        self.window.push(point.metrics)

    def detect(self, point: MetricPoint) -> AnomalyReport:
        if not self.window.ready():
            return AnomalyReport(
                ts=point.ts,
                is_anomaly=False,
                anomaly_score=0.0,
                abnormal_metrics={},
                window_size=self.cfg.window_size,
                reason="warming_up",
            )

        z = self.window.zscores(point.metrics)
        abnormal = {k: v for k, v in z.items() if abs(v) >= self.cfg.z_threshold}

        max_abs_z = max((abs(v) for v in z.values()), default=0.0)
        anomaly_score = max_abs_z + 0.25 * max(0, len(abnormal) - 1)

        is_anomaly = (
            len(abnormal) >= self.cfg.min_abnormal_metrics
            and anomaly_score >= self.cfg.score_threshold
        )

        reason = "normal"
        if is_anomaly:
            reason = f"zscore_spike({','.join(sorted(abnormal.keys()))}) score={anomaly_score:.2f}"

        return AnomalyReport(
            ts=point.ts,
            is_anomaly=is_anomaly,
            anomaly_score=float(anomaly_score),
            abnormal_metrics=abnormal,
            window_size=self.cfg.window_size,
            reason=reason,
        )