resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ─── User Service ───────────────────────────────────────────

resource "aws_ecs_task_definition" "user_service" {
  family                   = "${var.project_name}-user-service"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_cpu + 256
  memory                   = var.ecs_memory + 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "user-service"
      image = "${aws_ecr_repository.user_service.repository_url}:${var.user_service_image_tag}"

      portMappings = [{
        containerPort = 8000
        protocol      = "tcp"
      }]

      environment = [
        { name = "ENVIRONMENT", value = "aws" },
      ]

      secrets = [
        { name = "USER_DB_URL", valueFrom = aws_secretsmanager_secret.user_db.arn },
        { name = "JWT_SECRET", valueFrom = aws_secretsmanager_secret.jwt.arn },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.user_service.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    },
    {
      name      = "adot-collector"
      image     = "public.ecr.aws/aws-observability/aws-otel-collector:latest"
      essential = false

      secrets = [{
        name      = "AOT_CONFIG_CONTENT"
        valueFrom = aws_ssm_parameter.adot_config_user.arn
      }]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.adot.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "adot-user"
        }
      }
    },
  ])
}

resource "aws_ecs_service" "user_service" {
  name            = "user-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.user_service.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.user_service.arn
    container_name   = "user-service"
    container_port   = 8000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [aws_lb_listener.http]
}

# ─── Ingestion (Metrics) Service ────────────────────────────

resource "aws_ecs_task_definition" "ingestion_service" {
  family                   = "${var.project_name}-ingestion-service"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_cpu + 256
  memory                   = var.ecs_memory + 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "ingestion-service"
      image = "${aws_ecr_repository.ingestion_service.repository_url}:${var.ingestion_service_image_tag}"

      portMappings = [{
        containerPort = 8001
        protocol      = "tcp"
      }]

      environment = [
        { name = "ENVIRONMENT", value = "aws" },
        { name = "SQS_QUEUE_NAME", value = aws_sqs_queue.analytics.name },
        { name = "SQS_ENDPOINT_URL", value = "" },
        { name = "AWS_DEFAULT_REGION", value = var.aws_region },
      ]

      secrets = [
        { name = "ANALYTICS_DB_URL", valueFrom = aws_secretsmanager_secret.analytics_db.arn },
        { name = "JWT_SECRET", valueFrom = aws_secretsmanager_secret.jwt.arn },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ingestion_service.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    },
    {
      name      = "adot-collector"
      image     = "public.ecr.aws/aws-observability/aws-otel-collector:latest"
      essential = false

      secrets = [{
        name      = "AOT_CONFIG_CONTENT"
        valueFrom = aws_ssm_parameter.adot_config_ingestion.arn
      }]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.adot.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "adot-ingestion"
        }
      }
    },
  ])
}

resource "aws_ecs_service" "ingestion_service" {
  name            = "ingestion-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ingestion_service.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.metrics_service.arn
    container_name   = "ingestion-service"
    container_port   = 8001
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [aws_lb_listener.http]
}

# ─── Analytics DB Migration Task ─────────────────────────────
# One-off ECS task used by CI/CD to run Alembic migrations on
# analytics_db before deploying the Lambda. Uses the same Docker
# image as the analytics-lambda worker.

resource "aws_ecs_task_definition" "analytics_migrate" {
  family                   = "${var.project_name}-analytics-migrate"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_cpu
  memory                   = var.ecs_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([{
    name      = "analytics-migrate"
    image     = "${aws_ecr_repository.analytics_lambda.repository_url}:latest"
    essential = true

    environment = [
      { name = "ENVIRONMENT", value = "aws" },
    ]

    secrets = [
      { name = "ANALYTICS_DB_URL", valueFrom = aws_secretsmanager_secret.analytics_db.arn },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/${var.project_name}/migrations"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "analytics"
      }
    }
  }])

  lifecycle {
    ignore_changes = [container_definitions]
  }
}

# ─── Auto Scaling ─────────────────────────────────────────────

resource "aws_appautoscaling_target" "user_service" {
  max_capacity       = var.ecs_max_count
  min_capacity       = var.ecs_min_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.user_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_target" "ingestion_service" {
  max_capacity       = var.ecs_max_count
  min_capacity       = var.ecs_min_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.ingestion_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Scale on CPU utilization

resource "aws_appautoscaling_policy" "user_service_cpu" {
  name               = "${var.project_name}-user-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.user_service.resource_id
  scalable_dimension = aws_appautoscaling_target.user_service.scalable_dimension
  service_namespace  = aws_appautoscaling_target.user_service.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = var.autoscaling_cpu_target
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_policy" "ingestion_service_cpu" {
  name               = "${var.project_name}-ingestion-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ingestion_service.resource_id
  scalable_dimension = aws_appautoscaling_target.ingestion_service.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ingestion_service.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = var.autoscaling_cpu_target
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Scale on ALB request count per target

resource "aws_appautoscaling_policy" "user_service_requests" {
  name               = "${var.project_name}-user-request-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.user_service.resource_id
  scalable_dimension = aws_appautoscaling_target.user_service.scalable_dimension
  service_namespace  = aws_appautoscaling_target.user_service.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.main.arn_suffix}/${aws_lb_target_group.user_service.arn_suffix}"
    }
    target_value       = var.autoscaling_request_target
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_policy" "ingestion_service_requests" {
  name               = "${var.project_name}-ingestion-request-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ingestion_service.resource_id
  scalable_dimension = aws_appautoscaling_target.ingestion_service.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ingestion_service.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.main.arn_suffix}/${aws_lb_target_group.metrics_service.arn_suffix}"
    }
    target_value       = var.autoscaling_request_target
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
