"""Local SQS poller for docker-compose development.

Polls LocalStack SQS, formats messages into the Lambda event structure,
and calls lambda_handler() directly. Used in place of the AWS event
source mapping during local development.
"""

import json
import logging
import os
import sys
import time

import boto3

from handler import lambda_handler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger("analytics-worker")

SQS_ENDPOINT = os.environ.get("SQS_ENDPOINT_URL", "http://localhost:4566")
QUEUE_NAME = os.environ.get("SQS_QUEUE_NAME", "analytics-queue")
REGION = os.environ.get("AWS_REGION", "us-east-1")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "2"))


def main() -> None:
    sqs = boto3.client("sqs", endpoint_url=SQS_ENDPOINT, region_name=REGION)

    logger.info("Ensuring queue '%s' exists on %s", QUEUE_NAME, SQS_ENDPOINT)
    resp = sqs.create_queue(QueueName=QUEUE_NAME)
    queue_url = resp["QueueUrl"]
    logger.info("Polling %s", queue_url)

    while True:
        try:
            result = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=5,
                MessageAttributeNames=["All"],
            )
            messages = result.get("Messages", [])

            if not messages:
                time.sleep(POLL_INTERVAL)
                continue

            records = []
            for msg in messages:
                record = {
                    "messageId": msg["MessageId"],
                    "body": msg["Body"],
                    "messageAttributes": {
                        k: {"stringValue": v.get("StringValue", "")}
                        for k, v in msg.get("MessageAttributes", {}).items()
                    },
                }
                records.append(record)

            event = {"Records": records}
            response = lambda_handler(event, None)

            failed_ids = {f["itemIdentifier"] for f in response.get("batchItemFailures", [])}
            for msg, record in zip(messages, records):
                if record["messageId"] not in failed_ids:
                    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"])
                    logger.info("Deleted message %s", record["messageId"])
                else:
                    logger.warning("Message %s failed, leaving for retry", record["messageId"])

        except KeyboardInterrupt:
            logger.info("Shutting down")
            sys.exit(0)
        except Exception:
            logger.exception("Error in poll loop")
            time.sleep(POLL_INTERVAL * 2)


if __name__ == "__main__":
    main()
