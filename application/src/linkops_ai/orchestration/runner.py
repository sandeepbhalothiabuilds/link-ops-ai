from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from linkops_ai.product.config import get_settings

from ..adapters.checkpoints import build_checkpointer
from .artifacts import ArtifactStore
from .graph import build_graph
from .models import ApprovalRecord, AuditEvent, TaskPlan, WorkflowResult
from .replan import invalidate_downstream, plan_diff


class WorkflowRunner:
    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).resolve()

    def run(
        self,
        raw_requirement: str,
        scenario_type: str,
        *,
        run_id: str | None = None,
        auto_approve: bool = False,
        approvals: list[ApprovalRecord] | None = None,
        inject_failure: bool = False,
        inject_security_failure: bool = False,
    ) -> WorkflowResult:
        run_id = run_id or f"run-{uuid4().hex[:12]}"
        initial = {
            "run_id": run_id,
            "thread_id": run_id,
            "scenario_type": scenario_type,
            "raw_requirement": raw_requirement,
            "repository_path": str(self.workspace),
            "auto_approve": auto_approve,
            "inject_failure": inject_failure,
            "inject_security_failure": inject_security_failure,
            "approvals": approvals or [],
            "approval_requests": [],
            "artifacts": {},
            "retry_counts": {},
            "repair_attempts": 0,
            "rollback_count": 0,
            "audit_events": [],
            "decision_log": [],
        }
        settings = get_settings()
        graph = build_graph(
            self.workspace,
            settings=settings,
            checkpointer=build_checkpointer(settings),
        )
        state = graph.invoke(initial, config={"configurable": {"thread_id": run_id}})
        self._persist_run_state(run_id, state)
        return WorkflowResult(
            run_id=run_id,
            status=state.get("status", "UNKNOWN"),
            artifact_directory=str(self.workspace / "artifacts" / run_id),
            approval_requests=state.get("approval_requests", []),
            release_readiness=state.get("release_readiness"),
            state=cast(dict[str, Any], _jsonable(state)),
        )

    def resume(
        self,
        run_id: str,
        raw_requirement: str,
        scenario_type: str,
        gate_name: str,
        *,
        decider: str = "human-demo",
        comments: str | None = None,
        auto_approve: bool = False,
    ) -> WorkflowResult:
        prior_approvals: list[ApprovalRecord] = []
        state_path = self.workspace / "artifacts" / run_id / "state.json"
        if state_path.exists():
            saved = json.loads(state_path.read_text(encoding="utf-8"))
            prior_approvals = [
                ApprovalRecord.model_validate(item) for item in saved.get("approvals", [])
            ]
        approval = ApprovalRecord(
            run_id=run_id,
            gate_name=gate_name,
            request_summary=f"Approved {gate_name} gate",
            decision="approved",
            decider=decider,
            comments=comments,
        )
        return self.run(
            raw_requirement,
            scenario_type,
            run_id=run_id,
            auto_approve=auto_approve,
            approvals=[*prior_approvals, approval],
        )

    def replan(self, run_id: str, changed_task_ids: list[str]) -> WorkflowResult:
        state_path = self.workspace / "artifacts" / run_id / "state.json"
        if not state_path.exists():
            raise FileNotFoundError(f"workflow state not found for {run_id}")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        before = TaskPlan.model_validate(state["task_plan"])
        after = invalidate_downstream(before, changed_task_ids)
        diff = plan_diff(before, after)
        ref = ArtifactStore(self.workspace, run_id).write_json(
            "replan/plan_diff.json",
            {
                "changed_task_ids": changed_task_ids,
                "prior_version": before.plan_version,
                "new_version": after.plan_version,
                **diff,
            },
        )
        artifacts = dict(state.get("artifacts", {}))
        artifacts["replan"] = ref.model_dump(mode="json")
        state["task_plan"] = after.model_dump(mode="json")
        state["artifacts"] = artifacts
        state["status"] = "REPLANNED"
        state["metrics"] = {
            **state.get("metrics", {}),
            "replan_count": state.get("metrics", {}).get("replan_count", 0) + 1,
            "invalidated_task_count": len(diff["stale"]),
        }
        audit_path = self.workspace / "artifacts" / run_id / "audit" / "audit.ndjson"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.open("a", encoding="utf-8").write(
            AuditEvent(
                run_id=run_id,
                thread_id=run_id,
                agent="planner",
                node="replan",
                action_type="replan",
                result_status="success",
            ).model_dump_json()
            + "\n"
        )
        self._persist_run_state(run_id, state)
        return WorkflowResult(
            run_id=run_id,
            status="REPLANNED",
            artifact_directory=str(self.workspace / "artifacts" / run_id),
            state=cast(dict[str, Any], _jsonable(state)),
        )

    def _persist_run_state(self, run_id: str, state: dict[str, object]) -> None:
        target = self.workspace / "artifacts" / run_id / "state.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(_jsonable(state), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def _jsonable(value: object) -> object:
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump())
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
