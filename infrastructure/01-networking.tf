# ============================================
# VPC Module
# ============================================
module "vpc" {
  count  = var.create_vpc ? 1 : 0
  source = "./modules/networking/vpc"

  create_vpc         = var.create_vpc
  vpc_cidr           = var.vpc_cidr
  project_name       = var.project_name
  environment        = var.environment
  availability_zones = local.availability_zones
  tags               = local.common_tags
}

# ============================================
# Public Subnets for ALB
# ============================================
resource "aws_subnet" "public" {
  count = var.create_vpc ? 2 : 0

  vpc_id                  = module.vpc[0].vpc_id
  cidr_block              = "10.0.${count.index + 10}.0/24"
  availability_zone       = local.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-public-subnet-${count.index + 1}-${var.environment}"
    Type = "public"
  })
}

# ============================================
# Private Subnets for ECS
# ============================================
resource "aws_subnet" "private" {
  count = var.create_vpc ? 2 : 0

  vpc_id            = module.vpc[0].vpc_id
  cidr_block        = "10.0.${count.index + 20}.0/24"
  availability_zone = local.availability_zones[count.index]

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-private-subnet-${count.index + 1}-${var.environment}"
    Type = "private"
  })
}

# ============================================
# Internet Gateway (already in VPC module, but we need reference)
# ============================================
# Using the one from VPC module

# ============================================
# NAT Gateway for private subnets
# ============================================
resource "aws_eip" "nat" {
  count = var.create_vpc ? 1 : 0

  domain = "vpc"
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-nat-eip-${var.environment}"
  })
}

resource "aws_nat_gateway" "main" {
  count = var.create_vpc ? 1 : 0

  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-nat-${var.environment}"
  })

  depends_on = [module.vpc]
}

# ============================================
# Route Tables
# ============================================
resource "aws_route_table" "public" {
  count = var.create_vpc ? 1 : 0

  vpc_id = module.vpc[0].vpc_id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = module.vpc[0].internet_gateway_id
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-public-rt-${var.environment}"
  })
}

resource "aws_route_table" "private" {
  count = var.create_vpc ? 1 : 0

  vpc_id = module.vpc[0].vpc_id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[0].id
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-private-rt-${var.environment}"
  })
}

resource "aws_route_table_association" "public" {
  count = var.create_vpc ? 2 : 0

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}

resource "aws_route_table_association" "private" {
  count = var.create_vpc ? 2 : 0

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[0].id
}

# ============================================
# Security Groups
# ============================================
resource "aws_security_group" "alb" {
  count = var.create_vpc ? 1 : 0

  name        = "${var.project_name}-alb-sg-${var.environment}"
  description = "Security group for Application Load Balancer"
  vpc_id      = module.vpc[0].vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP traffic"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-alb-sg-${var.environment}"
  })
}

resource "aws_security_group" "ecs" {
  count = var.create_vpc ? 1 : 0

  name        = "${var.project_name}-ecs-sg-${var.environment}"
  description = "Security group for ECS tasks"
  vpc_id      = module.vpc[0].vpc_id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb[0].id]
    description     = "API from ALB"
  }

  ingress {
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb[0].id]
    description     = "Frontend from ALB"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-ecs-sg-${var.environment}"
  })
}

resource "aws_security_group" "efs" {
  count = var.create_vpc ? 1 : 0

  name        = "${var.project_name}-efs-sg-${var.environment}"
  description = "Security group for EFS"
  vpc_id      = module.vpc[0].vpc_id

  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs[0].id]
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

# Redis will use the same ECS security group
# Allow ECS containers to communicate with each other (including Redis)
resource "aws_security_group_rule" "ecs_redis" {
  count = var.create_vpc ? 1 : 0

  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ecs[0].id
  security_group_id        = aws_security_group.ecs[0].id
  description              = "Allow ECS containers to access Redis"
}

# ============================================
# Locals for VPC
# ============================================
locals {
  vpc_id          = var.create_vpc ? module.vpc[0].vpc_id : var.vpc_id
  public_subnets  = var.create_vpc ? aws_subnet.public[*].id : []
  private_subnets = var.create_vpc ? aws_subnet.private[*].id : var.subnet_ids
}
