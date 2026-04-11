# recovery_window_in_days = 0 allows clean `terraform destroy` cycles.

resource "aws_secretsmanager_secret" "user_db" {
  name                    = "${var.project_name}/user-db-url"
  recovery_window_in_days = 0

  tags = { Name = "${var.project_name}-user-db-secret" }
}

resource "aws_secretsmanager_secret_version" "user_db" {
  secret_id     = aws_secretsmanager_secret.user_db.id
  secret_string = "postgresql+asyncpg://${var.user_db_username}:${var.user_db_password}@${aws_db_instance.user_db.endpoint}/user_db"
}

resource "aws_secretsmanager_secret" "analytics_db" {
  name                    = "${var.project_name}/analytics-db-url"
  recovery_window_in_days = 0

  tags = { Name = "${var.project_name}-analytics-db-secret" }
}

resource "aws_secretsmanager_secret_version" "analytics_db" {
  secret_id     = aws_secretsmanager_secret.analytics_db.id
  secret_string = "postgresql://${var.analytics_db_username}:${var.analytics_db_password}@${aws_db_instance.analytics_db.endpoint}/analytics_db"
}

resource "aws_secretsmanager_secret" "jwt" {
  name                    = "${var.project_name}/jwt-secret"
  recovery_window_in_days = 0

  tags = { Name = "${var.project_name}-jwt-secret" }
}

resource "aws_secretsmanager_secret_version" "jwt" {
  secret_id     = aws_secretsmanager_secret.jwt.id
  secret_string = var.jwt_secret
}
