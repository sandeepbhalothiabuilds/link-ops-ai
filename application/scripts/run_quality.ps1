& .\.venv\Scripts\ruff.exe check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& .\.venv\Scripts\mypy.exe src
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& .\.venv\Scripts\python.exe -m pytest --cov=linkops_ai --cov-report=term-missing
exit $LASTEXITCODE
