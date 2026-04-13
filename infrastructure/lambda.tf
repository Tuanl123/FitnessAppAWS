# Placeholder zip — CI/CD (Phase 4) deploys the real package.
data "archive_file" "lambda_placeholder" {
  type        = "zip"
  output_path = "${path.module}/lambda_placeholder.zip"

  source {
    content  = "def lambda_handler(event, context): return {'statusCode': 200}"
    filename = "handler.py"
  }
}

resource "aws_lambda_function" "analytics" {
  function_name = "${var.project_name}-analytics"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60
  memory_size   = 256

  reserved_concurrent_executions = -1

  filename         = data.archive_file.lambda_placeholder.output_path
  source_code_hash = data.archive_file.lambda_placeholder.output_base64sha256

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENVIRONMENT      = "aws"
      ANALYTICS_DB_URL = "postgresql://${var.analytics_db_username}:${var.analytics_db_password}@${aws_db_instance.analytics_db.endpoint}/analytics_db"
      SNS_TOPIC_ARN    = aws_sns_topic.alerts.arn
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda]

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }

  tags = { Name = "${var.project_name}-analytics-lambda" }
}

resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.analytics.arn
  function_name    = aws_lambda_function.analytics.arn
  batch_size       = 10
  enabled          = true
}
