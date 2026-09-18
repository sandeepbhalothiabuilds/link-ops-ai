from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from .models import (
    ApprovalRecord,
    ApprovalRequest,
    ArtifactRef,
    AuditEvent,
    CodebaseImpact,
    DesignDocument,
    NormalizedRequirement,
    ReleaseReadiness,
    SecurityFinding,
    TaskPlan,
    ValidationResult,
)


def merge_dicts(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(left or {})
    merged.update(right or {})
    return merged


class WorkflowState(TypedDict, total=False):
    run_id: str
    thread_id: str
    scenario_type: str
    raw_requirement: str
    repository_path: str
    auto_approve: bool
    inject_failure: bool
    inject_security_failure: bool
    status: str
    safe_stop_reason: str | None
    approval_gate: str | None
    normalized_requirement: NormalizedRequirement
    acceptance_criteria: list[dict[str, Any]]
    assumptions: list[str]
    ambiguities: list[dict[str, Any]]
    task_plan: TaskPlan
    codebase_impact: CodebaseImpact | None
    design: DesignDocument
    test_plan: dict[str, Any]
    security_findings: list[SecurityFinding]
    validation: ValidationResult
    release_readiness: ReleaseReadiness
    approvals: list[ApprovalRecord]
    approval_requests: list[ApprovalRequest]
    artifacts: Annotated[dict[str, ArtifactRef], merge_dicts]
    artifact_versions: dict[str, int]
    artifact_input_hashes: dict[str, dict[str, str]]
    audit_events: Annotated[list[AuditEvent], operator.add]
    decision_log: Annotated[list[str], operator.add]
    retry_counts: dict[str, int]
    rollback_count: int
    metrics: dict[str, Any]
    repair_attempts: int
