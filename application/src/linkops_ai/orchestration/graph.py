from __future__ import annotations

import time
from pathlib import Path
from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from linkops_ai.product.config import Settings, get_settings

from .agents import (
    CodebaseAnalyst,
    DesignAgent,
    DevelopmentAgent,
    PlannerAgent,
    QAAgent,
    ReleaseAgent,
    RequirementsAgent,
    SecurityAgent,
)
from .artifacts import ArtifactStore
from .gates import design_gate, intake_gate, release_gate, security_gate, validation_gate
from .models import (
    ApprovalRecord,
    ApprovalRequest,
    ArtifactRef,
    AuditEvent,
    ReleaseReadiness,
    Severity,
)
from .state import WorkflowState


def build_graph(
    workspace: str | Path,
    settings: Settings | None = None,
    checkpointer: Any = None,
) -> Any:
    settings = settings or get_settings()
    requirement_agent = RequirementsAgent()
    planner_agent = PlannerAgent()
    analyst = CodebaseAnalyst()
    design_agent = DesignAgent()
    development_agent = DevelopmentAgent()
    qa_agent = QAAgent()
    security_agent = SecurityAgent()
    release_agent = ReleaseAgent()

    def store(state: WorkflowState) -> ArtifactStore:
        return ArtifactStore(workspace, state["run_id"])

    def artifact(
        state: WorkflowState,
        key: str,
        path: str,
        value: Any,
        input_hashes: dict[str, str] | None = None,
    ) -> dict[str, ArtifactRef]:
        refs = dict(state.get("artifacts", {}))
        if isinstance(value, str):
            ref = store(state).write_text(path, value, input_hashes=input_hashes)
        else:
            ref = store(state).write_json(path, value, input_hashes=input_hashes)
        refs[key] = ref
        return refs

    def event(
        state: WorkflowState, node: str, agent: str, action: str, outcome: str, duration_ms: int = 0
    ) -> AuditEvent:
        return AuditEvent(
            run_id=state["run_id"],
            thread_id=state["thread_id"],
            agent=agent,
            node=node,
            action_type=action,
            result_status=outcome,
            duration_ms=duration_ms,
            retry_count=state.get("retry_counts", {}).get(node, 0),
            rollback_count=state.get("rollback_count", 0),
        )

    def emit_audit(state: WorkflowState) -> None:
        audit_path = store(state).root / "audit" / "audit.ndjson"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        events = state.get("audit_events", [])
        if events:
            with audit_path.open("a", encoding="utf-8") as stream:
                for item in events[-1:]:
                    stream.write(item.model_dump_json() + "\n")

    def combined(state: WorkflowState, result: dict[str, Any]) -> WorkflowState:
        return cast(WorkflowState, {**state, **result})

    def intake(state: WorkflowState) -> dict[str, Any]:
        started = time.perf_counter()
        normalized = requirement_agent.normalize(state["raw_requirement"], state["scenario_type"])
        refs = artifact(
            state, "normalized_requirement", "requirements/normalized_requirement.json", normalized
        )
        artifact(
            state,
            "requirements_markdown",
            "requirements/normalized_requirement.md",
            _requirement_markdown(normalized),
        )
        result = {
            "normalized_requirement": normalized,
            "acceptance_criteria": [item.model_dump() for item in normalized.acceptance_criteria],
            "assumptions": normalized.assumptions,
            "ambiguities": [item.model_dump() for item in normalized.ambiguities],
            "artifacts": refs,
            "status": "INTAKE_COMPLETE",
            "decision_log": [
                "Requirements were normalized with explicit assumptions and ambiguity severity."
            ],
            "audit_events": [
                event(
                    state,
                    "intake",
                    "requirements",
                    "normalize_requirement",
                    "success",
                    _elapsed(started),
                )
            ],
        }
        emit_audit(combined(state, result))
        return result

    def planner(state: WorkflowState) -> dict[str, Any]:
        plan = planner_agent.plan(state["normalized_requirement"])
        refs = artifact(state, "task_plan", "plan/task_plan.json", plan)
        mmd = _task_plan_mermaid(plan)
        refs.update(artifact(state, "task_plan_graph", "plan/task_plan.mmd", mmd))
        result = {
            "task_plan": plan,
            "artifacts": refs,
            "status": "PLAN_COMPLETE",
            "audit_events": [event(state, "planner", "planner", "decompose_work", "success")],
        }
        emit_audit(combined(state, result))
        return result

    def codebase(state: WorkflowState) -> dict[str, Any]:
        impact = analyst.analyze(state["repository_path"])
        refs = artifact(state, "codebase_impact", "codebase/codebase_impact.json", impact)
        refs.update(
            artifact(
                state,
                "codebase_impact_markdown",
                "codebase/codebase_impact.md",
                _impact_markdown(impact),
            )
        )
        result = {
            "codebase_impact": impact,
            "artifacts": refs,
            "audit_events": [event(state, "codebase", "codebase", "analyze_repository", "success")],
        }
        emit_audit(combined(state, result))
        return result

    def design(state: WorkflowState) -> dict[str, Any]:
        design_doc = design_agent.design(
            state["normalized_requirement"], state.get("codebase_impact")
        )
        refs = artifact(state, "design", "design/design.json", design_doc)
        refs.update(
            artifact(state, "design_markdown", "design/design.md", _design_markdown(design_doc))
        )
        result = {
            "design": design_doc,
            "artifacts": refs,
            "status": "DESIGN_COMPLETE",
            "audit_events": [event(state, "design", "architecture", "produce_design", "success")],
        }
        emit_audit(combined(state, result))
        return result

    def request_approval(state: WorkflowState) -> dict[str, Any]:
        requirement = state.get("normalized_requirement")
        has_high_ambiguity = bool(
            requirement
            and any(
                item.severity in {Severity.HIGH, Severity.CRITICAL} and not item.resolved
                for item in requirement.ambiguities
            )
        )
        # The node can be revisited after a prior gate. Infer the next gate from
        # the current workflow stage instead of carrying the old gate forward.
        if state.get("release_readiness") is not None:
            gate_name = "release"
        elif state.get("design") is not None:
            gate_name = "architecture"
        else:
            gate_name = "requirements" if has_high_ambiguity else "architecture"
        existing = next(
            (item for item in state.get("approvals", []) if item.gate_name == gate_name), None
        )
        if existing and existing.decision == "approved":
            return {"approval_gate": gate_name, "status": "APPROVAL_ACCEPTED"}
        if state.get("auto_approve"):
            approval = ApprovalRecord(
                run_id=state["run_id"],
                gate_name=gate_name,
                request_summary=f"Auto-approved local {gate_name} gate.",
                decision="approved",
                decider="local-demo",
                decided_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            )
            return {
                "approval_gate": gate_name,
                "approvals": [approval],
                "status": "APPROVAL_ACCEPTED",
            }
        request = ApprovalRequest(
            gate_name=gate_name,
            summary={
                "requirements": "Clarify the high-impact analytics privacy and freshness policy.",
                "architecture": (
                    "Approve the public API, persistence, and controlled implementation design."
                ),
                "release": "Approve the final release-readiness package and any external action.",
            }.get(gate_name, "Review the protected workflow action."),
            artifact_hashes={
                key: ref.content_hash for key, ref in state.get("artifacts", {}).items()
            },
        )
        if settings.use_graph_interrupt:
            from langgraph.types import interrupt

            response = interrupt(request.model_dump())
            if isinstance(response, dict) and response.get("decision") == "approved":
                approval = ApprovalRecord(
                    run_id=state["run_id"],
                    gate_name=gate_name,
                    request_summary=request.summary,
                    decision="approved",
                    decider=str(response.get("decider", "human")),
                    comments=response.get("comments"),
                )
                return {
                    "approval_gate": gate_name,
                    "approvals": [approval],
                    "status": "APPROVAL_ACCEPTED",
                }
        result = {
            "approval_gate": gate_name,
            "approval_requests": [request],
            "status": "WAITING_APPROVAL",
            "audit_events": [event(state, "approval", "governance", "request_approval", "waiting")],
        }
        emit_audit(combined(state, result))
        return result

    def development(state: WorkflowState) -> dict[str, Any]:
        output = development_agent.execute(state["normalized_requirement"])
        refs = artifact(state, "development", "implementation/change_set.json", output)
        return {
            "artifacts": refs,
            "audit_events": [
                event(state, "development", "development", "implement_change", "success")
            ],
        }

    def testspec(state: WorkflowState) -> dict[str, Any]:
        test_plan = qa_agent.specify(state["normalized_requirement"])
        refs = artifact(state, "test_plan", "validation/test_plan.json", test_plan)
        return {
            "test_plan": test_plan,
            "artifacts": refs,
            "audit_events": [event(state, "testspec", "qa", "specify_tests", "success")],
        }

    def security(state: WorkflowState) -> dict[str, Any]:
        findings = security_agent.review(state.get("inject_security_failure", False))
        refs = artifact(state, "security", "validation/security_findings.json", findings)
        return {
            "security_findings": findings,
            "artifacts": refs,
            "audit_events": [
                event(
                    state,
                    "security",
                    "security",
                    "review_security",
                    "success" if not findings else "blocking",
                )
            ],
        }

    def validate(state: WorkflowState) -> dict[str, Any]:
        attempts = state.get("repair_attempts", 0)
        result = qa_agent.validate(state.get("inject_failure", False), attempts)
        findings = state.get("security_findings", [])
        if any(item.blocking and not item.resolved for item in findings):
            result = result.model_copy(
                update={
                    "passed": False,
                    "security_passed": False,
                    "failures": [*result.failures, "blocking security finding remains"],
                }
            )
        refs = artifact(state, "validation", "validation/test_results.json", result)
        return {
            "validation": result,
            "artifacts": refs,
            "status": "VALIDATED",
            "audit_events": [
                event(
                    state,
                    "validation",
                    "qa",
                    "run_validation",
                    "success" if result.passed else "failure",
                )
            ],
        }

    def repair(state: WorkflowState) -> dict[str, Any]:
        attempts = state.get("repair_attempts", 0) + 1
        retries = dict(state.get("retry_counts", {}))
        retries["validation"] = attempts
        return {
            "repair_attempts": attempts,
            "retry_counts": retries,
            "status": "REPAIRING",
            "audit_events": [event(state, "repair", "repair", "targeted_repair", "success")],
        }

    def docs(state: WorkflowState) -> dict[str, Any]:
        readiness = ReleaseReadiness.model_validate(release_agent.summarize(dict(state)))
        refs = artifact(state, "engineering_summary", "release/engineering_summary.json", readiness)
        refs.update(
            artifact(
                state,
                "engineering_summary_markdown",
                "release/engineering_summary.md",
                _release_markdown(readiness),
            )
        )
        return {
            "release_readiness": readiness,
            "artifacts": refs,
            "status": "RELEASE_REVIEW",
            "audit_events": [event(state, "docs", "release", "assemble_evidence", "success")],
        }

    def safe_stop(state: WorkflowState) -> dict[str, Any]:
        validation = state.get("validation")
        reason = (
            "; ".join(validation.failures)
            if validation and validation.failures
            else "workflow safe-stop gate reached"
        )
        if not reason or reason == "; ":
            reason = "workflow safe-stop gate reached"
        refs = artifact(state, "safe_stop", "release/safe_stop.json", {"reason": reason})
        return {
            "status": "SAFE_STOP",
            "safe_stop_reason": reason,
            "artifacts": refs,
            "audit_events": [event(state, "safe_stop", "governance", "safe_stop", "blocked")],
        }

    def complete(state: WorkflowState) -> dict[str, Any]:
        summary = {
            "status": "complete",
            "run_id": state["run_id"],
            "artifacts": sorted(state.get("artifacts", {})),
        }
        refs = artifact(state, "manifest", "manifest.json", summary)
        return {
            "status": "COMPLETE",
            "artifacts": refs,
            "audit_events": [event(state, "complete", "release", "complete_run", "success")],
        }

    def intake_route(state: WorkflowState) -> str:
        ok, _ = intake_gate(state)
        if ok:
            return "planner"
        state_ambiguities = state.get("normalized_requirement")
        if state_ambiguities and any(
            item.severity in {Severity.HIGH, Severity.CRITICAL} and not item.resolved
            for item in state_ambiguities.ambiguities
        ):
            return "requirements_approval"
        return "safe_stop"

    def approval_route(state: WorkflowState) -> str:
        if state.get("status") == "WAITING_APPROVAL":
            return "wait"
        gate_name = state.get("approval_gate")
        if gate_name == "requirements":
            return "planner"
        if gate_name == "architecture":
            return "development"
        if gate_name == "release":
            return "complete"
        return "safe_stop"

    def planner_route(state: WorkflowState) -> str:
        return "codebase" if state["scenario_type"] == "brownfield" else "design"

    def design_route(state: WorkflowState) -> str | list[str]:
        ok, _ = design_gate(state)
        if not ok:
            return "safe_stop"
        if (
            state["design"].approval_required
            and not state.get("auto_approve")
            and not any(
                item.gate_name == "architecture" and item.decision == "approved"
                for item in state.get("approvals", [])
            )
        ):
            return "architecture_approval"
        return ["development", "testspec", "security"]

    def validation_route(state: WorkflowState) -> str:
        if not security_gate(state)[0]:
            return "safe_stop"
        passed, _ = validation_gate(state["validation"])
        if passed:
            return "docs"
        if state.get("repair_attempts", 0) < 2:
            return "repair"
        return "safe_stop"

    def release_route(state: WorkflowState) -> str:
        if not release_gate(state)[0]:
            return "safe_stop"
        if state.get("auto_approve") or any(
            item.gate_name == "release" and item.decision == "approved"
            for item in state.get("approvals", [])
        ):
            return "complete"
        return "release_approval"

    graph = StateGraph(WorkflowState)
    graph.add_node("intake", intake)
    graph.add_node("planner", planner)
    graph.add_node("codebase", codebase)
    graph.add_node("design", design)
    graph.add_node("approval", request_approval)
    graph.add_node("development", development)
    graph.add_node("testspec", testspec)
    graph.add_node("security", security)
    graph.add_node("validation", validate)
    graph.add_node("repair", repair)
    graph.add_node("docs", docs)
    graph.add_node("safe_stop", safe_stop)
    graph.add_node("complete", complete)
    graph.add_edge(START, "intake")
    graph.add_conditional_edges(
        "intake",
        intake_route,
        {"planner": "planner", "requirements_approval": "approval", "safe_stop": "safe_stop"},
    )
    graph.add_conditional_edges(
        "approval",
        approval_route,
        {
            "wait": END,
            "planner": "planner",
            "development": "development",
            "complete": "complete",
            "safe_stop": "safe_stop",
        },
    )
    graph.add_conditional_edges(
        "planner", planner_route, {"codebase": "codebase", "design": "design"}
    )
    graph.add_edge("codebase", "design")
    graph.add_conditional_edges(
        "design",
        design_route,
        {
            "architecture_approval": "approval",
            "development": "development",
            "testspec": "testspec",
            "security": "security",
            "safe_stop": "safe_stop",
        },
    )
    graph.add_edge("development", "validation")
    graph.add_edge("testspec", "validation")
    graph.add_edge("security", "validation")
    graph.add_conditional_edges(
        "validation",
        validation_route,
        {"docs": "docs", "repair": "repair", "safe_stop": "safe_stop"},
    )
    graph.add_edge("repair", "validation")
    graph.add_conditional_edges(
        "docs",
        release_route,
        {"release_approval": "approval", "complete": "complete", "safe_stop": "safe_stop"},
    )
    graph.add_edge("safe_stop", END)
    graph.add_edge("complete", END)
    return graph.compile(checkpointer=checkpointer)


