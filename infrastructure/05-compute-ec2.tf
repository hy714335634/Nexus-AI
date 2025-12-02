# ============================================
# EC2 API Service Deployment
# ============================================

# Get latest Amazon Linux 2 AMI
data "aws_ami" "amazon_linux_2" {
  count = var.create_vpc && var.api_deploy_on_ec2 ? 1 : 0

  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Launch Template for EC2 API Service
resource "aws_launch_template" "api" {
  count = var.create_vpc && var.api_deploy_on_ec2 ? 1 : 0

  name_prefix   = "${var.project_name}-api-${var.environment}-"
  image_id      = data.aws_ami.amazon_linux_2[0].id
  instance_type = var.ec2_api_instance_type
  key_name      = var.ec2_api_key_name != "" ? var.ec2_api_key_name : null

  vpc_security_group_ids = [aws_security_group.ec2_api[0].id]

  iam_instance_profile {
    name = aws_iam_instance_profile.ec2_api[0].name
  }

  user_data = base64encode(templatefile("${path.module}/scripts/ec2-api-userdata.sh", {
    # Lowercase variables (used in script variable assignments)
    efs_file_system_id   = aws_efs_file_system.nexus_ai[0].id
    efs_access_point_id  = aws_efs_access_point.app_data[0].id
    aws_region           = var.aws_region
    ecr_repository_url   = aws_ecr_repository.api.repository_url
    dynamodb_region      = var.aws_region
    agent_projects_table = var.enable_dynamodb ? aws_dynamodb_table.agent_projects[0].name : ""
    agent_instances_table = var.enable_dynamodb ? aws_dynamodb_table.agent_instances[0].name : ""
    sqs_queue_url        = var.enable_sqs ? aws_sqs_queue.nexus_notifications[0].url : ""
    environment          = var.environment
    github_repo_url      = var.github_repo_url
    github_branch        = var.github_branch
    efs_mount_path       = "/mnt/efs"
    app_dir              = "/opt/nexus-ai-api"
    project_root         = "/opt/nexus-ai"
    # Uppercase variables (used directly in script commands and heredoc)
    EFS_FILE_SYSTEM_ID   = aws_efs_file_system.nexus_ai[0].id
    EFS_ACCESS_POINT_ID  = aws_efs_access_point.app_data[0].id
    AWS_REGION           = var.aws_region
    ECR_REPOSITORY_URL   = aws_ecr_repository.api.repository_url
    DYNAMODB_REGION      = var.aws_region
    AGENT_PROJECTS_TABLE = var.enable_dynamodb ? aws_dynamodb_table.agent_projects[0].name : ""
    AGENT_INSTANCES_TABLE = var.enable_dynamodb ? aws_dynamodb_table.agent_instances[0].name : ""
    SQS_QUEUE_URL        = var.enable_sqs ? aws_sqs_queue.nexus_notifications[0].url : ""
    ENVIRONMENT          = var.environment
    GITHUB_REPO_URL      = var.github_repo_url
    GITHUB_BRANCH        = var.github_branch
    EFS_MOUNT_PATH       = "/mnt/efs"
    APP_DIR              = "/opt/nexus-ai-api"
    PROJECT_ROOT         = "/opt/nexus-ai"
  }))

  # Configure Instance Metadata Service v2 (IMDSv2) - Security best practice
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"  # Require IMDSv2 (session tokens)
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "enabled"
  }

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size           = var.ec2_api_volume_size
      volume_type           = "gp3"
      delete_on_termination = true
      encrypted             = true
    }
  }

  tag_specifications {
    resource_type = "instance"

    tags = merge(local.common_tags, {
      Name = "${var.project_name}-api-ec2-${var.environment}"
    })
  }

  tag_specifications {
    resource_type = "volume"

    tags = merge(local.common_tags, {
      Name = "${var.project_name}-api-ec2-${var.environment}"
    })
  }

  tags = local.common_tags

  depends_on = [
    aws_efs_mount_target.nexus_ai
  ]
}

# Auto Scaling Group for EC2 API Service
resource "aws_autoscaling_group" "api" {
  count = var.create_vpc && var.api_deploy_on_ec2 ? 1 : 0

  name                = "${var.project_name}-api-asg-${var.environment}"
  vpc_zone_identifier = local.private_subnets
  target_group_arns   = [aws_lb_target_group.api[0].arn]
  health_check_type   = "EC2"
  health_check_grace_period = 300

  min_size         = var.ec2_api_min_size
  max_size         = var.ec2_api_max_size
  desired_capacity = var.ec2_api_desired_capacity

  launch_template {
    id      = aws_launch_template.api[0].id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "${var.project_name}-api-ec2-${var.environment}"
    propagate_at_launch = true
  }

  dynamic "tag" {
    for_each = local.common_tags
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }

  depends_on = [
    aws_lb_target_group.api,
    aws_launch_template.api
  ]
}

# Auto Scaling Policy - Scale up
resource "aws_autoscaling_policy" "api_scale_up" {
  count = var.create_vpc && var.api_deploy_on_ec2 ? 1 : 0

  name                   = "${var.project_name}-api-scale-up-${var.environment}"
  scaling_adjustment     = 1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_autoscaling_group.api[0].name
}

# Auto Scaling Policy - Scale down
resource "aws_autoscaling_policy" "api_scale_down" {
  count = var.create_vpc && var.api_deploy_on_ec2 ? 1 : 0

  name                   = "${var.project_name}-api-scale-down-${var.environment}"
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_autoscaling_group.api[0].name
}

# CloudWatch Alarm - High CPU
resource "aws_cloudwatch_metric_alarm" "api_cpu_high" {
  count = var.create_vpc && var.api_deploy_on_ec2 ? 1 : 0

  alarm_name          = "${var.project_name}-api-cpu-high-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 70
  alarm_description   = "This metric monitors EC2 API CPU utilization"
  alarm_actions       = [aws_autoscaling_policy.api_scale_up[0].arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.api[0].name
  }
}

# CloudWatch Alarm - Low CPU
resource "aws_cloudwatch_metric_alarm" "api_cpu_low" {
  count = var.create_vpc && var.api_deploy_on_ec2 ? 1 : 0

  alarm_name          = "${var.project_name}-api-cpu-low-${var.environment}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 30
  alarm_description   = "This metric monitors EC2 API CPU utilization"
  alarm_actions       = [aws_autoscaling_policy.api_scale_down[0].arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.api[0].name
  }
}

