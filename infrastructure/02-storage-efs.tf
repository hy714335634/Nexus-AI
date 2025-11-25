# ============================================
# EFS File System
# ============================================
resource "aws_efs_file_system" "lambda_efs" {
  count = var.enable_lambda ? 1 : 0

  encrypted = true

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-efs-${var.environment}"
  })
}

# ============================================
# EFS Mount Targets
# ============================================
resource "aws_efs_mount_target" "lambda_efs_mt" {
  count = var.enable_lambda ? length(local.subnet_ids) : 0

  file_system_id  = aws_efs_file_system.lambda_efs[0].id
  subnet_id       = local.subnet_ids[count.index]
  security_groups = [aws_security_group.efs_sg[0].id]
}

# ============================================
# EFS Access Point
# ============================================
resource "aws_efs_access_point" "lambda_ap" {
  count = var.enable_lambda ? 1 : 0

  file_system_id = aws_efs_file_system.lambda_efs[0].id

  posix_user {
    gid = 1000
    uid = 1000
  }

  root_directory {
    path = "/lambda"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }

  tags = local.common_tags
}
