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
    
    # Rebuild when Dockerfiles or dependencies change
    api_dockerfile_hash    = filemd5("${path.module}/../api/Dockerfile")
    frontend_dockerfile_hash = filemd5("${path.module}/../web/Dockerfile")
    api_requirements_hash   = filemd5("${path.module}/../api/requirements.txt")
    frontend_package_hash   = filemd5("${path.module}/../web/package.json")
    
    # Force rebuild trigger (increment this to force rebuild)
    rebuild_trigger = "2025-12-03-efs-permissions-fix"
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      echo "🚀 Building and pushing Docker images to ECR..."
      
      # Resolve absolute paths
      INFRA_DIR="$(cd "${path.module}" && pwd)"
      PROJECT_ROOT="$(cd "${path.module}/.." && pwd)"
      AWS_REGION="${var.aws_region}"
      AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
      
      echo "📁 Project root: $PROJECT_ROOT"
      echo "📁 Infrastructure dir: $INFRA_DIR"
      
      # Login to ECR
      echo "🔐 Logging in to ECR..."
      aws ecr get-login-password --region ${var.aws_region} | \
        docker login --username AWS --password-stdin ${aws_ecr_repository.api.repository_url}
      
      # Build and push API image
      echo "📦 Building API image..."
      cd "$PROJECT_ROOT"
      if [ ! -f "api/Dockerfile" ]; then
        echo "❌ Error: Dockerfile not found in $PROJECT_ROOT/api"
        exit 1
      fi
      # Build for linux/amd64 platform (required for AWS ECS Fargate)
      # Build from project root with project root as context (not api/)
      # This allows Dockerfile to access parent directories (nexus_utils, agents, tools, etc.)
      docker build --platform linux/amd64 -f api/Dockerfile -t ${aws_ecr_repository.api.repository_url}:latest .
      TIMESTAMP=$(date +%Y%m%d-%H%M%S)
      docker tag ${aws_ecr_repository.api.repository_url}:latest ${aws_ecr_repository.api.repository_url}:$TIMESTAMP
      echo "📤 Pushing API image..."
      # Retry logic for network issues
      MAX_PUSH_RETRIES=3
      PUSH_RETRY=0
      while [ $PUSH_RETRY -lt $MAX_PUSH_RETRIES ]; do
        if docker push ${aws_ecr_repository.api.repository_url}:latest; then
          echo "✅ API image pushed successfully"
          break
        else
          PUSH_RETRY=$((PUSH_RETRY + 1))
          if [ $PUSH_RETRY -lt $MAX_PUSH_RETRIES ]; then
            echo "⚠️  Push failed, retrying ($PUSH_RETRY/$MAX_PUSH_RETRIES) in 10 seconds..."
            sleep 10
          else
            echo "❌ Failed to push API image after $MAX_PUSH_RETRIES attempts"
            exit 1
          fi
        fi
      done
      
      PUSH_RETRY=0
      while [ $PUSH_RETRY -lt $MAX_PUSH_RETRIES ]; do
        if docker push ${aws_ecr_repository.api.repository_url}:$TIMESTAMP; then
          echo "✅ API image (tagged) pushed successfully"
          break
        else
          PUSH_RETRY=$((PUSH_RETRY + 1))
          if [ $PUSH_RETRY -lt $MAX_PUSH_RETRIES ]; then
            echo "⚠️  Push failed, retrying ($PUSH_RETRY/$MAX_PUSH_RETRIES) in 10 seconds..."
            sleep 10
          else
            echo "⚠️  Failed to push tagged API image, but latest tag succeeded"
          fi
        fi
      done
      
      # Build and push Frontend image
      echo "📦 Building Frontend image..."
      cd "$PROJECT_ROOT"
      if [ ! -d "web" ]; then
        echo "❌ Error: web directory not found in $PROJECT_ROOT"
        exit 1
      fi
      if [ ! -f "web/Dockerfile" ]; then
        echo "❌ Error: Dockerfile not found in $PROJECT_ROOT/web"
        exit 1
      fi
      # Build for linux/amd64 platform (required for AWS ECS Fargate)
      # Build from project root with web/ as context
      docker build --platform linux/amd64 -f web/Dockerfile -t ${aws_ecr_repository.frontend.repository_url}:latest web/
      docker tag ${aws_ecr_repository.frontend.repository_url}:latest ${aws_ecr_repository.frontend.repository_url}:$TIMESTAMP
      echo "📤 Pushing Frontend image..."
      # Retry logic for network issues
      MAX_PUSH_RETRIES=3
      PUSH_RETRY=0
      while [ $PUSH_RETRY -lt $MAX_PUSH_RETRIES ]; do
        if docker push ${aws_ecr_repository.frontend.repository_url}:latest; then
          echo "✅ Frontend image pushed successfully"
          break
        else
          PUSH_RETRY=$((PUSH_RETRY + 1))
          if [ $PUSH_RETRY -lt $MAX_PUSH_RETRIES ]; then
            echo "⚠️  Push failed, retrying ($PUSH_RETRY/$MAX_PUSH_RETRIES) in 10 seconds..."
            sleep 10
          else
            echo "❌ Failed to push Frontend image after $MAX_PUSH_RETRIES attempts"
            exit 1
          fi
        fi
      done
      
      PUSH_RETRY=0
      while [ $PUSH_RETRY -lt $MAX_PUSH_RETRIES ]; do
        if docker push ${aws_ecr_repository.frontend.repository_url}:$TIMESTAMP; then
          echo "✅ Frontend image (tagged) pushed successfully"
          break
        else
          PUSH_RETRY=$((PUSH_RETRY + 1))
          if [ $PUSH_RETRY -lt $MAX_PUSH_RETRIES ]; then
            echo "⚠️  Push failed, retrying ($PUSH_RETRY/$MAX_PUSH_RETRIES) in 10 seconds..."
            sleep 10
          else
            echo "⚠️  Failed to push tagged Frontend image, but latest tag succeeded"
          fi
        fi
      done
      
      echo "✅ All images built and pushed successfully!"
    EOT
  }

  depends_on = [
    aws_ecr_repository.api,
    aws_ecr_repository.frontend
  ]
}

