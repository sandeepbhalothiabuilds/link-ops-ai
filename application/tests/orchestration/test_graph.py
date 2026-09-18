from pathlib import Path

from linkops_ai.orchestration.runner import WorkflowRunner


def test_greenfield_graph_completes_with_artifacts(tmp_path: Path) -> None:
    result = WorkflowRunner(tmp_path).run(
        "Build the URL shortener.", "greenfield", auto_approve=True
    )
    assert result.status == "COMPLETE"
    assert "manifest" in result.state["artifacts"]
    assert (tmp_path / "artifacts" / result.run_id / "audit" / "audit.ndjson").exists()


def test_brownfield_graph_includes_impact_artifact(tmp_path: Path) -> None:
    result = WorkflowRunner(tmp_path).run(
        "Enhance the existing service.", "brownfield", auto_approve=True
    )
    assert result.status == "COMPLETE"
    assert "codebase_impact" in result.state["artifacts"]


def test_ambiguous_graph_waits_then_requires_two_more_gates(tmp_path: Path) -> None:
    runner = WorkflowRunner(tmp_path)
    requirement = "Make analytics privacy-friendly and near real time."
    result = runner.run(requirement, "ambiguous", run_id="ambiguous-test")
    assert result.status == "WAITING_APPROVAL"
    assert result.state["approval_gate"] == "requirements"
    result = runner.resume("ambiguous-test", requirement, "ambiguous", "requirements")
    assert result.status == "WAITING_APPROVAL"
    assert result.state["approval_gate"] == "architecture"
    result = runner.resume("ambiguous-test", requirement, "ambiguous", "architecture")
    assert result.status == "WAITING_APPROVAL"
    assert result.state["approval_gate"] == "release"
    result = runner.resume("ambiguous-test", requirement, "ambiguous", "release")
    assert result.status == "COMPLETE"


def test_recoverable_validation_failure_repairs_with_bounded_retry(tmp_path: Path) -> None:
    result = WorkflowRunner(tmp_path).run(
        "Build the URL shortener.", "greenfield", auto_approve=True, inject_failure=True
    )
    assert result.status == "COMPLETE"
    assert result.state["repair_attempts"] == 1


def test_critical_security_finding_safe_stops(tmp_path: Path) -> None:
    result = WorkflowRunner(tmp_path).run(
        "Build the URL shortener.", "greenfield", auto_approve=True, inject_security_failure=True
    )
    assert result.status == "SAFE_STOP"


def test_replan_marks_only_downstream_work_stale(tmp_path: Path) -> None:
    runner = WorkflowRunner(tmp_path)
    result = runner.run(
        "Build the URL shortener.", "greenfield", auto_approve=True, run_id="replan-test"
    )
    replanned = runner.replan("replan-test", ["T-DESIGN"])
    assert result.status == "COMPLETE"
    assert replanned.status == "REPLANNED"
    assert replanned.state["metrics"]["invalidated_task_count"] == 5
    assert (tmp_path / "artifacts" / "replan-test" / "replan" / "plan_diff.json").exists()
