# Technology Stack & Build System

## Core Technologies

- **Python 3.13+**: Primary development language
- **AWS Bedrock**: AI model hosting and inference
- **AWS AgentCore**: Agent runtime and deployment platform
- **Strands Framework**: Agent orchestration and tool integration
- **MCP (Model Context Protocol)**: Standardized tool and service integration

## Key Dependencies

- `strands-agents`: Core agent framework
- `strands-agents-tools`: Built-in tool collection
- `bedrock-agentcore`: AWS AgentCore integration
- `boto3`: AWS SDK for Python
- `PyYAML`: Configuration management
- `uv`: Python package management

## Project Structure

- **System Agents**: Core platform agents (orchestrator, code generator, requirements analyzer, deployment manager)
- **Template Agents**: Reusable agent templates for different patterns
- **Generated Agents**: Dynamically created agents from templates
- **Tools**: Local and MCP-integrated tools
- **Prompts**: YAML-based prompt templates with versioning

## Common Commands

```bash
# Environment setup
uv sync                    # Install dependencies
source .venv/bin/activate  # Activate virtual environment

# Development
python -m pytest tests/   # Run tests
python agents/system_agents/orchestrator_agent.py  # Test system agents

# MCP Server Management
uvx awslabs.aws-api-mcp-server@latest  # Run AWS API MCP server
uvx strands-agents-mcp-server          # Run Strands MCP server
```

## Configuration

- `config/default_config.yaml`: Main system configuration
- `config/agent_templates_config.yaml`: Agent template definitions
- `mcp/*.json`: MCP server configurations
- Environment variables for AWS credentials and regions