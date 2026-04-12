from __future__ import annotations

import json

import boto3

from app.models import FetchQueueMessage


class SqsQueuePublisher:
    def __init__(self, queue_url: str, *, region_name: str) -> None:
        self._client = boto3.client("sqs", region_name=region_name)
        self._queue_url = queue_url

    def send_fetch_job(self, message: FetchQueueMessage) -> None:
        self._client.send_message(
            QueueUrl=self._queue_url,
            MessageBody=json.dumps(message.model_dump()),
        )
