from __future__ import annotations

from .models import Severity, ValidationResult
from .state import WorkflowState


def intake_gate(state: WorkflowState) -> tuple[bool, str]:
    requirement = state.get("normalized_requirement")
    if requirement is None or not requirement.acceptance_criteria:
        return False, "normalized requirement and acceptance criteria are required"
    high = [
        item
        for item in requirement.ambiguities
        if item.severity in {Severity.HIGH, Severity.CRITICAL} and not item.resolved
    ]
    if high and not state.get("auto_approve"):
        return False, "high-impact ambiguity requires clarification approval"
    return True, "intake accepted"


def design_gate(state: WorkflowState) -> tuple[bool, str]:
    design = state.get("design")
    if design is None:
        return False, "design artifact is missing"
    if not design.api_impact or not design.data_impact or not design.security_impact:
        return False, "design must cover API, data, and security impact"
    return True, "design accepted"


def development_gate(state: WorkflowState) -> tuple[bool, str]:
    if not state.get("task_plan"):
        return False, "task plan is missing"
    return True, "development branch accepted"


def validation_gate(result: ValidationResult) -> tuple[bool, str]:
    if result.passed and result.coverage_percent >= 85 and result.security_passed:
        return True, "validation passed"
    return False, "; ".join(result.failures) or "mandatory validation failed"


def security_gate(state: WorkflowState) -> tuple[bool, str]:
    blocking = [
        item for item in state.get("security_findings", []) if item.blocking and not item.resolved
    ]
    return (False, "blocking security finding remains") if blocking else (True, "security accepted")


def release_gate(state: WorkflowState) -> tuple[bool, str]:
    validation = state.get("validation")
    if validation is None:
        return False, "validation result is missing"
    return validation_gate(validation)
