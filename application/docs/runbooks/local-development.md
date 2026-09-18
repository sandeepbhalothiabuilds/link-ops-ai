# Local development

1. Create and activate a Python 3.12 virtual environment.
2. Install `python -m pip install -e ".[dev]"`.
3. Copy `.env.example` to `.env` only when local overrides are needed.
4. Start the API with `uvicorn linkops_ai.product.api:app --reload`.
5. Run `python -m pytest`, `python -m ruff check .`, and `python -m mypy src`.

The default storage backend is in-memory. Set `LINKOPS_STORAGE_BACKEND=aws` only when
the infrastructure repository has created the DynamoDB tables and SQS queue and the AWS
identity is configured. Bedrock model and Knowledge Base calls are never required for
the deterministic local scenarios.

For the complete command-by-command walkthrough, expected responses, failure meanings,
analytics behavior, control-plane scenarios, and shutdown instructions, see
[local end-to-end testing](local-end-to-end-testing.md).
