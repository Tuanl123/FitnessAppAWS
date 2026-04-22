# Walkthrough Video
https://drive.google.com/file/d/1eqUYkbyE6c20L65WYIM13letrX-AYz0z/view?usp=sharing

# Fitness Metrics Tracker

A full-stack fitness tracking platform built with FastAPI microservices, a React dashboard, and an event-driven analytics pipeline on AWS. Users log health metrics (steps, heart rate, sleep, etc.), which flow through SQS into a Lambda-based processing pipeline that computes aggregations and generates insights like anomaly alerts, trend detection, and milestone achievements.

The AWS stack includes a custom domain (Route 53 + ACM), a WAFv2-protected CloudFront distribution, ECS Fargate auto-scaling, and a full observability pipeline built on Amazon Managed Prometheus and Amazon Managed Grafana with ADOT Collector sidecars.

## Architecture

### Cloud (AWS — us-east-1)

```
                            ┌──────────────────────┐
                            │   Route 53 (DNS)     │
                            │   app.example.com    │
                            └──────────┬───────────┘
                                       │ ACM + alias
                            ┌──────────▼───────────┐
                            │      WAFv2           │
                            │ (managed + rate lim) │
                            └──────────┬───────────┘
                                       │
                            ┌──────────▼───────────┐
                            │     CloudFront       │
                            │ (static → S3, /api → │
                            │         ALB)         │
                            └──────────┬───────────┘
                                       │
               ┌───────────────────────┼────────────────────────┐
               │                       │                        │
        Static Assets              /api/users/*            /api/metrics/*
               │                       │                        │
        ┌──────▼──────┐        ┌───────▼────────┐      ┌───────▼─────────┐
        │  S3 Bucket  │        │  User Service  │      │ Metrics Service │
        │ (React SPA) │        │ (ECS Fargate)  │      │ (ECS Fargate)   │
        └─────────────┘        │  + ADOT sidecar│      │ + ADOT sidecar  │
                               └───────┬────────┘      └──┬──────────┬───┘
                                       │                   │          │
                                 ┌─────▼─────┐      write │    read  │
                                 │  RDS       │            │          │
                                 │  user_db   │      ┌────▼───┐  ┌──▼──────────┐
                                 └───────────┘      │  SQS   │  │ RDS         │
                                                     │ Queue  │  │ analytics_db│
                                                     └───┬────┘  └──▲──────────┘
                                                         │          │
                                                    ┌────▼──────────┤
                                                    │    Lambda     │
                                                    │ (analytics)   │──► SNS → Email
                                                    └───────────────┘

    Observability:  ECS services → ADOT → Amazon Managed Prometheus → Amazon Managed Grafana
                    All services  → CloudWatch Logs + Metrics + Alarms
```

Services scale horizontally based on CPU utilization and ALB request count. CloudFront terminates TLS at the custom domain, forwards `/api/*` to the ALB, and serves SPA assets from S3 (with 403/404 → `index.html` SPA fallback).

### Local (Docker Compose)

Locally, the same services run via Docker Compose with Nginx routing, LocalStack SQS, and a poller-based analytics worker. The frontend runs on Vite's dev server with proxy configuration.

```
Browser (:5173) → Vite → Nginx (:80) → User Service / Metrics Service
                                         Metrics Service → LocalStack SQS → analytics-worker → Postgres
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts, TanStack Query |
| User Service | Python 3.11, FastAPI, SQLAlchemy (async), Alembic, bcrypt, JWT, Prometheus instrumentation |
| Metrics Service | Python 3.11, FastAPI, boto3 (SQS), psycopg2, slowapi, Prometheus instrumentation |
| Analytics Lambda | Python 3.11, psycopg2, boto3 (SNS) |
| Infrastructure | Terraform, ECS Fargate, RDS PostgreSQL, SQS, Lambda, S3, CloudFront, Route 53, ACM, WAFv2, Secrets Manager |
| Observability | ADOT Collector, Amazon Managed Prometheus, Amazon Managed Grafana, CloudWatch |
| CI/CD | GitHub Actions with AWS OIDC federation (no static credentials) |
| Cost Controls | AWS Budgets with email alerts |

## Local Development

### Prerequisites

- Python 3.11+
- Docker Desktop
- Node.js 18+

### Quick Start (without Docker Compose)

```bash
git clone https://github.com/Tuanl123/fitnessApp.git
cd fitnessApp

