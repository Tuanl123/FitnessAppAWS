#!/usr/bin/env python3
"""Seed the database with ~60 days of realistic fitness metrics for testing.

Usage:
    python scripts/seed-data.py [--api-url http://localhost:80]

Creates a test user (seed@test.com / SeedPass123) and ingests randomized
metrics across all 6 types. Includes enough data to trigger trends,
milestones, and anomalies in the analytics pipeline.
"""

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError

API_URL = "http://localhost:80"
EMAIL = "seed@test.com"
PASSWORD = "SeedPass123"
NAME = "Seed User"
DAYS = 60


_api_url = API_URL


def api(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    url = f"{_api_url}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        err_body = e.read().decode()
        if e.code == 409:
            return {"conflict": True}
        print(f"  API error {e.code}: {err_body}", file=sys.stderr)
        raise


def get_token() -> str:
    print("Setting up seed user...")
    resp = api("POST", "/api/users/auth/register", {
        "email": EMAIL, "password": PASSWORD, "name": NAME,
    })
    if resp.get("conflict"):
        resp = api("POST", "/api/users/auth/login", {
            "email": EMAIL, "password": PASSWORD,
        })
    token = resp["access_token"]

    api("PUT", "/api/users/profile", {
        "age": 28, "weight": 72.5, "fitness_goals": "Complete a half marathon and improve resting heart rate",
    }, token)

    print(f"  Logged in as {EMAIL}")
    return token


def generate_metrics(days: int) -> list[dict]:
    """Generate realistic daily metrics for the given number of days."""
    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    metrics = []

    steps_base = 7500
    hr_base = 68
    workout_streak = 0

    for day_offset in range(days, 0, -1):
        date = now - timedelta(days=day_offset)
        is_weekend = date.weekday() >= 5

        # Steps — daily, with weekly variation and a trend upward over time
        trend_boost = (days - day_offset) * 30
        steps = int(steps_base + trend_boost + random.gauss(0, 1200))
        if is_weekend:
            steps = int(steps * random.uniform(1.05, 1.3))
        steps = max(1500, min(steps, 25000))
        metrics.append({
            "metric_type": "steps",
            "value": steps,
            "recorded_at": (date + timedelta(hours=20, minutes=random.randint(0, 59))).isoformat(),
        })

        # Heart rate — resting measurement each morning
        hr = round(hr_base + random.gauss(0, 4), 1)
        hr = max(45, min(hr, 95))
        metrics.append({
            "metric_type": "heart_rate",
            "value": hr,
            "recorded_at": (date + timedelta(hours=7, minutes=random.randint(0, 30))).isoformat(),
        })

        # Workout duration — 4-5 days per week
        does_workout = random.random() < (0.65 if not is_weekend else 0.8)
        if does_workout:
            workout_streak += 1
            duration = round(random.gauss(45, 15), 1)
            duration = max(15, min(duration, 120))
            metrics.append({
                "metric_type": "workout_duration",
                "value": duration,
                "recorded_at": (date + timedelta(hours=random.choice([6, 7, 17, 18]), minutes=random.randint(0, 30))).isoformat(),
            })

            cals = round(duration * random.uniform(6, 10))
            cals = max(80, min(cals, 1200))
            metrics.append({
                "metric_type": "calories_burned",
                "value": cals,
                "recorded_at": (date + timedelta(hours=random.choice([6, 7, 17, 18]), minutes=random.randint(30, 59))).isoformat(),
            })
        else:
            workout_streak = 0

        # Sleep — nightly
        sleep = round(random.gauss(7.2, 0.8), 1)
        if is_weekend:
            sleep = round(sleep + random.uniform(0.3, 1.0), 1)
        sleep = max(4.5, min(sleep, 10))
        metrics.append({
            "metric_type": "sleep_hours",
            "value": sleep,
            "recorded_at": (date + timedelta(hours=6, minutes=random.randint(0, 30))).isoformat(),
        })

        # Distance — on workout days
        if does_workout and random.random() < 0.7:
            dist = round(random.gauss(5.5, 2.0), 2)
            dist = max(1.0, min(dist, 15.0))
            metrics.append({
                "metric_type": "distance_km",
                "value": dist,
                "recorded_at": (date + timedelta(hours=random.choice([7, 18]), minutes=random.randint(0, 59))).isoformat(),
            })

    # Inject a few anomalies for insight generation
    recent = now - timedelta(days=2)
    metrics.append({
        "metric_type": "heart_rate",
        "value": 210,
        "recorded_at": (recent + timedelta(hours=15)).isoformat(),
    })
    metrics.append({
        "metric_type": "sleep_hours",
        "value": 1.5,
        "recorded_at": (recent + timedelta(hours=6)).isoformat(),
    })

    return metrics


def ingest_all(token: str, metrics: list[dict]) -> None:
    """Send metrics in batches of 50 via the batch endpoint."""
    total = len(metrics)
    sent = 0

    for i in range(0, total, 50):
        batch = metrics[i : i + 50]
        try:
            resp = api("POST", "/api/metrics/ingest/batch", {"metrics": batch}, token)
            sent += resp.get("accepted_count", len(batch))
        except Exception as e:
            print(f"  Batch {i // 50 + 1} failed: {e}", file=sys.stderr)

        pct = min(100, int((i + len(batch)) / total * 100))
        print(f"  Progress: {pct}% ({sent}/{total} metrics sent)", end="\r")

    print(f"\n  Done: {sent}/{total} metrics ingested")


def main():
    parser = argparse.ArgumentParser(description="Seed fitness metrics data")
    parser.add_argument("--api-url", default=API_URL, help="Base API URL")
    args = parser.parse_args()

    global _api_url
    _api_url = args.api_url.rstrip("/")

    print(f"Seeding {DAYS} days of data via {API_URL}")
    token = get_token()

    print("Generating metrics...")
    metrics = generate_metrics(DAYS)
    print(f"  Generated {len(metrics)} metric data points")

    print("Ingesting via API...")
    ingest_all(token, metrics)

    print("\nWaiting for analytics worker to process...")
    print("  (check docker compose logs analytics-worker for progress)")
    print(f"\nSeed complete! Log in with {EMAIL} / {PASSWORD}")


if __name__ == "__main__":
    main()
