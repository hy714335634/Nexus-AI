# AgentProjects Table
resource "aws_dynamodb_table" "agent_projects" {
  count = var.enable_dynamodb ? 1 : 0

  name           = "AgentProjects"
  billing_mode   = "PROVISIONED"
  read_capacity  = var.dynamodb_read_capacity
  write_capacity = var.dynamodb_write_capacity
  hash_key       = "project_id"

  attribute {
    name = "project_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "UserIndex"
    hash_key        = "user_id"
    range_key       = "created_at"
    projection_type = "ALL"
    read_capacity   = 5
    write_capacity  = 5
  }

  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "status"
    range_key       = "created_at"
    projection_type = "ALL"
    read_capacity   = 5
    write_capacity  = 5
  }

  tags = local.common_tags
}

# AgentInstances Table
resource "aws_dynamodb_table" "agent_instances" {
  count = var.enable_dynamodb ? 1 : 0

  name           = "AgentInstances"
  billing_mode   = "PROVISIONED"
  read_capacity  = var.dynamodb_read_capacity
  write_capacity = var.dynamodb_write_capacity
  hash_key       = "agent_id"

  attribute {
    name = "agent_id"
    type = "S"
  }

  attribute {
    name = "project_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "category"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "ProjectIndex"
    hash_key        = "project_id"
    projection_type = "ALL"
    read_capacity   = 5
    write_capacity  = 5
  }

  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "status"
    range_key       = "created_at"
    projection_type = "ALL"
    read_capacity   = 5
    write_capacity  = 5
  }

  global_secondary_index {
    name            = "CategoryIndex"
    hash_key        = "category"
    range_key       = "created_at"
    projection_type = "ALL"
    read_capacity   = 5
    write_capacity  = 5
  }

  tags = local.common_tags
}

# AgentInvocations Table
resource "aws_dynamodb_table" "agent_invocations" {
  count = var.enable_dynamodb ? 1 : 0

  name           = "AgentInvocations"
  billing_mode   = "PROVISIONED"
  read_capacity  = var.dynamodb_read_capacity
  write_capacity = var.dynamodb_write_capacity
  hash_key       = "invocation_id"

  attribute {
    name = "invocation_id"
    type = "S"
  }

  attribute {
    name = "agent_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  global_secondary_index {
    name            = "AgentInvocationIndex"
    hash_key        = "agent_id"
    range_key       = "timestamp"
    projection_type = "ALL"
    read_capacity   = 5
    write_capacity  = 5
  }

  tags = local.common_tags
}

# AgentSessions Table
resource "aws_dynamodb_table" "agent_sessions" {
  count = var.enable_dynamodb ? 1 : 0

  name           = "AgentSessions"
  billing_mode   = "PROVISIONED"
  read_capacity  = var.dynamodb_read_capacity
  write_capacity = var.dynamodb_write_capacity
  hash_key       = "agent_id"
  range_key      = "session_id"

  attribute {
    name = "agent_id"
    type = "S"
  }

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "last_active_at"
    type = "S"
  }

  global_secondary_index {
    name            = "LastActiveIndex"
    hash_key        = "agent_id"
    range_key       = "last_active_at"
    projection_type = "ALL"
    read_capacity   = 5
    write_capacity  = 5
  }

  tags = local.common_tags
}

# AgentSessionMessages Table
resource "aws_dynamodb_table" "agent_session_messages" {
  count = var.enable_dynamodb ? 1 : 0

  name           = "AgentSessionMessages"
  billing_mode   = "PROVISIONED"
  read_capacity  = var.dynamodb_read_capacity
  write_capacity = var.dynamodb_write_capacity
  hash_key       = "session_id"
  range_key      = "created_at"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  tags = local.common_tags
}
