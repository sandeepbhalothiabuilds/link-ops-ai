from __future__ import annotations

from pathlib import Path

PROTECTED_PATH_PARTS = {".env", ".aws", ".ssh", "credentials", "id_rsa", "*.pem", "*.key"}
PROTECTED_TOOLS = {"git_push", "deploy_environment", "rollback_environment"}


def resolve_workspace_path(workspace: str | Path, requested: str, write: bool = False) -> Path:
    root = Path(workspace).resolve()
    target = (root / requested).resolve()
    if root not in target.parents and target != root:
        raise PermissionError("path escapes configured workspace")
    if any(
        part.lower() in {".git", ".aws", ".ssh", ".env", "credentials"} for part in target.parts
    ):
        raise PermissionError("protected path is not accessible to workflow tools")
    if write and target.name.lower() in {"id_rsa", "credentials"}:
        raise PermissionError("credential path is not writable")
    return target


def can_execute(tool_name: str, approved: bool = False) -> bool:
    return tool_name not in PROTECTED_TOOLS or approved
