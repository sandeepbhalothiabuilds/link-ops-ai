# Requirements traceability

| Requirement area | Implementation | Evidence |
| --- | --- | --- |
| URL create/redirect/lifecycle | product domain, service, FastAPI routes | tests/product |
| Collision safety and idempotency | conditional repository contract and hashed key lookup | test_service.py |
| Expiration and soft deletion | synchronous service checks | test_service.py, test_api.py |
| Privacy-safe asynchronous analytics | ClickEvent sanitization, publisher, hourly worker | test_api.py |
| Greenfield/brownfield/ambiguous flows | RequirementsAgent, PlannerAgent, CodebaseAnalyst | test_agents.py, test_graph.py |
| Explicit stateful LangGraph | typed WorkflowState and StateGraph topology | orchestration/graph.py |
| Sequential and parallel work | design-to-development/test/security fan-out and validation fan-in | test_graph.py |
| Human governance | requirements, architecture, and release approval records | test_graph.py |
| Retry, repair, safe-stop | injected failure and critical finding routes | test_graph.py |
| Dynamic replan | hash-based downstream invalidation and plan diff | replan.py, runner.replan |
| Durable AWS checkpointing | langgraph-checkpoint-aws adapter and CDK table | adapters/checkpoints.py, infrastructure repo |
| Knowledge grounding | seed corpus and Bedrock retrieval adapter | knowledge/seed, adapters/bedrock.py |
| AgentCore deployment | HTTP runtime artifact, memory resource, runtime role | infrastructure repo |
| Observability | audit.ndjson, metrics schema, CloudWatch dashboard | artifacts, observability.py |

The supplied assignment and SOW are intentionally not copied into the repository.
This matrix uses only concise implementation labels and does not publish confidential
source text.
