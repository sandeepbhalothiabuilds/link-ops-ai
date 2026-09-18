from __future__ import annotations

from pathlib import Path
from typing import Any

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_apigatewayv2 as apigwv2,
)
from aws_cdk import (
    aws_apigatewayv2_integrations as integrations,
)
from aws_cdk import (
    aws_cloudwatch as cloudwatch,
)
from aws_cdk import (
    aws_dynamodb as dynamodb,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as lambda_,
)
from aws_cdk import (
    aws_lambda_event_sources as event_sources,
)
from aws_cdk import (
    aws_logs as logs,
)
from aws_cdk import (
    aws_s3 as s3,
)
from aws_cdk import (
    aws_s3_deployment as s3deploy,
)
from aws_cdk import (
    aws_sqs as sqs,
)
from constructs import Construct


class LinkOpsProductStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        retain = RemovalPolicy.RETAIN

        self.links_table = dynamodb.Table(
            self,
            "LinksTable",
            table_name=f"linkops-links-{environment_name}",
            partition_key=dynamodb.Attribute(name="slug", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            time_to_live_attribute="ttl_epoch",
            removal_policy=retain,
        )
        self.links_table.add_global_secondary_index(
            index_name="idempotency-key-index",
            partition_key=dynamodb.Attribute(
                name="idempotency_key_hash", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )
        self.analytics_table = dynamodb.Table(
            self,
            "AnalyticsTable",
            table_name=f"linkops-analytics-{environment_name}",
            partition_key=dynamodb.Attribute(name="slug", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="bucket", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=retain,
        )
        self.click_dlq = sqs.Queue(
            self,
            "ClickEventsDlq",
            queue_name=f"linkops-click-events-dlq-{environment_name}",
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            retention_period=Duration.days(14),
        )
        self.click_queue = sqs.Queue(
            self,
            "ClickEvents",
            queue_name=f"linkops-click-events-{environment_name}",
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            visibility_timeout=Duration.seconds(120),
            dead_letter_queue=sqs.DeadLetterQueue(queue=self.click_dlq, max_receive_count=5),
            retention_period=Duration.days(4),
        )

        log_group = logs.LogGroup(
            self,
            "ProductLogGroup",
            log_group_name=f"/aws/lambda/linkops-product-{environment_name}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=retain,
        )
        product_code = Path(
            str(self.node.try_get_context("productCodePath") or "lambda_code")
        ).resolve()
        product_role = iam.Role(
            self,
            "ProductLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )
        self.links_table.grant_read_write_data(product_role)
        self.analytics_table.grant_read_write_data(product_role)
        self.click_queue.grant_send_messages(product_role)
        function = lambda_.Function(
            self,
            "ProductFunction",
            function_name=f"linkops-product-{environment_name}",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(str(product_code)),
            role=product_role,
            timeout=Duration.seconds(15),
            memory_size=512,
            environment={
                "LINKOPS_ENVIRONMENT": "aws",
                "LINKOPS_STORAGE_BACKEND": "aws",
                "LINKOPS_BASE_URL": "https://replace-with-api-domain",
                "LINKOPS_LINKS_TABLE_NAME": self.links_table.table_name,
                "LINKOPS_ANALYTICS_TABLE_NAME": self.analytics_table.table_name,
                "LINKOPS_ANALYTICS_QUEUE_URL": self.click_queue.queue_url,
            },
            log_group=log_group,
        )
        api = apigwv2.HttpApi(self, "ProductHttpApi", api_name=f"linkops-{environment_name}")
        integration = integrations.HttpLambdaIntegration("ProductIntegration", function)
        api.add_routes(path="/{proxy+}", methods=[apigwv2.HttpMethod.ANY], integration=integration)
        api.add_routes(path="/", methods=[apigwv2.HttpMethod.ANY], integration=integration)
        function.add_environment("LINKOPS_BASE_URL", api.api_endpoint)

        worker_role = iam.Role(
            self,
            "AnalyticsWorkerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )
        self.analytics_table.grant_write_data(worker_role)
        worker = lambda_.Function(
            self,
            "AnalyticsWorker",
            function_name=f"linkops-analytics-worker-{environment_name}",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.analytics_handler",
            code=lambda_.Code.from_asset(str(product_code)),
            role=worker_role,
            timeout=Duration.seconds(60),
            environment={"LINKOPS_ANALYTICS_TABLE_NAME": self.analytics_table.table_name},
        )
        worker.add_event_source(
            event_sources.SqsEventSource(
                self.click_queue, batch_size=10, report_batch_item_failures=True
            )
        )

        dashboard = cloudwatch.Dashboard(
            self, "ProductDashboard", dashboard_name=f"linkops-{environment_name}"
        )
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Product Lambda errors", left=[function.metric_errors()], width=12
            ),
            cloudwatch.GraphWidget(
                title="Analytics queue age",
                left=[self.click_queue.metric_approximate_age_of_oldest_message()],
                width=12,
            ),
        )
        cloudwatch.Alarm(
            self,
            "DeadLetterAlarm",
            metric=self.click_dlq.metric_number_of_messages_received(),
            threshold=1,
            evaluation_periods=1,
            alarm_description="Click events reached the dead-letter queue.",
        )

        self.artifact_bucket = s3.Bucket(
            self,
            "WorkflowArtifactsBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            versioned=True,
            removal_policy=retain,
        )
        seed_path = Path(
            str(self.node.try_get_context("knowledgeSeedPath") or "seed_knowledge")
        ).resolve()
        if seed_path.exists():
            s3deploy.BucketDeployment(
                self,
                "KnowledgeSeedDeployment",
                sources=[s3deploy.Source.asset(str(seed_path))],
                destination_bucket=self.artifact_bucket,
            )

        CfnOutput(self, "ProductApiUrl", value=api.api_endpoint)
        CfnOutput(self, "LinksTableName", value=self.links_table.table_name)
        CfnOutput(self, "AnalyticsTableName", value=self.analytics_table.table_name)
        CfnOutput(self, "ClickQueueUrl", value=self.click_queue.queue_url)
        CfnOutput(self, "ArtifactBucketName", value=self.artifact_bucket.bucket_name)
