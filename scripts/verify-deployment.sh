#!/usr/bin/env bash
set -euo pipefail

# E2E deployment verification for Fitness Metrics Tracker.
# Smoke-tests the live stack via ALB and CloudFront, checks
# CloudWatch, SQS, and SNS resources.
#
# Usage:
#   ./scripts/verify-deployment.sh
#   ./scripts/verify-deployment.sh --alb-dns <ALB_DNS> --cf-domain <CF_DOMAIN>
#
# Without flags the script reads Terraform outputs from infrastructure/.

REGION="${AWS_REGION:-us-east-1}"
PROJECT="fitness-tracker"
ALB_DNS=""
CF_DOMAIN=""
PASS=0
FAIL=0
WARN=0

# ─── Helpers ──────────────────────────────────────────────────

green()  { printf "\033[32m%s\033[0m\n" "$*"; }
red()    { printf "\033[31m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
bold()   { printf "\033[1m%s\033[0m\n" "$*"; }

pass() { PASS=$((PASS+1)); green "  PASS: $1"; }
fail() { FAIL=$((FAIL+1)); red   "  FAIL: $1"; }
warn() { WARN=$((WARN+1)); yellow "  WARN: $1"; }

section() { echo ""; bold "── $1 ──"; }

http_code() {
  curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$@" 2>/dev/null || echo "000"
}

http_body() {
  curl -s --max-time 10 "$@" 2>/dev/null || echo ""
}

# ─── Parse args ───────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
  case "$1" in
    --alb-dns)  ALB_DNS="$2";  shift 2 ;;
    --cf-domain) CF_DOMAIN="$2"; shift 2 ;;
    --region)   REGION="$2";   shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ─── Resolve endpoints ───────────────────────────────────────

if [[ -z "$ALB_DNS" || -z "$CF_DOMAIN" ]]; then
  section "Reading Terraform outputs"
  if [[ -d infrastructure ]]; then
    TF_OUT=$(cd infrastructure && terraform output -json 2>/dev/null) || true
    if [[ -n "$TF_OUT" ]]; then
      ALB_DNS="${ALB_DNS:-$(echo "$TF_OUT"  | jq -r '.alb_dns_name.value // empty')}"
      CF_DOMAIN="${CF_DOMAIN:-$(echo "$TF_OUT" | jq -r '.cloudfront_domain_name.value // empty')}"
    fi
  fi
fi

if [[ -z "$ALB_DNS" ]]; then
  red "ERROR: Could not determine ALB DNS. Pass --alb-dns <value>."
  exit 1
fi
if [[ -z "$CF_DOMAIN" ]]; then
  red "ERROR: Could not determine CloudFront domain. Pass --cf-domain <value>."
  exit 1
fi

ALB_URL="http://${ALB_DNS}"
CF_URL="https://${CF_DOMAIN}"

bold "Fitness Metrics Tracker — Deployment Verification"
echo "  ALB:        $ALB_URL"
echo "  CloudFront: $CF_URL"
echo "  Region:     $REGION"

# ─── 1. Health checks via ALB ─────────────────────────────────

section "1. Service Health Checks (ALB)"

CODE=$(http_code "${ALB_URL}/api/users/health")
if [[ "$CODE" == "200" ]]; then
  pass "User Service health ($CODE)"
else
  fail "User Service health (HTTP $CODE)"
fi

CODE=$(http_code "${ALB_URL}/api/metrics/health")
if [[ "$CODE" == "200" ]]; then
  pass "Metrics Service health ($CODE)"
else
  fail "Metrics Service health (HTTP $CODE)"
fi

# ─── 2. CloudFront serves frontend ───────────────────────────

section "2. CloudFront Frontend"

CODE=$(http_code "${CF_URL}/")
if [[ "$CODE" == "200" ]]; then
  pass "CloudFront root returns 200"
else
  fail "CloudFront root returned HTTP $CODE"
fi

BODY=$(http_body "${CF_URL}/")
if echo "$BODY" | grep -qi "<!doctype\|<html\|<div id"; then
  pass "CloudFront serves HTML (React SPA)"
else
  warn "CloudFront response doesn't look like HTML"
fi

# SPA fallback — a non-existent path should still return index.html
CODE=$(http_code "${CF_URL}/login")
if [[ "$CODE" == "200" ]]; then
  pass "SPA fallback: /login returns 200"
