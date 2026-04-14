from __future__ import annotations

import json
import logging
import time
from http import HTTPStatus
from typing import Any

from pydantic import ValidationError

from app.adapters.dynamodb import DynamoStorage
from app.adapters.queue import SqsQueuePublisher
from app.config import Settings
from app.logging import configure_logging
from app.models import UrlCategorizationRequest
from app.services.main_service import MainService
from app.utils.urls import InvalidUrlError

LOGGER = logging.getLogger(__name__)
SETTINGS = Settings.from_env()
configure_logging(SETTINGS.log_level)
INIT_AT_MONOTONIC = time.perf_counter()
_IS_COLD_START = True


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    global _IS_COLD_START

    handler_start = time.perf_counter()
    request_id = getattr(context, "aws_request_id", None)
    cold_start = _IS_COLD_START
    _IS_COLD_START = False

    service = MainService(
        settings=SETTINGS,
        storage=DynamoStorage(
            SETTINGS.url_categorization_table,
            SETTINGS.url_wip_table,
            region_name=SETTINGS.aws_region,
        ),
        queue_publisher=SqsQueuePublisher(
            SETTINGS.url_fetcher_queue_url,
            region_name=SETTINGS.aws_region,
        ),
    )

    try:
        extract_body_start = time.perf_counter()
        body = _extract_body(event)
        extract_body_ms = _elapsed_ms(extract_body_start)

        validation_start = time.perf_counter()
        request = UrlCategorizationRequest.model_validate(body)
        validation_ms = _elapsed_ms(validation_start)

        service_start = time.perf_counter()
        response = service.process_url(str(request.url))
        service_ms = _elapsed_ms(service_start)
    except (ValidationError, InvalidUrlError) as exc:
        LOGGER.info("invalid_request", extra={"error": str(exc)})
        LOGGER.info(
            "handler_timing",
            extra={
                "aws_request_id": request_id,
                "cold_start": cold_start,
                "time_since_init_ms": int((time.perf_counter() - INIT_AT_MONOTONIC) * 1000),
                "extract_body_ms": locals().get("extract_body_ms", 0),
                "validation_ms": locals().get("validation_ms", 0),
                "service_ms": 0,
                "total_handler_ms": _elapsed_ms(handler_start),
                "result": "invalid_request",
            },
        )
        return _json_response(
            HTTPStatus.BAD_REQUEST,
            {
                "message": "Invalid request payload",
                "details": str(exc),
            },
        )
    except Exception:
        LOGGER.exception("request_failed")
        LOGGER.info(
            "handler_timing",
            extra={
                "aws_request_id": request_id,
                "cold_start": cold_start,
                "time_since_init_ms": int((time.perf_counter() - INIT_AT_MONOTONIC) * 1000),
                "extract_body_ms": locals().get("extract_body_ms", 0),
                "validation_ms": locals().get("validation_ms", 0),
                "service_ms": locals().get("service_ms", 0),
                "total_handler_ms": _elapsed_ms(handler_start),
                "result": "request_failed",
            },
        )
        return _json_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {"message": "Internal server error"},
        )

    status_code = HTTPStatus.OK
    if response.status == "pending":
        status_code = HTTPStatus.ACCEPTED

    LOGGER.info(
        "handler_timing",
        extra={
            "aws_request_id": request_id,
            "cold_start": cold_start,
            "time_since_init_ms": int((time.perf_counter() - INIT_AT_MONOTONIC) * 1000),
            "extract_body_ms": extract_body_ms,
            "validation_ms": validation_ms,
            "service_ms": service_ms,
            "total_handler_ms": _elapsed_ms(handler_start),
            "result": response.status,
        },
    )
    return _json_response(status_code, response.model_dump(exclude_none=True))


def _extract_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body")
    if body is None:
        return event
    if event.get("isBase64Encoded"):
        raise InvalidUrlError("Base64 encoded payloads are not supported")
    if isinstance(body, str):
        return json.loads(body)
    if isinstance(body, dict):
        return body
    raise InvalidUrlError("Request body must be a JSON object")


def _json_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": int(status_code),
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)