cp .env.example .env

# Start Postgres with both databases
docker run -d --name fitness-pg \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=devpass \
  -p 5432:5432 \
  -v $(pwd)/scripts/init-db.sh:/docker-entrypoint-initdb.d/init-db.sh \
  postgres:16-alpine

# Install and run backend services (in separate terminals)
cd services/user-service && pip install -r requirements.txt
PYTHONPATH=.. uvicorn app.main:app --port 8000 --reload

cd services/ingestion-service && pip install -r requirements.txt
PYTHONPATH=.. uvicorn app.main:app --port 8001 --reload

# Install and run frontend
cd frontend && npm install && npm run dev
```

The frontend runs at `http://localhost:5173` and proxies API calls to the backend.

### Docker Compose (Full Stack)

```bash
docker compose up --build
```

This starts Postgres, Nginx, LocalStack SQS, both services, and the analytics worker. The frontend still runs separately:

```bash
cd frontend && npm install && npm run dev
```

### Seed Data

After the stack is running, populate the database with 60 days of realistic test data:

```bash
python scripts/seed-data.py --api-url http://localhost:80
```

This creates a test user (`seed@test.com` / `SeedPass123`) and ingests ~300 metrics across all types, including some anomalies to trigger insights.

### Running Tests

```bash
# User Service
cd services/user-service
PYTHONPATH=.. pytest -v

# Ingestion Service
cd services/ingestion-service
PYTHONPATH=.. pytest -v
```

## API Endpoints

### User Service (`/api/users/`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Register a new account |
| POST | `/auth/login` | No | Login and receive tokens |
| POST | `/auth/refresh` | No | Refresh access token |
| GET | `/profile` | Yes | Get user profile |
| PUT | `/profile` | Yes | Update profile (name, age, weight, fitness_goals) |
| GET | `/health` | No | Health check |
| GET | `/metrics` | No | Prometheus exposition (scraped by ADOT sidecar) |

### Metrics Service (`/api/metrics/`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/ingest` | Yes | Submit a single metric (→ SQS) |
| POST | `/ingest/batch` | Yes | Submit up to 50 metrics (→ SQS) |
| GET | `/history` | Yes | Retrieve raw metric history |
| GET | `/summary` | Yes | Retrieve analytics and insights |
| GET | `/health` | No | Health check |
| GET | `/metrics` | No | Prometheus exposition (scraped by ADOT sidecar) |

### Authentication

All protected endpoints require a `Bearer` token in the `Authorization` header. Tokens are obtained via the register or login endpoints:

- **Access token**: 15-minute expiry, used for API calls
- **Refresh token**: 7-day expiry, used to obtain new access tokens

## Supported Metrics

| Metric | Unit | Valid Range |
|---|---|---|
| Heart Rate | bpm | 30 – 220 |
| Steps | count | 0 – 100,000 |
| Workout Duration | minutes | 1 – 480 |
| Calories Burned | kcal | 0 – 10,000 |
| Sleep Hours | hours | 0 – 24 |
| Distance | km | 0 – 200 |

## Analytics Pipeline

Each metric submitted to the ingest endpoint is queued in SQS and processed by the Analytics Lambda in three stages:

1. **Raw Storage** — Insert into `raw_metrics` (idempotent via unique constraint)
2. **Aggregation** — Recompute daily/weekly avg/min/max/count in `processed_metrics`
3. **Insight Generation** — Evaluate rules for anomalies, trends, and milestones

### Insight Types

- **Anomalies**: heart rate > 100 or < 40, steps > 50k/day, sleep < 4 or > 14 hours
- **Trends**: weekly average change > 10% compared to previous week
- **Milestones**: total workouts (10, 25, 50, 100...), cumulative distance, step streaks

Anomalies and milestones trigger SNS email notifications.

## Project Structure

