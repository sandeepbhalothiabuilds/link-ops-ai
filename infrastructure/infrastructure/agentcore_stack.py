from __future__ import annotations

from pathlib import Path
from typing import Any

from aws_cdk import CfnOutput, CfnResource, RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3_assets as s3_assets
from constructs import Construct

from .product_stack import LinkOpsProductStack


class LinkOpsAgentCoreStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        product_stack: LinkOpsProductStack,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        runtime_code_path = Path(
            str(self.node.try_get_context("agentcoreCodePath") or "runtime/code")
        ).resolve()
        code_asset = s3_assets.Asset(self, "AgentCoreCode", path=str(runtime_code_path))
        checkpoint_table = self._checkpoint_table(environment_name)

        runtime_role = iam.Role(
            self,
            "AgentCoreRuntimeRole",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
        )
        runtime_role.add_to_policy(
            iam.PolicyStatement(
                actions=["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                resources=["*"],
            )
        )
        product_stack.links_table.grant_read_write_data(runtime_role)
        product_stack.analytics_table.grant_read_write_data(runtime_role)
        product_stack.artifact_bucket.grant_read_write(runtime_role)
        checkpoint_table.grant_read_write_data(runtime_role)
        runtime_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:Retrieve", "bedrock:RetrieveAndGenerate"],
                resources=["*"],
            )
        )
        runtime_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock-agentcore:CreateEvent",
                    "bedrock-agentcore:RetrieveMemoryRecords",
                    "bedrock-agentcore:ListMemoryRecords",
                ],
                resources=["*"],
            )
        )

        memory = CfnResource(
            self,
            "AgentCoreMemory",
            type="AWS::BedrockAgentCore::Memory",
            properties={
                "Name": f"LinkOpsMemory{environment_name.title()}",
                "Description": "Scoped session context and reusable engineering lessons.",
                "EventExpiryDuration": 30,
                "IndexedKeys": [
                    {"Key": "project", "Type": "STRING"},
                    {"Key": "scenario", "Type": "STRING"},
                ],
                "Tags": {"Project": "LinkOpsAI", "Environment": environment_name},
            },
        )

        runtime = CfnResource(
            self,
            "AgentCoreRuntime",
            type="AWS::BedrockAgentCore::Runtime",
            properties={
                "AgentRuntimeName": str(
                    self.node.try_get_context("agentcoreRuntimeName") or "LinkOpsControlPlane"
                ),
                "Description": "Governed LangGraph software-engineering control plane.",
                "RoleArn": runtime_role.role_arn,
                "ProtocolConfiguration": "HTTP",
                "AgentRuntimeArtifact": {
                    "CodeConfiguration": {
                        "Code": {
                            "S3": {
                                "Bucket": code_asset.s3_bucket_name,
                                "Prefix": code_asset.s3_object_key,
                            }
                        },
                        "Runtime": "PYTHON_3_12",
                        "EntryPoint": ["agentcore_entrypoint.py"],
                    }
                },
                "EnvironmentVariables": {
                    "LINKOPS_ENVIRONMENT": "aws",
                    "LINKOPS_STORAGE_BACKEND": "aws",
                    "LINKOPS_AWS_REGION": self.region,
                    "LINKOPS_LINKS_TABLE_NAME": product_stack.links_table.table_name,
                    "LINKOPS_ANALYTICS_TABLE_NAME": product_stack.analytics_table.table_name,
                    "LINKOPS_ARTIFACT_BUCKET": product_stack.artifact_bucket.bucket_name,
                    "LINKOPS_CHECKPOINT_TABLE_NAME": checkpoint_table.table_name,
                    "LINKOPS_AGENTCORE_MEMORY_ID": memory.ref,
                },
                "Tags": {"Project": "LinkOpsAI", "Environment": environment_name},
            },
        )
        code_asset.grant_read(runtime_role)
        runtime.add_resource_dependency(memory)
        CfnOutput(self, "AgentCoreRuntimeArn", value=runtime.get_att("AgentRuntimeArn").to_string())
        CfnOutput(self, "AgentCoreMemoryId", value=memory.ref)
        CfnOutput(self, "CheckpointTableName", value=checkpoint_table.table_name)

    def _checkpoint_table(self, environment_name: str) -> dynamodb.Table:
        return dynamodb.Table(
            self,
            "CheckpointTable",
            table_name=f"linkops-checkpoints-{environment_name}",
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.RETAIN,
        )
