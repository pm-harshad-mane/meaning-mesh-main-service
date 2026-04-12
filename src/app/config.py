from __future__ import annotations

import os
from dataclasses import dataclass


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    aws_region: str
    url_categorization_table: str
    url_wip_table: str
    url_fetcher_queue_url: str
    url_cache_ttl_seconds: int
    url_wip_ttl_seconds: int
    strip_tracking_params: bool
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            url_categorization_table=os.getenv(
                "URL_CATEGORIZATION_TABLE",
                "url_categorization",
            ),
            url_wip_table=os.getenv("URL_WIP_TABLE", "url_wip"),
            url_fetcher_queue_url=os.getenv("URL_FETCHER_QUEUE_URL", ""),
            url_cache_ttl_seconds=_get_int("URL_CACHE_TTL_SECONDS", 2_592_000),
            url_wip_ttl_seconds=_get_int("URL_WIP_TTL_SECONDS", 900),
            strip_tracking_params=_get_bool("STRIP_TRACKING_PARAMS", True),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