def _elapsed(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _requirement_markdown(value: Any) -> str:
    return (
        f"# {value.title}\n\n## Intent\n{value.intent}\n\n## Functional requirements\n"
        + "\n".join(f"- {item}" for item in value.functional_requirements)
        + "\n\n## Assumptions\n"
        + "\n".join(f"- {item}" for item in value.assumptions)
        + "\n"
    )


def _task_plan_mermaid(plan: Any) -> str:
    lines = ["graph TD"]
    for task in plan.tasks:
        lines.append(f"  {task.task_id.replace('-', '_')}['{{task.title}}']")
        for dependency in task.dependencies:
            lines.append(f"  {dependency.replace('-', '_')} --> {task.task_id.replace('-', '_')}")
    return "\n".join(lines) + "\n"


def _impact_markdown(impact: Any) -> str:
    return (
        f"# Codebase impact\n\nRepository: `{impact.repository_path}`\n\n## Files\n"
        + "\n".join(f"- `{item}`" for item in impact.files)
        + f"\n\n## Blast radius\n{impact.blast_radius}\n"
    )


def _design_markdown(value: Any) -> str:
    return (
        f"# {value.title}\n\n{value.context}\n\n## Decisions\n"
        + "\n".join(f"- {item}" for item in value.decisions)
        + "\n\n## API impact\n"
        + "\n".join(f"- {item}" for item in value.api_impact)
        + "\n\n## Security impact\n"
        + "\n".join(f"- {item}" for item in value.security_impact)
        + f"\n\n## Rollback\n{value.rollback_plan}\n"
    )


def _release_markdown(value: ReleaseReadiness) -> str:
    return (
        f"# Engineering summary\n\nRecommendation: **{value.recommendation}**\n\n## Rationale\n"
        + "\n".join(f"- {item}" for item in value.rationale)
        + "\n\n## Risks\n"
        + "\n".join(f"- {item}" for item in value.risks)
        + "\n"
    )
