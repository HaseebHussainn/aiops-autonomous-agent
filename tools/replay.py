from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional

from core.config import MonitorConfig
from agents.monitor import MonitorAgent


@dataclass
class MetricPointAdapter:
    ts: float
    cpu: float
    mem: float
    lat_ms: float
    err: float
    replicas: int
    version: str

    @property
    def metrics(self) -> Dict[str, float]:
        return {"cpu": self.cpu, "mem": self.mem, "lat_ms": self.lat_ms, "err": self.err}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Replay logs/metrics.jsonl through the MonitorAgent")
    p.add_argument("--path", type=str, default="logs/metrics.jsonl", help="Path to metrics.jsonl")
    p.add_argument("--window", type=int, default=30, help="Monitor window size for replay")
    p.add_argument("--z", type=float, default=3.0, help="z_threshold for replay")
    p.add_argument("--score", type=float, default=3.5, help="score_threshold for replay")
    p.add_argument("--min-abnormal", type=int, default=1, help="min_abnormal_metrics for replay")
    p.add_argument("--sleep", type=float, default=0.0, help="Sleep seconds between lines (0 = fast)")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    cfg = MonitorConfig(
        window_size=args.window,
        z_threshold=args.z,
        score_threshold=args.score,
        min_abnormal_metrics=args.min_abnormal,
    )

    monitor = MonitorAgent(cfg)

    total = 0
    anomalies = 0

    with open(args.path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec: Dict[str, Any] = json.loads(line)

            point = MetricPointAdapter(
                ts=float(rec.get("ts", time.time())),
                cpu=float(rec["cpu"]),
                mem=float(rec["mem"]),
                lat_ms=float(rec["lat_ms"]),
                err=float(rec["err"]),
                replicas=int(rec.get("replicas", 0)),
                version=str(rec.get("version", "")),
            )

            monitor.observe(point)
            report = monitor.detect(point)

            total += 1

            if report.reason == "warming_up":
                # keep it quiet or print if you want
                pass
            elif report.is_anomaly:
                anomalies += 1
                abnormal = list(report.abnormal_metrics.keys())
                print(
                    f"[REPLAY] anomaly=True score={report.anomaly_score:.2f} abnormal={abnormal} "
                    f"cpu={point.cpu:.1f} mem={point.mem:.1f} lat={point.lat_ms:.1f} err={point.err:.1f}"
                )

            if args.sleep > 0:
                time.sleep(args.sleep)

    print(f"Replay done. total_points={total} anomalies={anomalies}")


if __name__ == "__main__":
    main()