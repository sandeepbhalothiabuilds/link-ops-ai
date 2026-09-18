from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import boto3
from pydantic import BaseModel, Field


class KnowledgeReference(BaseModel):
    source: str
    uri: str | None = None
    snippet: str
    relevance_score: float | None = None
    knowledge_base_id: str | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BedrockKnowledgeBaseRetriever:
    def __init__(
        self, knowledge_base_id: str, region: str, data_source_id: str | None = None
    ) -> None:
        self.knowledge_base_id = knowledge_base_id
        self.data_source_id = data_source_id
        self.client = boto3.client("bedrock-agent-runtime", region_name=region)

    def retrieve_engineering_guidance(
        self, query: str, domains: list[str] | None = None, top_k: int = 5
    ) -> list[KnowledgeReference]:
        filters: dict[str, Any] | None = None
        if domains:
            filters = {"in": {"key": "domain", "value": domains}}
        kwargs: dict[str, Any] = {
            "knowledgeBaseId": self.knowledge_base_id,
            "retrievalQuery": {"text": query},
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {"numberOfResults": max(1, min(top_k, 20))}
            },
        }
        if filters:
            kwargs["retrievalConfiguration"]["vectorSearchConfiguration"]["filter"] = filters
        response = self.client.retrieve(**kwargs)
        references: list[KnowledgeReference] = []
        for item in response.get("retrievalResults", []):
            location = item.get("location", {})
            s3 = location.get("s3Location", {})
            references.append(
                KnowledgeReference(
                    source=s3.get("uri", "bedrock-knowledge-base"),
                    uri=s3.get("uri"),
                    snippet=item.get("content", {}).get("text", ""),
                    relevance_score=item.get("score"),
                    knowledge_base_id=self.knowledge_base_id,
                )
            )
        return references


class BedrockChatModel:
    """Small Converse wrapper used by optional model-backed agents."""

    def __init__(self, model_id: str, region: str, max_tokens: int = 4096) -> None:
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.client = boto3.client("bedrock-runtime", region_name=region)

    def invoke(self, system: str, user: str) -> str:
        response = self.client.converse(
            modelId=self.model_id,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": user}]}],
            inferenceConfig={"maxTokens": self.max_tokens, "temperature": 0},
        )
        content = response.get("output", {}).get("message", {}).get("content", [])
        return "\n".join(item.get("text", "") for item in content)
