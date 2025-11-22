# Nexus-AI Platform API - Usage Examples

This document provides practical examples for using the Nexus-AI Platform API.

## Table of Contents

- [Getting Started](#getting-started)
- [Project Management](#project-management)
- [Agent Management](#agent-management)
- [Session Management](#session-management)
- [Statistics and Monitoring](#statistics-and-monitoring)
- [Error Handling](#error-handling)

## Getting Started

### Base URL

```
http://localhost:8000/api/v1
```

### Response Format

All successful responses follow this format:

```json
{
  "success": true,
  "data": { ... },
  "timestamp": "2024-01-01T10:00:00.000000Z"
}
```

Error responses:

```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Project not found",
    "details": {},
    "suggestion": "Please confirm the resource ID is correct",
    "trace_id": "uuid"
  },
  "timestamp": "2024-01-01T10:00:00.000000Z",
  "request_id": "uuid"
}
```

## Project Management

### 1. Create a New Project

**Endpoint:** `POST /api/v1/projects`

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "requirement": "Create a customer service agent that can handle product inquiries and order tracking",
    "project_name": "CustomerServiceBot",
    "user_id": "user_123"
  }'
```

**Response:**

```json
{
  "success": true,
  "data": {
    "project_id": "proj_abc123",
    "project_name": "CustomerServiceBot",
    "requirement": "Create a customer service agent...",
    "status": "building",
    "progress": 0.0,
    "created_at": "2024-01-01T10:00:00.000000Z",
    "updated_at": "2024-01-01T10:00:00.000000Z"
  },
  "timestamp": "2024-01-01T10:00:00.000000Z"
}
```

### 2. Monitor Project Progress

**Endpoint:** `GET /api/v1/projects/{project_id}`

**Request:**

```bash
curl http://localhost:8000/api/v1/projects/proj_abc123
```

**Response:**

```json
{
  "success": true,
  "data": {
    "project_id": "proj_abc123",
    "project_name": "CustomerServiceBot",
    "status": "building",
    "progress": 45.5,
    "current_stage": "agent_developer_manager",
    "stages_snapshot": {
      "orchestrator": {
        "status": "completed",
        "progress": 100.0
      },
      "requirements_analysis": {
        "status": "completed",
        "progress": 100.0
      },
      "agent_developer_manager": {
        "status": "running",
        "progress": 50.0,
        "sub_stages": {
          "tool_developer": {
            "status": "completed",
            "artifacts": ["tools/product_search.py", "tools/order_tracker.py"]
          },
          "prompt_engineer": {
            "status": "running"
          }
        }
      }
    }
  },
  "timestamp": "2024-01-01T10:30:00.000000Z"
}
```

### 3. Get Stage Details

**Endpoint:** `GET /api/v1/projects/{project_id}/stages/{stage_name}`

**Request:**

```bash
curl http://localhost:8000/api/v1/projects/proj_abc123/stages/agent_developer_manager
```

**Response:**

```json
{
  "success": true,
  "data": {
    "stage_name": "agent_developer_manager",
    "stage_number": 5,
    "display_name": "Agent Developer Manager",
    "status": "running",
    "started_at": "2024-01-01T10:20:00.000000Z",
    "progress": 50.0,
    "sub_stages": {
      "tool_developer": {
        "status": "completed",
        "started_at": "2024-01-01T10:20:00.000000Z",
        "completed_at": "2024-01-01T10:25:00.000000Z",
        "artifacts": ["tools/product_search.py", "tools/order_tracker.py"]
      },
      "prompt_engineer": {
        "status": "running",
        "started_at": "2024-01-01T10:25:00.000000Z"
      },
      "agent_code_developer": {
        "status": "pending"
      }
    },
    "logs": [
      {
        "timestamp": "2024-01-01T10:20:05.000000Z",
        "level": "INFO",
        "message": "Starting tool development..."
      }
    ]
  },
  "timestamp": "2024-01-01T10:30:00.000000Z"
}
```

### 4. List All Projects

**Endpoint:** `GET /api/v1/projects`

**Request:**

```bash
# List all projects
curl http://localhost:8000/api/v1/projects

# Filter by status
curl http://localhost:8000/api/v1/projects?status=completed

# Filter by user
curl http://localhost:8000/api/v1/projects?user_id=user_123

# With pagination
curl http://localhost:8000/api/v1/projects?limit=10&last_key=proj_xyz
```

### 5. Control Project Execution

**Endpoint:** `PUT /api/v1/projects/{project_id}/control`

**Pause a Project:**

```bash
curl -X PUT http://localhost:8000/api/v1/projects/proj_abc123/control \
  -H "Content-Type: application/json" \
  -d '{"action": "pause"}'
```

**Resume a Project:**

```bash
curl -X PUT http://localhost:8000/api/v1/projects/proj_abc123/control \
  -H "Content-Type: application/json" \
  -d '{"action": "resume"}'
```

**Stop a Project:**

```bash
curl -X PUT http://localhost:8000/api/v1/projects/proj_abc123/control \
  -H "Content-Type: application/json" \
  -d '{"action": "stop"}'
```

### 6. Delete a Project

**Endpoint:** `DELETE /api/v1/projects/{project_id}`

**Request:**

```bash
curl -X DELETE http://localhost:8000/api/v1/projects/proj_abc123
```

**Note:** This will cascade delete all associated agents, invocations, sessions, and messages.

## Agent Management

### 1. List All Agents

**Endpoint:** `GET /api/v1/agents`

**Request:**

```bash
# List all agents
curl http://localhost:8000/api/v1/agents

# Filter by project
curl http://localhost:8000/api/v1/agents?project_id=proj_abc123

# Filter by status
curl http://localhost:8000/api/v1/agents?status=running

# Filter by capabilities
curl http://localhost:8000/api/v1/agents?capabilities=text_generation,search
```

**Response:**

```json
{
  "success": true,
  "data": {
    "agents": [
      {
        "agent_id": "proj_abc123:customer_service_agent",
        "agent_name": "customer_service_agent",
        "project_id": "proj_abc123",
        "status": "running",
        "category": "customer_service",
        "capabilities": ["text_generation", "tool:product_search", "tool:order_tracker"],
        "runtime_stats": {
          "total_invocations": 150,
          "successful_invocations": 145,
          "failed_invocations": 5,
          "avg_duration_ms": 1500.0,
          "last_invoked_at": "2024-01-01T12:00:00.000000Z"
        },
        "created_at": "2024-01-01T10:45:00.000000Z"
      }
    ],
    "total": 1,
    "last_key": null
  },
  "timestamp": "2024-01-01T12:00:00.000000Z"
}
```

### 2. Get Agent Details

**Endpoint:** `GET /api/v1/agents/{agent_id}`

**Request:**

```bash
curl http://localhost:8000/api/v1/agents/proj_abc123:customer_service_agent
```

**Response:**

```json
{
  "success": true,
  "data": {
    "agent_id": "proj_abc123:customer_service_agent",
    "agent_name": "customer_service_agent",
    "project_id": "proj_abc123",
    "status": "running",
    "description": "Customer service agent for handling inquiries",
    "category": "customer_service",
    "capabilities": ["text_generation", "tool:product_search", "tool:order_tracker"],
    "agentcore_config": {
      "agent_arn": "arn:aws:bedrock:us-east-1:123456789012:agent/AGENT123",
      "agent_alias_id": "ALIAS123",
      "agent_alias_arn": "arn:aws:bedrock:us-east-1:123456789012:agent-alias/AGENT123/ALIAS123"
    },
    "runtime_stats": {
      "total_invocations": 150,
      "successful_invocations": 145,
      "failed_invocations": 5,
      "avg_duration_ms": 1500.0,
      "last_invoked_at": "2024-01-01T12:00:00.000000Z"
    },
    "region": "us-east-1",
    "created_at": "2024-01-01T10:45:00.000000Z",
    "updated_at": "2024-01-01T12:00:00.000000Z"
  },
  "timestamp": "2024-01-01T12:00:00.000000Z"
}
```

### 3. Invoke an Agent

**Endpoint:** `POST /api/v1/agents/{agent_id}/invoke`

**Single-turn Invocation:**

```bash
curl -X POST http://localhost:8000/api/v1/agents/proj_abc123:customer_service_agent/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "What is the status of order #12345?"
  }'
```

**Multi-turn Invocation (with session):**

```bash
curl -X POST http://localhost:8000/api/v1/agents/proj_abc123:customer_service_agent/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "Can you track another order for me?",
    "session_id": "session_xyz",
    "enable_trace": true
  }'
```

**Response:**

```json
{
  "success": true,
  "data": {
    "invocation_id": "inv_123",
    "session_id": "session_xyz",
    "output": "Order #12345 is currently in transit and expected to arrive on Jan 5th.",
    "duration_ms": 1450,
    "status": "success",
    "trace": {
      "steps": [...]
    },
    "created_at": "2024-01-01T12:00:00.000000Z"
  },
  "timestamp": "2024-01-01T12:00:00.000000Z"
}
```

### 4. Update Agent Status

**Endpoint:** `PUT /api/v1/agents/{agent_id}/status`

**Request:**

```bash
curl -X PUT http://localhost:8000/api/v1/agents/proj_abc123:customer_service_agent/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "offline",
    "error_message": "Maintenance in progress"
  }'
```

### 5. Delete an Agent

**Endpoint:** `DELETE /api/v1/agents/{agent_id}`

**Request:**

```bash
curl -X DELETE http://localhost:8000/api/v1/agents/proj_abc123:customer_service_agent
```

**Note:** This will cascade delete all associated invocations, sessions, and messages.

## Session Management

### 1. Create a Session

**Endpoint:** `POST /api/v1/agents/{agent_id}/sessions`

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/agents/proj_abc123:customer_service_agent/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "metadata": {
      "channel": "web",
      "locale": "en-US"
    }
  }'
```

**Response:**

```json
{
  "success": true,
  "data": {
    "session_id": "sess_xyz789",
    "agent_id": "proj_abc123:customer_service_agent",
    "user_id": "user_123",
    "status": "active",
    "metadata": {
      "channel": "web",
      "locale": "en-US"
    },
    "created_at": "2024-01-01T12:00:00.000000Z",
    "last_active_at": "2024-01-01T12:00:00.000000Z"
  },
  "timestamp": "2024-01-01T12:00:00.000000Z"
}
```

### 2. Send a Message

**Endpoint:** `POST /api/v1/sessions/{session_id}/messages`

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/sessions/sess_xyz789/messages \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello, I need help with my order",
    "role": "user",
    "metadata": {
      "intent": "order_inquiry"
    }
  }'
```

**Response:**

```json
{
  "success": true,
  "data": {
    "message_id": "msg_001",
    "session_id": "sess_xyz789",
    "role": "assistant",
    "content": "Hello! I'd be happy to help you with your order. Could you please provide your order number?",
    "metadata": {},
    "created_at": "2024-01-01T12:00:05.000000Z"
  },
  "timestamp": "2024-01-01T12:00:05.000000Z"
}
```

### 3. List Session Messages

**Endpoint:** `GET /api/v1/sessions/{session_id}/messages`

**Request:**

```bash
curl http://localhost:8000/api/v1/sessions/sess_xyz789/messages?limit=20
```

**Response:**

```json
{
  "success": true,
  "data": {
    "messages": [
      {
        "message_id": "msg_001",
        "role": "user",
        "content": "Hello, I need help with my order",
        "created_at": "2024-01-01T12:00:00.000000Z"
      },
      {
        "message_id": "msg_002",
        "role": "assistant",
        "content": "Hello! I'd be happy to help...",
        "created_at": "2024-01-01T12:00:05.000000Z"
      }
    ],
    "total": 2,
    "last_key": null
  },
  "timestamp": "2024-01-01T12:01:00.000000Z"
}
```

### 4. Get Session Details

**Endpoint:** `GET /api/v1/sessions/{session_id}`

**Request:**

```bash
curl http://localhost:8000/api/v1/sessions/sess_xyz789
```

### 5. List Agent Sessions

**Endpoint:** `GET /api/v1/agents/{agent_id}/sessions`

**Request:**

```bash
curl http://localhost:8000/api/v1/agents/proj_abc123:customer_service_agent/sessions?limit=10
```

### 6. Delete a Session

**Endpoint:** `DELETE /api/v1/sessions/{session_id}`

**Request:**

```bash
curl -X DELETE http://localhost:8000/api/v1/sessions/sess_xyz789
```

## Statistics and Monitoring

### 1. Get System Overview

**Endpoint:** `GET /api/v1/statistics/overview`

**Request:**

```bash
curl http://localhost:8000/api/v1/statistics/overview
```

**Response:**

```json
{
  "success": true,
  "data": {
    "total_agents": 25,
    "running_agents": 20,
    "building_agents": 3,
    "offline_agents": 2,
    "total_builds": 100,
    "success_rate": 92.5,
    "avg_build_time_minutes": 45.5,
    "today_calls": 5420
  },
  "timestamp": "2024-01-01T12:00:00.000000Z"
}
```

### 2. Get Build Statistics

**Endpoint:** `GET /api/v1/statistics/builds`

**Request:**

```bash
# Get all build statistics
curl http://localhost:8000/api/v1/statistics/builds

# Filter by date range
curl "http://localhost:8000/api/v1/statistics/builds?start_date=2024-01-01&end_date=2024-01-31"
```

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "date": "2024-01-01",
      "total_builds": 10,
      "successful_builds": 9,
      "failed_builds": 1,
      "avg_duration_minutes": 42.5,
      "builds_by_stage": {
        "deployer": 9,
        "agent_developer_manager": 1
      }
    }
  ],
  "timestamp": "2024-01-01T12:00:00.000000Z"
}
```

### 3. Get Invocation Statistics

**Endpoint:** `GET /api/v1/statistics/invocations`

**Request:**

```bash
curl "http://localhost:8000/api/v1/statistics/invocations?start_date=2024-01-01&end_date=2024-01-31"
```

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "date": "2024-01-01",
      "total_invocations": 5420,
      "successful_invocations": 5280,
      "failed_invocations": 140,
      "success_rate": 97.42,
      "avg_duration_ms": 1450.5
    }
  ],
  "timestamp": "2024-01-01T12:00:00.000000Z"
}
```

### 4. Get Trends

**Endpoint:** `GET /api/v1/statistics/trends`

**Request:**

```bash
# Get build trends
curl "http://localhost:8000/api/v1/statistics/trends?metric=builds&start_date=2024-01-01&end_date=2024-01-31"

