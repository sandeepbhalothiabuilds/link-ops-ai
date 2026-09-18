from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from linkops_ai.product.analytics import AnalyticsProcessor
from linkops_ai.product.api import create_app


def test_functional_create_redirect_analytics_delete(service) -> None:
    publisher = service.publisher
    analytics = service.analytics
    client = TestClient(create_app(service))
    created = client.post(
        "/api/v1/links", json={"url": "https://example.com/docs", "custom_alias": "demo"}
    )
    assert created.status_code == 201
    assert created.json()["short_url"] == "http://testserver/demo"
    redirect = client.get("/demo", follow_redirects=False)
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "https://example.com/docs"
    AnalyticsProcessor(analytics).process(publisher.events)
    summary = client.get("/api/v1/links/demo/analytics")
    assert summary.json()["total_clicks"] == 1
    assert client.delete("/api/v1/links/demo").status_code == 204
    assert client.get("/demo", follow_redirects=False).status_code == 404


def test_stable_validation_error_and_health(service) -> None:
    client = TestClient(create_app(service))
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200
    response = client.post("/api/v1/links", json={"url": "file:///etc/passwd"})
    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"


def test_expired_link_returns_gone(service) -> None:
    client = TestClient(create_app(service))
    link = service.create(
        __import__("linkops_ai.product.domain", fromlist=["CreateLinkCommand"]).CreateLinkCommand(
            url="https://example.com",
            custom_alias="expired",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    service.links._links[link.slug] = link.model_copy(
        update={"expires_at": datetime.now(UTC) - timedelta(seconds=1)}
    )
    assert client.get("/expired", follow_redirects=False).status_code == 410


def test_past_expiry_is_a_stable_client_error(service) -> None:
    client = TestClient(create_app(service))
    response = client.post(
        "/api/v1/links",
        json={
            "url": "https://example.com",
            "custom_alias": "past-expiry",
            "expires_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        },
    )
    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"
