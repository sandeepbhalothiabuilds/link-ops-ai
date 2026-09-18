from __future__ import annotations

from .config import Settings, get_settings
from .repositories import (
    InMemoryAnalyticsRepository,
    InMemoryEventPublisher,
    InMemoryLinkRepository,
)
from .services import LinkService


def build_service(settings: Settings | None = None) -> LinkService:
    settings = settings or get_settings()
    if settings.storage_backend != "memory":
        from linkops_ai.adapters.aws_product import build_aws_service

        return build_aws_service(settings)
    links = InMemoryLinkRepository()
    analytics = InMemoryAnalyticsRepository()
    publisher = InMemoryEventPublisher()
    return LinkService(links, analytics, publisher, settings)
