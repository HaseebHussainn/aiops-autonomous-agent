
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class MetricPoint:
    ts: float
    cpu: float
    mem: float
    lat_ms: float
    err: float
    replicas: int
    version: str

    def as_dict(self) -> Dict[str, float]:
        return {"cpu": self.cpu, "mem": self.mem, "lat_ms": self.lat_ms, "err": self.err}


@dataclass
class AnomalyReport:
    ts: float
    is_anomaly: bool
    anomaly_score: float
    abnormal_metrics: Dict[str, float]  # metric -> signed z-score
    window_size: int
    reason: str = "normal"


@dataclass
class Hypothesis:
    name: str
    likelihood: float  # 0..1
    evidence: List[str] = field(default_factory=list)


@dataclass
class AnalysisReport:
    ts: float
    anomaly: AnomalyReport
    hypotheses: List[Hypothesis]
    summary: str


@dataclass
class PlanDecision:
    ts: float
    action: str  # restart|scale|rollback|escalate|noop
    confidence: float  # 0..1
    risk: float        # 0..1
    rationale: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    ts: float
    action: str
    success: bool
    outcome: str
    changed: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0


@dataclass
class IncidentReport:
    ts: float
    title: str
    summary: str
    timeline: List[str]
    metrics: Dict[str, Any]
    action_taken: Dict[str, Any]
    outcome: Dict[str, Any]