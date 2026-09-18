from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from .models import (
    AcceptanceCriterion,
    Ambiguity,
    CodebaseImpact,
    DesignDocument,
    NormalizedRequirement,
    PlannedTask,
    ScenarioType,
    SecurityFinding,
    Severity,
    TaskPlan,
    TaskRisk,
    ValidationResult,
)


class RequirementsAgent:
    """Deterministic baseline agent; a Bedrock-backed implementation can replace it."""

    def normalize(self, raw_requirement: str, scenario: str) -> NormalizedRequirement:
        text = raw_requirement.strip()
        lower = text.lower()
        selected = ScenarioType(scenario)
        ambiguities: list[Ambiguity] = []
        assumptions = ["The initial deployment is single-region and human-approved."]
        if (
            selected == ScenarioType.AMBIGUOUS
            or "privacy-friendly" in lower
            or "near real time" in lower
        ):
            ambiguities.append(
                Ambiguity(
                    question=(
                        "What retention period and aggregation granularity define acceptable "
                        "privacy and freshness?"
                    ),
                    impact=(
                        "This affects the analytics schema, privacy policy, and operational cost."
                    ),
                    severity=Severity.HIGH,
                )
            )
        if "existing" in lower or selected == ScenarioType.BROWNFIELD:
            intent = (
                "Safely enhance the existing URL-shortener codebase while preserving "
                "compatible behavior."
            )
        else:
            intent = (
                "Deliver a production-style URL-shortener capability with governed "
                "engineering evidence."
            )
        functional = [
            "Create HTTP/HTTPS short links with generated or custom aliases.",
            "Resolve active aliases with a low-latency HTTP redirect.",
            "Support metadata, soft deletion, expiration, and aggregate click analytics.",
        ]
        non_functional = [
            "Preserve privacy by storing aggregate analytics and no raw IP addresses.",
            (
                "Use deterministic validation, audit events, bounded retries, and human "
                "approval for high-impact actions."
            ),
        ]
        criteria = [
            AcceptanceCriterion(
                criterion_id="AC-01",
                statement="A valid HTTP/HTTPS URL can be shortened.",
                validation="API functional test",
            ),
            AcceptanceCriterion(
                criterion_id="AC-02",
                statement="Unknown and inactive aliases do not redirect.",
                validation="API edge-case test",
            ),
            AcceptanceCriterion(
                criterion_id="AC-03",
                statement="Expiration is enforced synchronously.",
                validation="expiry unit test",
            ),
            AcceptanceCriterion(
                criterion_id="AC-04",
                statement="Click analytics are emitted asynchronously and privacy-safe.",
                validation="worker and privacy tests",
            ),
            AcceptanceCriterion(
                criterion_id="AC-05",
                statement="The workflow emits traceable artifacts and stops at approval gates.",
                validation="orchestration test",
            ),
        ]
        return NormalizedRequirement(
            title="Governed URL-shortener delivery",
            intent=intent,
            scenario_type=selected,
            functional_requirements=functional,
            non_functional_requirements=non_functional,
            constraints=[
                "Python 3.12",
                "FastAPI",
                "LangGraph",
                "AWS adapters must be configurable",
            ],
            exclusions=["Custom domains", "Billing", "Autonomous production deployment"],
            acceptance_criteria=criteria,
            assumptions=assumptions,
            ambiguities=ambiguities,
        )


class PlannerAgent:
    def plan(self, requirement: NormalizedRequirement) -> TaskPlan:
        tasks = [
            PlannedTask(
                task_id="T-REQ",
                title="Normalize requirements",
                owner="requirements",
                risk=TaskRisk.LOW,
                validation=["intake gate"],
            ),
        ]
        if requirement.scenario_type == ScenarioType.BROWNFIELD:
            tasks.append(
                PlannedTask(
                    task_id="T-REPO",
                    title="Analyze existing codebase",
                    owner="codebase",
                    dependencies=["T-REQ"],
                    risk=TaskRisk.MEDIUM,
                    validation=["repository map exists"],
                    expected_outputs=["codebase_impact.md", "repo_map.json"],
                )
            )
            design_dependencies = ["T-REPO"]
        else:
            design_dependencies = ["T-REQ"]
        tasks.extend(
            [
                PlannedTask(
                    task_id="T-DESIGN",
                    title="Produce architecture design",
                    owner="architecture",
                    dependencies=design_dependencies,
                    risk=TaskRisk.HIGH,
                    validation=["design gate"],
                    expected_outputs=["design.md"],
                ),
                PlannedTask(
                    task_id="T-DEV",
                    title="Implement bounded change",
                    owner="development",
                    dependencies=["T-DESIGN"],
                    risk=TaskRisk.HIGH,
                    validation=["targeted tests"],
                ),
                PlannedTask(
                    task_id="T-QA",
                    title="Specify and run tests",
                    owner="qa",
                    dependencies=["T-DESIGN"],
                    validation=["coverage >= 85"],
                ),
                PlannedTask(
                    task_id="T-SEC",
                    title="Review security and privacy",
                    owner="security",
                    dependencies=["T-DESIGN"],
                    validation=["no blocking findings"],
                ),
                PlannedTask(
                    task_id="T-DOCS",
                    title="Assemble release evidence",
                    owner="release",
                    dependencies=["T-DEV", "T-QA", "T-SEC"],
                    validation=["artifact manifest"],
                ),
            ]
        )
        return TaskPlan(tasks=tasks)


