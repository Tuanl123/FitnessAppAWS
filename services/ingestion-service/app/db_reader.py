"""Read-only psycopg2 connection to analytics_db for metric history and summary queries."""

import asyncio
import uuid
from datetime import date

import psycopg2
import psycopg2.extras

from app.config import settings


def _connect():
    return psycopg2.connect(settings.analytics_db_url)


def _query_history_sync(
    user_id: uuid.UUID,
    metric_type: str | None,
    start_date: date | None,
    end_date: date | None,
    limit: int,
    offset: int,
) -> tuple[list[dict], int]:
    conditions = ["user_id = %s"]
    params: list = [str(user_id)]

    if metric_type:
        conditions.append("metric_type = %s")
        params.append(metric_type)
    if start_date:
        conditions.append("recorded_at >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("recorded_at <= %s")
        params.append(end_date)

    where = " AND ".join(conditions)

    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SELECT COUNT(*) AS cnt FROM raw_metrics WHERE {where}", params)
            total = cur.fetchone()["cnt"]

            cur.execute(
                f"SELECT id, metric_type, value, recorded_at FROM raw_metrics "
                f"WHERE {where} ORDER BY recorded_at DESC LIMIT %s OFFSET %s",
                [*params, limit, offset],
            )
            rows = cur.fetchall()

    return [dict(r) for r in rows], total


async def query_history(
    user_id: uuid.UUID,
    metric_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _query_history_sync, user_id, metric_type, start_date, end_date, limit, offset
    )


def _query_summary_sync(
    user_id: uuid.UUID,
    period: str,
    metric_type: str | None,
    start_date: date | None,
    end_date: date | None,
) -> tuple[list[dict], list[dict]]:
    agg_conds = ["user_id = %s", "period = %s"]
    agg_params: list = [str(user_id), period]

    if metric_type:
        agg_conds.append("metric_type = %s")
        agg_params.append(metric_type)
    if start_date:
        agg_conds.append("period_start >= %s")
        agg_params.append(start_date)
    if end_date:
        agg_conds.append("period_start <= %s")
        agg_params.append(end_date)

    ins_conds = ["user_id = %s"]
    ins_params: list = [str(user_id)]

    if metric_type:
        ins_conds.append("metric_type = %s")
        ins_params.append(metric_type)
    if start_date:
        ins_conds.append("generated_at::date >= %s")
        ins_params.append(start_date)
    if end_date:
        ins_conds.append("generated_at::date <= %s")
        ins_params.append(end_date)

    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            agg_where = " AND ".join(agg_conds)
            cur.execute(
                f"SELECT metric_type, period, period_start::text AS date, "
                f"avg_value, min_value, max_value "
                f"FROM processed_metrics WHERE {agg_where} "
                f"ORDER BY period_start DESC LIMIT 100",
                agg_params,
            )
            aggregations = [dict(r) for r in cur.fetchall()]

            ins_where = " AND ".join(ins_conds)
            cur.execute(
                f"SELECT insight_type AS type, description, generated_at "
                f"FROM aggregations WHERE {ins_where} "
                f"ORDER BY generated_at DESC LIMIT 50",
                ins_params,
            )
            insights = [dict(r) for r in cur.fetchall()]

    return aggregations, insights


async def query_summary(
    user_id: uuid.UUID,
    period: str,
    metric_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[list[dict], list[dict]]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _query_summary_sync, user_id, period, metric_type, start_date, end_date
    )
