from __future__ import annotations

from typing import Dict, List
import time

from core.types import AnomalyReport, Hypothesis, AnalysisReport
from core.config import AnalystConfig
from core.memory import MemoryStore


class AnalystAgent:
    def __init__(self, cfg: AnalystConfig, memory: MemoryStore):
        self.cfg = cfg
        self.memory = memory

    @staticmethod
    def signature(anomaly: AnomalyReport) -> str:
        parts = []
        for k in sorted(anomaly.abnormal_metrics.keys()):
            sign = "pos" if anomaly.abnormal_metrics[k] >= 0 else "neg"
            parts.append(f"{k}:{sign}")
        return "|".join(parts) if parts else "none"

    def analyze(self, anomaly: AnomalyReport, latest: Dict[str, float]) -> AnalysisReport:
        ts = time.time()
        ab = anomaly.abnormal_metrics
        hyps: List[Hypothesis] = []

        if "cpu" in ab:
            hyps.append(Hypothesis(
                name="cpu_saturation",
                likelihood=self.cfg.base_cpu,
                evidence=[f"cpu z={ab['cpu']:.2f}"]
            ))

        if "mem" in ab:
            hyps.append(Hypothesis(
                name="memory_pressure_or_leak",
                likelihood=self.cfg.base_mem,
                evidence=[f"mem z={ab['mem']:.2f}"]
            ))

        if "lat_ms" in ab:
            hyps.append(Hypothesis(
                name="network_latency_or_downstream_slow",
                likelihood=self.cfg.base_latency,
                evidence=[f"lat_ms z={ab['lat_ms']:.2f}"]
            ))

        if "err" in ab:
            hyps.append(Hypothesis(
                name="error_burst_or_bad_deploy",
                likelihood=self.cfg.base_errors,
                evidence=[f"err z={ab['err']:.2f}"]
            ))

        if not hyps:
            hyps.append(Hypothesis(
                name="unknown_anomaly",
                likelihood=self.cfg.base_unknown,
                evidence=[f"abnormal={list(ab.keys())}"]
            ))

        if ("err" in ab) and ("lat_ms" in ab):
            for h in hyps:
                if h.name in ("network_latency_or_downstream_slow", "error_burst_or_bad_deploy"):
                    h.likelihood = min(1.0, h.likelihood + 0.10)
                    h.evidence.append("coupled(ERR+LAT)")

        sig = self.signature(anomaly)
        rollback_boost = self.memory.bias(sig, "rollback", base=0.0, max_boost=0.10)
        restart_boost = self.memory.bias(sig, "restart", base=0.0, max_boost=0.10)
        scale_boost = self.memory.bias(sig, "scale", base=0.0, max_boost=0.10)

        for h in hyps:
            if h.name == "error_burst_or_bad_deploy":
                h.likelihood = min(1.0, h.likelihood + rollback_boost + restart_boost * 0.5)
            if h.name == "cpu_saturation":
                h.likelihood = min(1.0, h.likelihood + scale_boost)

        hyps.sort(key=lambda x: x.likelihood, reverse=True)
        summary = f"Top: {hyps[0].name} ({hyps[0].likelihood:.2f})"

        return AnalysisReport(ts=ts, anomaly=anomaly, hypotheses=hyps, summary=summary)