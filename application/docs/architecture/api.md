# API contract

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/api/v1/links` | Create generated/custom link; supports `Idempotency-Key` |
| GET | `/api/v1/links/{slug}` | Read metadata |
| DELETE | `/api/v1/links/{slug}` | Soft delete; returns 204 |
| GET | `/api/v1/links/{slug}/analytics` | Hourly aggregate analytics |
| GET | `/{slug}` | 302 redirect, 404 unknown/inactive, 410 expired |
| GET | `/health/live` | Process liveness |
| GET | `/health/ready` | Storage/publisher readiness |

Destination URLs must use HTTP or HTTPS and cannot include embedded credentials. Custom
aliases are normalized to lowercase and cannot shadow system routes.
