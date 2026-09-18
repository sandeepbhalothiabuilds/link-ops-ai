from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any


def summarize_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    durations = [int(event.get("duration_ms", 0)) for event in events]
    failures = sum(event.get("result_status") in {"failure", "blocked"} for event in events)
    retries = sum(int(event.get("retry_count", 0)) for event in events)
    return {
        "event_count": len(events),
        "node_success_count": len(events) - failures,
        "node_failure_count": failures,
        "retry_count": retries,
        "mean_node_latency_ms": mean(durations) if durations else 0,
        "max_node_latency_ms": max(durations, default=0),
    }


def write_metrics(path: str | Path, events: list[dict[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(summarize_metrics(events), indent=2) + "\n", encoding="utf-8")
