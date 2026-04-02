"""Three-stage analytics processing pipeline.

Stage 1: Raw storage — insert into raw_metrics (idempotent).
Stage 2: Aggregation — recalculate daily/weekly processed_metrics.
Stage 3: Insight generation — anomaly detection, trend analysis, milestone checks.
"""

import logging
import uuid
from datetime import datetime, timezone

from db import get_connection, dict_cursor
from notifier import send_notification

logger = logging.getLogger(__name__)

ANOMALY_THRESHOLDS: dict[str, dict[str, float]] = {
    "heart_rate": {"low": 35, "high": 200},
    "steps": {"high": 50_000},
    "workout_duration": {"high": 300},
    "sleep_hours": {"low": 2, "high": 14},
}

METRIC_UNITS: dict[str, str] = {
    "heart_rate": "bpm",
    "steps": "steps",
    "workout_duration": "min",
    "calories_burned": "kcal",
    "sleep_hours": "hrs",
    "distance_km": "km",
}

METRIC_DISPLAY: dict[str, str] = {
    "heart_rate": "heart rate",
    "steps": "daily step count",
    "workout_duration": "workout duration",
    "calories_burned": "calories burned",
    "sleep_hours": "sleep",
    "distance_km": "distance",
}

WORKOUT_MILESTONES = [10, 25, 50, 100, 250, 500, 1000]
DISTANCE_MILESTONES = [100, 500, 1000, 5000]
STREAK_MILESTONES = [7, 14, 30, 60, 90]


def process_metric(message: dict) -> None:
    """Run the full 3-stage pipeline for a single metric message."""
    user_id = message["user_id"]
    metric_type = message["metric_type"]
    value = float(message["value"])
    recorded_at = datetime.fromisoformat(message["recorded_at"])
    ingested_at = datetime.fromisoformat(message.get("ingested_at", datetime.now(timezone.utc).isoformat()))

    with get_connection() as conn:
        inserted = _stage1_raw_storage(conn, user_id, metric_type, value, recorded_at, ingested_at)
        if not inserted:
            logger.info("Duplicate metric skipped", extra={"user_id": user_id, "metric_type": metric_type})
            return

        _stage2_aggregation(conn, user_id, metric_type, recorded_at)
        _stage3_insights(conn, user_id, metric_type, value, recorded_at)


