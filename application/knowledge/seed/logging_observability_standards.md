# Logging and observability standards

Emit structured JSON events with run/thread ID, node, agent, tool, attempt, outcome,
latency, and safe artifact references. Do not log authorization values, raw prompt
secrets, or complete personal identifiers. Keep human decisions append-only.
