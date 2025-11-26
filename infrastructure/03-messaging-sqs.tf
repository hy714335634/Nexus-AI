resource "aws_sqs_queue" "nexus_notifications" {
  count = var.enable_sqs ? 1 : 0

  name                       = "${var.project_name}-notifications-${var.environment}"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 345600
  receive_wait_time_seconds  = 10
  visibility_timeout_seconds = 300

  tags = local.common_tags
}

resource "aws_sqs_queue" "nexus_notifications_dlq" {
  count = var.enable_sqs ? 1 : 0

  name                      = "${var.project_name}-notifications-dlq-${var.environment}"
  message_retention_seconds = 1209600

  tags = local.common_tags
}

resource "aws_sqs_queue_redrive_policy" "nexus_notifications" {
  count = var.enable_sqs ? 1 : 0

  queue_url = aws_sqs_queue.nexus_notifications[0].id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.nexus_notifications_dlq[0].arn
    maxReceiveCount     = 3
  })
}