def _stage1_raw_storage(conn, user_id, metric_type, value, recorded_at, ingested_at) -> bool:
    """Insert into raw_metrics. Returns False if duplicate."""
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO raw_metrics (id, user_id, metric_type, value, recorded_at, ingested_at)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (user_id, metric_type, recorded_at) DO NOTHING""",
            (str(uuid.uuid4()), user_id, metric_type, value, recorded_at, ingested_at),
        )
        return cur.rowcount > 0


def _stage2_aggregation(conn, user_id, metric_type, recorded_at) -> None:
    """Recalculate daily and weekly aggregations for the period containing recorded_at."""
    with conn.cursor() as cur:
        for period, trunc in [("daily", "day"), ("weekly", "week")]:
            cur.execute(
                f"""INSERT INTO processed_metrics
                        (id, user_id, metric_type, period, period_start,
                         avg_value, min_value, max_value, sample_count, calculated_at)
                    SELECT gen_random_uuid(), %s::uuid, %s, %s, date_trunc(%s, %s::timestamptz)::date,
                           AVG(value), MIN(value), MAX(value), COUNT(*), NOW()
                    FROM raw_metrics
                    WHERE user_id = %s
                      AND metric_type = %s
                      AND date_trunc(%s, recorded_at) = date_trunc(%s, %s::timestamptz)
                    ON CONFLICT (user_id, metric_type, period, period_start)
                    DO UPDATE SET avg_value = EXCLUDED.avg_value,
                                  min_value = EXCLUDED.min_value,
                                  max_value = EXCLUDED.max_value,
                                  sample_count = EXCLUDED.sample_count,
                                  calculated_at = EXCLUDED.calculated_at""",
                (user_id, metric_type, period, trunc, recorded_at.isoformat(),
                 user_id, metric_type, trunc, trunc, recorded_at.isoformat()),
            )


def _stage3_insights(conn, user_id, metric_type, value, recorded_at) -> None:
    """Evaluate anomaly, trend, and milestone rules."""
    _check_anomaly(conn, user_id, metric_type, value)
    _check_milestones(conn, user_id, metric_type)
    _check_trends(conn, user_id, metric_type, recorded_at)


_ANOMALY_HIGH_CONTEXT: dict[str, str] = {
    "heart_rate": "If this was not during intense exercise, consider consulting a healthcare professional.",
    "steps": "That's extraordinary — make sure you're giving your body enough rest to recover.",
    "workout_duration": "Extended sessions increase injury risk. Consider splitting into shorter workouts.",
    "sleep_hours": "Consistently oversleeping may indicate an underlying health issue worth checking.",
}

_ANOMALY_LOW_CONTEXT: dict[str, str] = {
    "heart_rate": "A resting heart rate this low (bradycardia) may need medical attention.",
    "sleep_hours": "Severe sleep deprivation impacts recovery, focus, and long-term health.",
}


def _check_anomaly(conn, user_id, metric_type, value) -> None:
    thresholds = ANOMALY_THRESHOLDS.get(metric_type)
    if not thresholds:
        return

    unit = METRIC_UNITS.get(metric_type, "")
    label = METRIC_DISPLAY.get(metric_type, metric_type.replace("_", " "))

    alert_msg = None
    if "high" in thresholds and value > thresholds["high"]:
        context = _ANOMALY_HIGH_CONTEXT.get(metric_type, "")
        alert_msg = (
            f"Your {label} of {value:g} {unit} is unusually high. "
            f"{context}"
        )
    elif "low" in thresholds and value < thresholds["low"]:
        context = _ANOMALY_LOW_CONTEXT.get(metric_type, "")
        alert_msg = (
            f"Your {label} of {value:g} {unit} is critically low. "
            f"{context}"
        )

    if alert_msg:
        _insert_insight(conn, user_id, "anomaly", metric_type, alert_msg)
        send_notification("Health Metric Alert", alert_msg)


def _check_milestones(conn, user_id, metric_type) -> None:
    if metric_type == "workout_duration":
        _check_count_milestone(conn, user_id, "workout_duration", WORKOUT_MILESTONES, "workout")
    elif metric_type == "distance_km":
        _check_cumulative_milestone(conn, user_id, "distance_km", DISTANCE_MILESTONES, "km total distance")


def _check_count_milestone(conn, user_id, metric_type, milestones, label) -> None:
    with dict_cursor(conn) as cur:
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM raw_metrics WHERE user_id = %s AND metric_type = %s",
            (user_id, metric_type),
        )
        count = cur.fetchone()["cnt"]

    for m in milestones:
        if count == m:
            desc = f"You have logged {m} {label}s!"
            if not _insight_exists(conn, user_id, "milestone", desc):
                _insert_insight(conn, user_id, "milestone", metric_type, desc)
                send_notification("New Milestone Achieved!", desc)


def _check_cumulative_milestone(conn, user_id, metric_type, milestones, unit) -> None:
    with dict_cursor(conn) as cur:
        cur.execute(
            "SELECT COALESCE(SUM(value), 0) AS total FROM raw_metrics WHERE user_id = %s AND metric_type = %s",
            (user_id, metric_type),
        )
        total = cur.fetchone()["total"]

    for m in milestones:
        if total >= m:
            desc = f"You have reached {m} {unit}!"
            if not _insight_exists(conn, user_id, "milestone", desc):
                _insert_insight(conn, user_id, "milestone", metric_type, desc)
                send_notification("New Milestone Achieved!", desc)


_TREND_POSITIVE: dict[str, dict[str, str]] = {
    "steps": {"up": "Great job staying active!", "down": "Try to find opportunities to walk more throughout the day."},
    "heart_rate": {"up": "An increasing resting heart rate may signal overtraining or stress.", "down": "A lower resting heart rate is a sign of improving cardiovascular fitness."},
    "workout_duration": {"up": "Nice work increasing your training volume!", "down": "Shorter sessions are fine — consistency matters more than duration."},
    "calories_burned": {"up": "You're burning more energy — make sure you're fueling properly.", "down": "Consider adding some higher-intensity activities to your routine."},
    "sleep_hours": {"up": "More rest is helping your recovery.", "down": "Try to prioritize sleep — it's essential for recovery and performance."},
    "distance_km": {"up": "You're covering more ground. Keep building gradually!", "down": "A lighter week is okay — recovery is part of progress."},
}


def _check_trends(conn, user_id, metric_type, recorded_at) -> None:
    """Compare this week's average to last week's. Generate trend if >10% change."""
    with dict_cursor(conn) as cur:
        cur.execute(
            """SELECT period_start, avg_value
               FROM processed_metrics
               WHERE user_id = %s AND metric_type = %s AND period = 'weekly'
               ORDER BY period_start DESC LIMIT 2""",
            (user_id, metric_type),
        )
        rows = cur.fetchall()

    if len(rows) < 2:
        return

    this_week = rows[0]
    last_week = rows[1]
    if last_week["avg_value"] == 0:
        return

    pct_change = ((this_week["avg_value"] - last_week["avg_value"]) / last_week["avg_value"]) * 100

    if abs(pct_change) < 10:
        return

    unit = METRIC_UNITS.get(metric_type, "")
    label = METRIC_DISPLAY.get(metric_type, metric_type.replace("_", " "))
    direction = "up" if pct_change > 0 else "down"
    arrow = "↑" if pct_change > 0 else "↓"

    tips = _TREND_POSITIVE.get(metric_type, {})
    tip = tips.get(direction, "")

    desc = (
        f"Your average {label} is {arrow} {abs(pct_change):.0f}% this week "
        f"({last_week['avg_value']:.0f} → {this_week['avg_value']:.0f} {unit}). "
        f"{tip}"
    )

    week_key = str(this_week["period_start"])
    full_desc = f"[{week_key}] {desc}"
    if not _insight_exists(conn, user_id, "trend", full_desc):
        _insert_insight(conn, user_id, "trend", metric_type, full_desc)


def _insert_insight(conn, user_id, insight_type, metric_type, description) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO aggregations (id, user_id, insight_type, metric_type, description, generated_at)
               VALUES (%s, %s, %s, %s, %s, NOW())""",
            (str(uuid.uuid4()), user_id, insight_type, metric_type, description),
        )
    logger.info("Insight generated", extra={"type": insight_type, "user_id": user_id})


def _insight_exists(conn, user_id, insight_type, description) -> bool:
    with dict_cursor(conn) as cur:
        cur.execute(
            "SELECT 1 FROM aggregations WHERE user_id = %s AND insight_type = %s AND description = %s LIMIT 1",
            (user_id, insight_type, description),
        )
        return cur.fetchone() is not None
