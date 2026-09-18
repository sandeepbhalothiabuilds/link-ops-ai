# AWS deployment boundary

Application code and AWS deployment code are separate repositories:

* this repository contains the URL shortener, LangGraph orchestration, tests, safe seed
  knowledge corpus, and local demo;
* agentic-sdlc-url-shortener-infrastructure contains CDK stacks, runtime packaging,
  IAM, tables, queues, dashboard, and deployment scripts.

The local system deliberately runs with in-memory adapters. The AWS environment selects
the DynamoDB/SQS adapters, the AWS LangGraph checkpointer, Bedrock Knowledge Base
retrieval, and the AgentCore memory adapter through environment variables. Deployment
is never triggered implicitly by a workflow run.

Follow the infrastructure repository README for the ordered package, synth, deploy,
ingest, and invoke flow. Supply the AWS account, region, model access, Knowledge Base
identifiers, and GitHub remotes only when those external systems are ready.
