variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "fitness-tracker"
}

variable "environment" {
  type    = string
  default = "prod"
}

# ─── Domain ───────────────────────────────────────────────────

variable "domain_name" {
  description = "Root domain for the application (e.g. example.com)"
  type        = string
}

# ─── Networking ──────────────────────────────────────────────

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

# ─── Database ────────────────────────────────────────────────

variable "user_db_username" {
  type    = string
  default = "fitness_user"
}

variable "user_db_password" {
  type      = string
  sensitive = true
}

variable "analytics_db_username" {
  type    = string
  default = "fitness_analytics"
}

variable "analytics_db_password" {
  type      = string
  sensitive = true
}

# ─── Auth ────────────────────────────────────────────────────

variable "jwt_secret" {
  type      = string
  sensitive = true
}

# ─── Notifications ───────────────────────────────────────────

variable "notification_email" {
  description = "Email address for SNS anomaly and milestone alerts"
  type        = string
}

# ─── Container images ───────────────────────────────────────

variable "user_service_image_tag" {
  type    = string
  default = "latest"
}

variable "ingestion_service_image_tag" {
  type    = string
  default = "latest"
}

# ─── ECS sizing ──────────────────────────────────────────────

variable "ecs_cpu" {
  type    = number
  default = 256
}

variable "ecs_memory" {
  type    = number
  default = 512
}

variable "ecs_desired_count" {
  type    = number
  default = 2
}

variable "ecs_min_count" {
  description = "Minimum number of ECS tasks per service (auto-scaling floor)"
  type        = number
  default     = 1
}

variable "ecs_max_count" {
  description = "Maximum number of ECS tasks per service (auto-scaling ceiling)"
  type        = number
  default     = 4
}

variable "autoscaling_cpu_target" {
  description = "Target average CPU utilization (%) for ECS auto-scaling"
  type        = number
  default     = 70
}

variable "autoscaling_request_target" {
  description = "Target ALB request count per ECS task for auto-scaling"
  type        = number
  default     = 1000
}

# ─── CI/CD ────────────────────────────────────────────────────

variable "github_repo" {
  description = "GitHub repository in owner/repo format for OIDC trust policy"
  type        = string
}
