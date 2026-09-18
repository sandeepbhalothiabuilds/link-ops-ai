# LinkOps AI architecture

```mermaid
flowchart LR
  Client --> API[FastAPI / Lambda adapter]
  API --> Links[(DynamoDB links)]
  API --> Queue[SQS click events]
  Queue --> Worker[Analytics worker]
  Worker --> Analytics[(DynamoDB analytics)]
  API --> Ops[Structured logs / metrics]
  Worker --> Ops
  Requirement --> Graph[LangGraph control plane]
  Graph --> KB[Bedrock Knowledge Base]
  Graph --> Model[Bedrock Converse]
  Graph --> Artifacts[Artifact store + audit]
  Graph --> Checkpoints[DynamoDB checkpoints]
  Graph --> AgentCore[AgentCore Runtime]
```

The product request path is intentionally short: link lookup, synchronous status and
expiry checks, sanitized event publication, and redirect. Analytics is asynchronous.

The control-plane graph is explicit:

```mermaid
flowchart TD
  START --> Intake --> IntakeGate{ambiguity?}
  IntakeGate -- high --> RequirementsApproval[Human clarification]
  IntakeGate -- clear --> Plan
  RequirementsApproval --> Plan
  Plan --> Brownfield{brownfield?}
  Brownfield -- yes --> Codebase
  Brownfield -- no --> Design
  Codebase --> Design
  Design --> ArchitectureApproval[Human architecture approval]
  ArchitectureApproval --> Fanout((fan-out))
  Fanout --> Development
  Fanout --> TestSpec
  Fanout --> Security
  Development --> Validate
  TestSpec --> Validate
  Security --> Validate
  Validate -->|recoverable failure| Repair --> Validate
  Validate -->|critical/exhausted| SafeStop
  Validate -->|pass| ReleaseDocs --> ReleaseApproval[Human release approval]
  ReleaseApproval --> Complete
```

Large artifacts live under `artifacts/<run_id>`; graph state carries typed metadata,
references, hashes, approvals, and audit events. No hidden model chain-of-thought is
persisted.
