from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from threading import RLock
from typing import Protocol

from .domain import AnalyticsBucket, ClickEvent, Link
from .exceptions import AliasAlreadyExists, LinkNotFound


class LinkRepository(Protocol):
    def put_if_absent(self, link: Link) -> None: ...

    def get(self, slug: str) -> Link | None: ...

    def get_by_idempotency_hash(self, key_hash: str) -> Link | None: ...

    def soft_delete(self, slug: str, updated_at: datetime) -> Link: ...

    def is_ready(self) -> bool: ...


class AnalyticsRepository(Protocol):
    def increment(self, event: ClickEvent) -> AnalyticsBucket: ...

    def list_for_slug(self, slug: str) -> list[AnalyticsBucket]: ...

    def is_ready(self) -> bool: ...


class EventPublisher(Protocol):
    def publish(self, event: ClickEvent) -> None: ...

    def is_ready(self) -> bool: ...


class InMemoryLinkRepository:
    def __init__(self) -> None:
        self._links: dict[str, Link] = {}
        self._idempotency: dict[str, str] = {}
        self._lock = RLock()

    def put_if_absent(self, link: Link) -> None:
        with self._lock:
            if link.slug in self._links:
                raise AliasAlreadyExists(link.slug)
            self._links[link.slug] = link
            if link.idempotency_key_hash:
                self._idempotency[link.idempotency_key_hash] = link.slug

    def get(self, slug: str) -> Link | None:
        with self._lock:
            return self._links.get(slug)

    def get_by_idempotency_hash(self, key_hash: str) -> Link | None:
        with self._lock:
            slug = self._idempotency.get(key_hash)
            return self._links.get(slug) if slug else None

    def soft_delete(self, slug: str, updated_at: datetime) -> Link:
        with self._lock:
            current = self._links.get(slug)
            if current is None:
                raise LinkNotFound(slug)
            deleted = current.model_copy(update={"status": "deleted", "updated_at": updated_at})
            self._links[slug] = deleted
            return deleted

    def is_ready(self) -> bool:
        return True

    def all_links(self) -> Iterable[Link]:
        return tuple(self._links.values())


class InMemoryAnalyticsRepository:
    def __init__(self) -> None:
        self._buckets: dict[tuple[str, str], AnalyticsBucket] = {}
        self._lock = RLock()

    def increment(self, event: ClickEvent) -> AnalyticsBucket:
        occurred = event.occurred_at.astimezone(UTC)
        bucket = occurred.strftime("%Y-%m-%d-%H")
        key = (event.slug, bucket)
        with self._lock:
            current = self._buckets.get(key) or AnalyticsBucket(slug=event.slug, bucket=bucket)
            refs = dict(current.referrer_counts)
            if event.referrer_host:
                refs[event.referrer_host] = refs.get(event.referrer_host, 0) + 1
            agents = dict(current.user_agent_counts)
            agents[event.user_agent_category] = agents.get(event.user_agent_category, 0) + 1
            updated = current.model_copy(
                update={
                    "click_count": current.click_count + 1,
                    "referrer_counts": refs,
                    "user_agent_counts": agents,
                    "last_click_at": occurred,
                }
            )
            self._buckets[key] = updated
            return updated

    def list_for_slug(self, slug: str) -> list[AnalyticsBucket]:
        with self._lock:
            return sorted(
                (item for (item_slug, _), item in self._buckets.items() if item_slug == slug),
                key=lambda item: item.bucket,
            )

    def is_ready(self) -> bool:
        return True


class InMemoryEventPublisher:
    def __init__(self) -> None:
        self.events: list[ClickEvent] = []
        self.fail_next = False

    def publish(self, event: ClickEvent) -> None:
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("injected publisher failure")
        self.events.append(event)

    def is_ready(self) -> bool:
        return True