else
  warn "SPA fallback: /login returned HTTP $CODE"
fi

# API passthrough via CloudFront
CODE=$(http_code "${CF_URL}/api/users/health")
if [[ "$CODE" == "200" ]]; then
  pass "CloudFront -> ALB API passthrough works"
else
  fail "CloudFront -> ALB API passthrough returned HTTP $CODE"
fi

# ─── 3. User journey: register → login → profile ──────────────

section "3. User Journey (Auth)"

TIMESTAMP=$(date +%s)
TEST_EMAIL="verify-${TIMESTAMP}@e2e-test.com"
TEST_PASS="E2eTestPass1"

REGISTER=$(http_body -X POST "${ALB_URL}/api/users/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${TEST_EMAIL}\",\"password\":\"${TEST_PASS}\",\"name\":\"E2E Test\"}")

ACCESS=$(echo "$REGISTER" | jq -r '.access_token // empty')
REFRESH=$(echo "$REGISTER" | jq -r '.refresh_token // empty')

if [[ -n "$ACCESS" ]]; then
  pass "Register user ($TEST_EMAIL)"
else
  fail "Register user — no access_token returned"
  # Try login in case user already exists
  LOGIN=$(http_body -X POST "${ALB_URL}/api/users/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${TEST_EMAIL}\",\"password\":\"${TEST_PASS}\"}")
  ACCESS=$(echo "$LOGIN" | jq -r '.access_token // empty')
  REFRESH=$(echo "$LOGIN" | jq -r '.refresh_token // empty')
fi

