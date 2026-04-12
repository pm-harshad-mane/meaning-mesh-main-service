from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class Category(BaseModel):
    id: str
    name: str
    score: float
    rank: int


class UrlCategorizationRequest(BaseModel):
    url: HttpUrl


class UrlCategorizationResponse(BaseModel):
    status: Literal["ready", "pending", "unknown"]
    url: str | None = None
    categories: list[Category] = Field(default_factory=list)


class CategorizationRecord(BaseModel):
    url_hash: str
    normalized_url: str
    status: Literal["ready", "unknown", "fetch_failed"]
    categories: list[Category]
    model_version: str | None = None
    source_http_status: int | None = None
    source_content_type: str | None = None
    title: str | None = None
    content_fingerprint: str | None = None
    first_seen_at: int
    last_updated_at: int
    expires_at: int
    trace_id: str
    error_code: str | None = None
    error_message: str | None = None


class WipRecord(BaseModel):
    url_hash: str
    normalized_url: str
    state: Literal["queued", "fetching", "categorizing"]
    created_at: int
    updated_at: int
    expires_at: int
    fetch_attempts: int = 0
    request_count: int = 1
    trace_id: str
    owner: str


class FetchQueueMessage(BaseModel):
    url_hash: str
    normalized_url: str
    trace_id: str
    queued_at: int
    requested_ttl_seconds: int
