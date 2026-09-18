from __future__ import annotations

import importlib
from typing import Any


def build_checkpointer(settings: Any) -> Any:
    """Return a durable saver when installed, otherwise use LangGraph's memory saver.

    The optional AWS checkpoint package changes its import path across releases. Keeping
    this adapter isolated lets local tests remain deterministic while AWS deployment can
    pin and validate the selected implementation.
    """
    if getattr(settings, "environment", "local") == "aws":
        try:
            module = importlib.import_module("langgraph_checkpoint_aws")
            options: dict[str, Any] = {
                "table_name": settings.checkpoint_table_name,
                "region_name": settings.aws_region,
                "ttl_seconds": 86400 * 7,
                "enable_checkpoint_compression": True,
            }
            if getattr(settings, "artifact_bucket", None):
                options["s3_offload_config"] = {"bucket_name": settings.artifact_bucket}
            return module.DynamoDBSaver(**options)
        except ImportError as exc:
            raise RuntimeError(
                "AWS environment requires the pinned DynamoDB checkpoint package"
            ) from exc
    from langgraph.checkpoint.memory import MemorySaver

    return MemorySaver()
