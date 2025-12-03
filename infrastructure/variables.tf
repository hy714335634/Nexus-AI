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

# ALB Configuration
variable "alb_internal" {
  description = "Whether the ALB should be internal (true) or internet-facing (false). Internal ALB is accessible only from within the VPC."
  type        = bool
  default     = false # Changed to false for public access (can be restricted via security group)
}

variable "alb_allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the ALB (frontend). Defaults to VPC CIDR for internal access. Set to ['0.0.0.0/0'] for public access."
  type        = list(string)
  default     = null # Will default to VPC CIDR if not specified
}

# ECS Configuration
variable "api_cpu" {
  description = "CPU units for API service (1024 = 1 vCPU). For workflows with async threads, recommend at least 4096 (4 vCPU)"
  type        = number
  default     = 4096
}

variable "api_memory" {
  description = "Memory for API service in MB. For workflows with async threads, recommend at least 8192 MB"
  type        = number
  default     = 8192
}

variable "max_workflow_workers" {
  description = "Maximum number of concurrent workflow workers (ThreadPoolExecutor max_workers)"
  type        = number
  default     = 5
}

# Jaeger Configuration
variable "enable_jaeger" {
  description = "Enable Jaeger tracing as standalone service (for OpenTelemetry)"
  type        = bool
  default     = false
}

variable "jaeger_cpu" {
  description = "CPU units for Jaeger service (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "jaeger_memory" {
  description = "Memory for Jaeger service in MB"
  type        = number
  default     = 2048
}

variable "jaeger_desired_count" {
  description = "Desired number of Jaeger service instances"
  type        = number
  default     = 1
}

variable "api_desired_count" {
  description = "Desired number of API service instances"
  type        = number
  default     = 2
}

variable "frontend_cpu" {
  description = "CPU units for Frontend service (1024 = 1 vCPU). For Fargate: 1024 CPU allows 2048-3072 MB, 2048 CPU requires 4096-16384 MB"
  type        = number
  default     = 2048
}

variable "frontend_memory" {
  description = "Memory for Frontend service in MB. For Fargate, must be valid combination with CPU (e.g., 1024 CPU: 2048-3072 MB, 2048 CPU: 4096-16384 MB)"
  type        = number
  default     = 4096
}

variable "frontend_desired_count" {
  description = "Desired number of Frontend service instances"
  type        = number
  default     = 1
}

# Docker Build Configuration
variable "skip_docker_build" {
  description = "Skip automatic Docker image build and push during terraform apply"
  type        = bool
  default     = false
}

# ============================================
# Bastion Host Configuration
# ============================================
variable "enable_bastion" {
  description = "Enable creation of Bastion Host (EC2 instance for accessing applications)"
  type        = bool
  default     = true
}

variable "bastion_key_name" {
  description = "Name of the AWS Key Pair to use for Bastion Host SSH access. Must already exist in AWS."
  type        = string
  default     = "Og_Normal"

  validation {
    condition     = var.enable_bastion ? var.bastion_key_name != "" : true
    error_message = "bastion_key_name must be provided when enable_bastion is true."
  }
}

# ============================================
# EC2 API Service Configuration
# ============================================
variable "api_deploy_on_ec2" {
  description = "Deploy API service on EC2 instead of ECS Fargate. Required when API needs to build Docker images."
  type        = bool
  default     = false
}

variable "ec2_api_instance_type" {
  description = "EC2 instance type for API service"
  type        = string
  default     = "t3.xlarge"
}

variable "ec2_api_key_name" {
  description = "Name of the AWS Key Pair to use for EC2 API instances SSH access. Leave empty to disable SSH access."
  type        = string
  default     = "Og_Normal"
}

variable "ec2_api_volume_size" {
  description = "Root volume size in GB for EC2 API instances"
  type        = number
  default     = 50
}

variable "ec2_api_min_size" {
  description = "Minimum number of EC2 API instances in Auto Scaling Group"
  type        = number
  default     = 1
}

variable "ec2_api_max_size" {
  description = "Maximum number of EC2 API instances in Auto Scaling Group"
  type        = number
  default     = 4
}

variable "ec2_api_desired_capacity" {
  description = "Desired number of EC2 API instances in Auto Scaling Group"
  type        = number
  default     = 2
}

variable "github_repo_url" {
  description = "GitHub repository URL for cloning project code"
  type        = string
  default     = "https://github.com/hy714335634/Nexus-AI.git"
}

variable "github_branch" {
  description = "GitHub branch to clone (default: main)"
  type        = string
  default     = "main"
}
