from __future__ import annotations

import os
from pathlib import Path

from linkops_ai.orchestration.runner import WorkflowRunner


def handler(payload: dict[str, object]) -> dict[str, object]:
    requirement = payload.get("requirement")
    scenario = payload.get("scenario", "greenfield")
    if not isinstance(requirement, str) or not requirement.strip():
        return {"status": "error", "detail": "requirement must be a non-empty string"}
    if not isinstance(scenario, str):
        return {"status": "error", "detail": "scenario must be a string"}
    workspace = Path(os.environ.get("LINKOPS_WORKSPACE", "/tmp/linkops-workspace"))
    result = WorkflowRunner(workspace).run(
        requirement,
        scenario,
        auto_approve=bool(payload.get("auto_approve", False)),
    )
    return result.model_dump(mode="json")
