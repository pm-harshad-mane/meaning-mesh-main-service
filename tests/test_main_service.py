from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.models import Category, CategorizationRecord, FetchQueueMessage, WipRecord
from app.services.main_service import MainService


class FakeStorage:
    def __init__(
        self,
        *,
        cached_record: CategorizationRecord | None = None,
        create_wip_result: bool = True,
    ) -> None:
        self.cached_record = cached_record
        self.create_wip_result = create_wip_result
        self.created_records: list[WipRecord] = []
        self.deleted_wip_hashes: list[str] = []

    def get_categorization(self, url_hash: str) -> CategorizationRecord | None:
        return self.cached_record

    def create_wip_if_absent(self, record: WipRecord) -> bool:
        self.created_records.append(record)
        return self.create_wip_result

    def delete_wip(self, url_hash: str) -> None:
        self.deleted_wip_hashes.append(url_hash)


@dataclass
class FakePublisher:
    sent_messages: list[FetchQueueMessage]

    def send_fetch_job(self, message: FetchQueueMessage) -> None:
        self.sent_messages.append(message)


def _settings() -> Settings:
    return Settings(
        aws_region="us-east-1",
        url_categorization_table="url_categorization",
        url_wip_table="url_wip",
        url_fetcher_queue_url="https://example.com/queue",
        url_cache_ttl_seconds=2_592_000,
        url_wip_ttl_seconds=900,
        strip_tracking_params=True,
        log_level="INFO",
    )


def test_process_url_returns_cached_ready_response() -> None:
    storage = FakeStorage(
        cached_record=CategorizationRecord(
            url_hash="sha256:test",
            normalized_url="https://example.com/news",
            status="ready",
            categories=[
                Category(id="IAB12", name="News and Politics", score=0.94, rank=1)
            ],
            model_version="model-v1",
            first_seen_at=100,
            last_updated_at=100,
            expires_at=4_102_444_800,
            trace_id="trace-1",
        )
    )
    publisher = FakePublisher(sent_messages=[])
    service = MainService(settings=_settings(), storage=storage, queue_publisher=publisher)

    response = service.process_url("https://example.com/news")

    assert response.status == "ready"
    assert response.url == "https://example.com/news"
    assert publisher.sent_messages == []


def test_process_url_returns_pending_when_work_already_exists() -> None:
    storage = FakeStorage(create_wip_result=False)
    publisher = FakePublisher(sent_messages=[])
    service = MainService(settings=_settings(), storage=storage, queue_publisher=publisher)

    response = service.process_url("https://example.com/path")

    assert response.status == "pending"
    assert response.categories == []
    assert publisher.sent_messages == []


def test_process_url_enqueues_fetch_job_on_cache_miss() -> None:
    storage = FakeStorage()
    publisher = FakePublisher(sent_messages=[])
    service = MainService(settings=_settings(), storage=storage, queue_publisher=publisher)

    response = service.process_url("https://example.com/path?utm_source=x&b=2&a=1")

    assert response.status == "pending"
    assert len(storage.created_records) == 1
    assert storage.created_records[0].normalized_url == "https://example.com/path?a=1&b=2"
    assert len(publisher.sent_messages) == 1
    assert publisher.sent_messages[0].requested_ttl_seconds == 2_592_000
