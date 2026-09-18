from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def timestamp() -> datetime:
    return datetime.now(UTC)


class ScenarioType(StrEnum):
    GREENFIELD = "greenfield"
    BROWNFIELD = "brownfield"
    AMBIGUOUS = "ambiguous"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Ambiguity(BaseModel):
    ambiguity_id: str = Field(default_factory=lambda: str(uuid4()))
    question: str
    impact: str
    severity: Severity
    resolved: bool = False
    resolution: str | None = None


class AcceptanceCriterion(BaseModel):
    criterion_id: str
    statement: str
    validation: str


class NormalizedRequirement(BaseModel):
    title: str
    intent: str
    scenario_type: ScenarioType
    functional_requirements: list[str]
    non_functional_requirements: list[str]
    constraints: list[str]
    exclusions: list[str]
    acceptance_criteria: list[AcceptanceCriterion]
    assumptions: list[str]
    ambiguities: list[Ambiguity]
    knowledge_references: list[str] = Field(default_factory=list)
    artifact_version: int = 1


class TaskRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PlannedTask(BaseModel):
    task_id: str
    title: str
    owner: str
    dependencies: list[str] = Field(default_factory=list)
    risk: TaskRisk = TaskRisk.MEDIUM
    validation: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    status: Literal["PENDING", "READY", "RUNNING", "DONE", "STALE"] = "PENDING"
    input_hashes: dict[str, str] = Field(default_factory=dict)


class TaskPlan(BaseModel):
    plan_version: int = 1
    tasks: list[PlannedTask]
    generated_at: datetime = Field(default_factory=timestamp)


class CodebaseImpact(BaseModel):
    repository_path: str
    files: list[str]
    modules: list[str]
    routes: list[str]
    tests: list[str]
    data_flows: list[str]
    blast_radius: str
    notes: list[str] = Field(default_factory=list)


class DesignDocument(BaseModel):
    title: str
    context: str
    decisions: list[str]
    api_impact: list[str]
    data_impact: list[str]
    security_impact: list[str]
    observability_impact: list[str]
    rollback_plan: str
    approval_required: bool = True
    artifact_version: int = 1


class SecurityFinding(BaseModel):
    finding_id: str = Field(default_factory=lambda: str(uuid4()))
    severity: Severity
    title: str
    detail: str
    blocking: bool = False
    resolved: bool = False


class ValidationResult(BaseModel):
    passed: bool
    tests_passed: int = 0
    tests_failed: int = 0
    coverage_percent: float = 0.0
    lint_passed: bool = True
    typecheck_passed: bool = True
    security_passed: bool = True
    failures: list[str] = Field(default_factory=list)


class ApprovalRecord(BaseModel):
    approval_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    gate_name: str
    requested_at: datetime = Field(default_factory=timestamp)
    request_summary: str
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    decision: Literal["approved", "rejected", "changes_requested"] | None = None
    decided_at: datetime | None = None
    decider: str | None = None
    comments: str | None = None


class ArtifactRef(BaseModel):
    path: str
    content_hash: str
    artifact_version: int = 1
    input_hashes: dict[str, str] = Field(default_factory=dict)


class AuditEvent(BaseModel):
    timestamp: datetime = Field(default_factory=timestamp)
    run_id: str
    thread_id: str
    agent: str
    node: str
    action_type: str
    task_id: str | None = None
    input_artifacts: dict[str, str] = Field(default_factory=dict)
    output_artifacts: dict[str, str] = Field(default_factory=dict)
    tool_name: str | None = None
    result_status: str
    duration_ms: int = 0
    attempt: int = 1
    retry_count: int = 0
    rollback_count: int = 0
    approval_id: str | None = None


class ReleaseReadiness(BaseModel):
    recommendation: Literal["ready", "not_ready", "safe_stop"]
    rationale: list[str]
    risks: list[str]
    assumptions: list[str]
    limitations: list[str]


class RunMetrics(BaseModel):
    started_at: datetime = Field(default_factory=timestamp)
    finished_at: datetime | None = None
    total_latency_ms: int = 0
    node_latency_ms: dict[str, int] = Field(default_factory=dict)
    node_successes: dict[str, int] = Field(default_factory=dict)
    node_failures: dict[str, int] = Field(default_factory=dict)
    model_invocations: int = 0
    tool_invocations: int = 0
    retry_count: int = 0
    rollback_count: int = 0
    replan_count: int = 0
    invalidated_task_count: int = 0
    waiting_for_approval_ms: int = 0


class ApprovalRequest(BaseModel):
    gate_name: str
    summary: str
    artifact_hashes: dict[str, str] = Field(default_factory=dict)


class WorkflowResult(BaseModel):
    run_id: str
    status: str
    artifact_directory: str
    approval_requests: list[ApprovalRequest] = Field(default_factory=list)
    release_readiness: ReleaseReadiness | None = None
    state: dict[str, Any] = Field(default_factory=dict)
