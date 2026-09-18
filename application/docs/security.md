# Security and governance

## Product controls

* Destination validation accepts only HTTP and HTTPS and rejects embedded credentials.
* Aliases are lowercase, URL-safe, collision-safe, and cannot shadow system routes.
* Expiry is checked synchronously; DynamoDB TTL is only cleanup.
* Analytics never stores raw IP addresses or complete user-agent strings.
* Stable problem-detail responses avoid stack traces and secret values.

## Control-plane controls

* Workspace tools reject traversal, .git, credential, SSH, and environment-secret paths.
* Agents use narrow typed tools instead of arbitrary shell commands.
* Push and deployment are protected tools and require approval.
* Each run records artifact hashes, approvals, decisions, node outcomes, retries, and
  rollback metadata.
* Critical security findings, exhausted retry budgets, integrity mismatches, and missing
  approvals safe-stop the workflow.

## AWS controls

The infrastructure repository uses managed encryption for DynamoDB/SQS/S3, on-demand
DynamoDB capacity, point-in-time recovery, SQS DLQ redrive, TLS-only artifact buckets,
and separate roles for product Lambdas and AgentCore. The initial role policies are
development-scoped and must be reviewed against the target account's IAM boundary before
production use.
