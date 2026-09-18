from __future__ import annotations

from ..adapters.aws_product import DynamoAnalyticsRepository
from .analytics import AnalyticsProcessor
from .config import get_settings
from .domain import ClickEvent


def lambda_handler(event: dict[str, object], _context: object) -> dict[str, list[dict[str, str]]]:
    processor = AnalyticsProcessor(DynamoAnalyticsRepository(get_settings()))
    failures: list[dict[str, str]] = []
    records = event.get("Records", [])
    if not isinstance(records, list):
        return {"batchItemFailures": failures}
    for record in records:
        if not isinstance(record, dict):
            continue
        message_id = str(record.get("messageId", "unknown"))
        try:
            body = record.get("body", "")
            processor.process(
                [
                    ClickEvent.model_validate_json(body)
                    if isinstance(body, str)
                    else ClickEvent.model_validate(body)
                ]
            )
        except Exception:
            failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": failures}
