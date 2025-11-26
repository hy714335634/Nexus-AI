.PHONY: help docker-build docker-push deploy-lambda

help:
	@echo "NexusAI Lambda Deployment"
	@echo ""
	@echo "Available commands:"
	@echo "  make docker-build  - Build Lambda Docker image"
	@echo "  make docker-push   - Push image to ECR and update Lambda"
	@echo "  make deploy-lambda - Build and push (complete deployment)"

docker-build:
	@echo "Building Docker image..."
	@cd ../.. && docker build -f infrastructure/scripts/Dockerfile -t nexus-ai-lambda:latest .

docker-push:
	@echo "Pushing to ECR..."
	@cd .. && \
	AWS_REGION=$$(terraform output -raw region 2>/dev/null || echo "us-west-2"); \
	ECR_REPO=$$(terraform output -raw ecr_repository_url 2>/dev/null); \
	if [ -z "$$ECR_REPO" ]; then \
		echo "Error: ECR repository not found. Run 'terraform apply' first."; \
		exit 1; \
	fi; \
	echo "Logging into ECR..."; \
	aws ecr get-login-password --region $$AWS_REGION | docker login --username AWS --password-stdin $${ECR_REPO%%/*}; \
	echo "Tagging image..."; \
	docker tag nexus-ai-lambda:latest $$ECR_REPO:latest; \
	echo "Pushing image..."; \
	docker push $$ECR_REPO:latest; \
	echo "✅ Image pushed successfully!"; \
	LAMBDA_NAME=$$(terraform output -raw lambda_function_name 2>/dev/null); \
	if [ -n "$$LAMBDA_NAME" ]; then \
		echo "Updating Lambda function..."; \
		aws lambda update-function-code --function-name $$LAMBDA_NAME --image-uri $$ECR_REPO:latest --region $$AWS_REGION; \
		echo "✅ Lambda updated!"; \
	else \
		echo "⚠️  Lambda not yet created. Run 'terraform apply' after pushing image."; \
	fi

deploy-lambda: docker-build docker-push
	@echo "✅ Lambda deployment complete!"