# Get invocation trends
curl "http://localhost:8000/api/v1/statistics/trends?metric=invocations&start_date=2024-01-01&end_date=2024-01-31"

# Get success rate trends
curl "http://localhost:8000/api/v1/statistics/trends?metric=success_rate&start_date=2024-01-01&end_date=2024-01-31"
```

**Response:**

```json
{
  "success": true,
  "data": {
    "metric": "builds",
    "data_points": [
      {
        "date": "2024-01-01",
        "value": 10.0
      },
      {
        "date": "2024-01-02",
        "value": 15.0
      }
    ]
  },
  "timestamp": "2024-01-01T12:00:00.000000Z"
}
```

## Error Handling

### Common Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `RESOURCE_NOT_FOUND` | 404 | Resource not found |
| `RESOURCE_CONFLICT` | 409 | Resource already exists |
| `INVALID_STATE` | 400 | Invalid state transition |
| `PERMISSION_DENIED` | 403 | Permission denied |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |
| `STAGE_UPDATE_FAILED` | 500 | Stage update failed |
| `AGENT_INVOCATION_FAILED` | 500 | Agent invocation failed |
| `DATABASE_ERROR` | 500 | Database operation failed |
| `BUILD_ERROR` | 500 | Build process error |
| `INTERNAL_ERROR` | 500 | Internal server error |

### Error Response Example

```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Project with ID 'proj_abc123' not found",
    "details": {
      "project_id": "proj_abc123"
    },
    "suggestion": "Please confirm the resource ID is correct",
    "trace_id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "timestamp": "2024-01-01T12:00:00.000000Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Best Practices

1. **Always check the `success` field** before processing the response
2. **Use the `trace_id`** when reporting errors to support
3. **Follow the `suggestion`** field for quick resolution
4. **Implement exponential backoff** for retries on 5xx errors
5. **Validate input** before sending requests to avoid 400 errors
6. **Handle pagination** properly using `last_key` for large result sets

## Health Check

Check API health status:

```bash
curl http://localhost:8000/health
```

**Response:**

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2024-01-01T12:00:00.000000Z"
  }
}
```

## Interactive Documentation

Access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to:
- Browse all available endpoints
- View request/response schemas
- Try out API calls directly in the browser
- Download the OpenAPI specification

## Support

For additional support:
- Email: support@nexus-ai.com
- Documentation: See `/docs` and `/redoc` endpoints
- GitHub Issues: Report bugs and feature requests