```
├── frontend/                   # React + TypeScript + Tailwind
│   ├── src/
│   │   ├── api/                # Axios client + service modules
│   │   ├── components/         # Dashboard, analytics, layout, metrics
│   │   ├── contexts/           # Auth + theme contexts
│   │   ├── hooks/              # useAuth, useMetrics, useTheme
│   │   ├── pages/              # Login, Register, Dashboard, Log, Analytics, Profile
│   │   └── types/              # Shared TypeScript interfaces
│   └── vite.config.ts          # Proxy /api → localhost:80
├── services/
│   ├── user-service/           # Auth + profile (FastAPI + SQLAlchemy + Alembic)
│   ├── ingestion-service/      # Metric ingest + read (FastAPI + SQS + psycopg2)
│   ├── analytics-lambda/       # Processing pipeline (Lambda + psycopg2 + SNS)
│   └── shared/                 # JWT auth dependency
├── infrastructure/             # Terraform
│   ├── main.tf                 # Provider + shared locals
│   ├── vpc.tf                  # VPC, subnets, NAT, routes
│   ├── security_groups.tf      # ALB, ECS, RDS, Lambda SGs
│   ├── alb.tf                  # Application Load Balancer + target groups
│   ├── ecs.tf                  # ECS cluster, task defs, services, auto-scaling
│   ├── rds.tf                  # user_db + analytics_db (db.t3.micro)
│   ├── sqs.tf                  # Analytics queue + DLQ
│   ├── sns.tf                  # Alerts topic + email subscription
│   ├── lambda.tf               # Analytics Lambda + SQS trigger
│   ├── s3_cloudfront.tf        # Frontend S3 + CloudFront (ACM, WAF, SPA fallback)
│   ├── dns.tf                  # Route 53 hosted zone + ACM cert + alias
│   ├── waf.tf                  # WAFv2 managed rules + rate limiting + alarm
│   ├── cloudwatch.tf           # Log groups + alarms + dashboard
│   ├── monitoring.tf           # Amazon Managed Prometheus + Grafana + ADOT SSM configs
│   ├── secrets.tf              # Secrets Manager (DB URLs + JWT)
│   ├── ecr.tf                  # Container registries (3x)
│   ├── iam.tf                  # ECS execution/task + Lambda + observability roles
│   ├── oidc.tf                 # GitHub Actions OIDC role
│   ├── budget.tf               # AWS Budget with 50/80/100% alerts
│   └── outputs.tf              # All exported values
├── nginx/                      # Local Nginx routing config
├── scripts/
│   ├── init-db.sh              # Creates user_db + analytics_db
│   ├── init-sqs.sh             # Creates LocalStack SQS queue
│   ├── seed-data.py            # Populates 60 days of test data
│   ├── verify-deployment.sh    # E2E smoke test for AWS deployment
│   └── teardown.sh             # Destroys all AWS resources
├── .github/workflows/
│   ├── ci.yml                  # Tests + lint + Docker build
│   └── deploy.yml              # ECR push, migrate, ECS deploy, Lambda, S3+CF
└── docker-compose.yml          # Local full-stack environment
```

## Deployment

### Prerequisites

- AWS account with permissions to create VPC, ECS, RDS, SQS, Lambda, S3, CloudFront, Route 53, ACM, WAF, IAM, Secrets Manager, CloudWatch, SNS, Amazon Managed Prometheus, and Amazon Managed Grafana resources
- A registered domain whose nameservers you can point to Route 53
- **AWS IAM Identity Center (SSO) enabled** in the account — required by Amazon Managed Grafana (`monitoring.tf`)
- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) v2, configured with appropriate credentials
- A GitHub repository (for OIDC-based CI/CD)

### Step 1 — Configure Terraform Variables

```bash
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with real values:

```hcl
aws_region   = "us-east-1"
project_name = "fitness-tracker"
environment  = "prod"

domain_name = "app.example.com"

user_db_username      = "fitness_user"
user_db_password      = "your-secure-password-here"
analytics_db_username = "fitness_analytics"
analytics_db_password = "your-secure-password-here"

