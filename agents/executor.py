from __future__ import annotations

import time
from core.types import PlanDecision, ActionResult
from core.config import ExecutorConfig
from core.logger import ActionLogger


class ExecutorAgent:

    def __init__(self, cfg: ExecutorConfig, logger: ActionLogger):
        self.cfg = cfg
        self.logger = logger
        self.last_action_time = 0

    def execute(self, decision: PlanDecision, cluster_state: dict) -> ActionResult:
        now = time.time()

        # cooldown protection
        if now - self.last_action_time < self.cfg.cooldown_seconds:
            return ActionResult(
                ts=now,
                action="noop",
                success=False,
                outcome="cooldown_active"
            )

        action = decision.action
        changed = {}

        if action == "scale":
            cluster_state["replicas"] += 1
            changed["replicas"] = cluster_state["replicas"]
            outcome = "scaled_up"

        elif action == "restart":
            outcome = "service_restarted"

        elif action == "rollback":
            cluster_state["version"] = "v0"
            changed["version"] = cluster_state["version"]
            outcome = "rollback_complete"

        elif action == "escalate":
            outcome = "incident_escalated"

        else:
            outcome = "noop"

        self.last_action_time = now

        # log action
        self.logger.log("execute", {
            "action": action,
            "outcome": outcome,
            "cluster_state": cluster_state
        })

        return ActionResult(
            ts=now,
            action=action,
            success=True,
            outcome=outcome,
            changed=changed
        )