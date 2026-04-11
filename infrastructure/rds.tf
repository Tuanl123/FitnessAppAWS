resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db"
  subnet_ids = aws_subnet.private[*].id

  tags = { Name = "${var.project_name}-db-subnet-group" }
}

# ─── User DB ────────────────────────────────────────────────

resource "aws_db_instance" "user_db" {
  identifier     = "${var.project_name}-user-db"
  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t3.micro"

  allocated_storage     = 20
  max_allocated_storage = 50
  storage_type          = "gp3"

  db_name  = "user_db"
  username = var.user_db_username
  password = var.user_db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az            = false
  publicly_accessible = false
  skip_final_snapshot = true

  backup_retention_period = 7

  tags = { Name = "${var.project_name}-user-db" }
}

# ─── Analytics DB ───────────────────────────────────────────

resource "aws_db_instance" "analytics_db" {
  identifier     = "${var.project_name}-analytics-db"
  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t3.micro"

  allocated_storage     = 20
  max_allocated_storage = 50
  storage_type          = "gp3"

  db_name  = "analytics_db"
  username = var.analytics_db_username
  password = var.analytics_db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az            = false
  publicly_accessible = false
  skip_final_snapshot = true

  backup_retention_period = 7

  tags = { Name = "${var.project_name}-analytics-db" }
}