jwt_secret         = "your-jwt-secret-min-32-characters"
notification_email = "your-email@example.com"
github_repo        = "YourGitHubUser/fitnessApp"
```

Optional overrides (defaults shown):

```hcl
ecs_cpu                    = 256   # +256 added automatically for ADOT sidecar
ecs_memory                 = 512   # +256 added automatically for ADOT sidecar
ecs_desired_count          = 2
ecs_min_count              = 1
ecs_max_count              = 4
autoscaling_cpu_target     = 70    # % CPU target for target-tracking
autoscaling_request_target = 1000  # ALB requests/target for target-tracking
```

### Step 2 — Provision Infrastructure

```bash
cd infrastructure
terraform init
terraform plan
terraform apply
```

This creates the full stack: VPC (2 public + 2 private subnets), ALB, ECS cluster with auto-scaling, RDS instances, SQS queues, Lambda, S3 bucket, CloudFront distribution, Route 53 hosted zone, ACM certificate, WAFv2 Web ACL, Secrets Manager secrets, CloudWatch log groups/alarms/dashboard, SNS topic, Amazon Managed Prometheus workspace, Amazon Managed Grafana workspace, ADOT collector SSM configs, AWS Budget, and the GitHub Actions OIDC role.

After `terraform apply`, note the outputs:

```bash
terraform output
```

Key outputs:

| Output | Description |
|---|---|
| `alb_dns_name` | ALB public DNS for direct API access |
| `cloudfront_domain_name` | CloudFront distribution domain (aliased by `app_domain`) |
| `cloudfront_distribution_id` | For CI/CD cache invalidation |
| `frontend_bucket_name` | S3 bucket for frontend artifacts |
| `github_actions_role_arn` | IAM role ARN for GitHub Actions OIDC |
| `route53_name_servers` | Point your registrar NS records at these |
| `app_domain` | Custom domain served by CloudFront |
| `amp_workspace_endpoint` | Amazon Managed Prometheus remote-write / query URL |
| `grafana_workspace_url` | Amazon Managed Grafana workspace URL |
| `waf_web_acl_arn` | WAFv2 Web ACL attached to CloudFront |

### Step 3 — Point Your Domain at Route 53

Take the four nameservers from `terraform output route53_name_servers` and set them as the NS records at your domain registrar. DNS validation for the ACM certificate will complete automatically once propagation finishes.

### Step 4 — Confirm SNS + Budget Email Subscriptions

After `terraform apply`, AWS sends confirmation emails to `notification_email`:

- **SNS alerts topic** — **you must click the confirmation link** to activate anomaly, milestone, and infrastructure alerts.
- **AWS Budget notifications** — confirmation is automatic for Budgets.

### Step 5 — Enable AWS IAM Identity Center (one-time)

Amazon Managed Grafana requires AWS IAM Identity Center (SSO) to be enabled in the account. If it isn't yet, enable it in the AWS Console and assign users to the Grafana workspace after `terraform apply`. The workspace URL is in `grafana_workspace_url`.

### Step 6 — Configure GitHub Secrets

In your GitHub repository, go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|---|---|
| `AWS_ROLE_ARN` | Value of `github_actions_role_arn` from Terraform output |
| `FRONTEND_BUCKET_NAME` | Value of `frontend_bucket_name` from Terraform output |
| `CLOUDFRONT_DISTRIBUTION_ID` | Value of `cloudfront_distribution_id` from Terraform output |

### Step 7 — Deploy via CI/CD

Push to `main` to trigger the full pipeline:

1. **CI** (`ci.yml`): runs pytest for both services, lints and builds the frontend, builds all Docker images
2. **Deploy** (`deploy.yml`): on CI success, builds and pushes images to ECR, runs Alembic migrations via one-off ECS tasks, performs rolling ECS deploys, packages and updates the Lambda, builds the React app, syncs to S3, and invalidates CloudFront

```bash
git push origin main
```

### Step 8 — Verify Deployment

Run the E2E verification script:

```bash
# Auto-reads Terraform outputs
./scripts/verify-deployment.sh

# Or pass endpoints explicitly
./scripts/verify-deployment.sh \
  --alb-dns <ALB_DNS_NAME> \
  --cf-domain <CLOUDFRONT_DOMAIN>
