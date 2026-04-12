from __future__ import annotations

import json
import logging
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


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
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
        request = UrlCategorizationRequest.model_validate(_extract_body(event))
        response = service.process_url(str(request.url))
    except (ValidationError, InvalidUrlError) as exc:
        LOGGER.info("invalid_request", extra={"error": str(exc)})
        return _json_response(
            HTTPStatus.BAD_REQUEST,
            {
                "message": "Invalid request payload",
                "details": str(exc),
            },
        )
    except Exception:
        LOGGER.exception("request_failed")
        return _json_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {"message": "Internal server error"},
        )

    status_code = HTTPStatus.OK
    if response.status == "pending":
        status_code = HTTPStatus.ACCEPTED

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
