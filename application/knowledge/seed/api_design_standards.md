# API design standards

Use versioned routes, stable problem-detail errors, explicit status codes, idempotency
for retryable creates, and health endpoints that distinguish liveness from readiness.
Public responses must not expose internal credentials, stack traces, or secret headers.
