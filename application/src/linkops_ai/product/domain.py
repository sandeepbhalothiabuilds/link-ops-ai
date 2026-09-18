from __future__ import annotations

import re
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .exceptions import InvalidAlias, InvalidDestinationUrl

ALIAS_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
RESERVED_ALIASES = frozenset({"api", "health", "docs", "openapi.json", "redoc", "favicon.ico"})
MAX_REFERRER_HOST_LENGTH = 253


def utc_now() -> datetime:
    return datetime.now(UTC)


def validate_destination_url(value: str, max_length: int = 2048) -> str:
    if not isinstance(value, str) or len(value) > max_length:
        raise InvalidDestinationUrl("destination URL is missing or exceeds the configured length")
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise InvalidDestinationUrl("destination URL must use http or https and include a host")
    if parsed.username or parsed.password:
        raise InvalidDestinationUrl("destination URL must not contain embedded credentials")
    return value


def normalize_alias(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in RESERVED_ALIASES or not ALIAS_RE.fullmatch(normalized):
        raise InvalidAlias("alias must be a lowercase URL-safe slug and not a reserved route")
    return normalized


def hash_idempotency_key(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


class Link(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    destination_url: str
    status: Literal["active", "deleted"] = "active"
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    ttl_epoch: int | None = None
    created_by: str | None = None
    idempotency_key_hash: str | None = None
    version: int = 1

    def is_expired(self, now: datetime | None = None) -> bool:
        return self.expires_at is not None and self.expires_at <= (now or utc_now())


class CreateLinkCommand(BaseModel):
    url: str = Field(min_length=1)
    custom_alias: str | None = None
    expires_at: datetime | None = None
    created_by: str | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return validate_destination_url(value)

    @field_validator("custom_alias")
    @classmethod
    def validate_alias(cls, value: str | None) -> str | None:
        return None if value is None else normalize_alias(value)

    @field_validator("expires_at")
    @classmethod
    def validate_expiry(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("expires_at must include a timezone")
            if value <= utc_now():
                raise ValueError("expires_at must be in the future")
        return value.astimezone(UTC) if value is not None else None


class ClickEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    slug: str
    occurred_at: datetime = Field(default_factory=utc_now)
    referrer_host: str | None = Field(default=None, max_length=MAX_REFERRER_HOST_LENGTH)
    user_agent_category: Literal["browser", "mobile", "bot", "other", "unknown"] = "unknown"


class AnalyticsBucket(BaseModel):
    slug: str
    bucket: str
    click_count: int = 0
    referrer_counts: dict[str, int] = Field(default_factory=dict)
    user_agent_counts: dict[str, int] = Field(default_factory=dict)
    last_click_at: datetime | None = None


def to_ttl_epoch(expires_at: datetime | None) -> int | None:
    return int(expires_at.timestamp()) if expires_at else None
