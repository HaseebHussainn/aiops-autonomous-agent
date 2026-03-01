from __future__ import annotations
import time
from core.types import AnalysisReport, PlanDecision
from core.config import PlannerConfig
from core.memory import MemoryStore
from agents.analyst import AnalystAgent


class PlannerAgent:
    def __init__(self, cfg: PlannerConfig, memory: MemoryStore):
        self.cfg = cfg
        self.memory = memory

    def plan(self, analysis: AnalysisReport) -> PlanDecision:
        ts = time.time()
        top = analysis.hypotheses[0]
        sig = AnalystAgent.signature(analysis.anomaly)

        # map hypothesis -> default action
        if top.name == "cpu_saturation":
            action = "scale"
            base_conf = min(0.95, top.likelihood + 0.10)
            base_risk = 0.25
        elif top.name == "memory_pressure_or_leak":
            action = "restart"
            base_conf = min(0.90, top.likelihood + 0.05)
            base_risk = 0.30
        elif top.name == "error_burst_or_bad_deploy":
            action = "rollback"
            base_conf = min(0.92, top.likelihood + 0.08)
            base_risk = 0.32
        elif top.name == "network_latency_or_downstream_slow":
            action = "escalate"
            base_conf = top.likelihood
            base_risk = 0.15
        else:
            action = "escalate"
            base_conf = top.likelihood
            base_risk = 0.20

        # memory bias directly for action confidence
        conf = self.memory.bias(sig, action, base=base_conf, max_boost=0.20)

        # risk rises if many abnormal metrics
        risk = min(1.0, base_risk + 0.05 * max(0, len(analysis.anomaly.abnormal_metrics) - 1))

        auto_ok = (conf >= self.cfg.auto_confidence_threshold) and (risk <= self.cfg.auto_risk_threshold)
        if not auto_ok and action != "noop":
            chosen = "escalate"
            rationale = (f"Policy blocked auto-action. Proposed={action} conf={conf:.2f} risk={risk:.2f}; escalating.")
            return PlanDecision(ts=ts, action=chosen, confidence=conf, risk=risk, rationale=rationale,
                               metadata={"proposed_action": action, "signature": sig, "top_hypothesis": top.name})

        rationale = f"Chosen action={action} based on {top.name}. conf={conf:.2f} risk={risk:.2f}"
        return PlanDecision(ts=ts, action=action, confidence=conf, risk=risk, rationale=rationale,
                           metadata={"signature": sig, "top_hypothesis": top.name})