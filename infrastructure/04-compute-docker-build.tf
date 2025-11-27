# ============================================
# Docker Image Build and Push
# ============================================
# This resource automatically builds and pushes Docker images
# to ECR after the repositories are created.
#
# Note: This will run during terraform apply. Make sure you have:
# - Docker installed and running
# - AWS CLI configured
# - jq installed (for parsing terraform outputs)
#
# To skip automatic build, set TF_VAR_skip_docker_build=true

resource "null_resource" "docker_build_and_push" {
  count = var.create_vpc && !var.skip_docker_build ? 1 : 0

  triggers = {
    # Rebuild when ECR repositories change
    api_repo          = aws_ecr_repository.api.repository_url
    frontend_repo     = aws_ecr_repository.frontend.repository_url
    celery_repo       = aws_ecr_repository.celery_worker.repository_url
    
    # Rebuild when source code changes (optional - uncomment if needed)
    # api_dockerfile_hash    = filemd5("${path.module}/../api/Dockerfile")
    # frontend_dockerfile_hash = filemd5("${path.module}/../web/Dockerfile")
    # api_requirements_hash   = filemd5("${path.module}/../api/requirements.txt")
    # frontend_package_hash   = filemd5("${path.module}/../web/package.json")
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      echo "🚀 Building and pushing Docker images to ECR..."
      
      PROJECT_ROOT="${path.module}/.."
      INFRA_DIR="${path.module}"
      AWS_REGION="${var.aws_region}"
      AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
      
      # Login to ECR
      echo "🔐 Logging in to ECR..."
      aws ecr get-login-password --region ${var.aws_region} | \
        docker login --username AWS --password-stdin ${aws_ecr_repository.api.repository_url}
      
      # Build and push API image
      echo "📦 Building API image..."
      cd $PROJECT_ROOT/api
      if [ ! -f "Dockerfile" ]; then
        echo "❌ Error: Dockerfile not found in $PROJECT_ROOT/api"
        exit 1
      fi
      # Build for linux/amd64 platform (required for AWS ECS Fargate)
      docker build --platform linux/amd64 -t ${aws_ecr_repository.api.repository_url}:latest .
      TIMESTAMP=$(date +%Y%m%d-%H%M%S)
      docker tag ${aws_ecr_repository.api.repository_url}:latest ${aws_ecr_repository.api.repository_url}:$TIMESTAMP
      echo "📤 Pushing API image..."
      docker push ${aws_ecr_repository.api.repository_url}:latest
      docker push ${aws_ecr_repository.api.repository_url}:$TIMESTAMP
      
      # Build and push Frontend image
      echo "📦 Building Frontend image..."
      cd $PROJECT_ROOT/web
      if [ ! -f "Dockerfile" ]; then
        echo "❌ Error: Dockerfile not found in $PROJECT_ROOT/web"
        exit 1
      fi
      # Build for linux/amd64 platform (required for AWS ECS Fargate)
      docker build --platform linux/amd64 -t ${aws_ecr_repository.frontend.repository_url}:latest .
      docker tag ${aws_ecr_repository.frontend.repository_url}:latest ${aws_ecr_repository.frontend.repository_url}:$TIMESTAMP
      echo "📤 Pushing Frontend image..."
      docker push ${aws_ecr_repository.frontend.repository_url}:latest
      docker push ${aws_ecr_repository.frontend.repository_url}:$TIMESTAMP
      
      # Build and push Celery Worker image (reuse API image)
      echo "📦 Building Celery Worker image..."
      cd $PROJECT_ROOT/api
      # Build for linux/amd64 platform (required for AWS ECS Fargate)
      docker build --platform linux/amd64 -t ${aws_ecr_repository.celery_worker.repository_url}:latest .
      docker tag ${aws_ecr_repository.celery_worker.repository_url}:latest ${aws_ecr_repository.celery_worker.repository_url}:$TIMESTAMP
      echo "📤 Pushing Celery Worker image..."
      docker push ${aws_ecr_repository.celery_worker.repository_url}:latest
      docker push ${aws_ecr_repository.celery_worker.repository_url}:$TIMESTAMP
      
      echo "✅ All images built and pushed successfully!"
    EOT
  }

  depends_on = [
    aws_ecr_repository.api,
    aws_ecr_repository.frontend,
    aws_ecr_repository.celery_worker
  ]
}

