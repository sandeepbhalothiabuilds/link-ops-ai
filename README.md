# LinkOps AI

Production-ready AI-assisted URL shortener and governed agentic software-engineering control plane.

## Repository layout

- [`application/`](application/README.md) — URL-shortener product APIs, LangGraph control plane, tests, scenarios, documentation, and local demo tooling.
- [`infrastructure/`](infrastructure/README.md) — separate AWS CDK deployment project for DynamoDB, SQS, Lambda, API Gateway, Bedrock/AgentCore, observability, packaging, and knowledge-base seeding.

## Quick start

Run the application locally:

```powershell
cd application
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
\.venv\Scripts\python.exe -m uvicorn linkops_ai.product.api:app --reload
```

Run the AWS infrastructure checks and synthesis:

```powershell
cd infrastructure
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
\.venv\Scripts\python.exe -m pytest -q
npx --yes aws-cdk synth --app ".\.venv\Scripts\python.exe app.py"
```

See the application and infrastructure READMEs for configuration, deployment, operations, and scenario walkthroughs.
The complete local command-by-command walkthrough is in
[`application/docs/runbooks/local-end-to-end-testing.md`](application/docs/runbooks/local-end-to-end-testing.md).
The application README also includes the Swagger screenshot and architecture visuals
under [`application/docs/assets/`](application/docs/assets/).
