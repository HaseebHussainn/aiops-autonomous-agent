from __future__ import annotations

import argparse
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Any

from simulation.simulator import Simulator

from core.logger import ActionLogger
from core.memory import MemoryStore
from core.config import MonitorConfig, AnalystConfig, PlannerConfig, ExecutorConfig
from core.telemetry import TelemetryLogger

from agents.monitor import MonitorAgent
from agents.analyst import AnalystAgent
from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent


# ✅ Adapter so BOTH styles work:
# - point.cpu / point.mem / point.lat_ms / point.err
# - point.metrics["cpu"] / etc.
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
    p = argparse.ArgumentParser()
    p.add_argument(
        "--scenario",
        type=str,
        default=None,
        choices=["cpu_spike", "memory_leak", "error_burst", "network_latency"],
        help="Inject a failure scenario into the simulator",
    )
    p.add_argument("--interval", type=float, default=1.0, help="Seconds between ticks")
    p.add_argument("--window", type=int, default=None, help="Override monitor rolling window size")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # --- Simulator ---
    sim = Simulator(scenario=args.scenario)

    # --- Core services ---
    logger = ActionLogger(path="logs/actions.jsonl")
    memory = MemoryStore(path="memory/aiops_memory.jsonl")
    telemetry = TelemetryLogger(metrics_path="logs/metrics.jsonl", incidents_path="logs/incidents.jsonl")

    # --- Agent configs ---
    mon_cfg = MonitorConfig()
    if args.window is not None:
        mon_cfg.window_size = args.window

    analyst_cfg = AnalystConfig()
    planner_cfg = PlannerConfig()
    exec_cfg = ExecutorConfig()

    # --- Agents ---
    monitor = MonitorAgent(mon_cfg)
    analyst = AnalystAgent(analyst_cfg, memory)
    planner = PlannerAgent(planner_cfg, memory)
    executor = ExecutorAgent(exec_cfg, logger)

    # --- State we allow executor to mutate (simulated "cluster") ---
    cluster_state: Dict[str, Any] = {
        "replicas": 2,
        "version": "v1",
        "service_health": "ok",
    }

    print("Starting AIOps loop...")
    if args.scenario:
        print(f"Scenario enabled: {args.scenario}")

    while True:
        # 1) OBSERVE
        tick = sim.step(cluster_state=cluster_state)

        cpu = float(tick.cpu)
        mem = float(tick.mem)
        lat_ms = float(tick.lat_ms)
        err = float(tick.err)

        # Sync state from simulator tick
        cluster_state["replicas"] = int(getattr(tick, "replicas", cluster_state["replicas"]))
        cluster_state["version"] = str(getattr(tick, "version", cluster_state["version"]))

        point = MetricPointAdapter(
            ts=time.time(),
            cpu=cpu,
            mem=mem,
            lat_ms=lat_ms,
            err=err,
            replicas=int(cluster_state["replicas"]),
            version=str(cluster_state["version"]),
        )

        latest_metrics = point.metrics

        # Structured tick logging (replayable)
        telemetry.log_metric(
            {
                "cpu": cpu,
                "mem": mem,
                "lat_ms": lat_ms,
                "err": err,
                "replicas": cluster_state["replicas"],
                "version": cluster_state["version"],
                "scenario": args.scenario,
            }
        )

        # Print baseline metrics
        print(
            f"CPU={cpu:.0f}  MEM={mem:.0f}  "
            f"LAT(ms)={lat_ms:.0f}  ERR={err:.0f}  "
            f"replicas={cluster_state['replicas']}  version={cluster_state['version']}"
        )

        # 2) DETECT
        monitor.observe(point)
        anomaly = monitor.detect(point)

        if getattr(anomaly, "reason", None) == "warming_up":
            print("[MONITOR] warming up...")
        else:
            abnormal_keys = []
            if hasattr(anomaly, "abnormal_metrics") and isinstance(anomaly.abnormal_metrics, dict):
                abnormal_keys = list(anomaly.abnormal_metrics.keys())

            print(
                f"[MONITOR] anomaly={anomaly.is_anomaly} score={anomaly.anomaly_score:.2f} "
                f"abnormal={abnormal_keys} reason={getattr(anomaly, 'reason', 'n/a')}"
            )

        if anomaly.is_anomaly:
            incident_id = str(uuid.uuid4())[:8]

            telemetry.log_incident(
                {
                    "incident_id": incident_id,
                    "stage": "detect",
                    "anomaly_score": anomaly.anomaly_score,
                    "abnormal_metrics": list(getattr(anomaly, "abnormal_metrics", {}).keys()),
                    "reason": getattr(anomaly, "reason", None),
                    "cluster_state_before": dict(cluster_state),
                }
            )

            # 3) ANALYZE
            analysis = analyst.analyze(anomaly, latest=latest_metrics)
            top = analysis.hypotheses[0]
            print(f"[ANALYST] {analysis.summary}")
            print(f"[ANALYST] top={top.name} likelihood={top.likelihood:.2f} evidence={top.evidence}")

            telemetry.log_incident(
                {
                    "incident_id": incident_id,
                    "stage": "analyze",
                    "top_hypothesis": top.name,
                    "likelihood": top.likelihood,
                    "evidence": top.evidence,
                }
            )

            # 4) DECIDE
            decision = planner.plan(analysis)
            print(
                f"[PLANNER] action={decision.action} confidence={decision.confidence:.2f} "
                f"risk={decision.risk:.2f} rationale={decision.rationale}"
            )

            telemetry.log_incident(
                {
                    "incident_id": incident_id,
                    "stage": "decide",
                    "action": decision.action,
                    "confidence": decision.confidence,
                    "risk": decision.risk,
                    "rationale": decision.rationale,
                }
            )

            # 5) ACT
            result = executor.execute(decision, cluster_state=cluster_state)
            print(f"[EXECUTOR] action={result.action} success={result.success} outcome={result.outcome}")

            telemetry.log_incident(
                {
                    "incident_id": incident_id,
                    "stage": "act",
                    "action": result.action,
                    "success": result.success,
                    "outcome": result.outcome,
                    "cluster_state_after": dict(cluster_state),
                }
            )

            # 6) LEARN
            sig = AnalystAgent.signature(anomaly)
            memory.append(
                signature=sig,
                action=result.action,
                success=result.success,
                outcome=result.outcome,
                metadata={
                    "incident_id": incident_id,
                    "scenario": args.scenario,
                    "anomaly_score": anomaly.anomaly_score,
                    "abnormal_metrics": getattr(anomaly, "abnormal_metrics", {}),
                    "decision": {
                        "confidence": decision.confidence,
                        "risk": decision.risk,
                        "rationale": decision.rationale,
                    },
                    "cluster_state_after": dict(cluster_state),
                },
            )
            print(f"[MEMORY] stored signature={sig} action={result.action} success={result.success}")

        print("-" * 70)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()