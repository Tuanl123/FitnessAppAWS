"""Tests for metric ingestion endpoints."""

import pytest
from datetime import datetime, timezone


async def test_ingest_single_metric(client):
    resp = await client.post(
        "/ingest",
        json={
            "metric_type": "heart_rate",
            "value": 72.0,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["message"] == "Metric accepted for processing"
    assert data["message_id"] == "mock-msg-id"


async def test_ingest_invalid_metric_type(client):
    resp = await client.post(
        "/ingest",
        json={
            "metric_type": "invalid_type",
            "value": 50,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert resp.status_code == 422


async def test_ingest_value_out_of_range(client):
    resp = await client.post(
        "/ingest",
        json={
            "metric_type": "heart_rate",
            "value": 300,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert resp.status_code == 422


async def test_ingest_future_timestamp(client):
    from datetime import timedelta

    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    resp = await client.post(
        "/ingest",
        json={"metric_type": "steps", "value": 5000, "recorded_at": future},
    )
    assert resp.status_code == 422


async def test_ingest_batch(client):
    now = datetime.now(timezone.utc).isoformat()
    resp = await client.post(
        "/ingest/batch",
        json={
            "metrics": [
                {"metric_type": "steps", "value": 8500, "recorded_at": now},
                {"metric_type": "calories_burned", "value": 2100, "recorded_at": now},
            ]
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["accepted_count"] == 2
    assert len(data["message_ids"]) == 2


async def test_ingest_batch_too_large(client):
    now = datetime.now(timezone.utc).isoformat()
    metrics = [{"metric_type": "steps", "value": 100, "recorded_at": now}] * 51
    resp = await client.post("/ingest/batch", json={"metrics": metrics})
    assert resp.status_code == 422


async def test_ingest_unauthorized():
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post(
            "/ingest",
            json={
                "metric_type": "steps",
                "value": 5000,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    assert resp.status_code in (401, 403)


async def test_get_history(client):
    resp = await client.get("/history")
    assert resp.status_code == 200
    data = resp.json()
    assert "metrics" in data
    assert "total" in data


async def test_get_summary(client):
    resp = await client.get("/summary", params={"period": "daily"})
    assert resp.status_code == 200
    data = resp.json()
    assert "aggregations" in data
    assert "insights" in data
