# ============================================
# IAM Role for Bastion Host
# ============================================

# EC2 Instance Role
resource "aws_iam_role" "bastion" {
  count = var.create_vpc && var.enable_bastion ? 1 : 0

  name = "${var.project_name}-bastion-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# Attach AWS managed policy for EC2 instance
resource "aws_iam_role_policy_attachment" "bastion_ssm" {
  count = var.create_vpc && var.enable_bastion ? 1 : 0

  role       = aws_iam_role.bastion[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Policy for EFS access
resource "aws_iam_role_policy" "bastion_efs" {
  count = var.create_vpc && var.enable_bastion ? 1 : 0

  name = "${var.project_name}-bastion-efs-${var.environment}"
  role = aws_iam_role.bastion[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientRootAccess",
          "elasticfilesystem:DescribeMountTargets",
          "elasticfilesystem:DescribeFileSystems",
          "elasticfilesystem:DescribeAccessPoints"
        ]
        Resource = var.create_vpc ? aws_efs_file_system.nexus_ai[0].arn : "*"
      },
      {
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientRootAccess"
        ]
        Resource = var.create_vpc ? aws_efs_access_point.app_data[0].arn : "*"
      }
    ]
  })
}

# Instance Profile
resource "aws_iam_instance_profile" "bastion" {
  count = var.create_vpc && var.enable_bastion ? 1 : 0

  name = "${var.project_name}-bastion-${var.environment}"
  role = aws_iam_role.bastion[0].name

  tags = local.common_tags
}

