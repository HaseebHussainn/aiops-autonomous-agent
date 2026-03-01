from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import random


@dataclass
class FailureState:
    scenario: Optional[str] = None
    t: int = 0  # ticks since start


class FailureInjector:
    def __init__(self, scenario: Optional[str]):
        self.state = FailureState(scenario=scenario, t=0)

    def step(self) -> None:
        self.state.t += 1

    def apply(self, cpu: float, mem: float, lat_ms: float, err: float):
        s = self.state.scenario
        t = self.state.t

        if s is None:
            return cpu, mem, lat_ms, err

        if s == "cpu_spike":
            if 20 <= t <= 40:
                cpu += 45 + random.uniform(-5, 5)

        elif s == "memory_leak":
            if t >= 15:
                mem += min(60.0, (t - 15) * 2.0)

        elif s == "error_burst":
            if 25 <= t <= 35:
                err += 20 + random.uniform(-3, 3)

        elif s == "network_latency":
            if 18 <= t <= 45:
                lat_ms += 250 + random.uniform(-20, 20)

        return cpu, mem, lat_ms, err