if [[ -n "$ACCESS" ]]; then
  # Refresh token
  REFRESH_RESP=$(http_body -X POST "${ALB_URL}/api/users/auth/refresh" \
    -H "Content-Type: application/json" \
    -d "{\"refresh_token\":\"${REFRESH}\"}")
  NEW_TOKEN=$(echo "$REFRESH_RESP" | jq -r '.access_token // empty')
  if [[ -n "$NEW_TOKEN" ]]; then
    pass "Refresh token exchange"
    ACCESS="$NEW_TOKEN"
  else
    fail "Refresh token exchange"
  fi

  # Get profile
  CODE=$(http_code -H "Authorization: Bearer ${ACCESS}" "${ALB_URL}/api/users/profile")
  if [[ "$CODE" == "200" ]]; then
    pass "Get user profile"
  else
    fail "Get user profile (HTTP $CODE)"
  fi

  # Update profile
  CODE=$(http_code -X PUT "${ALB_URL}/api/users/profile" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${ACCESS}" \
    -d '{"age":25,"weight":70.0,"fitness_goals":"E2E test goals"}')
  if [[ "$CODE" == "200" ]]; then
    pass "Update user profile"
  else
    fail "Update user profile (HTTP $CODE)"
  fi
fi

# ─── 4. Metric ingestion → SQS → Lambda pipeline ─────────────

section "4. Metric Ingestion Pipeline"

if [[ -n "$ACCESS" ]]; then
  RECORDED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  # Single ingest
  INGEST=$(http_body -X POST "${ALB_URL}/api/metrics/ingest" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${ACCESS}" \
    -d "{\"metric_type\":\"steps\",\"value\":8500,\"recorded_at\":\"${RECORDED_AT}\"}")
  MSG_ID=$(echo "$INGEST" | jq -r '.message_id // empty')
  if [[ -n "$MSG_ID" ]]; then
    pass "Single metric ingest (SQS message_id: ${MSG_ID:0:8}...)"
  else
    fail "Single metric ingest"
  fi

  # Batch ingest
  BATCH=$(http_body -X POST "${ALB_URL}/api/metrics/ingest/batch" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${ACCESS}" \
    -d "{\"metrics\":[
      {\"metric_type\":\"heart_rate\",\"value\":72,\"recorded_at\":\"${RECORDED_AT}\"},
      {\"metric_type\":\"calories_burned\",\"value\":350,\"recorded_at\":\"${RECORDED_AT}\"},
      {\"metric_type\":\"sleep_hours\",\"value\":7.5,\"recorded_at\":\"${RECORDED_AT}\"}
    ]}")
  ACCEPTED=$(echo "$BATCH" | jq -r '.accepted_count // 0')
  if [[ "$ACCEPTED" -ge 3 ]]; then
    pass "Batch metric ingest ($ACCEPTED accepted)"
  else
    fail "Batch metric ingest (accepted: $ACCEPTED)"
  fi

  echo "  Waiting 10s for Lambda processing..."
  sleep 10

  # Read history
  HISTORY=$(http_body -H "Authorization: Bearer ${ACCESS}" \
    "${ALB_URL}/api/metrics/history?metric_type=steps&limit=5")
  TOTAL=$(echo "$HISTORY" | jq -r '.total // 0')
  if [[ "$TOTAL" -ge 1 ]]; then
    pass "Metric history returns data (total: $TOTAL)"
  else
    warn "Metric history empty — Lambda may still be processing"
  fi

  # Read summary
  CODE=$(http_code -H "Authorization: Bearer ${ACCESS}" \
    "${ALB_URL}/api/metrics/summary?period=daily&metric_type=steps")
  if [[ "$CODE" == "200" ]]; then
    pass "Metric summary endpoint reachable"
  else
    fail "Metric summary endpoint (HTTP $CODE)"
  fi
else
  warn "Skipping metric tests — no auth token available"
fi

# ─── 5. AWS Resource Verification ─────────────────────────────

section "5. CloudWatch Resources"

for LOG_GROUP in \
  "/ecs/${PROJECT}/user-service" \
  "/ecs/${PROJECT}/ingestion-service" \
  "/aws/lambda/${PROJECT}-analytics" \
  "/ecs/${PROJECT}/migrations"; do
  EXISTS=$(aws logs describe-log-groups \
    --log-group-name-prefix "$LOG_GROUP" \
    --region "$REGION" \
    --query "logGroups[?logGroupName=='${LOG_GROUP}'].logGroupName" \
    --output text 2>/dev/null)
  if [[ -n "$EXISTS" ]]; then
    pass "Log group: $LOG_GROUP"
  else
    fail "Log group missing: $LOG_GROUP"
  fi
done

# Check recent log streams exist (proves services are actually logging)
for SVC in "user-service" "ingestion-service"; do
  STREAMS=$(aws logs describe-log-streams \
    --log-group-name "/ecs/${PROJECT}/${SVC}" \
    --order-by LastEventTime --descending --limit 1 \
    --region "$REGION" \
    --query 'logStreams[0].logStreamName' \
    --output text 2>/dev/null)
  if [[ -n "$STREAMS" && "$STREAMS" != "None" ]]; then
    pass "Recent log stream in /ecs/${PROJECT}/${SVC}"
  else
    warn "No recent log streams in /ecs/${PROJECT}/${SVC}"
  fi
done

section "6. CloudWatch Alarms"

EXPECTED_ALARMS=(
  "${PROJECT}-sqs-depth"
  "${PROJECT}-dlq-messages"
  "${PROJECT}-lambda-errors"
  "${PROJECT}-user-db-cpu"
  "${PROJECT}-analytics-db-cpu"
  "${PROJECT}-ecs-user-cpu"
  "${PROJECT}-ecs-ingestion-cpu"
)

ALARM_JSON=$(aws cloudwatch describe-alarms \
  --alarm-name-prefix "${PROJECT}-" \
  --region "$REGION" \
  --query 'MetricAlarms[*].[AlarmName,StateValue]' \
  --output json 2>/dev/null)

for ALARM in "${EXPECTED_ALARMS[@]}"; do
  STATE=$(echo "$ALARM_JSON" | jq -r ".[] | select(.[0]==\"${ALARM}\") | .[1]" 2>/dev/null)
  if [[ -z "$STATE" ]]; then
    fail "Alarm missing: $ALARM"
  elif [[ "$STATE" == "OK" ]]; then
    pass "Alarm OK: $ALARM"
  elif [[ "$STATE" == "INSUFFICIENT_DATA" ]]; then
    warn "Alarm INSUFFICIENT_DATA: $ALARM (normal for new deployments)"
  else
    fail "Alarm in ALARM state: $ALARM"
  fi
done

section "7. SQS Queues"

for QUEUE in "analytics-queue" "analytics-dlq"; do
  Q_URL=$(aws sqs get-queue-url --queue-name "$QUEUE" --region "$REGION" \
    --query 'QueueUrl' --output text 2>/dev/null)
  if [[ -n "$Q_URL" && "$Q_URL" != "None" ]]; then
    ATTRS=$(aws sqs get-queue-attributes --queue-url "$Q_URL" --region "$REGION" \
      --attribute-names ApproximateNumberOfMessages \
      --query 'Attributes.ApproximateNumberOfMessages' --output text 2>/dev/null)
    pass "Queue: $QUEUE (messages: ${ATTRS:-0})"
    if [[ "$QUEUE" == "analytics-dlq" && "${ATTRS:-0}" -gt 0 ]]; then
      warn "DLQ has $ATTRS message(s) — check Lambda processing errors"
    fi
  else
    fail "Queue missing: $QUEUE"
  fi
done

section "8. SNS Topic & Subscriptions"

TOPIC_ARN=$(aws sns list-topics --region "$REGION" \
  --query "Topics[?ends_with(TopicArn, ':${PROJECT}-alerts')].TopicArn | [0]" \
  --output text 2>/dev/null)

if [[ -n "$TOPIC_ARN" && "$TOPIC_ARN" != "None" ]]; then
  pass "SNS topic: ${PROJECT}-alerts"

  SUBS=$(aws sns list-subscriptions-by-topic --topic-arn "$TOPIC_ARN" --region "$REGION" \
    --query 'Subscriptions[*].[Protocol,Endpoint,SubscriptionArn]' --output json 2>/dev/null)
  SUB_COUNT=$(echo "$SUBS" | jq 'length' 2>/dev/null)

  if [[ "${SUB_COUNT:-0}" -gt 0 ]]; then
    CONFIRMED=$(echo "$SUBS" | jq '[.[] | select(.[2] != "PendingConfirmation")] | length' 2>/dev/null)
    PENDING=$(echo "$SUBS" | jq '[.[] | select(.[2] == "PendingConfirmation")] | length' 2>/dev/null)
    if [[ "${CONFIRMED:-0}" -gt 0 ]]; then
      pass "SNS subscription confirmed ($CONFIRMED confirmed)"
    fi
    if [[ "${PENDING:-0}" -gt 0 ]]; then
      warn "SNS subscription pending confirmation ($PENDING pending) — check your email inbox"
    fi
  else
    warn "No SNS subscriptions found — add notification_email in terraform.tfvars"
  fi
else
  fail "SNS topic missing: ${PROJECT}-alerts"
fi

section "9. ECS Services"

for SVC in "user-service" "ingestion-service"; do
  STATUS=$(aws ecs describe-services \
    --cluster "${PROJECT}-cluster" --services "$SVC" \
    --region "$REGION" \
    --query 'services[0].[status,runningCount,desiredCount]' \
    --output json 2>/dev/null)
  SVC_STATUS=$(echo "$STATUS" | jq -r '.[0] // "UNKNOWN"' 2>/dev/null)
  RUNNING=$(echo "$STATUS" | jq -r '.[1] // 0' 2>/dev/null)
  DESIRED=$(echo "$STATUS" | jq -r '.[2] // 0' 2>/dev/null)
  if [[ "$SVC_STATUS" == "ACTIVE" && "$RUNNING" -ge "$DESIRED" ]]; then
    pass "ECS: $SVC (running: $RUNNING/$DESIRED)"
  elif [[ "$SVC_STATUS" == "ACTIVE" ]]; then
    warn "ECS: $SVC running $RUNNING/$DESIRED tasks"
  else
    fail "ECS: $SVC status=$SVC_STATUS"
  fi
done

section "10. CloudWatch Dashboard"

DASH=$(aws cloudwatch get-dashboard --dashboard-name "$PROJECT" --region "$REGION" \
  --query 'DashboardName' --output text 2>/dev/null)
if [[ "$DASH" == "$PROJECT" ]]; then
  pass "CloudWatch dashboard: $PROJECT"
else
  fail "CloudWatch dashboard missing"
fi

# ─── Summary ──────────────────────────────────────────────────

echo ""
bold "════════════════════════════════════════════"
bold "  Verification Summary"
bold "════════════════════════════════════════════"
green "  Passed:   $PASS"
if [[ $WARN -gt 0 ]]; then
  yellow "  Warnings: $WARN"
fi
if [[ $FAIL -gt 0 ]]; then
  red "  Failed:   $FAIL"
fi
echo ""

if [[ $FAIL -gt 0 ]]; then
  red "Some checks failed. Review output above."
  exit 1
else
  green "All critical checks passed!"
  if [[ $WARN -gt 0 ]]; then
    yellow "Review warnings above (usually resolve after the first full pipeline run)."
  fi
  exit 0
fi
