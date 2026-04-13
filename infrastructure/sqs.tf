resource "aws_sqs_queue" "analytics_dlq" {
  name                      = "analytics-dlq"
  message_retention_seconds = 1209600 # 14 days

  tags = { Name = "${var.project_name}-analytics-dlq" }
}

resource "aws_sqs_queue" "analytics" {
  name                       = "analytics-queue"
  visibility_timeout_seconds = 360 # 6× Lambda timeout (60 s)

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.analytics_dlq.arn
    maxReceiveCount     = 3
  })

  tags = { Name = "${var.project_name}-analytics-queue" }
}

resource "aws_sqs_queue_redrive_allow_policy" "dlq" {
  queue_url = aws_sqs_queue.analytics_dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.analytics.arn]
  })
}
