from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitSavepoint:
    head: str
    status: str


class GitRecovery:
    """Deterministic savepoint/restore primitive for controlled workspace writes."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).resolve()

    def create_savepoint(self) -> GitSavepoint:
        status = self._run("status", "--porcelain")
        head = self._run("rev-parse", "HEAD").strip()
        return GitSavepoint(head=head, status=status)

    def restore(self, savepoint: GitSavepoint, *, allow_destructive: bool = False) -> None:
        if not allow_destructive:
            raise PermissionError("restore requires explicit destructive-action approval")
        self._run("restore", "--source", savepoint.head, "--staged", "--worktree", "--", ".")

    def _run(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
        return result.stdout
