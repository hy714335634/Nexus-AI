# ============================================
# Cleanup Resources for terraform destroy
# ============================================
# This file ensures proper cleanup order and handles
# resources that might have dependencies preventing deletion

# Ensure ECS services are scaled down before deletion
# This helps avoid issues when destroying resources
resource "null_resource" "scale_down_services" {
  count = var.create_vpc ? 1 : 0

  triggers = {
    # This will run on destroy
    cluster_name = aws_ecs_cluster.nexus_ai[0].name
  }

  provisioner "local-exec" {
    when    = destroy
    command = <<-EOT
      echo "Scaling down ECS services before destruction..."
      
      CLUSTER_NAME="${self.triggers.cluster_name}"
      
      # Scale down all services to 0
      for service in $(aws ecs list-services --cluster $CLUSTER_NAME --query 'serviceArns[]' --output text 2>/dev/null || echo ""); do
        if [ -n "$service" ]; then
          echo "Scaling down service: $service"
          aws ecs update-service --cluster $CLUSTER_NAME --service $service --desired-count 0 --no-cli-pager 2>/dev/null || true
        fi
      done
      
      # Wait for tasks to stop
      echo "Waiting for tasks to stop..."
      sleep 30
    EOT
  }

  depends_on = [
    aws_ecs_service.api,
    aws_ecs_service.frontend,
    aws_ecs_service.celery_worker_builds,
    aws_ecs_service.celery_worker_status,
    aws_ecs_service.redis
  ]
}

