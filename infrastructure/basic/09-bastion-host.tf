# ============================================
# Bastion Host (Proxy/Jump Server)
# ============================================
# EC2 instance for accessing deployed applications
# Located in public subnet with SSH access from anywhere

# Security Group for Bastion Host
resource "aws_security_group" "bastion" {
  count = var.create_vpc && var.enable_bastion ? 1 : 0

  name        = "${var.project_name}-bastion-sg-${var.environment}"
  description = "Security group for Bastion Host - allows SSH access"
  vpc_id      = module.vpc[0].vpc_id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access from anywhere"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-bastion-sg-${var.environment}"
  })
}

# Data source to get the latest Amazon Linux 2023 AMI for ARM64 (t4g instances)
data "aws_ami" "amazon_linux_2023_arm64" {
  count = var.create_vpc && var.enable_bastion ? 1 : 0

  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-arm64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# EC2 Instance - Bastion Host
resource "aws_instance" "bastion" {
  count = var.create_vpc && var.enable_bastion ? 1 : 0

  ami                    = data.aws_ami.amazon_linux_2023_arm64[0].id
  instance_type          = "t4g.nano"  # 1 vCPU, 1 GB RAM, ARM architecture
  key_name               = var.bastion_key_name
  iam_instance_profile   = aws_iam_instance_profile.bastion[0].name
  vpc_security_group_ids = [aws_security_group.bastion[0].id]
  subnet_id              = aws_subnet.public[0].id  # Place in first public subnet

  # User data script to mount EFS
  user_data = base64encode(templatefile("${path.module}/scripts/bastion-userdata.sh", {
    # Lowercase variables (used in script variable assignments)
    efs_file_system_id  = aws_efs_file_system.nexus_ai[0].id
    aws_region          = var.aws_region
    efs_mount_path      = "/mnt/efs"
    github_repo_url     = var.github_repo_url
    github_branch       = var.github_branch
    # Uppercase variables (used directly in script commands)
    EFS_FILE_SYSTEM_ID  = aws_efs_file_system.nexus_ai[0].id
    AWS_REGION          = var.aws_region
    EFS_MOUNT_PATH      = "/mnt/efs"
  }))

  # Enable detailed monitoring (optional, can disable to save costs)
  monitoring = false

  # Configure Instance Metadata Service v2 (IMDSv2) - Security best practice
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"  # Require IMDSv2 (session tokens)
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "enabled"
  }

  # Root volume configuration
  # Amazon Linux 2023 requires at least 30GB for the root volume
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 30  # Minimum required by Amazon Linux 2023 AMI
    delete_on_termination = true
    encrypted             = true

    tags = merge(local.common_tags, {
      Name = "${var.project_name}-bastion-root-${var.environment}"
    })
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-bastion-${var.environment}"
    Type = "bastion"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Elastic IP for Bastion Host (optional, but recommended for consistent access)
resource "aws_eip" "bastion" {
  count = var.create_vpc && var.enable_bastion ? 1 : 0

  domain = "vpc"
  instance = aws_instance.bastion[0].id

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-bastion-eip-${var.environment}"
  })

  depends_on = [aws_instance.bastion]
}

