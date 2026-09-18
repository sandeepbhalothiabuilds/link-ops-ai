# Local end-to-end testing

This runbook explains how to start LinkOps AI locally and what to expect from each
test. It covers both the URL-shortener product plane and the LangGraph engineering
control plane.

The default local mode uses in-memory repositories. It requires Python and internet
access to install packages, but it does not require an AWS account, AWS credentials,
Bedrock access, or a model key. Data is intentionally lost when the API process
restarts.

For the published monorepo, run the commands from:

```text
link-ops-ai/application
```

For the original split repository, run them from the application repository root.

## 1. Prepare the local environment

Use Python 3.12 and PowerShell:

```powershell
cd C:\Users\sande\OneDrive\Documents\Projects\link-ops-ai\application
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Expected result: installation completes without errors. The default `.env` selects
`LINKOPS_STORAGE_BACKEND=memory` and `LINKOPS_BASE_URL=http://localhost:8000`.

If PowerShell blocks activation, use the virtual-environment executable directly:

```powershell
.\.venv\Scripts\python.exe -m uvicorn linkops_ai.product.api:app --reload
```

## 2. Start the API

Keep this terminal open:

```powershell
python -m uvicorn linkops_ai.product.api:app --host 127.0.0.1 --port 8000 --reload
```

Expected result:

```text
Uvicorn running on http://127.0.0.1:8000
```

Open the interactive API console at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

If port 8000 is already in use, either use the running service or select another
port. When using another port, set `LINKOPS_BASE_URL` in `.env` to the same address.

## 3. Verify health and readiness

Run from a second PowerShell terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

Expected results:

```text
status
------
ok

status
------
ready
```

`/health/live` confirms the process is responding. `/health/ready` confirms the
configured storage and event publisher are usable. In memory mode both should be
ready immediately.

## 4. Create a short link

Use a unique alias for each run:

```powershell
$alias = "demo-" + (Get-Date -Format "HHmmss")
$idempotencyKey = "test-" + $alias
$body = @{
    url = "https://example.com/my-test-page"
    custom_alias = $alias
} | ConvertTo-Json

$headers = @{ "Idempotency-Key" = $idempotencyKey }
$link = Invoke-RestMethod `
    http://127.0.0.1:8000/api/v1/links `
    -Method Post `
    -Body $body `
    -ContentType "application/json" `
    -Headers $headers

$link
```

Expected result: HTTP 201 and a response containing:

- `slug`: the requested alias;
- `short_url`: the generated local URL;
- `destination_url`: the original URL;
- `status`: `active`;
- `created_at` and optional `expires_at` timestamps.

If `custom_alias` is omitted, the service generates an eight-character alias.

## 5. Verify idempotency

Repeat the same create request with the same `Idempotency-Key`:

```powershell
$replay = Invoke-RestMethod `
    http://127.0.0.1:8000/api/v1/links `
    -Method Post `
    -Body $body `
    -ContentType "application/json" `
    -Headers $headers

$replay.slug
```

Expected result: the same slug is returned and a second link is not created. Reusing
the same key for a different destination is rejected with HTTP 409.

## 6. Read link metadata

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/links/$alias"
```

Expected result: HTTP 200 with the same metadata returned during creation.

## 7. Verify redirect behavior

```powershell
curl.exe -i "http://127.0.0.1:8000/$alias"
```

Expected result:

```text
HTTP/1.1 302 Found
location: https://example.com/my-test-page
```

Opening the short URL in a browser follows the redirect to the destination. Unknown
aliases return 404. Deleted aliases return 404. Expired links return 410.

## 8. Verify validation errors

```powershell
$invalidBody = @{ url = "file:///etc/passwd" } | ConvertTo-Json

try {
    Invoke-RestMethod `
        http://127.0.0.1:8000/api/v1/links `
        -Method Post `
        -Body $invalidBody `
        -ContentType "application/json"
} catch {
    $_.Exception.Response.StatusCode.value__
}
```

Expected result: HTTP 400 with an `application/problem+json` response. Only HTTP and
HTTPS destination URLs are accepted; embedded URL credentials are rejected.

Past expiry values are also rejected with HTTP 400. The expiry behavior test can be
run directly with:

```powershell
python -m pytest tests/product/test_api.py -k expiry -q
```

Expected result: both expiry tests pass, including the 410 response for an expired
link and the 400 response for an invalid past expiry request.

## 9. Verify soft deletion

```powershell
Invoke-RestMethod `
    "http://127.0.0.1:8000/api/v1/links/$alias" `
    -Method Delete

curl.exe -i "http://127.0.0.1:8000/$alias"
```

Expected result: the delete returns HTTP 204 with no response body. The subsequent
redirect attempt returns HTTP 404.

## 10. Understand local analytics

The redirect path publishes a sanitized event containing the slug, referrer host,
user-agent category, and timestamp. It never stores a raw IP address or full
user-agent string.

Analytics aggregation is intentionally asynchronous. In AWS, the path is:

```text
redirect -> SQS -> analytics Lambda -> DynamoDB hourly aggregate
```

The in-memory local server captures the event but does not start a background SQS
worker, so the running API may show zero analytics until a worker processes the
event. The complete redirect-to-aggregate behavior is covered by the functional
test:

```powershell
python -m pytest tests/product/test_api.py -k functional -q
```

Expected result: the test creates a link, follows the redirect, processes the
captured event, verifies one aggregate click, and deletes the link.

## 11. Run the engineering control plane

Run the deterministic local scenarios from the application root:

```powershell
python -m linkops_ai.cli scenario greenfield --auto-approve
python -m linkops_ai.cli scenario brownfield --auto-approve
python -m linkops_ai.cli scenario ambiguous --approve-clarification --auto-approve
```

Expected result for each command: JSON containing `status: "COMPLETE"` and a release
recommendation of `ready`. Artifacts are written to:

```text
artifacts\<run_id>\
```

Important artifacts include the normalized requirements, task plan, Mermaid task
graph, design, validation results, audit log, manifest, and release summary.

To observe the approval workflow instead of automatically approving it:

```powershell
python scripts/run_ambiguous_demo.py
```

Expected result: the run pauses for requirements clarification, architecture approval,
and release approval, then resumes to `COMPLETE` after each approval.

To exercise bounded repair behavior:

```powershell
python -m linkops_ai.cli scenario greenfield --auto-approve --inject-failure
```

Expected result: the workflow repairs the injected recoverable failure and completes
with one repair attempt recorded in its state and audit artifacts.

## 12. Run the quality gates

```powershell
python -m pytest --cov=linkops_ai --cov-report=term-missing
python -m ruff check .
python -m mypy src
python -m bandit -r src -ll
```

Expected result: tests pass, Ruff reports no violations, mypy reports no issues, and
Bandit reports no medium or high-confidence security findings.

## 13. Stop the API

If the API is running in the current terminal, press `Ctrl+C`.

If it is running in another terminal, identify the listener:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
```

Stop only the process shown by that command:

```powershell
Stop-Process -Id <PID>
```

## AWS-backed mode

AWS-backed local execution is optional. It requires deployed infrastructure, an AWS
profile or environment-based credentials, the deployment region, DynamoDB table names,
and the SQS queue URL. Set `LINKOPS_STORAGE_BACKEND=aws` only after those resources
exist and the identity passes:

```powershell
aws sts get-caller-identity
```

Follow the deployment sequence in `../infrastructure/README.md`. AWS-backed analytics
are eventually consistent because the click event is processed asynchronously through
SQS and Lambda.
