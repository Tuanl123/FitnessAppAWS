"""Metric ingestion routes: single and batch ingest via SQS."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status

from app.schemas import (
    BatchIngestRequest,
    BatchIngestResponse,
    IngestResponse,
    MetricIngestRequest,
)
from app import sqs_client
from shared.auth import get_current_user

router = APIRouter()


def _build_sqs_body(user_id: uuid.UUID, metric: MetricIngestRequest) -> dict:
    return {
        "user_id": str(user_id),
        "metric_type": metric.metric_type.value,
        "value": metric.value,
        "recorded_at": metric.recorded_at.isoformat(),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED, response_model=IngestResponse)
async def ingest_metric(
    body: MetricIngestRequest,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user),
):
    """Validate a single metric and send it to the SQS analytics queue."""
    correlation_id = getattr(request.state, "correlation_id", None)
    sqs_body = _build_sqs_body(user_id, body)
    message_id = sqs_client.send_message(sqs_body, correlation_id)
    return IngestResponse(message="Metric accepted for processing", message_id=message_id)


@router.post("/ingest/batch", status_code=status.HTTP_202_ACCEPTED, response_model=BatchIngestResponse)
async def ingest_batch(
    body: BatchIngestRequest,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user),
):
    """Validate a batch of metrics and send each to the SQS analytics queue."""
    correlation_id = getattr(request.state, "correlation_id", None)
    message_ids: list[str] = []
    for metric in body.metrics:
        sqs_body = _build_sqs_body(user_id, metric)
        mid = sqs_client.send_message(sqs_body, correlation_id)
        message_ids.append(mid)

    return BatchIngestResponse(
        message="Batch accepted for processing",
        accepted_count=len(message_ids),
        message_ids=message_ids,
    )
