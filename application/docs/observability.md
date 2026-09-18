# Observability and reliability evidence

Each workflow produces artifacts/<run_id>/audit/audit.ndjson with:

* run and thread identifiers;
* agent, node, action, tool, and task context;
* result, duration, retry, and rollback metadata;
* safe artifact references and approval identifiers.

The metrics model covers end-to-end latency, per-node latency, success/failure counts,
model/tool invocation counts, retry and rollback rates, approval wait time, test pass
rate, coverage, security findings, and replan invalidation counts. The infrastructure
repository adds CloudWatch Lambda error, queue age, and dead-letter alarms and a
dashboard. AgentCore-hosted runs are expected to use the service's built-in telemetry
plus ADOT/OTEL where custom spans are required.
