#!/usr/bin/env python3
import aws_cdk as cdk

from infrastructure.agentcore_stack import LinkOpsAgentCoreStack
from infrastructure.product_stack import LinkOpsProductStack

app = cdk.App()
environment = app.node.try_get_context("environment") or "dev"
env = cdk.Environment(
    account=app.node.try_get_context("account") or None,
    region=app.node.try_get_context("region") or None,
)

product = LinkOpsProductStack(app, "LinkOpsProductStack", env=env, environment_name=environment)
LinkOpsAgentCoreStack(
    app,
    "LinkOpsAgentCoreStack",
    env=env,
    environment_name=environment,
    product_stack=product,
)

app.synth()