```

The script checks:
- Service health via ALB
- CloudFront frontend serving + SPA fallback + API passthrough
- Full user journey (register → login → refresh → profile)
- Metric ingestion pipeline (single + batch → SQS → Lambda → read back)
- CloudWatch log groups and recent log streams
- CloudWatch alarms
- SQS queues and DLQ status
- SNS topic and subscription confirmation
- ECS service status and task counts
- CloudWatch dashboard existence

## Monitoring & Observability

The platform uses a dual observability stack: **CloudWatch** for AWS-native metrics, logs, and alarms, and **Amazon Managed Prometheus + Managed Grafana** for application-level metrics scraped from the FastAPI `/metrics` endpoints.

### Application Metrics (Prometheus / Grafana)

Each FastAPI service exposes a `/metrics` endpoint via `prometheus-fastapi-instrumentator` (request counts, latency histograms, in-flight requests, etc.). An **ADOT (AWS Distro for OpenTelemetry) Collector** runs as a sidecar container in each ECS task, scraping the app on `localhost:8000`/`localhost:8001` every 30 seconds and remote-writing the metrics to **Amazon Managed Prometheus** using SigV4 authentication.

**Amazon Managed Grafana** is provisioned with the Prometheus data source and wired to AWS IAM Identity Center for SSO login. Access the workspace at `grafana_workspace_url` from `terraform output`.

### CloudWatch Dashboard

A unified dashboard (`fitness-tracker`) provides real-time visibility into:

- ECS CPU utilization (both services)
- RDS CPU utilization (both databases)
- SQS queue depth (main queue + DLQ)
- Lambda invocations, errors, and duration
- ALB request count and HTTP error rates (4xx/5xx)

Access it at: `https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=fitness-tracker`

### CloudWatch Alarms

| Alarm | Condition | Action |
|---|---|---|
| SQS queue depth | > 100 messages | SNS email |
| DLQ messages | > 0 messages | SNS email |
| Lambda errors | > 0 errors / 5 min | SNS email |
| User DB CPU | > 80% average / 10 min | SNS email |
| Analytics DB CPU | > 80% average / 10 min | SNS email |
| ECS User Service CPU | > 75% average / 10 min | SNS email |
| ECS Ingestion Service CPU | > 75% average / 10 min | SNS email |
| WAF blocked requests | > 100 blocked / 10 min | SNS email |

### Log Groups

| Service | Log Group | Retention |
|---|---|---|
| User Service | `/ecs/fitness-tracker/user-service` | 30 days |
| Metrics Service | `/ecs/fitness-tracker/ingestion-service` | 30 days |
| Analytics Lambda | `/aws/lambda/fitness-tracker-analytics` | 30 days |
| DB Migrations | `/ecs/fitness-tracker/migrations` | 30 days |
| ADOT Collector (both services) | `/ecs/fitness-tracker/adot-collector` | 30 days |

All services use structured JSON logging via `python-json-logger`.

### SNS Notifications

Email alerts are sent for:
- **Anomaly alerts** — e.g., "Health Metric Alert: heart rate of 115 bpm exceeds normal resting range"
- **Milestone achievements** — e.g., "Congratulations! You've logged 100 workouts!"
- **Infrastructure alarms** — DLQ messages, Lambda errors, high CPU, WAF blocked requests

### Dead Letter Queue

Failed SQS messages (after 3 processing attempts) are routed to the `analytics-dlq` with 14-day retention. The DLQ alarm fires immediately when any message lands in the DLQ.

To inspect DLQ messages:

```bash
aws sqs receive-message \
  --queue-url $(aws sqs get-queue-url --queue-name analytics-dlq --query QueueUrl --output text) \
  --max-number-of-messages 10 \
  --region us-east-1
