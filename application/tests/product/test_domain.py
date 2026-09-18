from datetime import UTC, datetime, timedelta

import pytest

from linkops_ai.product.domain import CreateLinkCommand, normalize_alias, validate_destination_url
from linkops_ai.product.exceptions import InvalidAlias, InvalidDestinationUrl


def test_destination_validation_allows_http_and_https() -> None:
    assert validate_destination_url("https://example.com/path") == "https://example.com/path"
    assert validate_destination_url("http://example.com") == "http://example.com"


@pytest.mark.parametrize(
    "value",
    ["ftp://example.com", "javascript:alert(1)", "https://user:pass@example.com", "not-a-url"],
)
def test_destination_validation_rejects_unsafe_values(value: str) -> None:
    with pytest.raises(InvalidDestinationUrl):
        validate_destination_url(value)


def test_alias_normalization_and_reserved_route_rejection() -> None:
    assert normalize_alias("  My-Link ") == "my-link"
    with pytest.raises(InvalidAlias):
        normalize_alias("api")
    with pytest.raises(InvalidAlias):
        normalize_alias("bad alias")


def test_expiry_requires_timezone_and_future_value() -> None:
    with pytest.raises(ValueError):
        CreateLinkCommand(url="https://example.com", expires_at=datetime.now() + timedelta(hours=1))
    item = CreateLinkCommand(
        url="https://example.com", expires_at=datetime.now(UTC) + timedelta(hours=1)
    )
    assert item.expires_at is not None
