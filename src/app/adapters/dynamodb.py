from __future__ import annotations

from typing import Any

import boto3
from botocore.exceptions import ClientError

from app.models import CategorizationRecord, WipRecord


class DynamoStorage:
    def __init__(
        self,
        categorization_table_name: str,
        wip_table_name: str,
        *,
        region_name: str,
    ) -> None:
        dynamodb = boto3.resource("dynamodb", region_name=region_name)
        self._categorization_table = dynamodb.Table(categorization_table_name)
        self._wip_table = dynamodb.Table(wip_table_name)

    def get_categorization(self, url_hash: str) -> CategorizationRecord | None:
        response = self._categorization_table.get_item(Key={"url_hash": url_hash})
        item = response.get("Item")
        if not item:
            return None
        return CategorizationRecord.model_validate(item)

    def create_wip_if_absent(self, record: WipRecord) -> bool:
        try:
            self._wip_table.put_item(
                Item=record.model_dump(),
                ConditionExpression="attribute_not_exists(url_hash)",
            )
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise

    def delete_wip(self, url_hash: str) -> None:
        self._wip_table.delete_item(Key={"url_hash": url_hash})