```

## Auto Scaling

Both ECS services use target-tracking scaling on two dimensions:

| Policy | Metric | Target | Cooldown |
|---|---|---|---|
| CPU | `ECSServiceAverageCPUUtilization` | 70% (default) | 300s in / 60s out |
| Requests | `ALBRequestCountPerTarget` | 1000 req/target (default) | 300s in / 60s out |

Scaling bounds are controlled by `ecs_min_count` / `ecs_max_count` (defaults: 1–4 tasks per service).

## Security

- **TLS everywhere** — ACM-provisioned certificate on CloudFront for the custom domain; HTTP → HTTPS redirect.
- **WAFv2** in front of CloudFront with:
  - `AWSManagedRulesCommonRuleSet` (OWASP Top 10)
  - `AWSManagedRulesSQLiRuleSet`
  - `AWSManagedRulesKnownBadInputsRuleSet`
  - Rate limiting: 2000 requests per 5 minutes per source IP
- **Private data plane** — RDS and Lambda run in private subnets; ECS services are in public subnets with security groups that only accept traffic from the ALB.
- **Secrets Manager** — DB URLs and JWT secret are never in plaintext; injected into tasks at runtime via the ECS execution role.
- **OIDC-only CI/CD** — GitHub Actions assume a scoped IAM role; no long-lived AWS keys.
- **S3 bucket is private** — frontend assets are only reachable through the CloudFront OAC; public access is fully blocked.
- **Per-container rate limiting** — slowapi caps abuse on the metrics ingest path in addition to the WAF.

## CI/CD Pipeline

### CI (`ci.yml`)

Runs on every push/PR to `main`:

- **Test User Service** — pytest with a Postgres service container
- **Test Ingestion Service** — pytest with mocked SQS
- **Lint & Build Frontend** — ESLint + production build
- **Build Docker Images** — validates all three Dockerfiles compile

### Deploy (`deploy.yml`)

Triggered when CI passes on `main`:

1. **Build & Push** — parallel matrix build of 3 Docker images → ECR
2. **Migrate** — runs Alembic migrations via one-off ECS Fargate tasks for both databases
3. **Deploy Backend** — rolling ECS service updates with circuit breaker
4. **Deploy Lambda** — packages and updates the analytics function code
5. **Deploy Frontend** — `npm run build` → S3 sync → CloudFront invalidation

All AWS operations use OIDC federation (no static access keys).

## Cost Management

An AWS Budget (`budget.tf`) enforces a **$100/month** cost cap with email notifications:

| Threshold | Type |
|---|---|
| 50% of budget | Actual |
| 80% of budget | Actual |
| 100% of budget | Actual |
| 80% of budget | Forecasted |

### Estimated AWS Cost

| Resource | Monthly Estimate |
|---|---|
| ECS Fargate (2 services × 2 tasks, 0.5 vCPU / 768 MB incl. ADOT sidecar) | ~$45 |
| RDS db.t3.micro × 2 | ~$30 |
| NAT Gateway | ~$35 |
| ALB | ~$18 |
| Amazon Managed Prometheus | ~$3–$10 (scales with series) |
| Amazon Managed Grafana | $9/user/month |
| WAFv2 (Web ACL + managed rule groups) | ~$10 |
| Route 53 hosted zone | $0.50 |
| ACM certificate | Free |
| SQS / Lambda / SNS | < $1 |
| S3 + CloudFront | < $1 |
| Secrets Manager (3 secrets) | ~$1.50 |
| CloudWatch | < $2 |
| **Total** | **~$155–$200/month** |

To minimize cost during development:
- Reduce `ecs_desired_count` to 1 and `ecs_max_count` to 2 in `terraform.tfvars`
- Remove the Managed Grafana workspace (and `aws_iam_role.grafana`) if you don't need dashboards
- Remove WAFv2 if your app is not public-facing

## Teardown

To destroy all AWS resources:

```bash
./scripts/teardown.sh
```

This script empties the frontend S3 bucket, runs `terraform destroy`, and cleans up local Terraform state. Pass `--yes` to skip the interactive confirmation.

Or manually:

```bash
cd infrastructure
terraform destroy
```

RDS instances have `skip_final_snapshot = true` so no manual cleanup is needed.

## Environment Variables

| Variable | Service | Description |
|---|---|---|
| `USER_DB_URL` | User Service | PostgreSQL connection string (asyncpg) |
| `ANALYTICS_DB_URL` | Metrics Service, Lambda | PostgreSQL connection string |
| `SQS_ENDPOINT_URL` | Metrics Service, Worker | SQS endpoint (LocalStack locally, omit on AWS) |
| `SQS_QUEUE_NAME` | Metrics Service, Worker | SQS queue name |
| `SNS_TOPIC_ARN` | Lambda | SNS topic for notifications |
| `JWT_SECRET` | User Service, Metrics Service | Shared JWT signing key |
| `ENVIRONMENT` | All | `local` or `aws` |
| `VITE_API_BASE_URL` | Frontend | Empty locally (Vite proxy), empty on AWS (CloudFront routes) |
| `AOT_CONFIG_CONTENT` | ADOT sidecar | OTel collector config (loaded from SSM on AWS) |

## Known Trade-offs

- **ECS in public subnets** — saves ~$35/month on a second NAT Gateway; security-group-enforced access (ALB only)
- **Per-container rate limiting** — slowapi limits per instance, not globally shared; WAFv2 provides the global enforcement
- **localStorage for JWT** — production would use httpOnly cookies, but localStorage simplifies the demo
- **SNS is a no-op locally** — notifications are logged at INFO level in local environment
- **No WebSocket/real-time** — dashboard refreshes via TanStack Query polling (staleTime-based)
- **Single light theme** — no dark mode toggle
- **Health data compliance** — HIPAA/GDPR considerations are out of scope
- **AWS IAM Identity Center required** — Amazon Managed Grafana's `AWS_SSO` provider prevents a fully hands-off `terraform apply` in new accounts
