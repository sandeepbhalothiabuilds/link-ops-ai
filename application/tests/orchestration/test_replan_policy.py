from linkops_ai.orchestration.agents import PlannerAgent, RequirementsAgent
from linkops_ai.orchestration.policy import can_execute, resolve_workspace_path
from linkops_ai.orchestration.replan import content_hash, invalidate_downstream, plan_diff


def test_replan_invalidates_only_downstream_tasks() -> None:
    plan = PlannerAgent().plan(
        RequirementsAgent().normalize("Build the URL shortener.", "greenfield")
    )
    changed = invalidate_downstream(plan, ["T-DESIGN"])
    assert {task.task_id for task in changed.tasks if task.status == "STALE"} == {
        "T-DESIGN",
        "T-DEV",
        "T-QA",
        "T-SEC",
        "T-DOCS",
    }
    assert plan_diff(plan, changed)["stale"]
    assert content_hash("a") != content_hash("b")


def test_workspace_policy_rejects_traversal_and_protected_tools(tmp_path) -> None:
    assert resolve_workspace_path(tmp_path, "src/app.py").name == "app.py"
    try:
        resolve_workspace_path(tmp_path, "../outside.txt")
    except PermissionError:
        pass
    else:
        raise AssertionError("traversal should be rejected")
    assert not can_execute("git_push")
    assert can_execute("git_push", approved=True)
