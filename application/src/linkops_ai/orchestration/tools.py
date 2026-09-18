from __future__ import annotations

import ast
import subprocess
from pathlib import Path

from .policy import resolve_workspace_path


class WorkspaceTools:
    """Narrow repository tools used by agents and safe to expose through a gateway."""

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).resolve()

    def list_files(self, pattern: str = "*") -> list[str]:
        return sorted(
            str(path.relative_to(self.workspace))
            for path in self.workspace.rglob(pattern)
            if path.is_file()
        )

    def search(self, term: str, pattern: str = "*.py") -> list[str]:
        matches: list[str] = []
        for path in self.workspace.rglob(pattern):
            if path.is_file() and term in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(str(path.relative_to(self.workspace)))
        return sorted(matches)

    def read_file(self, relative_path: str) -> str:
        return resolve_workspace_path(self.workspace, relative_path).read_text(encoding="utf-8")

    def write_file(self, relative_path: str, content: str) -> None:
        target = resolve_workspace_path(self.workspace, relative_path, write=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def ast_map(self, relative_path: str) -> dict[str, list[str]]:
        tree = ast.parse(self.read_file(relative_path))
        return {
            "classes": [node.name for node in tree.body if isinstance(node, ast.ClassDef)],
            "functions": [
                node.name
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            ],
        }

    def diff(self) -> str:
        result = subprocess.run(
            ["git", "diff", "--", "."],
            cwd=self.workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout
