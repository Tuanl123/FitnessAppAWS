# ─── Networking ──────────────────────────────────────────────

output "vpc_id" {
  value = aws_vpc.main.id
}

output "alb_dns_name" {
  description = "ALB public DNS — use for API requests before CloudFront"
  value       = aws_lb.main.dns_name
}

# ─── CDN ─────────────────────────────────────────────────────

output "cloudfront_domain_name" {
  description = "CloudFront URL — main entry point for the application"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_distribution_id" {
  description = "Used by CI/CD to invalidate the cache after deploy"
  value       = aws_cloudfront_distribution.frontend.id
}

# ─── ECR ─────────────────────────────────────────────────────

output "ecr_user_service_url" {
  value = aws_ecr_repository.user_service.repository_url
}

output "ecr_ingestion_service_url" {
  value = aws_ecr_repository.ingestion_service.repository_url
}

output "ecr_analytics_lambda_url" {
  value = aws_ecr_repository.analytics_lambda.repository_url
}

# ─── Databases ───────────────────────────────────────────────

output "user_db_endpoint" {
  value = aws_db_instance.user_db.endpoint
}

output "analytics_db_endpoint" {
  value = aws_db_instance.analytics_db.endpoint
}

# ─── Messaging ───────────────────────────────────────────────

output "sqs_queue_url" {
  value = aws_sqs_queue.analytics.url
}

output "sns_topic_arn" {
  value = aws_sns_topic.alerts.arn
}

# ─── Compute ─────────────────────────────────────────────────

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "lambda_function_name" {
  value = aws_lambda_function.analytics.function_name
}

# ─── Storage ─────────────────────────────────────────────────

output "frontend_bucket_name" {
  description = "S3 bucket for frontend build artifacts"
  value       = aws_s3_bucket.frontend.bucket
}

# ─── Monitoring ───────────────────────────────────────────────

output "amp_workspace_endpoint" {
  description = "Amazon Managed Prometheus remote-write and query endpoint"
  value       = aws_prometheus_workspace.main.prometheus_endpoint
}

output "grafana_workspace_url" {
  description = "Amazon Managed Grafana workspace URL"
  value       = aws_grafana_workspace.main.endpoint
}

# ─── WAF ──────────────────────────────────────────────────────

output "waf_web_acl_arn" {
  description = "WAFv2 Web ACL ARN attached to CloudFront"
  value       = aws_wafv2_web_acl.cloudfront.arn
}

# ─── DNS ──────────────────────────────────────────────────────

output "route53_name_servers" {
  description = "Point your domain registrar NS records to these"
  value       = aws_route53_zone.main.name_servers
}

output "app_domain" {
  description = "Custom domain for the application"
  value       = var.domain_name
}

# ─── CI/CD ─────────────────────────────────────────────────────

output "github_actions_role_arn" {
  description = "IAM role ARN for GitHub Actions OIDC — set as AWS_ROLE_ARN repo secret"
  value       = aws_iam_role.github_actions.arn
}
