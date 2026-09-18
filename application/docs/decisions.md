# Decision log

## ADR-001: Separate product and engineering control planes

The URL shortener is independently runnable and deployable from the LangGraph control
plane. This keeps redirect latency and product operations independent from model calls,
while preserving the ability to generate engineering evidence about the product.

## ADR-002: Local adapters are first-class

The product and workflow run deterministically without AWS credentials. DynamoDB, SQS,
Bedrock Knowledge Bases, Bedrock Converse, AgentCore runtime, and durable checkpoints
are optional production adapters selected by configuration. This makes tests reproducible
and keeps cloud deployment a deliberate, approved side effect.

## ADR-003: Aggregate analytics only

The redirect path emits a sanitized event and never waits for analytics persistence.
The worker stores hourly aggregates, referrer host counters, and coarse user-agent
categories. Raw IP and full user-agent values are intentionally excluded.
