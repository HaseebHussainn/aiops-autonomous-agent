from __future__ import annotations

import random
import time
from typing import Optional, Dict, Any

from core.types import MetricPoint
from simulation.failure_injector import FailureInjector


class Simulator:
    """
    Generates CPU, MEM, LAT(ms), ERR every second.
    Also tracks 'replicas' and 'version' in a simple state dict.
    """

    def __init__(self, scenario: Optional[str] = None):
        self.injector = FailureInjector(scenario=scenario)
        self.state: Dict[str, Any] = {"replicas": 2, "version": "v3", "service_health": "ok"}

        # baseline values
        self._cpu = 35.0
        self._mem = 40.0
        self._lat = 120.0
        self._err = 1.0

    def step(self, cluster_state: Optional[Dict[str, Any]] = None) -> MetricPoint:
        """
        Compatibility method for run_agent.py.
        Syncs simulator internal state with the caller's cluster_state, then returns the next tick.
        """
        if cluster_state is not None:
            # Only sync known keys; don't accidentally copy garbage
            if "replicas" in cluster_state:
                self.state["replicas"] = int(cluster_state["replicas"])
            if "version" in cluster_state:
                self.state["version"] = str(cluster_state["version"])
            if "service_health" in cluster_state:
                self.state["service_health"] = str(cluster_state["service_health"])

        return self.tick()

    def tick(self) -> MetricPoint:
        self.injector.step()

        # random walk baseline
        self._cpu = max(0.0, min(100.0, self._cpu + random.uniform(-2, 2)))
        self._mem = max(0.0, min(100.0, self._mem + random.uniform(-1.5, 1.5)))
        self._lat = max(1.0, self._lat + random.uniform(-5, 5))
        self._err = max(0.0, self._err + random.uniform(-0.4, 0.4))

        # apply failures
        cpu, mem, lat, err = self.injector.apply(self._cpu, self._mem, self._lat, self._err)

        # small effect of scaling: more replicas slightly lowers cpu/err
        r = int(self.state.get("replicas", 1))
        if r > 1:
            cpu = max(0.0, cpu - (r - 1) * 1.5)
            err = max(0.0, err - (r - 1) * 0.2)

        # effect of restart: brief instability then normalize
        if self.state.get("service_health") == "restarting":
            # after 3 ticks, mark ok again
            if self.injector.state.t % 3 == 0:
                self.state["service_health"] = "ok"
            lat += 40
            err += 1.0

        self._cpu, self._mem, self._lat, self._err = cpu, mem, lat, err

        return MetricPoint(
            ts=time.time(),
            cpu=cpu,
            mem=mem,
            lat_ms=lat,
            err=err,
            replicas=int(self.state["replicas"]),
            version=str(self.state["version"]),
        )