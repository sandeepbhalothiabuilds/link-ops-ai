from __future__ import annotations

import pytest

from linkops_ai.product.config import Settings
from linkops_ai.product.repositories import (
    InMemoryAnalyticsRepository,
    InMemoryEventPublisher,
    InMemoryLinkRepository,
)
from linkops_ai.product.services import LinkService


@pytest.fixture
def service() -> LinkService:
    return LinkService(
        InMemoryLinkRepository(),
        InMemoryAnalyticsRepository(),
        InMemoryEventPublisher(),
        Settings(base_url="http://testserver"),
    )
