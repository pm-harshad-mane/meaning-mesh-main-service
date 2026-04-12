from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Protocol

from app.config import Settings
from app.models import (
    CategorizationRecord,
    FetchQueueMessage,
    UrlCategorizationResponse,
    WipRecord,
)
from app.utils.time import unix_timestamp
from app.utils.urls import hash_normalized_url, normalize_url

LOGGER = logging.getLogger(__name__)


class StorageProtocol(Protocol):
    def get_categorization(self, url_hash: str) -> CategorizationRecord | None: ...

    def create_wip_if_absent(self, record: WipRecord) -> bool: ...

    def delete_wip(self, url_hash: str) -> None: ...


class QueuePublisherProtocol(Protocol):
    def send_fetch_job(self, message: FetchQueueMessage) -> None: ...


@dataclass
class MainService:
    settings: Settings
    storage: StorageProtocol
    queue_publisher: QueuePublisherProtocol

    def process_url(self, raw_url: str) -> UrlCategorizationResponse:
        normalized_url = normalize_url(
            raw_url,
            strip_tracking_params=self.settings.strip_tracking_params,
        )
        url_hash = hash_normalized_url(normalized_url)
        now = unix_timestamp()

        cached_record = self.storage.get_categorization(url_hash)
        if cached_record and cached_record.expires_at > now:
            LOGGER.info(
                "cache_hit",
                extra={"url_hash": url_hash, "status": cached_record.status},
            )
            return self._response_from_record(cached_record)

        trace_id = _new_trace_id()
        created = self.storage.create_wip_if_absent(
            WipRecord(
                url_hash=url_hash,
                normalized_url=normalized_url,
                state="queued",
                created_at=now,
                updated_at=now,
                expires_at=now + self.settings.url_wip_ttl_seconds,
                fetch_attempts=0,
                request_count=1,
                trace_id=trace_id,
                owner="main-service",
            )
        )
        if not created:
            LOGGER.info("work_already_in_flight", extra={"url_hash": url_hash})
            return UrlCategorizationResponse(status="pending", categories=[])

        try:
            self.queue_publisher.send_fetch_job(
                FetchQueueMessage(
                    url_hash=url_hash,
                    normalized_url=normalized_url,
                    trace_id=trace_id,
                    queued_at=now,
                    requested_ttl_seconds=self.settings.url_cache_ttl_seconds,
                )
            )
        except Exception:
            self.storage.delete_wip(url_hash)
            LOGGER.exception("fetch_enqueue_failed", extra={"url_hash": url_hash})
            raise

        LOGGER.info("fetch_enqueued", extra={"url_hash": url_hash, "trace_id": trace_id})
        return UrlCategorizationResponse(status="pending", categories=[])

    @staticmethod
    def _response_from_record(
        record: CategorizationRecord,
    ) -> UrlCategorizationResponse:
        if record.status == "ready":
            return UrlCategorizationResponse(
                status="ready",
                url=record.normalized_url,
                categories=record.categories,
            )
        return UrlCategorizationResponse(
            status="unknown",
            url=record.normalized_url,
            categories=record.categories,
        )


def _new_trace_id() -> str:
    return f"trace-{uuid.uuid4().hex}"
