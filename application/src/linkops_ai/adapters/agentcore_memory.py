from __future__ import annotations

from typing import Any

import boto3


class AgentCoreMemoryAdapter:
    """Optional session-memory adapter; canonical workflow state remains LangGraph checkpoints."""

    def __init__(self, memory_id: str, region: str) -> None:
        self.memory_id = memory_id
        self.client = boto3.client("bedrock-agentcore", region_name=region)

    def record_event(
        self, actor_id: str, session_id: str, content: str, metadata: dict[str, Any]
    ) -> None:
        self.client.create_event(
            memoryId=self.memory_id,
            actorId=actor_id,
            sessionId=session_id,
            eventTimestamp=__import__("datetime").datetime.now(__import__("datetime").UTC),
            payload=[{"conversational": {"role": "ASSISTANT", "content": {"text": content}}}],
            clientToken=f"{session_id}-{actor_id}",
        )

    def retrieve(self, actor_id: str, session_id: str, namespace: str) -> list[dict[str, Any]]:
        response = self.client.retrieve_memory_records(
            memoryId=self.memory_id,
            namespace=namespace,
            searchCriteria={"searchQuery": session_id, "topK": 10},
        )
        records = response.get("memoryRecordSummaries", [])
        return records if isinstance(records, list) else []
