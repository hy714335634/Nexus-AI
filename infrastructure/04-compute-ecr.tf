# ============================================
# ECR Repository for Lambda Container Images
# ============================================

resource "aws_ecr_repository" "nexus_ai" {
  count = var.enable_lambda ? 1 : 0

  name                 = "${var.project_name}-lambda-${var.environment}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

resource "aws_ecr_lifecycle_policy" "nexus_ai" {
  count = var.enable_lambda ? 1 : 0

  repository = aws_ecr_repository.nexus_ai[0].name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = {
        type = "expire"
      }
    }]
  })
}
