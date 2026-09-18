from __future__ import annotations

import json
from pathlib import Path

from .models import AuditEvent


class AuditEmitter:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: AuditEvent) -> None:
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(event.model_dump_json() + "\n")

    def read_all(self) -> list[AuditEvent]:
        if not self.path.exists():
            return []
        return [
            AuditEvent.model_validate(json.loads(line))
            for line in self.path.read_text().splitlines()
            if line
        ]
