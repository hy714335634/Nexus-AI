# Technology Stack & Build System

## Core Technologies

- **Python 3.13+**: Primary development language
- **AWS Bedrock**: AI model hosting and inference with multiple model support (Claude 3.5 Haiku, Claude 3.7 Sonnet, Claude Opus 4)
- **AWS AgentCore**: Agent runtime and deployment platform
- **Strands Framework**: Agent orchestration and tool integration with multi-agent support
- **MCP (Model Context Protocol)**: Standardized tool and service integration

## Key Dependencies

- `strands-agents`: Core agent framework with multi-agent capabilities (Graph, Swarm)
- `strands-agents-tools`: Built-in tool collection
- `bedrock-agentcore`: AWS AgentCore integration
- `boto3`: AWS SDK for Python
- `PyYAML`: Configuration management
- `uv`: Python package management

## Architecture Components

### Agent Factory System
- **Agent Factory** (`utils/agent_factory.py`): Dynamic agent creation from prompt templates
- **Prompt Manager** (`utils/prompts_manager.py`): YAML-based prompt template management with versioning
- **MCP Manager** (`utils/mcp_manager.py`): MCP server configuration and client management
- **Config Loader** (`utils/config_loader.py`): Centralized configuration management

### Agent Types
- **System Agents**: Core platform agents with specialized workflow roles
  - Orchestrator Agent: Workflow coordination and management
  - Requirements Analyzer: Business requirement analysis
  - System Architect: Technical architecture design
  - Agent Designer: Agent specification design
  - Prompt Engineer: Prompt template optimization
  - Tool Developer: Custom tool development
  - Agent Code Developer: Agent implementation
  - Agent Developer Manager: Development lifecycle management
- **Template Agents**: Reusable agent templates for different patterns
- **Generated Agents**: Dynamically created agents from templates

### Multi-Agent Orchestration
- **Graph-based Workflows**: Dependency-driven agent execution
- **Swarm Intelligence**: Collaborative agent problem-solving
- **Agent Build Workflow**: Automated agent development pipeline

## Common Commands

```bash
# Environment setup
uv sync                    # Install dependencies
source .venv/bin/activate  # Activate virtual environment

# Development
python -m pytest tests/   # Run tests
python agents/system_agents/agent_build_workflow/orchestrator_agent.py  # Test workflow

# Agent Factory Usage
python -c "from utils.agent_factory import create_agent_from_prompt_template; agent = create_agent_from_prompt_template('requirements_analyzer')"

# Multi-Agent Testing
python tests/multi-agent_base_on_graph.py    # Test graph-based multi-agent
python tests/multi-agent_base_on_swarm.py    # Test swarm-based multi-agent

# MCP Server Management
uvx awslabs.aws-api-mcp-server@latest  # Run AWS API MCP server
uvx strands-agents-mcp-server          # Run Strands MCP server
```

## Configuration

- `config/default_config.yaml`: Main system configuration with model settings
- `prompts/`: YAML-based prompt templates with hierarchical structure
  - `system_agents_prompts/`: System agent prompts
  - `template_prompts/`: Template agent prompts  
  - `generated_agents_prompts/`: Generated agent prompts
- `mcp/*.json`: MCP server configurations with auto-approval settings
- `utils/`: Core utility modules for agent management
- Environment variables for AWS credentials and regions

## Key Features

- **Dynamic Agent Creation**: Create agents from YAML prompt templates
- **Multi-Model Support**: Automatic model selection based on agent requirements
- **Tool Integration**: Dynamic tool loading and dependency management
- **Configuration Management**: Hierarchical YAML configuration system
- **MCP Integration**: Standardized protocol for external tool integration
- **Multi-Agent Workflows**: Graph and swarm-based agent collaboration