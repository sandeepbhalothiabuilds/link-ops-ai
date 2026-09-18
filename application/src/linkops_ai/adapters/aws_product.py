from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from linkops_ai.product.config import Settings
from linkops_ai.product.domain import AnalyticsBucket, ClickEvent, Link
from linkops_ai.product.exceptions import AliasAlreadyExists, LinkNotFound, PersistenceUnavailable
from linkops_ai.product.repositories import AnalyticsRepository, EventPublisher, LinkRepository
from linkops_ai.product.services import LinkService


class DynamoLinkRepository(LinkRepository):
    def __init__(self, settings: Settings) -> None:
        self.table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(
            settings.links_table_name
        )

    def put_if_absent(self, link: Link) -> None:
        item = link.model_dump(mode="json")
        if link.expires_at:
            item["expires_at"] = link.expires_at.isoformat()
        try:
            self.table.put_item(Item=item, ConditionExpression="attribute_not_exists(slug)")
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                raise AliasAlreadyExists(link.slug) from exc
            raise PersistenceUnavailable("DynamoDB write failed") from exc
        except BotoCoreError as exc:
            raise PersistenceUnavailable("DynamoDB is unavailable") from exc

    def get(self, slug: str) -> Link | None:
        try:
            response = self.table.get_item(Key={"slug": slug}, ConsistentRead=True)
        except (BotoCoreError, ClientError) as exc:
            raise PersistenceUnavailable("DynamoDB read failed") from exc
        item = response.get("Item")
        return _link_from_item(item) if item else None

    def get_by_idempotency_hash(self, key_hash: str) -> Link | None:
        try:
            response = self.table.query(
                IndexName="idempotency-key-index",
                KeyConditionExpression="idempotency_key_hash = :key",
                ExpressionAttributeValues={":key": key_hash},
                Limit=1,
            )
        except ClientError as exc:
            # The index is optional for existing tables; a missing index means no
            # idempotent replay can be resolved by this adapter.
            if exc.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                return None
            raise PersistenceUnavailable("DynamoDB idempotency lookup failed") from exc
        except BotoCoreError as exc:
            raise PersistenceUnavailable("DynamoDB idempotency lookup failed") from exc
        items = response.get("Items", [])
        return _link_from_item(items[0]) if items else None

    def soft_delete(self, slug: str, updated_at: datetime) -> Link:
        try:
            response = self.table.update_item(
                Key={"slug": slug},
                UpdateExpression=(
                    "SET #status = :deleted, updated_at = :updated, version = version + :one"
                ),
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":deleted": "deleted",
                    ":updated": updated_at.isoformat(),
                    ":one": 1,
                },
                ConditionExpression="attribute_exists(slug)",
                ReturnValues="ALL_NEW",
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                raise LinkNotFound(slug) from exc
            raise PersistenceUnavailable("DynamoDB delete failed") from exc
        except BotoCoreError as exc:
            raise PersistenceUnavailable("DynamoDB delete failed") from exc
        return _link_from_item(response["Attributes"])

    def is_ready(self) -> bool:
        try:
            self.table.meta.client.describe_table(TableName=self.table.name)
            return True
        except (BotoCoreError, ClientError):
            return False


class DynamoAnalyticsRepository(AnalyticsRepository):
    def __init__(self, settings: Settings) -> None:
        self.table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(
            settings.analytics_table_name
        )

    def increment(self, event: ClickEvent) -> AnalyticsBucket:
        occurred = event.occurred_at.astimezone(UTC)
        bucket = occurred.strftime("%Y-%m-%d-%H")
        try:
            self.table.update_item(
                Key={"slug": event.slug, "bucket": bucket},
                UpdateExpression=(
                    "SET #count = if_not_exists(#count, :zero) + :one, "
                    "#last = :last, "
                    "#refs = if_not_exists(#refs, :empty_map), "
                    "#agents = if_not_exists(#agents, :empty_map)"
                ),
                ExpressionAttributeNames={
                    "#count": "click_count",
                    "#last": "last_click_at",
                    "#refs": "referrer_counts",
                    "#agents": "user_agent_counts",
                },
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":one": 1,
                    ":last": occurred.isoformat(),
                    ":empty_map": {},
                },
            )
            self.table.update_item(
                Key={"slug": event.slug, "bucket": bucket},
                UpdateExpression=(
                    "SET #agents.#agent = if_not_exists(#agents.#agent, :zero) + :one"
                ),
                ExpressionAttributeNames={
                    "#agents": "user_agent_counts",
                    "#agent": event.user_agent_category,
                },
                ExpressionAttributeValues={":zero": 0, ":one": 1},
            )
            if event.referrer_host:
                self.table.update_item(
                    Key={"slug": event.slug, "bucket": bucket},
                    UpdateExpression=(
                        "SET #refs.#ref = if_not_exists(#refs.#ref, :zero) + :one"
                    ),
                    ExpressionAttributeNames={
                        "#refs": "referrer_counts",
                        "#ref": event.referrer_host,
                    },
                    ExpressionAttributeValues={":zero": 0, ":one": 1},
                )
        except (BotoCoreError, ClientError) as exc:
            raise PersistenceUnavailable("DynamoDB analytics write failed") from exc
        referrer_counts = {event.referrer_host: 1} if event.referrer_host else {}
        return AnalyticsBucket(
            slug=event.slug,
            bucket=bucket,
            click_count=1,
            referrer_counts=referrer_counts,
            user_agent_counts={event.user_agent_category: 1},
            last_click_at=occurred,
        )

    def list_for_slug(self, slug: str) -> list[AnalyticsBucket]:
        try:
            response = self.table.query(
                KeyConditionExpression="slug = :slug", ExpressionAttributeValues={":slug": slug}
            )
        except (BotoCoreError, ClientError) as exc:
            raise PersistenceUnavailable("DynamoDB analytics read failed") from exc
        return [AnalyticsBucket.model_validate(item) for item in response.get("Items", [])]

    def is_ready(self) -> bool:
        try:
            self.table.meta.client.describe_table(TableName=self.table.name)
            return True
        except (BotoCoreError, ClientError):
            return False


class SqsEventPublisher(EventPublisher):
    def __init__(self, settings: Settings) -> None:
        if not settings.analytics_queue_url:
            raise ValueError("LINKOPS_ANALYTICS_QUEUE_URL is required for SQS publishing")
        self.client = boto3.client("sqs", region_name=settings.aws_region)
        self.queue_url = settings.analytics_queue_url

    def publish(self, event: ClickEvent) -> None:
        try:
            self.client.send_message(QueueUrl=self.queue_url, MessageBody=event.model_dump_json())
        except (BotoCoreError, ClientError) as exc:
            raise PersistenceUnavailable("SQS analytics publish failed") from exc

    def is_ready(self) -> bool:
        try:
            self.client.get_queue_attributes(QueueUrl=self.queue_url, AttributeNames=["QueueArn"])
            return True
        except (BotoCoreError, ClientError):
            return False


def _link_from_item(item: dict[str, Any]) -> Link:
    value = dict(item)
    for field in ("created_at", "updated_at", "expires_at"):
        if value.get(field):
            value[field] = datetime.fromisoformat(str(value[field]).replace("Z", "+00:00"))
    return Link.model_validate(value)


def build_aws_service(settings: Settings) -> LinkService:
    return LinkService(
        DynamoLinkRepository(settings),
        DynamoAnalyticsRepository(settings),
        SqsEventPublisher(settings),
        settings,
    )
