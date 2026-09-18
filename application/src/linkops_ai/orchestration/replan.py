from __future__ import annotations

from collections.abc import Iterable
from hashlib import sha256

from .models import TaskPlan


def content_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def invalidate_downstream(plan: TaskPlan, changed_task_ids: Iterable[str]) -> TaskPlan:
    changed = set(changed_task_ids)
    invalidated = set(changed)
    changed_again = True
    while changed_again:
        changed_again = False
        for task in plan.tasks:
            if task.task_id in invalidated:
                continue
            if any(dep in invalidated for dep in task.dependencies):
                invalidated.add(task.task_id)
                changed_again = True
    tasks = [
        task.model_copy(update={"status": "STALE" if task.task_id in invalidated else task.status})
        for task in plan.tasks
    ]
    return plan.model_copy(update={"plan_version": plan.plan_version + 1, "tasks": tasks})


def plan_diff(before: TaskPlan, after: TaskPlan) -> dict[str, list[str]]:
    old = {task.task_id: task.status for task in before.tasks}
    new = {task.task_id: task.status for task in after.tasks}
    return {
        "stale": sorted(
            task_id
            for task_id, status in new.items()
            if status == "STALE" and old.get(task_id) != "STALE"
        ),
        "added": sorted(set(new) - set(old)),
        "removed": sorted(set(old) - set(new)),
    }
