# ─── Amazon Managed Prometheus (AMP) ─────────────────────────

resource "aws_prometheus_workspace" "main" {
  alias = "${var.project_name}-prometheus"

  tags = { Name = "${var.project_name}-amp" }
}

# ─── Amazon Managed Grafana (AMG) ────────────────────────────
# Requires AWS IAM Identity Center (SSO) enabled in the account.

resource "aws_grafana_workspace" "main" {
  name                     = "${var.project_name}-grafana"
  account_access_type      = "CURRENT_ACCOUNT"
  authentication_providers = ["AWS_SSO"]
  permission_type          = "SERVICE_MANAGED"
  role_arn                 = aws_iam_role.grafana.arn
  data_sources             = ["PROMETHEUS"]

  tags = { Name = "${var.project_name}-amg" }
}

# ─── IAM Role for Grafana (read AMP) ─────────────────────────

resource "aws_iam_role" "grafana" {
  name = "${var.project_name}-grafana"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "grafana.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "grafana_amp" {
  name = "amp-read"
  role = aws_iam_role.grafana.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "aps:QueryMetrics",
        "aps:GetSeries",
        "aps:GetLabels",
        "aps:GetMetricMetadata",
      ]
      Resource = "${aws_prometheus_workspace.main.arn}/*"
    }]
  })
}

# ─── ADOT: AMP remote-write permission on ECS task role ──────

resource "aws_iam_role_policy" "ecs_task_amp" {
  name = "amp-remote-write"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["aps:RemoteWrite"]
      Resource = "${aws_prometheus_workspace.main.arn}/*"
    }]
  })
}

# ─── ADOT Collector configs (one per service) ────────────────

resource "aws_ssm_parameter" "adot_config_user" {
  name = "/${var.project_name}/adot-config-user"
  type = "String"

  value = yamlencode({
    receivers = {
      prometheus = {
        config = {
          scrape_configs = [{
            job_name        = "user-service"
            scrape_interval = "30s"
            static_configs  = [{ targets = ["localhost:8000"] }]
          }]
        }
      }
    }
    exporters = {
      prometheusremotewrite = {
        endpoint = "${aws_prometheus_workspace.main.prometheus_endpoint}api/v1/remote_write"
        auth     = { authenticator = "sigv4auth" }
      }
    }
    extensions = {
      sigv4auth = { region = var.aws_region, service = "aps" }
    }
    service = {
      extensions = ["sigv4auth"]
      pipelines = {
        metrics = {
          receivers = ["prometheus"]
          exporters = ["prometheusremotewrite"]
        }
      }
    }
  })

  tags = { Name = "${var.project_name}-adot-config-user" }
}

resource "aws_ssm_parameter" "adot_config_ingestion" {
  name = "/${var.project_name}/adot-config-ingestion"
  type = "String"

  value = yamlencode({
    receivers = {
      prometheus = {
        config = {
          scrape_configs = [{
            job_name        = "ingestion-service"
            scrape_interval = "30s"
            static_configs  = [{ targets = ["localhost:8001"] }]
          }]
        }
      }
    }
    exporters = {
      prometheusremotewrite = {
        endpoint = "${aws_prometheus_workspace.main.prometheus_endpoint}api/v1/remote_write"
        auth     = { authenticator = "sigv4auth" }
      }
    }
    extensions = {
      sigv4auth = { region = var.aws_region, service = "aps" }
    }
    service = {
      extensions = ["sigv4auth"]
      pipelines = {
        metrics = {
          receivers = ["prometheus"]
          exporters = ["prometheusremotewrite"]
        }
      }
    }
  })

  tags = { Name = "${var.project_name}-adot-config-ingestion" }
}
