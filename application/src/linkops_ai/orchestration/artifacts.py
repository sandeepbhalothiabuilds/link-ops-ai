from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path
from typing import Any

from .models import ArtifactRef


class ArtifactStore:
    def __init__(self, workspace: str | Path, run_id: str) -> None:
        self.workspace = Path(workspace).resolve()
        self.run_id = re.sub(r"[^a-zA-Z0-9_-]", "-", run_id)
        self.root = (self.workspace / "artifacts" / self.run_id).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def write_text(
        self,
        relative_path: str,
        content: str,
        artifact_version: int = 1,
        input_hashes: dict[str, str] | None = None,
    ) -> ArtifactRef:
        target = self._safe_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        digest = sha256(content.encode("utf-8")).hexdigest()
        return ArtifactRef(
            path=str(target.relative_to(self.workspace)),
            content_hash=digest,
            artifact_version=artifact_version,
            input_hashes=input_hashes or {},
        )

    def write_json(
        self,
        relative_path: str,
        value: Any,
        artifact_version: int = 1,
        input_hashes: dict[str, str] | None = None,
    ) -> ArtifactRef:
        content = json.dumps(value, indent=2, default=_json_default, sort_keys=True) + "\n"
        return self.write_text(relative_path, content, artifact_version, input_hashes)

    def read_text(self, relative_path: str) -> str:
        return self._safe_path(relative_path).read_text(encoding="utf-8")

    def _safe_path(self, relative_path: str) -> Path:
        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("artifact path escapes the run directory")
        # The artifact API accepts only relative paths and rejects traversal before
        # touching the filesystem. Avoid resolving a concurrently-created OneDrive
        # directory here; the run root itself is already resolved and trusted.
        return self.root / relative


def _json_default(value: Any) -> str:
    if hasattr(value, "model_dump"):
        return json.dumps(value.model_dump(), default=_json_default)
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return str(value)
