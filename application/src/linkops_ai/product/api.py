from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, cast

import structlog
from fastapi import Depends, FastAPI, Header, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from .config import get_settings
from .domain import AnalyticsBucket, CreateLinkCommand, Link
from .exceptions import (
    AliasAlreadyExists,
    AliasGenerationExhausted,
    InvalidAlias,
    InvalidDestinationUrl,
    LinkExpired,
    LinkInactive,
    LinkNotFound,
)
from .runtime import build_service
from .services import LinkService

logger = structlog.get_logger("linkops.product")


class CreateLinkRequest(BaseModel):
    url: str = Field(min_length=1)
    custom_alias: str | None = None
    expires_at: datetime | None = None


class LinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    short_url: str
    destination_url: str
    status: str
    created_at: datetime
    expires_at: datetime | None


class AnalyticsResponse(BaseModel):
    slug: str
    total_clicks: int
    buckets: list[AnalyticsBucket]
    most_recent_click_at: datetime | None


class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str


def _link_response(link: Link, base_url: str | None = None) -> LinkResponse:
    return LinkResponse(
        slug=link.slug,
        short_url=f"{(base_url or get_settings().base_url).rstrip('/')}/{link.slug}",
        destination_url=link.destination_url,
        status=link.status,
        created_at=link.created_at,
        expires_at=link.expires_at,
    )


def create_app(service: LinkService | None = None) -> FastAPI:
    app = FastAPI(title="LinkOps URL Shortener", version="0.1.0")
    app.state.link_service = service or build_service()

    def get_service() -> LinkService:
        return cast(LinkService, app.state.link_service)

    async def invalid_input(_request: Request, exc: Exception) -> Response:
        return _problem(400, "Invalid request", str(exc), "invalid-request")

    app.add_exception_handler(InvalidDestinationUrl, invalid_input)
    app.add_exception_handler(InvalidAlias, invalid_input)

    @app.exception_handler(AliasAlreadyExists)
    async def duplicate_alias(_request: Request, exc: Exception) -> Response:
        return _problem(409, "Alias already exists", str(exc), "alias-conflict")

    @app.exception_handler(AliasGenerationExhausted)
    async def exhausted_aliases(_request: Request, exc: Exception) -> Response:
        return _problem(503, "Alias allocation unavailable", str(exc), "alias-allocation-failed")

    @app.exception_handler(LinkNotFound)
    async def not_found(_request: Request, exc: Exception) -> Response:
        return _problem(404, "Link not found", str(exc), "link-not-found")

    @app.exception_handler(LinkExpired)
    async def expired(_request: Request, exc: Exception) -> Response:
        return _problem(410, "Link expired", str(exc), "link-expired")

    @app.exception_handler(LinkInactive)
    async def inactive(_request: Request, exc: Exception) -> Response:
        return _problem(404, "Link unavailable", str(exc), "link-inactive")

    @app.post("/api/v1/links", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
    def create_link(
        body: CreateLinkRequest,
        idempotency_key: Annotated[str | None, Header()] = None,
        link_service: LinkService = Depends(get_service),
    ) -> LinkResponse:
        command = CreateLinkCommand(
            url=body.url,
            custom_alias=body.custom_alias,
            expires_at=body.expires_at,
        )
        return _link_response(
            link_service.create(command, idempotency_key), link_service.settings.base_url
        )

    @app.get("/api/v1/links/{slug}", response_model=LinkResponse)
    def get_link(slug: str, link_service: LinkService = Depends(get_service)) -> LinkResponse:
        return _link_response(link_service.get(slug), link_service.settings.base_url)

    @app.delete("/api/v1/links/{slug}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_link(slug: str, link_service: LinkService = Depends(get_service)) -> Response:
        link_service.delete(slug)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/api/v1/links/{slug}/analytics", response_model=AnalyticsResponse)
    def get_analytics(
        slug: str, link_service: LinkService = Depends(get_service)
    ) -> AnalyticsResponse:
        buckets = link_service.analytics_for(slug)
        return AnalyticsResponse(
            slug=slug.lower(),
            total_clicks=sum(item.click_count for item in buckets),
            buckets=buckets,
            most_recent_click_at=max(
                (item.last_click_at for item in buckets if item.last_click_at), default=None
            ),
        )

    @app.get("/health/live")
    def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    def readiness(link_service: LinkService = Depends(get_service)) -> Response:
        if not link_service.readiness():
            return Response(
                content='{"status":"not_ready"}',
                media_type="application/json",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(content='{"status":"ready"}', media_type="application/json")

    @app.get("/{slug}", response_class=RedirectResponse, status_code=status.HTTP_302_FOUND)
    def redirect(
        slug: str,
        request: Request,
        link_service: LinkService = Depends(get_service),
    ) -> RedirectResponse:
        link = link_service.resolve(
            slug, request.headers.get("referer"), request.headers.get("user-agent")
        )
        return RedirectResponse(link.destination_url, status_code=status.HTTP_302_FOUND)

    return app


def _problem(status_code: int, title: str, detail: str, error_type: str) -> Response:
    return Response(
        content=ProblemDetail(
            type=error_type, title=title, status=status_code, detail=detail
        ).model_dump_json(),
        status_code=status_code,
        media_type="application/problem+json",
    )


logging.basicConfig(level=get_settings().log_level)
app = create_app()
