# ============================================
# VPC Module
# ============================================
module "vpc" {
  count  = var.create_vpc && var.enable_lambda ? 1 : 0
  source = "./modules/networking/vpc"

  create_vpc         = var.create_vpc
  vpc_cidr           = var.vpc_cidr
  project_name       = var.project_name
  environment        = var.environment
  availability_zones = local.availability_zones
  tags               = local.common_tags
}

# ============================================
# Security Groups
# ============================================
resource "aws_security_group" "lambda_sg" {
  count = var.enable_lambda ? 1 : 0

  name        = "${var.project_name}-lambda-sg-${var.environment}"
  description = "Security group for Lambda function"
  vpc_id      = local.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-lambda-sg-${var.environment}"
  })
}

resource "aws_security_group" "efs_sg" {
  count = var.enable_lambda ? 1 : 0

  name        = "${var.project_name}-efs-sg-${var.environment}"
  description = "Security group for EFS"
  vpc_id      = local.vpc_id

  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg[0].id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-efs-sg-${var.environment}"
  })
}

# ============================================
# Locals for VPC
# ============================================
locals {
  vpc_id     = var.create_vpc ? module.vpc[0].vpc_id : var.vpc_id
  subnet_ids = var.create_vpc ? module.vpc[0].subnet_ids : var.subnet_ids
}
