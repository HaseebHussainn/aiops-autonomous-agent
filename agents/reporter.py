from __future__ import annotations
from core.config import ReportingConfig
from core.reporting import StubIncidentReporter, IncidentReporter


def build_reporter(cfg: ReportingConfig) -> IncidentReporter:
    # Later you can switch on provider=OpenAI/Azure and keep same interface.
    # For now: stub only.
    return StubIncidentReporter()