class CodebaseAnalyst:
    def analyze(self, repository_path: str) -> CodebaseImpact:
        root = Path(repository_path).resolve()
        files: list[str] = []
        modules: list[str] = []
        routes: list[str] = []
        tests: list[str] = []
        for path in root.rglob("*.py"):
            if any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
                continue
            relative = str(path.relative_to(root))
            files.append(relative)
            if "test" in path.name:
                tests.append(relative)
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError):
                continue
            modules.extend(
                node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
            )
            routes.extend(
                node.decorator_list[0].func.attr
                for node in tree.body
                if isinstance(node, ast.FunctionDef)
                and node.decorator_list
                and isinstance(node.decorator_list[0], ast.Call)
                and isinstance(node.decorator_list[0].func, ast.Attribute)
            )
        return CodebaseImpact(
            repository_path=str(root),
            files=sorted(files),
            modules=sorted(set(modules)),
            routes=sorted(set(routes)),
            tests=sorted(tests),
            data_flows=[
                "FastAPI -> LinkService -> repository",
                "redirect -> publisher -> analytics worker",
            ],
            blast_radius="product and orchestration modules are isolated behind typed interfaces",
        )


class DesignAgent:
    def design(
        self, requirement: NormalizedRequirement, impact: CodebaseImpact | None
    ) -> DesignDocument:
        context = "Greenfield design with replaceable local/AWS adapters."
        if impact:
            context = (
                f"Brownfield design based on {len(impact.files)} Python files and "
                f"{len(impact.tests)} tests."
            )
        return DesignDocument(
            title=requirement.title,
            context=context,
            decisions=[
                "Keep redirect resolution independent from analytics persistence.",
                "Use conditional writes for aliases and explicit expiration checks.",
                "Use a typed LangGraph state with deterministic entry/exit gates.",
            ],
            api_impact=["POST /api/v1/links", "GET /{slug}", "GET /api/v1/links/{slug}/analytics"],
            data_impact=["Links keyed by slug; analytics aggregated by hour."],
            security_impact=[
                "Only http/https destinations; no raw IP or full user-agent retention."
            ],
            observability_impact=[
                "Structured audit events with run, node, tool, outcome, and latency."
            ],
            rollback_plan=(
                "Create a Git savepoint before controlled writes; restore it on "
                "unrecoverable validation failure."
            ),
        )


class DevelopmentAgent:
    def execute(self, _requirement: NormalizedRequirement) -> dict[str, Any]:
        return {
            "changed_paths": ["src/linkops_ai/product", "src/linkops_ai/orchestration"],
            "savepoint": "local-demo-savepoint",
        }


class QAAgent:
    def specify(self, requirement: NormalizedRequirement) -> dict[str, Any]:
        return {
            "suites": ["unit", "integration", "functional", "orchestration", "security"],
            "coverage_target": 85,
            "acceptance_criteria": [item.model_dump() for item in requirement.acceptance_criteria],
        }

    def validate(self, inject_failure: bool = False, repair_attempts: int = 0) -> ValidationResult:
        if inject_failure and repair_attempts == 0:
            return ValidationResult(
                passed=False,
                tests_passed=8,
                tests_failed=1,
                coverage_percent=82,
                failures=["injected recoverable test failure"],
            )
        return ValidationResult(passed=True, tests_passed=42, coverage_percent=91.0)


class SecurityAgent:
    def review(self, inject_failure: bool = False) -> list[SecurityFinding]:
        if inject_failure:
            return [
                SecurityFinding(
                    severity=Severity.CRITICAL,
                    title="Injected policy failure",
                    detail="Protected action attempted without a valid approval record.",
                    blocking=True,
                )
            ]
        return []


class ReleaseAgent:
    def summarize(self, state: dict[str, Any]) -> dict[str, Any]:
        validation = state.get("validation")
        security = state.get("security_findings", [])
        ready = bool(
            validation and validation.passed and not any(item.blocking for item in security)
        )
        return {
            "recommendation": "ready" if ready else "not_ready",
            "rationale": [
                "All mandatory local gates passed."
                if ready
                else "A mandatory gate remains unresolved."
            ],
            "risks": ["AWS managed-service behavior still requires environment validation."],
            "assumptions": state.get("assumptions", []),
            "limitations": ["Single-region prototype; aggregate analytics only."],
        }
