from datetime import UTC, datetime

import boto3
from moto import mock_aws

from linkops_ai.adapters.aws_product import DynamoAnalyticsRepository
from linkops_ai.product.config import Settings
from linkops_ai.product.domain import ClickEvent


@mock_aws
def test_dynamo_analytics_preserves_privacy_safe_breakdowns() -> None:
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName="analytics",
        KeySchema=[
            {"AttributeName": "slug", "KeyType": "HASH"},
            {"AttributeName": "bucket", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "slug", "AttributeType": "S"},
            {"AttributeName": "bucket", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    repository = DynamoAnalyticsRepository(
        Settings(aws_region="us-east-1", analytics_table_name="analytics")
    )
    event = ClickEvent(
        slug="demo",
        occurred_at=datetime(2026, 9, 18, 12, 30, tzinfo=UTC),
        referrer_host="example.com",
        user_agent_category="browser",
    )

    repository.increment(event)
    repository.increment(event.model_copy(update={"user_agent_category": "bot"}))

    buckets = repository.list_for_slug("demo")

    assert len(buckets) == 1
    assert buckets[0].click_count == 2
    assert buckets[0].referrer_counts == {"example.com": 2}
    assert buckets[0].user_agent_counts == {"browser": 1, "bot": 1}
