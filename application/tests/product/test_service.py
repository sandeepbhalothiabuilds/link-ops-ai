from datetime import UTC, datetime, timedelta

import pytest

from linkops_ai.product.domain import CreateLinkCommand
from linkops_ai.product.exceptions import AliasAlreadyExists, LinkExpired, LinkInactive
from linkops_ai.product.repositories import InMemoryEventPublisher


def test_lifecycle_idempotency_and_collision(service) -> None:
    first = service.create(
        CreateLinkCommand(url="https://example.com", custom_alias="Demo"), "retry-key"
    )
    second = service.create(CreateLinkCommand(url="https://example.com"), "retry-key")
    assert first == second
    with pytest.raises(AliasAlreadyExists):
        service.create(CreateLinkCommand(url="https://other.example", custom_alias="demo"))
    service.delete("demo")
    with pytest.raises(LinkInactive):
        service.resolve("demo", None, None)


def test_expiry_is_enforced_without_waiting_for_ttl(service) -> None:
    link = service.create(
        CreateLinkCommand(
            url="https://example.com",
            custom_alias="soon",
            expires_at=datetime.now(UTC) + timedelta(seconds=1),
        )
    )
    service.links._links[link.slug] = link.model_copy(
        update={"expires_at": datetime.now(UTC) - timedelta(seconds=1)}
    )
    with pytest.raises(LinkExpired):
        service.resolve("soon", None, None)


def test_redirect_publishes_sanitized_event_and_worker_aggregates(service) -> None:
    link = service.create(CreateLinkCommand(url="https://example.com", custom_alias="analytics"))
    service.resolve(link.slug, "https://search.example/results", "Mozilla/5.0 (iPhone; Mobile)")
    publisher = service.publisher
    assert isinstance(publisher, InMemoryEventPublisher)
    assert publisher.events[0].referrer_host == "search.example"
    assert not hasattr(publisher.events[0], "ip_address")
