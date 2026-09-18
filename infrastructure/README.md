# LinkOps AI infrastructure

This repository owns AWS deployment independently from the application repository.
It provisions the product plane data path (DynamoDB, SQS, Lambda/API Gateway,
CloudWatch alarms/dashboard), the engineering-control-plane AgentCore runtime,
AgentCore Memory, and the seed knowledge corpus bucket.

The application repository is expected at the sibling path
../agentic-sdlc-url-shortener during packaging. No credentials or confidential
assignment documents belong in either repository.

## Prerequisites

* AWS CLI configured for the target account and region
* Node.js and the current @aws/agentcore CLI for direct AgentCore code deployment
* Python 3.12 and a virtual environment
* AWS CDK v2 CLI
* Bedrock model access enabled in the selected region

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -e ".[dev]"
    cdk bootstrap
    cdk synth

## Deployment sequence

1. python scripts/package_product.py --app-repo ..\agentic-sdlc-url-shortener
2. cdk deploy LinkOpsProductStack
3. Upload the seed corpus and create/supply the Bedrock Knowledge Base ID with
   python scripts/sync_knowledge_base.py --knowledge-base-id ID --data-source-id ID.
4. python scripts/package_agentcore.py --app-repo ..\agentic-sdlc-url-shortener
5. cdk deploy LinkOpsAgentCoreStack -c agentcoreCodePath=build\agentcore
6. Invoke the runtime using python scripts/invoke_agentcore.py --runtime-arn ARN.

The AgentCore runtime uses Python 3.12 and an HTTP entry point. The CloudFormation
resource is the deployable path; the AWS AgentCore CLI remains available for local
packaging/invocation and diagnostics. Push and deployment remain human-approved
actions in the workflow.

## Destruction

This is a development stack. DynamoDB tables and S3 buckets use RETAIN by default.
Review data-retention and deletion approvals before removing resources.
