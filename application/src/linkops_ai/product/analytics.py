from __future__ import annotations

from collections.abc import Iterable

from .domain import ClickEvent
from .repositories import AnalyticsRepository


class AnalyticsProcessor:
    """Consumes sanitized click events and creates hourly aggregates."""

    def __init__(self, repository: AnalyticsRepository) -> None:
        self.repository = repository

    def process(self, events: Iterable[ClickEvent]) -> int:
        processed = 0
        for event in events:
            self.repository.increment(event)
            processed += 1
        return processed


def lambda_handler(
    event: dict[str, object], _context: object, processor: AnalyticsProcessor
) -> dict[str, int]:
    records = event.get("Records", [])
    if not isinstance(records, list):
        return {"processed": 0}
    events = []
    for record in records:
        if not isinstance(record, dict) or "body" not in record:
            continue
        body = record["body"]
        events.append(
            ClickEvent.model_validate_json(body)
            if isinstance(body, str)
            else ClickEvent.model_validate(body)
        )
    return {"processed": processor.process(events)}
