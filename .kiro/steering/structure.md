# Project Structure & Organization

## Directory Layout

```
nexus-ai/
├── agents/                           # Agent implementations
│   ├── system_agents/               # Core platform agents
│   │   └── agent_build_workflow/    # Specialized workflow agents
│   │       ├── orchestrator_agent.py
│   │       ├── requirements_analyzer_agent.py
│   │       ├── system_architect_agent.py
│   │       ├── agent_designer_agent.py
│   │       ├── prompt_engineer_agent.py
│   │       ├── tool_developer_agent.py
│   │       ├── agent_code_developer_agent.py
│   │       └── agent_developer_manager_agent.py
│   ├── template_agents/             # Reusable agent templates
│   └── generated_agents/            # Dynamically created agents
├── config/                          # Configuration files
│   └── default_config.yaml         # Main system configuration
├── prompts/                         # YAML prompt templates (hierarchical)
│   ├── system_agents_prompts/       # System agent prompts
│   │   └── agent_build_workflow/    # Workflow-specific prompts
│   ├── template_prompts/            # Template prompts
│   └── generated_agents_prompts/    # Generated prompts
├── tools/                           # Tool implementations
│   ├── system_tools/                # Core platform tools
│   │   └── tool_template_provider.py # Tool discovery and management
│   ├── template_tools/              # Tool templates
│   └── generated_tools/             # Generated tools
├── utils/                           # Core utility modules
│   ├── agent_factory.py             # Dynamic agent creation system
│   ├── prompts_manager.py           # Prompt template management
│   ├── mcp_manager.py               # MCP server management
│   ├── config_loader.py             # Configuration management
│   ├── strands_agent_logging_hook.py # Agent logging utilities
│   ├── multimodal_processing/       # Multimodal content processing
│   │   ├── content_parsing_engine.py # Unified content processing
│   │   ├── file_upload_manager.py   # File upload handling
│   │   ├── image_processor.py       # Image processing
│   │   ├── document_processor.py    # Document processing
│   │   ├── s3_storage_service.py    # S3 storage management
│   │   ├── multimodal_model_service.py # AI model integration
│   │   └── markdown_generator.py    # Markdown output generation
│   └── structured_output_model/     # Structured output models
├── mcp/                             # MCP server configurations
├── tests/                           # Test files and examples
│   ├── multi-agent_base_on_graph.py # Graph-based multi-agent tests
│   ├── multi-agent_base_on_swarm.py # Swarm-based multi-agent tests
│   ├── strands_mcp_*.py             # MCP integration tests
│   └── test_image_processor.py      # Multimodal processing tests
├── docs/                            # Documentation
│   └── file_validation_implementation.md # Implementation guides
├── models/                          # Data models and schemas
├── projects/                        # Generated agent projects
│   └── aws_pricing_agent/          # AWS pricing agent project
└── logs/                           # Application logs
```

## Code Organization Patterns

### Agent Factory System
- **Dynamic Creation**: Agents created from YAML prompt templates via `agent_factory.py`
- **Template-Driven**: Each agent defined by structured YAML configuration
- **Multi-Level Paths**: Support for hierarchical agent organization (e.g., `system_agents_prompts/agent_build_workflow/orchestrator`)
- **Version Management**: Multiple versions per agent with automatic latest selection

### Agent Structure
- Each agent has a corresponding YAML prompt file with metadata
- System agents use specialized workflow roles in `agent_build_workflow/`
- Agents created via `create_agent_from_prompt_template()` function
- Automatic tool dependency resolution and model selection

### Configuration Management
- **Hierarchical YAML**: Multi-level configuration structure
- **Environment Support**: Development, production, testing environments
- **Model Configuration**: Multiple Bedrock models (Haiku, Sonnet, Opus)
- **Tool Dependencies**: Automatic tool loading based on agent metadata

### Prompt Template System
- **YAML-Based**: Structured prompt definitions with metadata
- **Versioning**: Multiple versions per agent with semantic versioning
- **Metadata**: Tool dependencies, model support, performance metrics
- **Examples**: Built-in conversation examples for training
- **Constraints**: Behavioral constraints and guidelines

### Tool Integration
- **Dynamic Loading**: Tools loaded based on agent requirements
- **Built-in Tools**: Strands framework tools (calculator, shell, file operations)
- **System Tools**: Custom tools in `tools/system_tools/`
- **MCP Integration**: External tools via Model Context Protocol
- **Tool Discovery**: Automatic tool discovery via `tool_template_provider.py`

### Multi-Agent Orchestration
- **Graph Workflows**: Dependency-based agent execution graphs
- **Swarm Intelligence**: Collaborative problem-solving patterns
- **Workflow Management**: Specialized workflow agents for complex tasks

### Naming Conventions
- Snake_case for Python files and directories
- Hierarchical paths for agent organization (e.g., `agent_build_workflow/orchestrator`)
- Descriptive names indicating purpose and role
- YAML files mirror agent structure with metadata

## Key Files

### Core System
- `utils/agent_factory.py`: Dynamic agent creation and management
- `utils/prompts_manager.py`: YAML prompt template system
- `utils/mcp_manager.py`: MCP server configuration and client management
- `utils/config_loader.py`: Centralized configuration management

### Multimodal Processing
- `utils/multimodal_processing/content_parsing_engine.py`: Main content processing interface
- `utils/multimodal_processing/file_upload_manager.py`: File upload and validation
- `utils/multimodal_processing/s3_storage_service.py`: AWS S3 integration
- `utils/multimodal_processing/multimodal_model_service.py`: AI model services

### Agent Workflow
- `agents/system_agents/agent_build_workflow/orchestrator_agent.py`: Main workflow orchestration
- `prompts/system_agents_prompts/agent_build_workflow/`: Workflow agent prompt templates

### Configuration
- `config/default_config.yaml`: System-wide configuration with model settings
- `mcp/*.json`: MCP server definitions with auto-approval settings

### Testing
- `tests/multi-agent_*.py`: Multi-agent collaboration examples
- `tests/strands_mcp_*.py`: MCP integration testing