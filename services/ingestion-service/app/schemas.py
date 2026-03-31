"""Pydantic schemas for metric payload validation."""

from datetime import datetime, timedelta, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator

METRIC_RANGES: dict[str, tuple[float, float]] = {
    "heart_rate": (30, 220),
    "steps": (0, 100_000),
    "workout_duration": (1, 480),
    "calories_burned": (0, 10_000),
    "sleep_hours": (0, 24),
    "distance_km": (0, 200),
}


class MetricType(str, Enum):
    heart_rate = "heart_rate"
    steps = "steps"
    workout_duration = "workout_duration"
    calories_burned = "calories_burned"
    sleep_hours = "sleep_hours"
    distance_km = "distance_km"


class MetricIngestRequest(BaseModel):
    metric_type: MetricType
    value: float = Field(ge=0)
    recorded_at: datetime

    @field_validator("value")
    @classmethod
    def value_in_range(cls, v: float, info) -> float:
        mt = info.data.get("metric_type")
        if mt and mt in METRIC_RANGES:
            lo, hi = METRIC_RANGES[mt]
            if not (lo <= v <= hi):
                raise ValueError(f"Value {v} out of range [{lo}, {hi}] for {mt}")
        return v

    @field_validator("recorded_at")
    @classmethod
    def not_in_future(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("recorded_at cannot be in the future")
        return v


class BatchIngestRequest(BaseModel):
    metrics: list[MetricIngestRequest] = Field(min_length=1, max_length=50)


class IngestResponse(BaseModel):
    message: str
    message_id: str


class BatchIngestResponse(BaseModel):
    message: str
    accepted_count: int
    message_ids: list[str]


class MetricHistoryItem(BaseModel):
    id: str
    metric_type: str
    value: float
    recorded_at: datetime


class MetricHistoryResponse(BaseModel):
    metrics: list[MetricHistoryItem]
    total: int
    limit: int
    offset: int


class AggregationItem(BaseModel):
    metric_type: str
    period: str
    date: str
    avg_value: float
    min_value: float
    max_value: float


class InsightItem(BaseModel):
    type: str
    description: str
    generated_at: datetime


class MetricSummaryResponse(BaseModel):
    aggregations: list[AggregationItem]
    insights: list[InsightItem]
