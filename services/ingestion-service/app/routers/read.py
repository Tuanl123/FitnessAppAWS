"""Metric read routes: history and summary from analytics_db."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query

from app import db_reader
from app.schemas import MetricHistoryResponse, MetricSummaryResponse
from shared.auth import get_current_user

router = APIRouter()


@router.get("/history", response_model=MetricHistoryResponse)
async def get_history(
    user_id: uuid.UUID = Depends(get_current_user),
    metric_type: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Retrieve raw metric history for the authenticated user."""
    rows, total = await db_reader.query_history(
        user_id, metric_type, start_date, end_date, limit, offset
    )
    metrics = [
        {"id": str(r["id"]), "metric_type": r["metric_type"], "value": r["value"], "recorded_at": r["recorded_at"]}
        for r in rows
    ]
    return MetricHistoryResponse(metrics=metrics, total=total, limit=limit, offset=offset)


@router.get("/summary", response_model=MetricSummaryResponse)
async def get_summary(
    user_id: uuid.UUID = Depends(get_current_user),
    period: str = Query("daily", pattern="^(daily|weekly)$"),
    metric_type: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
):
    """Retrieve aggregated analytics and insights for the authenticated user."""
    aggregations, insights = await db_reader.query_summary(
        user_id, period, metric_type, start_date, end_date
    )
    return MetricSummaryResponse(aggregations=aggregations, insights=insights)
