# Fitness Metrics Tracker — Complete Project Guide

Comprehensive documentation covering architecture, local development, API usage, AWS deployment, monitoring, troubleshooting, and operations.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Getting Started (Local)](#4-getting-started-local)
5. [API Reference](#5-api-reference)
6. [Frontend](#6-frontend)
7. [Backend Services](#7-backend-services)
8. [Database Schemas](#8-database-schemas)
9. [Analytics Pipeline](#9-analytics-pipeline)
10. [Notifications](#10-notifications)
11. [AWS Deployment](#11-aws-deployment)
12. [Infrastructure Details](#12-infrastructure-details)
13. [CI/CD Pipeline](#13-cicd-pipeline)
14. [Monitoring & Observability](#14-monitoring--observability)
15. [Troubleshooting](#15-troubleshooting)
16. [Cost Estimate](#16-cost-estimate)
17. [Teardown](#17-teardown)
18. [Environment Variables](#18-environment-variables)
19. [Known Trade-offs](#19-known-trade-offs)

---

## 1. Project Overview

A full-stack fitness tracking platform where users log health metrics (steps, heart rate, sleep, workout duration, calories, distance). Metrics flow through an event-driven pipeline:

1. User submits metrics via the **React dashboard**
2. The **Metrics Service** validates and queues them in **SQS**
3. An **Analytics Lambda** processes each message: stores raw data, computes daily/weekly aggregations, and generates insights (anomaly alerts, trend detection, milestone achievements)
4. **SNS** sends email notifications for anomalies and milestones
5. The dashboard displays charts, summaries, and insights

The same codebase runs **locally via Docker Compose** (with LocalStack for SQS) and **on AWS** via ECS Fargate, RDS, Lambda, S3 + CloudFront. Infrastructure is fully managed with **Terraform**, and deployments are automated via **GitHub Actions** using OIDC federation (no static AWS credentials).

---

## 2. Architecture

### Cloud Architecture (AWS — us-east-1)

```
                              ┌────────────────────────────┐
                              │        CloudFront          │
                              │  (static → S3, /api → ALB) │
                              └────────┬───────────────────┘
                                       │
               ┌───────────────────────┼────────────────────────┐
               │                       │                        │
        Static Assets              /api/users/*            /api/metrics/*
               │                       │                        │
        ┌──────▼──────┐        ┌───────▼────────┐      ┌───────▼─────────┐
        │  S3 Bucket  │        │  User Service  │      │ Metrics Service │
        │ (React SPA) │        │ (ECS Fargate)  │      │ (ECS Fargate)   │
        └─────────────┘        └───────┬────────┘      └──┬──────────┬───┘
                                       │                   │          │
                                 ┌─────▼─────┐      write │    read  │
                                 │  RDS       │            │          │
                                 │  user_db   │      ┌────▼───┐  ┌──▼──────────┐
                                 └───────────┘      │  SQS   │  │ RDS         │
                                                     │ Queue  │  │ analytics_db│
                                                     └───┬────┘  └──▲──────────┘
                                                         │          │
                                                    ┌────▼──────────┤
                                                    │    Lambda     │──► SNS → Email
                                                    │ (analytics)   │
                                                    └───────────────┘
                                                    ┌───────────────┐
                                                    │ SQS DLQ       │──► CloudWatch Alarm
                                                    └───────────────┘
```

**Request flow:**
- All traffic enters via **CloudFront**
- Static assets (`/`, `/login`, `/analytics`, etc.) are served from **S3** via CloudFront's default behavior
- API calls (`/api/*`) are forwarded by CloudFront to the **ALB**
- The ALB routes `/api/users/*` to the User Service target group and `/api/metrics/*` to the Metrics Service target group
- Both ECS services run in **public subnets** with `assignPublicIp` (security group restricts inbound to ALB only)
- RDS instances run in **private subnets**
- Lambda runs in **private subnets** and reaches SNS via a **VPC endpoint**

### Local Architecture (Docker Compose)

```
Browser (:5173) ──► Vite Dev Server ──► Nginx (:80)
                                          ├── /api/users/*  ──► User Service (:8000) ──► Postgres (user_db)
                                          └── /api/metrics/* ──► Metrics Service (:8001)
                                                                    ├── write ──► LocalStack SQS
                                                                    └── read  ──► Postgres (analytics_db)
                                              analytics-worker (polls SQS) ──► Postgres (analytics_db)
```

- **Vite** runs on the host at `:5173` and proxies `/api` requests to Nginx
- **Nginx** acts as the ALB equivalent, path-routing to the two backend services
- **LocalStack** provides a local SQS queue
- **analytics-worker** polls SQS and invokes the same handler code used by Lambda

---

## 3. Technology Stack

### Backend

| Component | Technology | Purpose |
|---|---|---|
| User Service | FastAPI, SQLAlchemy (async), asyncpg, Alembic | Auth (register/login/refresh) + profile CRUD |
| Metrics Service | FastAPI, boto3, psycopg2, slowapi | Metric validation, SQS send, analytics reads |
| Analytics Lambda | psycopg2, boto3 | Raw storage, aggregation, insights, SNS |
| Shared auth | python-jose, FastAPI Depends | JWT decode across both services |
| Password hashing | passlib[bcrypt] | bcrypt for registration/login |
| Logging | python-json-logger | Structured JSON logs for CloudWatch |
| Rate limiting | slowapi | 60 req/min per IP on ingest endpoints |
| Testing | pytest, httpx, moto, unittest.mock | Unit + integration tests |

### Frontend

| Library | Purpose |
|---|---|
| React 18 + TypeScript | UI framework |
| Vite | Build tool + dev server |
| Tailwind CSS v4 | Utility-first styling |
| React Router v6 | Client-side routing |
| TanStack Query v5 | Server state caching (staleTime 30-60s) |
| Axios | HTTP client with auth interceptor |
| Recharts | Line charts and data visualization |
| react-hot-toast | Success/error notifications |
| date-fns | Date formatting |

### Infrastructure

| Tool | Purpose |
|---|---|
| Terraform >= 1.5 | IaC for all AWS resources |
| Docker + Docker Compose | Local containerized environment |
| GitHub Actions | CI (test + build) and CD (deploy) |
| AWS OIDC | Credential-free auth from GitHub Actions |

---

## 4. Getting Started (Local)

### Prerequisites

- **Python 3.11+** — backend services
- **Docker Desktop** — Postgres, LocalStack, Nginx (or the full Compose stack)
- **Node.js 18+** — frontend build

### Option A: Quick Start (Standalone Services)

Best for active development with hot reload on all services.

```bash
# 1. Clone and configure
git clone https://github.com/Tuanl123/fitnessApp.git
cd fitnessApp
cp .env.example .env

# 2. Start Postgres with both databases
docker run -d --name fitness-pg \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=devpass \
  -p 5432:5432 \
  -v $(pwd)/scripts/init-db.sh:/docker-entrypoint-initdb.d/init-db.sh \
  postgres:16-alpine

# Wait for Postgres to be ready
sleep 5

# 3. Run Alembic migrations
cd services/user-service
pip install -r requirements.txt
PYTHONPATH=.. USER_DB_URL=postgresql+asyncpg://postgres:devpass@localhost:5432/user_db \
  alembic upgrade head
cd ../..

cd services/analytics-lambda
pip install -r requirements.txt
ANALYTICS_DB_URL=postgresql://postgres:devpass@localhost:5432/analytics_db \
  alembic upgrade head
cd ../..

# 4. Start the User Service (terminal 1)
cd services/user-service
PYTHONPATH=.. uvicorn app.main:app --port 8000 --reload

# 5. Start the Metrics Service (terminal 2)
cd services/ingestion-service
pip install -r requirements.txt
PYTHONPATH=.. uvicorn app.main:app --port 8001 --reload

# 6. Start the frontend (terminal 3)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

> **Note:** In standalone mode, SQS is not available, so metric ingestion will fail at the SQS send step. Use Docker Compose (Option B) for the full pipeline.

### Option B: Docker Compose (Full Stack)

Runs the complete pipeline including SQS and the analytics worker.

```bash
# 1. Clone and configure
git clone https://github.com/Tuanl123/fitnessApp.git
cd fitnessApp
cp .env.example .env

# 2. Start all backend services
docker compose up --build

# 3. In a separate terminal, start the frontend
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The full pipeline is active: metric ingestion → SQS → analytics worker → Postgres.

#### What Docker Compose starts:

| Service | Port | Description |
|---|---|---|
| `postgres` | 5432 | PostgreSQL 16 with both `user_db` and `analytics_db` |
| `localstack` | 4566 | LocalStack SQS with `analytics-queue` |
| `nginx` | 80 | Path routing to backend services |
| `user-service` | (internal) 8000 | FastAPI User Service |
| `ingestion-service` | (internal) 8001 | FastAPI Metrics Service |
| `analytics-worker` | — | Polls SQS, processes via Lambda handler |

### Seed Data

After the stack is running (either option), populate 60 days of realistic test data:

```bash
python scripts/seed-data.py --api-url http://localhost:80
```

This creates:
- A test user: `seed@test.com` / `SeedPass123`
- ~300+ metric data points across all 6 types
- Enough data for trends, milestones, and chart visualizations
- Two injected anomalies (extreme heart rate, very low sleep) to trigger insight generation

### Running Tests

```bash
# User Service (requires Postgres)
cd services/user-service
PYTHONPATH=.. USER_DB_URL=postgresql+asyncpg://postgres:devpass@localhost:5432/user_db \
  JWT_SECRET=test-secret ENVIRONMENT=local pytest -v

# Ingestion Service (mocks SQS, no external deps)
cd services/ingestion-service
PYTHONPATH=.. JWT_SECRET=test-secret ENVIRONMENT=local pytest -v
```

---

## 5. API Reference

All endpoints are prefixed by the API gateway path. Locally, use `http://localhost:80` (Nginx/Docker Compose) or the individual service ports. On AWS, use the CloudFront domain or ALB DNS.

### Authentication

Protected endpoints require `Authorization: Bearer <access_token>`. Tokens are JWTs signed with HS256.

- **Access token**: 15-minute expiry
- **Refresh token**: 7-day expiry, stored as a SHA-256 hash in `refresh_tokens` table

The Axios client in the frontend automatically attaches tokens and handles silent refresh on 401.

### User Service

#### POST `/api/users/auth/register`

Create a new account and receive tokens.

```bash
curl -X POST http://localhost:80/api/users/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "MyPass123",
    "name": "Jane Doe"
  }'
```

**Validation rules:**
- `email`: valid email format, must be unique
- `password`: 8–128 characters (must contain uppercase, lowercase, and digit)
- `name`: 1–100 characters

**201 response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "name": "Jane Doe",
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer"
}
```

**Errors:** `409` email taken, `422` validation failure.

#### POST `/api/users/auth/login`

```bash
curl -X POST http://localhost:80/api/users/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "MyPass123"
  }'
```

**200 response:**
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer"
}
```

**Errors:** `401` invalid credentials.

#### POST `/api/users/auth/refresh`

Exchange a refresh token for a new access token. The old refresh token is consumed (one-time use) and a new one is returned implicitly.

```bash
curl -X POST http://localhost:80/api/users/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbG..."}'
```

**200 response:**
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer"
}
```

#### GET `/api/users/profile` (protected)

```bash
curl http://localhost:80/api/users/profile \
  -H "Authorization: Bearer <access_token>"
```

**200 response:**
```json
{
  "user_id": "550e8400-...",
  "email": "user@example.com",
  "name": "Jane Doe",
  "age": 28,
  "weight": 72.5,
  "fitness_goals": "Run a half marathon",
  "created_at": "2026-03-15T10:30:00Z",
  "updated_at": "2026-03-20T14:00:00Z"
}
```

#### PUT `/api/users/profile` (protected)

All fields are optional — only provided fields are updated.

```bash
curl -X PUT http://localhost:80/api/users/profile \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "age": 28,
    "weight": 72.5,
    "fitness_goals": "Run a half marathon"
  }'
```

**Validation:** age 13–120, weight 20–500 kg, name 1–100 chars, fitness_goals max 500 chars.

#### GET `/api/users/health`

```bash
curl http://localhost:80/api/users/health
```

**200:** `{"status": "healthy", "service": "user-service"}`

### Metrics Service

#### POST `/api/metrics/ingest` (protected)

Submit a single metric to the SQS queue for async processing.

```bash
curl -X POST http://localhost:80/api/metrics/ingest \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "metric_type": "steps",
    "value": 8500,
    "recorded_at": "2026-04-05T20:30:00Z"
  }'
```

**Validation:**
- `metric_type`: must be one of `heart_rate`, `steps`, `workout_duration`, `calories_burned`, `sleep_hours`, `distance_km`
- `value`: must be within the valid range for the metric type (see [Supported Metrics](#supported-metrics))
- `recorded_at`: ISO 8601, cannot be more than 5 minutes in the future

**Rate limit:** 60 requests/minute per IP.

**202 response:**
```json
{
  "message": "Metric accepted for processing",
  "message_id": "a1b2c3d4-..."
}
```

#### POST `/api/metrics/ingest/batch` (protected)

Submit up to 50 metrics in a single request. The entire batch is rejected if any individual metric fails validation.

```bash
curl -X POST http://localhost:80/api/metrics/ingest/batch \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": [
      {"metric_type": "steps", "value": 8500, "recorded_at": "2026-04-05T20:30:00Z"},
      {"metric_type": "heart_rate", "value": 72, "recorded_at": "2026-04-05T07:15:00Z"},
      {"metric_type": "sleep_hours", "value": 7.5, "recorded_at": "2026-04-05T06:00:00Z"}
    ]
  }'
```

**202 response:**
```json
{
  "message": "Batch accepted for processing",
  "accepted_count": 3,
  "message_ids": ["a1b2...", "c3d4...", "e5f6..."]
}
```

#### GET `/api/metrics/history` (protected)

Retrieve raw metric data points. Results are filtered by the authenticated user.

```bash
curl "http://localhost:80/api/metrics/history?metric_type=steps&start_date=2026-03-01&end_date=2026-04-05&limit=10&offset=0" \
  -H "Authorization: Bearer <access_token>"
```

**Query parameters:**
- `metric_type` (optional): filter by type
- `start_date`, `end_date` (optional): date range filter
- `limit`: 1–500 (default 100)
- `offset`: pagination offset (default 0)

**200 response:**
```json
{
  "metrics": [
    {
      "id": "550e8400-...",
      "metric_type": "steps",
      "value": 8500.0,
      "recorded_at": "2026-04-05T20:30:00Z"
    }
  ],
  "total": 60,
  "limit": 10,
  "offset": 0
}
```

#### GET `/api/metrics/summary` (protected)

Retrieve aggregated analytics (avg/min/max) and generated insights.

```bash
curl "http://localhost:80/api/metrics/summary?period=daily&metric_type=steps&start_date=2026-03-01&end_date=2026-04-05" \
  -H "Authorization: Bearer <access_token>"
```

**Query parameters:**
- `period`: `daily` or `weekly` (default `daily`)
- `metric_type` (optional): filter by type
- `start_date`, `end_date` (optional): date range filter

**200 response:**
```json
{
  "aggregations": [
    {
      "metric_type": "steps",
      "period": "daily",
      "date": "2026-04-05",
      "avg_value": 8500.0,
      "min_value": 8500.0,
      "max_value": 8500.0
    }
  ],
  "insights": [
    {
      "type": "trend",
      "description": "[2026-03-31] Your average daily step count is ↑ 15% this week...",
      "generated_at": "2026-04-01T12:00:00Z"
    }
  ]
}
```

### Supported Metrics

| Type | Unit | Valid Range | Example |
|---|---|---|---|
| `heart_rate` | bpm | 30 – 220 | Resting: 60–80, Exercise: 120–180 |
| `steps` | count | 0 – 100,000 | Average day: 7,000–10,000 |
| `workout_duration` | minutes | 1 – 480 | Typical session: 30–60 |
| `calories_burned` | kcal | 0 – 10,000 | Moderate workout: 200–500 |
| `sleep_hours` | hours | 0 – 24 | Healthy: 7–9 |
| `distance_km` | km | 0 – 200 | Daily run: 3–10 |

---

## 6. Frontend

### Routes

| Route | Page | Auth Required |
|---|---|---|
| `/login` | Login form | No |
| `/register` | Registration form | No |
| `/` | Dashboard (metric cards, recent activity, insights) | Yes |
| `/log` | Log a metric (single + batch mode) | Yes |
| `/analytics` | Charts, trends, summaries | Yes |
| `/profile` | View/edit user profile | Yes |

All protected routes redirect to `/login` if no valid token exists. The `ProtectedRoute` component wraps the authenticated layout.

### Layout

```
┌────────────┬──────────────────────────────────┐
│  Sidebar   │  Top Bar (greeting + logout)     │
│            ├──────────────────────────────────┤
│  Dashboard │                                  │
│  Log       │         Main Content Area        │
│  Analytics │                                  │
│  Profile   │                                  │
└────────────┴──────────────────────────────────┘
```

The sidebar collapses to a hamburger menu on screens narrower than 768px (Tailwind `md:` breakpoint).

### Pages

**Dashboard** — Row of 5 metric summary cards (steps, heart rate, workout duration, calories, sleep) showing today's latest value with a trend arrow vs yesterday. Below: a recent activity list (last 10 entries) and 3 insight cards (gold = milestone, red = anomaly, blue = trend). A "Log Metric" FAB button links to `/log`.

**Log Metric** — Default single mode: metric type dropdown, numeric input (unit label updates dynamically), date/time picker. Toggle to batch mode: editable table with add/remove rows (max 50). Success toast on 202.

**Analytics** — Date range presets (7d / 30d / 90d / custom), metric type selector. Recharts line chart with hover tooltips. Summary stat cards (avg, min, max, count). Week-over-week comparison. Scrollable insights feed grouped by type.

**Profile** — View mode by default. Edit mode for name, age, weight, fitness goals. Email is read-only. "Member since" date at the bottom.

### Auth Flow

1. Login/register stores `access_token` + `refresh_token` in `localStorage`
2. Axios interceptor attaches `Authorization: Bearer <token>` to every request
3. On 401 response, interceptor attempts silent refresh via `/api/users/auth/refresh`
4. If refresh fails, tokens are cleared and user is redirected to `/login`
5. TanStack Query manages server state caching: `staleTime` of 30s for dashboard, 60s for analytics

### Visual Design

- **Primary**: teal/blue `#0891b2`
- **Positive**: green `#10b981`
- **Warning**: amber `#f59e0b`
- **Danger**: red `#ef4444`
- **Backgrounds**: gray scale `#f8fafc`, `#f1f5f9`
- White cards with `shadow-sm` and `rounded-lg`

---

## 7. Backend Services

### User Service

**Responsibilities:** User registration, login, JWT token management, profile CRUD.

**Stack:** FastAPI + SQLAlchemy async + asyncpg + Alembic.

**Key files:**
- `app/main.py` — FastAPI app with CORS and correlation ID middleware, root_path `/api/users`
- `app/config.py` — Settings from env vars via pydantic-settings
- `app/models.py` — `User` and `RefreshToken` ORM models
- `app/schemas.py` — Request/response Pydantic schemas
- `app/routers/auth.py` — Register, login, refresh endpoints
- `app/routers/users.py` — Profile get/update endpoints
- `app/database.py` — Async SQLAlchemy session factory
- `app/middleware.py` — Correlation ID middleware
- `migrations/` — Alembic migrations for `user_db`

**Auth implementation:**
- Passwords are hashed with bcrypt via passlib
- Access tokens: HS256 JWT with 15-min expiry, payload contains `sub` (user UUID)
- Refresh tokens: HS256 JWT with 7-day expiry, stored as SHA-256 hash in DB (one-time use, rotated on each refresh)

### Metrics / Ingestion Service

**Responsibilities:** Validate and queue metric data (writes), serve historical data and analytics (reads).

**Stack:** FastAPI + boto3 (SQS) + psycopg2 (sync reads from analytics_db) + slowapi.

**Key files:**
- `app/main.py` — FastAPI app with rate limiter, root_path `/api/metrics`
- `app/routers/ingest.py` — Single and batch ingest endpoints (send to SQS)
- `app/routers/read.py` — History and summary read endpoints (query analytics_db)
- `app/sqs_client.py` — SQS message sender with correlation ID
- `app/db_reader.py` — Psycopg2 queries for raw_metrics, processed_metrics, aggregations
- `app/schemas.py` — Metric validation with per-type range checks and future-date guard

**SQS message format:**
```json
{
  "user_id": "uuid",
  "metric_type": "steps",
  "value": 8500,
  "recorded_at": "2026-04-05T20:30:00+00:00",
  "ingested_at": "2026-04-05T20:30:05+00:00"
}
```

Message attributes include `correlation_id` for tracing.

### Analytics Lambda

**Responsibilities:** Process SQS messages through a 3-stage pipeline (raw storage → aggregation → insight generation). Publish SNS notifications for anomalies and milestones.

**Key files:**
- `handler.py` — Lambda entry point, iterates SQS records
- `processor.py` — 3-stage pipeline logic
- `db.py` — psycopg2 connection management (no pooling; concurrency capped at 10)
- `notifier.py` — SNS publish (or log-only in local mode)
- `local_worker.py` — SQS poller for local Docker Compose environment
- `migrations/` — Alembic migrations for `analytics_db`

### Shared Auth Module

`services/shared/auth.py` provides `get_current_user` — a FastAPI dependency that decodes the JWT, extracts the `user_id` UUID, and raises 401 on invalid/expired tokens. Used by both services. Configured at startup with the JWT secret.

---

## 8. Database Schemas

### user_db (User Service, SQLAlchemy + Alembic)

#### `users` table

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK, default `uuid4` |
| `email` | VARCHAR(320) | UNIQUE, NOT NULL, indexed |
| `hashed_password` | VARCHAR(128) | NOT NULL |
| `name` | VARCHAR(100) | NOT NULL |
| `age` | INTEGER | nullable |
| `weight` | FLOAT | nullable |
| `fitness_goals` | TEXT | nullable |
| `created_at` | TIMESTAMPTZ | default `now()` |
| `updated_at` | TIMESTAMPTZ | default `now()`, auto-updates |

#### `refresh_tokens` table

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK → `users.id` |
| `token_hash` | VARCHAR(128) | NOT NULL (SHA-256 of JWT) |
| `expires_at` | TIMESTAMPTZ | NOT NULL |
| `created_at` | TIMESTAMPTZ | default `now()` |

### analytics_db (Lambda writes, Metrics Service reads, Alembic)

#### `raw_metrics` table

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | NOT NULL |
| `metric_type` | VARCHAR(30) | NOT NULL |
| `value` | FLOAT | NOT NULL |
| `recorded_at` | TIMESTAMPTZ | NOT NULL |
| `ingested_at` | TIMESTAMPTZ | NOT NULL, default `now()` |

**Unique constraint:** `(user_id, metric_type, recorded_at)` — ensures idempotent processing.
**Index:** `(user_id, metric_type, recorded_at)` — optimizes history queries.

#### `processed_metrics` table

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | NOT NULL |
| `metric_type` | VARCHAR(30) | NOT NULL |
| `period` | VARCHAR(10) | `daily` or `weekly` |
| `period_start` | DATE | NOT NULL |
| `avg_value` | FLOAT | NOT NULL |
| `min_value` | FLOAT | NOT NULL |
| `max_value` | FLOAT | NOT NULL |
| `sample_count` | INTEGER | NOT NULL |
| `calculated_at` | TIMESTAMPTZ | NOT NULL |

**Unique constraint:** `(user_id, metric_type, period, period_start)` — upserted on each aggregation.

#### `aggregations` table (insights)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | NOT NULL |
| `insight_type` | VARCHAR(20) | `anomaly`, `trend`, or `milestone` |
| `metric_type` | VARCHAR(30) | nullable |
| `description` | TEXT | NOT NULL |
| `generated_at` | TIMESTAMPTZ | NOT NULL |

**Index:** `(user_id, generated_at)` — optimizes summary queries.

### Local Setup

A single Postgres container hosts both databases. The `scripts/init-db.sh` script creates `user_db` and `analytics_db` on first boot. Alembic migrations run automatically via the User Service entrypoint (user_db) and can be run manually for analytics_db.

---

## 9. Analytics Pipeline

Each SQS message is processed through three stages:

### Stage 1: Raw Storage

Inserts the data point into `raw_metrics`. Uses `ON CONFLICT DO NOTHING` on the `(user_id, metric_type, recorded_at)` unique constraint, so duplicate messages are safely skipped. If the row already exists, the pipeline stops early.

### Stage 2: Aggregation

For both the **daily** and **weekly** periods containing the data point's `recorded_at`:
- Queries all `raw_metrics` for that user + metric type + period
- Computes `AVG`, `MIN`, `MAX`, `COUNT`
- Upserts into `processed_metrics`

This means aggregations are always recalculated from raw data, ensuring consistency even if messages arrive out of order.

### Stage 3: Insight Generation

Three rule categories are evaluated:

#### Anomaly Detection (fires on every occurrence)

| Metric | Low Threshold | High Threshold |
|---|---|---|
| heart_rate | < 35 bpm | > 200 bpm |
| steps | — | > 50,000 /day |
| workout_duration | — | > 300 min |
| sleep_hours | < 2 hrs | > 14 hrs |

Each anomaly is written to `aggregations` and triggers an **SNS notification** with contextual advice.

#### Trend Detection (once per week per metric type)

- Compares this week's average to last week's average
- If the change exceeds ±10%, generates a trend insight
- Includes a contextual tip (e.g., "Great job staying active!" or "Try to prioritize sleep")
- Deduplicated by week: won't fire again for the same week+metric combination

#### Milestone Detection (one-time each)

- **Workout milestones**: 10, 25, 50, 100, 250, 500, 1000 workouts logged
- **Distance milestones**: 100, 500, 1000, 5000 km cumulative distance
- Checked against `aggregations` table to ensure each milestone fires only once
- Milestones trigger **SNS notification**

---

## 10. Notifications

### SNS Email Alerts

**On AWS:** Anomalies and milestones publish to the `fitness-tracker-alerts` SNS topic, which forwards to the configured email subscription.

**Subject format:**
- Anomaly: `"Fitness Tracker: Health Metric Alert"`
- Milestone: `"Fitness Tracker: New Milestone Achieved!"`

**Body:** Human-readable description with specific values and contextual advice.

**Locally:** Notifications are logged at INFO level and not sent anywhere. The `notifier.py` module checks the `ENVIRONMENT` variable.

### Infrastructure Alarms

CloudWatch alarm actions also publish to the same SNS topic, so you'll receive email for DLQ messages, Lambda errors, and high CPU on RDS/ECS.

---

## 11. AWS Deployment

### Prerequisites

- AWS account with admin-level permissions
- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), configured (`aws configure`)
- GitHub repository for CI/CD

### Step 1 — Configure Terraform Variables

```bash
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
aws_region   = "us-east-1"
project_name = "fitness-tracker"
environment  = "prod"

# Database credentials (choose strong passwords)
user_db_username      = "fitness_user"
user_db_password      = "YourStrongPassword1!"
analytics_db_username = "fitness_analytics"
analytics_db_password = "YourStrongPassword2!"

# JWT secret (min 32 characters)
jwt_secret = "your-production-jwt-secret-at-least-32-chars"

# Email for anomaly/milestone alerts + infrastructure alarms
notification_email = "your-email@example.com"

# GitHub repo for OIDC trust (owner/repo format)
github_repo = "YourGitHubUser/fitnessApp"
```

> **Security:** `terraform.tfvars` is gitignored. Never commit real credentials.

### Step 2 — Provision Infrastructure

```bash
cd infrastructure
terraform init
terraform plan    # review the ~50 resources to be created
terraform apply   # type 'yes' to confirm
```

This creates:
- VPC with 2 public + 2 private subnets across 2 AZs
- Internet Gateway + NAT Gateway
- ALB with path-based routing rules
- ECS Fargate cluster with 2 services (2 tasks each)
- 2 RDS PostgreSQL instances (db.t3.micro)
- 3 ECR repositories (user-service, ingestion-service, analytics-lambda)
- SQS queue + DLQ (3 retries, 14-day DLQ retention)
- Lambda function (Python 3.11, private subnets, concurrency: 10)
- S3 bucket + CloudFront distribution (OAC, SPA fallback)
- Secrets Manager (3 secrets: user-db URL, analytics-db URL, JWT)
- SNS topic + email subscription
- CloudWatch: 4 log groups, 7 alarms, 1 dashboard
- IAM roles: ECS execution, ECS task, Lambda execution, GitHub Actions OIDC
- VPC endpoint for SNS (Lambda → SNS without traversing NAT)

Save the outputs:

```bash
terraform output
```

### Step 3 — Confirm SNS Subscription

After `terraform apply`, check the email address you configured. AWS sends a subscription confirmation email — **click the link** to activate notifications. Without confirmation, you won't receive anomaly/milestone alerts or infrastructure alarm emails.

### Step 4 — Configure GitHub Repository Secrets

In your GitHub repository: **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Value |
|---|---|
| `AWS_ROLE_ARN` | `terraform output github_actions_role_arn` |
| `FRONTEND_BUCKET_NAME` | `terraform output frontend_bucket_name` |
| `CLOUDFRONT_DISTRIBUTION_ID` | `terraform output cloudfront_distribution_id` |

### Step 5 — Deploy

Push to `main` to trigger the CI/CD pipeline:

```bash
git push origin main
```

The pipeline will:
1. Run tests and lint (CI)
2. Build and push Docker images to ECR
3. Run Alembic migrations via one-off ECS tasks
4. Rolling-deploy both ECS services
5. Package and update the Lambda function
6. Build the React app, sync to S3, invalidate CloudFront

Monitor progress in the GitHub Actions tab.

### Step 6 — Verify

```bash
# Using Terraform outputs (run from repo root)
./scripts/verify-deployment.sh

# Or with explicit endpoints
./scripts/verify-deployment.sh \
  --alb-dns <your-alb-dns-name> \
  --cf-domain <your-cloudfront-domain>
```

The script runs 10 verification sections:
1. Service health checks via ALB
2. CloudFront frontend (HTML, SPA fallback, API passthrough)
3. User journey (register → login → refresh → profile CRUD)
4. Metric ingestion pipeline (single + batch → SQS → Lambda → read back)
5. CloudWatch log groups + recent streams
6. CloudWatch alarms (all 7)
7. SQS queues + DLQ status
8. SNS topic + subscription confirmation
9. ECS service status + task counts
10. CloudWatch dashboard

### Step 7 — Access the Application

- **Frontend:** `https://<cloudfront-domain>` — the main entry point
- **API (direct):** `http://<alb-dns>/api/users/health`
- **CloudWatch Dashboard:** `https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=fitness-tracker`

---

## 12. Infrastructure Details

### VPC & Networking

| Resource | CIDR / Details |
|---|---|
| VPC | `10.0.0.0/16` |
| Public subnet AZ-1 | `10.0.1.0/24` (ALB, ECS) |
| Public subnet AZ-2 | `10.0.2.0/24` (ALB, ECS) |
| Private subnet AZ-1 | `10.0.3.0/24` (RDS, Lambda) |
| Private subnet AZ-2 | `10.0.4.0/24` (RDS, Lambda) |
| NAT Gateway | In public subnet AZ-1, used by Lambda |
| VPC endpoint | SNS interface endpoint in private subnets |

### Security Groups

| SG | Inbound | Outbound |
|---|---|---|
| ALB | 80 from 0.0.0.0/0 | All |
| ECS | All TCP from ALB SG only | All |
| Lambda | — (no inbound) | All |
| RDS | 5432 from ECS SG + Lambda SG | — |
| VPC endpoints | 443 from Lambda SG | — |

### ECS Fargate

- **Cluster:** `fitness-tracker-cluster` with Container Insights enabled
- **User Service:** 2 tasks, 0.25 vCPU, 512 MB, port 8000
- **Ingestion Service:** 2 tasks, 0.25 vCPU, 512 MB, port 8001
- **Deployment:** circuit breaker with auto-rollback
- **Logs:** awslogs driver → CloudWatch log groups

### RDS

- **Engine:** PostgreSQL 16
- **Instance class:** db.t3.micro
- **Storage:** 20 GB gp3, auto-scaling to 50 GB
- **Backups:** 7-day retention
- **Multi-AZ:** disabled (cost optimization)
- **Public access:** disabled (private subnets only)

### SQS

- **analytics-queue:** 360s visibility timeout (6× Lambda timeout), redrive to DLQ after 3 failures
- **analytics-dlq:** 14-day message retention

### Lambda

- **Runtime:** Python 3.11
- **Memory:** 256 MB
- **Timeout:** 60 seconds
- **Concurrency:** reserved at 10
- **VPC:** private subnets
- **Trigger:** SQS event source mapping, batch size 10
- **Partial batch failure:** returns `batchItemFailures` so only failed messages retry

### S3 + CloudFront

- **S3:** private bucket (public access fully blocked), versioned
- **CloudFront OAC:** signed requests from CloudFront to S3
- **Cache behaviors:** `/api/*` → ALB (no caching, all headers forwarded), default → S3 (1h default TTL)
- **SPA fallback:** 403 and 404 errors return `/index.html` with 200 status
- **Price class:** PriceClass_100 (US + Europe)

### Secrets Manager

3 secrets with `recovery_window_in_days = 0` (allows clean `terraform destroy`):
- `fitness-tracker/user-db-url` — full `postgresql+asyncpg://...` connection string
- `fitness-tracker/analytics-db-url` — full `postgresql://...` connection string
- `fitness-tracker/jwt-secret` — shared JWT signing key

ECS tasks retrieve these as container secrets (injected as environment variables at launch).

---

## 13. CI/CD Pipeline

### CI Workflow (`ci.yml`)

**Trigger:** push or PR to `main`.

| Job | What it does |
|---|---|
| test-user-service | Spins up Postgres service container, installs deps, runs `pytest -v` |
| test-ingestion-service | Installs deps (SQS is mocked), runs `pytest -v` |
| lint-and-build-frontend | `npm ci`, `npm run lint`, `npm run build` |
| build-docker-images | Matrix build of 3 Docker images (validates Dockerfiles) |

### Deploy Workflow (`deploy.yml`)

**Trigger:** after CI succeeds on `main` (via `workflow_run`).

**Concurrency:** `deploy-production` group, no cancellation (ensures deploys complete).

| Job | Depends On | What it does |
|---|---|---|
| build-and-push | — | Matrix build: 3 Docker images → ECR (`$SHA` + `latest` tags) |
| migrate | build-and-push | Runs Alembic via `ecs run-task` for user_db and analytics_db |
| deploy-backend | migrate | `ecs update-service --force-new-deployment` + wait for stability |
| deploy-lambda | migrate | Packages Python deps + handler → zip → `lambda update-function-code` |
| deploy-frontend | — (parallel) | `npm run build` → `s3 sync --delete` → `cloudfront create-invalidation` |

**OIDC:** All AWS calls use `aws-actions/configure-aws-credentials` with role assumption via OIDC. No static AWS keys are stored.

---

## 14. Monitoring & Observability

### CloudWatch Dashboard

Dashboard name: `fitness-tracker`

7 widgets showing:
1. ECS CPU utilization (both services)
2. RDS CPU utilization (both databases)
3. SQS queue depth (main + DLQ)
4. Lambda invocations + errors
5. Lambda average duration
6. ALB total request count
7. ALB HTTP error rates (4xx + 5xx)

### CloudWatch Alarms

| Alarm | Metric | Threshold | Period | Actions |
|---|---|---|---|---|
| sqs-depth | SQS ApproximateNumberOfMessagesVisible | > 100 | 5 min | SNS email |
| dlq-messages | SQS DLQ ApproximateNumberOfMessagesVisible | > 0 | 1 min | SNS email |
| lambda-errors | Lambda Errors | > 0 | 5 min | SNS email |
| user-db-cpu | RDS CPUUtilization | > 80% (avg, 2 periods) | 5 min | SNS email |
| analytics-db-cpu | RDS CPUUtilization | > 80% (avg, 2 periods) | 5 min | SNS email |
| ecs-user-cpu | ECS CPUUtilization | > 75% (avg, 2 periods) | 5 min | SNS email |
| ecs-ingestion-cpu | ECS CPUUtilization | > 75% (avg, 2 periods) | 5 min | SNS email |

### Log Groups

| Log Group | Source | Retention |
|---|---|---|
| `/ecs/fitness-tracker/user-service` | ECS task stdout | 30 days |
| `/ecs/fitness-tracker/ingestion-service` | ECS task stdout | 30 days |
| `/aws/lambda/fitness-tracker-analytics` | Lambda execution | 30 days |
| `/ecs/fitness-tracker/migrations` | One-off migration tasks | 30 days |

### Viewing Logs

```bash
# Recent user service logs
aws logs tail /ecs/fitness-tracker/user-service --since 1h --follow

# Lambda errors only
aws logs filter-log-events \
  --log-group-name /aws/lambda/fitness-tracker-analytics \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s000) \
  --region us-east-1

# Migration logs
aws logs tail /ecs/fitness-tracker/migrations --since 2h
```

### Dead Letter Queue

```bash
# Check DLQ depth
aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name analytics-dlq --query QueueUrl --output text) \
  --attribute-names ApproximateNumberOfMessages \
  --region us-east-1

# Peek at DLQ messages (does not delete)
aws sqs receive-message \
  --queue-url $(aws sqs get-queue-url --queue-name analytics-dlq --query QueueUrl --output text) \
  --max-number-of-messages 5 \
  --visibility-timeout 0 \
  --region us-east-1

# Reprocess: use SQS redrive (AWS Console → SQS → analytics-dlq → Start DLQ redrive)
```

---

## 15. Troubleshooting

### Common Issues

**ECS tasks won't start / keep restarting**

1. Check the ECS service events: `aws ecs describe-services --cluster fitness-tracker-cluster --services user-service --query 'services[0].events[:5]'`
2. Check container logs: `aws logs tail /ecs/fitness-tracker/user-service --since 30m`
3. Common causes: Secrets Manager permissions, RDS connectivity (check security groups), image not in ECR

**Lambda not processing messages**

1. Check Lambda logs: `aws logs tail /aws/lambda/fitness-tracker-analytics --since 1h`
2. Check SQS queue depth is decreasing: watch the CloudWatch dashboard
3. If messages pile up in DLQ: inspect message bodies for malformed data
4. Common causes: analytics_db unreachable (security group or secret mismatch), Lambda not in correct subnets

**CloudFront returns 502/504 for API calls**

1. Verify ALB is reachable: `curl http://<alb-dns>/api/users/health`
2. Check ALB target group health: `aws elbv2 describe-target-health --target-group-arn <arn>`
3. Common causes: ECS tasks not registered with target group, health check failing

**Frontend shows blank page on CloudFront**

1. Verify S3 bucket has files: `aws s3 ls s3://<bucket-name>/`
2. Check CloudFront distribution status: `aws cloudfront get-distribution --id <dist-id> --query 'Distribution.Status'`
3. Invalidate cache: `aws cloudfront create-invalidation --distribution-id <dist-id> --paths "/*"`

**Migrations fail in CI/CD**

1. Check migration task logs: `aws logs tail /ecs/fitness-tracker/migrations --since 1h`
2. The migration task needs: correct DB secret, network access to RDS, the `alembic upgrade head` command (set via entrypoint)
3. Verify the analytics-lambda ECR image includes migration files

**Rate limit errors (429)**

The Metrics Service applies a 60 req/min per IP limit via slowapi. This is per-container (not globally shared). With 2 tasks, effective limit is ~120/min total. For bulk loading, use the batch endpoint (50 metrics per request).

**Refresh token errors**

Refresh tokens are one-time use. After each refresh, the old token is deleted and a new one is issued. If you see persistent 401s, the token may have already been consumed. Log in again to get fresh tokens.

---

## 16. Cost Estimate

Estimated monthly cost running the full AWS stack:

| Resource | Monthly Cost |
|---|---|
| ECS Fargate (2 services × 2 tasks, 0.25 vCPU / 512 MB each) | ~$30 |
| RDS db.t3.micro × 2 (PostgreSQL 16, 20 GB gp3) | ~$30 |
| NAT Gateway (1, single AZ) | ~$35 |
| ALB (Application Load Balancer) | ~$18 |
| SQS + Lambda + SNS | < $1 |
| S3 + CloudFront (PriceClass_100) | < $1 |
| Secrets Manager (3 secrets) | ~$1.50 |
| CloudWatch (logs, alarms, dashboard) | < $2 |
| **Total** | **~$85 – $120/month** |

### Cost Optimization Tips

- Set `ecs_desired_count = 1` to halve ECS cost during development
- RDS offers free-tier for the first 12 months (750 hrs/month of db.t3.micro)
- NAT Gateway is the largest fixed cost; the architecture uses only 1 NAT across 2 AZs
- Lambda + SQS + SNS are essentially free at this scale

---

## 17. Teardown

To destroy all AWS resources and stop incurring charges:

```bash
cd infrastructure
terraform destroy
```

Type `yes` to confirm. This removes all provisioned resources including:
- VPC and all networking
- ECS cluster and services
- RDS instances (skip_final_snapshot = true, no manual cleanup needed)
- SQS queues (messages are deleted)
- Lambda function
- S3 bucket (contents deleted)
- CloudFront distribution
- Secrets Manager secrets (recovery_window = 0, immediate delete)
- CloudWatch log groups, alarms, dashboard
- All IAM roles and policies

> **Note:** ECR repositories and images may need manual cleanup if they were not created by Terraform: `aws ecr delete-repository --repository-name fitness-tracker/user-service --force`

---

## 18. Environment Variables

### Backend Services

| Variable | Used By | Default (local) | AWS Source |
|---|---|---|---|
| `USER_DB_URL` | User Service | `postgresql+asyncpg://postgres:devpass@localhost:5432/user_db` | Secrets Manager |
| `ANALYTICS_DB_URL` | Metrics Service, Lambda | `postgresql://postgres:devpass@localhost:5432/analytics_db` | Secrets Manager |
| `JWT_SECRET` | User Service, Metrics Service | `dev-secret-key-change-in-production` | Secrets Manager |
| `SQS_ENDPOINT_URL` | Metrics Service, Worker | `http://localhost:4566` | Not set (uses default AWS endpoint) |
| `SQS_QUEUE_NAME` | Metrics Service, Worker | `analytics-queue` | Set via ECS task definition |
| `SNS_TOPIC_ARN` | Lambda | `""` (empty = no-op) | Lambda env var |
| `ENVIRONMENT` | All | `local` | `aws` |
| `AWS_REGION` | Lambda, Metrics Service | `us-east-1` | `us-east-1` |

### Frontend

| Variable | Default | AWS |
|---|---|---|
| `VITE_API_BASE_URL` | `""` (Vite proxy handles routing) | `""` (CloudFront handles routing) |

### Docker Compose Overrides

In `docker-compose.yml`, services reference internal Docker hostnames:
- Postgres: `postgres:5432` (not `localhost`)
- LocalStack: `localstack:4566`
- User DB URL uses `postgres:5432` host

---

## 19. Known Trade-offs

| Decision | Rationale |
|---|---|
| ECS in public subnets | Saves ~$86/month on a second NAT Gateway. Access restricted via security group (inbound from ALB only). |
| Per-container rate limiting (slowapi) | Not globally shared across ECS tasks. Acceptable for portfolio scale. |
| No custom domain | Uses ALB DNS + CloudFront default domain. Custom domain would require Route 53 + ACM certificate. |
| localStorage for JWT | Production should use httpOnly cookies. localStorage is simpler and sufficient for a portfolio demo. |
| SNS is a no-op locally | `notifier.py` logs the message instead of sending. Avoids requiring SNS setup for local dev. |
| No WebSocket / real-time updates | Dashboard refreshes via TanStack Query polling (staleTime-based). WebSockets would add complexity without significant benefit at this scale. |
| Single light theme | No dark mode toggle to keep scope manageable. |
| No connection pooling in Lambda | Lambda concurrency is capped at 10; each invocation opens/closes a connection. Acceptable at this scale. |
| Health data compliance out of scope | HIPAA/GDPR would require encryption at rest, audit logging, and access controls beyond this demo. |
| Single NAT Gateway (1 AZ) | Production would use 1 per AZ for HA. Single NAT saves cost. |
| skip_final_snapshot on RDS | Simplifies teardown. Production would enable final snapshots. |
