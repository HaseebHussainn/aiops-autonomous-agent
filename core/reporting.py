from __future__ import annotations
from typing import Protocol, Optional, Dict, Any, List
import time

from core.types import IncidentReport, MetricPoint, AnalysisReport, PlanDecision, ActionResult


class IncidentReporter(Protocol):
    def generate(
        self,
        last_point: MetricPoint,
        analysis: AnalysisReport,
        decision: PlanDecision,
        result: ActionResult,
    ) -> IncidentReport:
        ...


class StubIncidentReporter:
    def generate(self, last_point, analysis, decision, result) -> IncidentReport:
        title = f"Incident: {analysis.hypotheses[0].name}"
        summary = (
            f"Anomaly detected (score={analysis.anomaly.anomaly_score:.2f}). "
            f"Action={decision.action} (conf={decision.confidence:.2f}, risk={decision.risk:.2f}). "
            f"Outcome={result.outcome}."
        )
        timeline = [
            f"t0 anomaly: {analysis.anomaly.reason}",
            f"t1 analysis: {analysis.summary}",
            f"t2 decision: {decision.rationale}",
            f"t3 action: {result.action} -> {result.outcome}",
        ]
        return IncidentReport(
            ts=time.time(),
            title=title,
            summary=summary,
            timeline=timeline,
            metrics={
                "cpu": last_point.cpu,
                "mem": last_point.mem,
                "lat_ms": last_point.lat_ms,
                "err": last_point.err,
                "replicas": last_point.replicas,
                "version": last_point.version,
            },
            action_taken={"decision": decision.__dict__},
            outcome={"result": result.__dict__},
        )