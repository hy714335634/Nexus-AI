# Project Structure & Organization

## Directory Layout

```
nexus-ai/
├── agents/                    # Agent implementations
│   ├── system_agents/         # Core platform agents
│   ├── template_agents/       # Reusable agent templates
│   └── generated_agents/      # Dynamically created agents
├── config/                    # Configuration files
├── prompts/                   # YAML prompt templates
│   ├── system_agents_prompts/ # System agent prompts
│   ├── template_prompts/      # Template prompts
│   └── generated_agents_prompts/ # Generated prompts
├── tools/                     # Tool implementations
│   ├── system_tools/          # Core platform tools
│   ├── tempalte_tools/        # Tool templates
│   └── generated_tools/       # Generated tools
├── mcp/                       # MCP server configurations
├── utils/                     # Shared utilities
├── tests/                     # Test files and examples
└── templates/                 # Project templates
```

## Code Organization Patterns

### Agent Structure
- Each agent has a corresponding prompt file in `prompts/`
- System agents use the Strands framework with tools integration
- Template agents demonstrate different integration patterns (local tools, MCP SSE, stdio, etc.)

### Configuration Management
- YAML-based configuration with hierarchical structure
- Separate configs for agents, templates, and MCP servers
- Environment-specific overrides supported

### Tool Integration
- Local tools in `tools/system_tools/`
- MCP integration via JSON configuration files
- Template tools for code generation

### Naming Conventions
- Snake_case for Python files and directories
- Descriptive names indicating purpose (e.g., `orchestrator_agent.py`, `requirements_analyzer_agent.py`)
- Template files include integration type in name (e.g., `single_agent_with_mcp_stdio.py`)

## Key Files
- `config/default_config.yaml`: Main system configuration
- `agents/system_agents/orchestrator_agent.py`: Main orchestration logic
- `utils/prompts_manager.py`: Prompt template management
- `mcp/system_mcp_server.json`: System MCP server definitions