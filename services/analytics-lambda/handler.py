"""AWS Lambda entry point for processing analytics messages from SQS.

Receives SQS events, delegates to the processor for raw storage,
aggregation, and insight generation.
"""

import json
import logging

from processor import process_metric

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Process a batch of SQS messages.

    Each record's body is a JSON metric message with: user_id, metric_type,
    value, recorded_at, ingested_at.
    """
    records = event.get("Records", [])
    failures = []

    for i, record in enumerate(records):
        try:
            body = json.loads(record["body"])
            correlation_id = (
                record.get("messageAttributes", {})
                .get("correlation_id", {})
                .get("stringValue")
            )
            logger.info(
                "Processing metric",
                extra={
                    "metric_type": body.get("metric_type"),
                    "user_id": body.get("user_id"),
                    "correlation_id": correlation_id,
                },
            )
            process_metric(body)
        except Exception:
            logger.exception("Failed to process record %d", i)
            failures.append({"itemIdentifier": record.get("messageId", str(i))})

    if failures:
        return {"batchItemFailures": failures}

    return {"batchItemFailures": []}
