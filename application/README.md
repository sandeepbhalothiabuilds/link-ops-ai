# LinkOps AI

LinkOps AI is a production-style URL shortener wrapped in a governed, stateful
agentic software-engineering workflow. It is intentionally split into two planes:

* **Product plane** — FastAPI URL shortening, redirect resolution, lifecycle
  management, privacy-conscious asynchronous analytics, and health checks.
* **Engineering control plane** — a typed LangGraph workflow that normalizes a
  requirement, plans dependencies, analyzes brownfield code, produces design
  artifacts, gates risky work with approvals, runs parallel implementation/QA/
  security branches, repairs bounded failures, and emits an auditable release
  package.

The application is runnable locally with no AWS account or model credentials. AWS
adapters, Bedrock Knowledge Base retrieval, DynamoDB checkpointing, and AgentCore
runtime deployment are enabled by configuration and are documented in the
separate sibling repository `agentic-sdlc-url-shortener-infrastructure`.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn linkops_ai.product.api:app --reload
```

Create and resolve a link:

```powershell
$body = @{ url = "https://example.com/docs" } | ConvertTo-Json
$link = Invoke-RestMethod http://localhost:8000/api/v1/links -Method Post -Body $body -ContentType application/json
Invoke-WebRequest $link.short_url -MaximumRedirection 0
```

Run the deterministic agentic scenarios:

```powershell
python -m linkops_ai.cli scenario greenfield --auto-approve
python -m linkops_ai.cli scenario brownfield --auto-approve
python -m linkops_ai.cli scenario ambiguous --approve-clarification --auto-approve
```

Run the quality gates:

```powershell
python -m pytest
python -m ruff check .
python -m mypy src
```

## Repository map

```text
src/linkops_ai/product/         URL shortener domain, API, repositories, analytics
src/linkops_ai/orchestration/  LangGraph, typed state, gates, approvals, audit, replan
src/linkops_ai/adapters/       DynamoDB, SQS, Bedrock and Knowledge Base adapters
knowledge/seed/                 Safe, candidate-authored engineering guidance
scenarios/                      Greenfield, brownfield and ambiguous demo fixtures
docs/                           Architecture, operations and decision records
scripts/                        Reproducible local quality/demo commands
```

AWS infrastructure is deliberately kept in the sibling `../infrastructure` folder
so application changes and cloud deployment changes have independent review and
release lifecycles.

## Safety and data handling

The workflow never receives arbitrary shell access. Repository tools enforce a
workspace boundary, deny credential/secret paths, and require explicit approval for
external side effects. The supplied SOW is retained under `docs/reference/` for
traceability; the assignment PDF and confidential source materials are not copied.
Analytics persist aggregate counters only; raw IP addresses and complete user-agent
strings are never stored.

See [docs/architecture/overview.md](docs/architecture/overview.md),
[docs/architecture/README.md](docs/architecture/README.md),
[docs/runbooks/local-end-to-end-testing.md](docs/runbooks/local-end-to-end-testing.md),
[docs/runbooks/local-development.md](docs/runbooks/local-development.md), and the
`../infrastructure/README.md` for deployment instructions.
