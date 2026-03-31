"""Boto3 SQS wrapper for sending metric messages to the analytics queue."""

import json
import logging

import boto3

from app.config import settings

logger = logging.getLogger(__name__)

_client = None
_queue_url: str | None = None


def _get_client():
    global _client
    if _client is None:
        kwargs: dict = {"region_name": settings.aws_region}
        if settings.sqs_endpoint_url:
            kwargs["endpoint_url"] = settings.sqs_endpoint_url
        _client = boto3.client("sqs", **kwargs)
    return _client


def _get_queue_url() -> str:
    global _queue_url
    if _queue_url is None:
        client = _get_client()
        resp = client.get_queue_url(QueueName=settings.sqs_queue_name)
        _queue_url = resp["QueueUrl"]
    return _queue_url


def send_message(body: dict, correlation_id: str | None = None) -> str:
    """Send a JSON message to the analytics queue. Returns the SQS MessageId."""
    client = _get_client()
    kwargs: dict = {
        "QueueUrl": _get_queue_url(),
        "MessageBody": json.dumps(body),
    }
    if correlation_id:
        kwargs["MessageAttributes"] = {
            "correlation_id": {"DataType": "String", "StringValue": correlation_id},
        }

    resp = client.send_message(**kwargs)
    logger.info("SQS message sent", extra={"message_id": resp["MessageId"]})
    return resp["MessageId"]
