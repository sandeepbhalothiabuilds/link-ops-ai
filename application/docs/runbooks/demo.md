# Reviewer demo

```powershell
python -m linkops_ai.cli scenario greenfield --auto-approve
python -m linkops_ai.cli scenario brownfield --auto-approve
python scripts/run_ambiguous_demo.py
python -m pytest --cov=linkops_ai --cov-report=term-missing
```

The ambiguous demo intentionally runs three approval phases: requirements clarification,
architecture, and release. Inspect the generated `artifacts/<run_id>/audit/audit.ndjson`,
`plan/task_plan.mmd`, `codebase/codebase_impact.md`, and release summary.
