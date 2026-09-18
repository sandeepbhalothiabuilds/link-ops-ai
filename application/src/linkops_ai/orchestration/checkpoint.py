from __future__ import annotations

from pathlib import Path
from typing import Any


def local_checkpointer() -> Any:
    from langgraph.checkpoint.memory import MemorySaver

    return MemorySaver()


def checkpoint_metadata(run_id: str, workspace: str | Path) -> dict[str, str]:
    return {"thread_id": run_id, "artifact_workspace": str(Path(workspace).resolve())}
