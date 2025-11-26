# ============================================
# Docker Image Build and Push
# ============================================

resource "null_resource" "docker_image" {
  count = var.enable_lambda ? 1 : 0

  triggers = {
    # 当 Dockerfile 或源代码变化时重新构建
    dockerfile_hash = filemd5("${path.module}/scripts/Dockerfile")
    ecr_repo        = aws_ecr_repository.nexus_ai[0].repository_url
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      echo "Building Docker image..."
      cd ${path.module}/..
      docker build -f infrastructure/scripts/Dockerfile -t nexus-ai-lambda:latest .
      
      echo "Logging into ECR..."
      aws ecr get-login-password --region ${var.aws_region} | \
        docker login --username AWS --password-stdin ${aws_ecr_repository.nexus_ai[0].repository_url}
      
      echo "Tagging and pushing image..."
      docker tag nexus-ai-lambda:latest ${aws_ecr_repository.nexus_ai[0].repository_url}:latest
      docker push ${aws_ecr_repository.nexus_ai[0].repository_url}:latest
      
      echo "✅ Docker image pushed successfully!"
    EOT
  }

  depends_on = [aws_ecr_repository.nexus_ai]
}
