# LinkOps AI agent instructions

## Working agreement

1. Keep product-plane and control-plane changes independently testable.
2. Use typed Pydantic models at boundaries and deterministic gates alongside model output.
3. Add or update tests in the same change as behavior.
4. Never add credentials, source-assignment text, raw IP data, or full authorization values.
5. Record material architecture decisions in `docs/decisions/`.
6. Protected actions such as push and deployment require an approval record.

## Verification

Run `python -m pytest`, `python -m ruff check .`, and `python -m mypy src` for a normal
change. The AWS repository has its own CDK synth gate.
