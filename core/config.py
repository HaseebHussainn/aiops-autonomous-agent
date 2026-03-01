from __future__ import annotations
from dataclasses import dataclass


@dataclass
class MonitorConfig:
    window_size: int = 30
    z_threshold: float = 3.0
    score_threshold: float = 3.5
    min_abnormal_metrics: int = 1


@dataclass
class AnalystConfig:
    base_cpu: float = 0.55
    base_mem: float = 0.55
    base_latency: float = 0.50
    base_errors: float = 0.60
    base_unknown: float = 0.25


@dataclass
class PlannerConfig:
    auto_confidence_threshold: float = 0.75
    auto_risk_threshold: float = 0.35


@dataclass
class ExecutorConfig:
    cooldown_seconds: float = 10.0
    rate_limit_per_minute: int = 6


@dataclass
class ReportingConfig:
    enabled: bool = False   # keep False unless you decide later
    provider: str = "stub"  # stub|openai|azure_openai