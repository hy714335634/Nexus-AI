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

variable "enable_lambda" {
  description = "Enable Lambda function creation"
  type        = bool
  default     = true
}

variable "enable_stepfunctions" {
  description = "Enable Step Functions state machine creation"
  type        = bool
  default     = false
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
