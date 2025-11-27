variable "aws_region" {
  description = "AWS deployment region"
  type        = string
  default     = "us-east-1"
}

variable "aws_access_key" {
  description = "AWS Access Key (leave empty to use default profile)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "aws_secret_key" {
  description = "AWS Secret Key (leave empty to use default profile)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
  default     = "nexus-ai"
}

variable "environment" {
  description = "Environment (dev/staging/prod)"
  type        = string
  default     = "dev"
}

variable "enable_sqs" {
  description = "Enable SQS queue creation"
  type        = bool
  default     = true
}

variable "enable_dynamodb" {
  description = "Enable DynamoDB tables creation"
  type        = bool
  default     = true
}


variable "dynamodb_read_capacity" {
  description = "DynamoDB read capacity units"
  type        = number
  default     = 10
}

variable "dynamodb_write_capacity" {
  description = "DynamoDB write capacity units"
  type        = number
  default     = 10
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}

# VPC Configuration
variable "create_vpc" {
  description = "Whether to create a new VPC (true) or use existing VPC (false)"
  type        = bool
  default     = true
}

variable "vpc_id" {
  description = "Existing VPC ID (required if create_vpc = false)"
  type        = string
  default     = ""
}

variable "vpc_cidr" {
  description = "CIDR block for new VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_ids" {
  description = "Existing subnet IDs (required if create_vpc = false)"
  type        = list(string)
  default     = []
}

variable "availability_zones" {
  description = "Availability zones for subnets (defaults to first 2 AZs in region)"
  type        = list(string)
  default     = []
}

# ECS Configuration
variable "api_cpu" {
  description = "CPU units for API service (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "api_memory" {
  description = "Memory for API service in MB"
  type        = number
  default     = 2048
}

variable "api_desired_count" {
  description = "Desired number of API service instances"
  type        = number
  default     = 2
}

variable "frontend_cpu" {
  description = "CPU units for Frontend service (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "frontend_memory" {
  description = "Memory for Frontend service in MB"
  type        = number
  default     = 1024
}

variable "frontend_desired_count" {
  description = "Desired number of Frontend service instances"
  type        = number
  default     = 2
}

variable "celery_worker_cpu" {
  description = "CPU units for Celery worker service (1024 = 1 vCPU)"
  type        = number
  default     = 2048
}

variable "celery_worker_memory" {
  description = "Memory for Celery worker service in MB"
  type        = number
  default     = 4096
}

variable "celery_worker_desired_count" {
  description = "Desired number of Celery worker instances per queue"
  type        = number
  default     = 2
}

variable "redis_cpu" {
  description = "CPU units for Redis service (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "redis_memory" {
  description = "Memory for Redis service in MB"
  type        = number
  default     = 1024
}

# Docker Build Configuration
variable "skip_docker_build" {
  description = "Skip automatic Docker image build and push during terraform apply"
  type        = bool
  default     = false
}
