from __future__ import annotations

import secrets
import string
from contextlib import suppress
from typing import Literal
from urllib.parse import urlsplit

from .config import Settings, get_settings
from .domain import (
    AnalyticsBucket,
    ClickEvent,
    CreateLinkCommand,
    Link,
    hash_idempotency_key,
    normalize_alias,
    to_ttl_epoch,
    utc_now,
    validate_destination_url,
)
from .exceptions import (
    AliasAlreadyExists,
    AliasGenerationExhausted,
    LinkExpired,
    LinkInactive,
    LinkNotFound,
)
from .repositories import AnalyticsRepository, EventPublisher, LinkRepository

ALPHABET = string.ascii_lowercase + string.digits


class LinkService:
    def __init__(
        self,
        links: LinkRepository,
        analytics: AnalyticsRepository,
        publisher: EventPublisher,
        settings: Settings | None = None,
    ) -> None:
        self.links = links
        self.analytics = analytics
        self.publisher = publisher
        self.settings = settings or get_settings()

    def create(
        self,
        command: CreateLinkCommand,
        idempotency_key: str | None = None,
    ) -> Link:
        validate_destination_url(command.url, self.settings.max_url_length)
        key_hash = hash_idempotency_key(idempotency_key) if idempotency_key else None
        if key_hash:
            previous = self.links.get_by_idempotency_hash(key_hash)
            if previous:
                if previous.destination_url != command.url:
                    raise AliasAlreadyExists("idempotency key was used for a different URL")
                return previous

        preferred = normalize_alias(command.custom_alias) if command.custom_alias else None
        attempts = 1 if preferred else self.settings.max_collision_retries
        for _ in range(attempts):
            slug = preferred or self._new_slug(self.settings.generated_slug_length)
            now = utc_now()
            link = Link(
                slug=slug,
                destination_url=command.url,
                created_at=now,
                updated_at=now,
                expires_at=command.expires_at,
                ttl_epoch=to_ttl_epoch(command.expires_at),
                created_by=command.created_by,
                idempotency_key_hash=key_hash,
            )
            try:
                self.links.put_if_absent(link)
                return link
            except AliasAlreadyExists:
                if preferred:
                    raise
        raise AliasGenerationExhausted("could not allocate a unique slug within the retry budget")

    def get(self, slug: str) -> Link:
        link = self.links.get(normalize_alias(slug))
        if link is None:
            raise LinkNotFound(slug)
        return link

    def delete(self, slug: str) -> None:
        self.links.soft_delete(normalize_alias(slug), utc_now())

    def resolve(self, slug: str, referrer: str | None, user_agent: str | None) -> Link:
        link = self.get(slug)
        if link.status != "active":
            raise LinkInactive(slug)
        if link.is_expired():
            raise LinkExpired(slug)
        event = ClickEvent(
            slug=link.slug,
            referrer_host=self._referrer_host(referrer),
            user_agent_category=self._user_agent_category(user_agent),
        )
        # Analytics is intentionally best-effort on the redirect path. The SQS
        # adapter is asynchronous in AWS; local memory retains the event for the worker.
        with suppress(Exception):
            self.publisher.publish(event)
        return link

    def analytics_for(self, slug: str) -> list[AnalyticsBucket]:
        self.get(slug)
        return self.analytics.list_for_slug(normalize_alias(slug))

    def readiness(self) -> bool:
        return self.links.is_ready() and self.analytics.is_ready() and self.publisher.is_ready()

    @staticmethod
    def _new_slug(length: int = 8) -> str:
        return "".join(secrets.choice(ALPHABET) for _ in range(length))

    @staticmethod
    def _referrer_host(referrer: str | None) -> str | None:
        if not referrer:
            return None
        try:
            host = urlsplit(referrer).hostname
        except ValueError:
            return None
        return host[:253] if host else None

    @staticmethod
    def _user_agent_category(
        user_agent: str | None,
    ) -> Literal["browser", "mobile", "bot", "other", "unknown"]:
        if not user_agent:
            return "unknown"
        value = user_agent.lower()
        if "bot" in value or "crawler" in value or "spider" in value:
            return "bot"
        if "mobile" in value or "android" in value or "iphone" in value:
            return "mobile"
        if any(token in value for token in ("mozilla", "chrome", "safari", "firefox", "edge")):
            return "browser"
        return "other"
