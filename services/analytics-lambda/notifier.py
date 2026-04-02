"""SNS notification publisher.

Publishes milestone and anomaly alerts to the fitness-analytics-notifications
topic on AWS. Locally, logs the notification payload instead.
"""

import logging
import os

import boto3

logger = logging.getLogger(__name__)

_environment = os.environ.get("ENVIRONMENT", "local")
_sns_topic_arn = os.environ.get("SNS_TOPIC_ARN", "")
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client("sns", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return _client


def send_notification(subject: str, message: str) -> None:
    """Publish a notification. On AWS, sends to SNS. Locally, logs only."""
    full_subject = f"Fitness Tracker: {subject}"

    if _environment == "local" or not _sns_topic_arn:
        logger.info(
            "Notification (local, not sent): %s — %s",
            full_subject,
            message,
        )
        return

    try:
        client = _get_client()
        client.publish(
            TopicArn=_sns_topic_arn,
            Subject=full_subject[:100],
            Message=message,
        )
        logger.info("SNS notification published", extra={"subject": full_subject})
    except Exception:
        logger.exception("Failed to publish SNS notification")
