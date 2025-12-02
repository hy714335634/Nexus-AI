# ============================================
# EFS File System for Shared Storage
# ============================================
resource "aws_efs_file_system" "nexus_ai" {
  count = var.create_vpc ? 1 : 0

  encrypted        = true
  performance_mode = "generalPurpose"
  throughput_mode  = "bursting"

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-efs-${var.environment}"
  })
}

# ============================================
# EFS Mount Targets
# ============================================
resource "aws_efs_mount_target" "nexus_ai" {
  count = var.create_vpc ? length(local.private_subnets) : 0

  file_system_id  = aws_efs_file_system.nexus_ai[0].id
  subnet_id       = local.private_subnets[count.index]
  security_groups = [aws_security_group.efs[0].id]
}

# ============================================
# EFS Access Point for Application Data (Root Access)
# ============================================
# This access point provides root directory access so all services
# (Bastion, EC2, Fargate) can share the same repo and projects directory
resource "aws_efs_access_point" "app_data" {
  count = var.create_vpc ? 1 : 0

  file_system_id = aws_efs_file_system.nexus_ai[0].id

  posix_user {
    gid = 1000
    uid = 1000
  }

  # Use root directory "/" to allow access to all paths including /nexus-ai-repo
  root_directory {
    path = "/"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-efs-access-point-${var.environment}"
  })
}
