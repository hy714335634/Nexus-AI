# Project Structure & Organization

## Directory Layout

```
Nexus-AI/
├── agents/                           # Agent实现目录
│   ├── generated_agents/             # 生成的Agent
│   │   └── aws_pricing_agent/        # AWS定价Agent示例
│   ├── system_agents/                # 系统Agent
│   │   ├── agent_build_workflow/     # Agent构建工作流
│   │   │   ├── agent_build_workflow.py           # 主工作流编排器
│   │   │   ├── requirements_analyzer_agent.py    # 需求分析Agent
│   │   │   ├── system_architect_agent.py         # 系统架构Agent
│   │   │   ├── agent_designer_agent.py          # Agent设计Agent
│   │   │   ├── prompt_engineer_agent.py         # 提示词工程Agent
│   │   │   ├── tool_developer_agent.py          # 工具开发Agent
│   │   │   ├── agent_code_developer_agent.py   # Agent代码开发Agent
│   │   │   └── agent_developer_manager_agent.py # Agent开发管理Agent
│   │   ├── magician.py               # 魔法师Agent
│   │   └── multimodal_analysis/      # 多模态分析Agent
│   └── template_agents/             # Agent模板
├── tools/                            # 工具集合
│   ├── generated_tools/              # 生成的工具
│   │   └── aws_pricing_agent/        # AWS定价相关工具
│   ├── system_tools/                 # 系统工具
│   │   ├── agent_build_workflow/     # Agent构建工作流工具
│   │   │   ├── project_manager.py           # 项目管理工具
│   │   │   ├── agent_template_provider.py   # Agent模板提供器
│   │   │   ├── prompt_template_provider.py # 提示词模板提供器
│   │   │   ├── tool_template_provider.py   # 工具模板提供器
│   │   │   ├── mcp_config_manager.py        # MCP配置管理器
│   │   │   └── agent_developer_team_members.py # Agent开发团队成员
│   │   └── multimodal_content_parser.py     # 多模态内容解析工具
│   └── template_tools/               # 工具模板
├── prompts/                          # 提示词管理
│   ├── generated_agents_prompts/     # 生成的Agent提示词
│   ├── system_agents_prompts/        # 系统Agent提示词
│   │   └── agent_build_workflow/     # Agent构建工作流提示词
│   └── template_prompts/             # 提示词模板
├── utils/                            # 工具函数
│   ├── agent_factory.py              # Agent工厂
│   ├── config_loader.py              # 配置加载器
│   ├── prompts_manager.py            # 提示词管理器
│   ├── mcp_manager.py                # MCP管理器
│   ├── multimodal_processing/        # 多模态处理模块
│   │   ├── content_parsing_engine.py # 内容解析引擎
│   │   ├── multimodal_model_service.py # 多模态模型服务
│   │   ├── s3_storage_service.py    # S3存储服务
│   │   ├── file_upload_manager.py   # 文件上传管理器
│   │   ├── document_processor.py    # 文档处理器
│   │   ├── image_processor.py       # 图像处理器
│   │   ├── text_processor.py        # 文本处理器
│   │   ├── markdown_generator.py    # Markdown生成器
│   │   ├── error_handler.py         # 错误处理器
│   │   └── models/                  # 数据模型
│   ├── service_role_binding/         # 服务角色绑定
│   ├── agent_hosting/               # Agent托管
│   ├── mcp_hosting/                 # MCP托管
│   ├── strands_agent_logging_hook.py # Strands Agent日志钩子
│   └── structured_output_model/      # 结构化输出模型
├── config/                           # 配置文件
│   ├── default_config.yaml          # 默认配置
│   └── logging_config.yaml         # 日志配置
├── projects/                         # 项目文件
│   └── aws_pricing_agent/           # AWS定价Agent项目
├── tests/                            # 测试文件
├── logs/                             # 日志文件
├── mcp/                              # MCP配置
├── web/                              # Web应用
├── requirements.txt                  # Python依赖
├── pyproject.toml                    # 项目配置
└── README.md                        # 项目说明
```

## Code Organization Patterns

### Agent Factory System
- **Dynamic Creation**: Agents created from YAML prompt templates via `agent_factory.py`
- **Template-Driven**: Each agent defined by structured YAML configuration
- **Multi-Level Paths**: Support for hierarchical agent organization (e.g., `system_agents_prompts/agent_build_workflow/orchestrator`)
- **Version Management**: Multiple versions per agent with automatic latest selection
- **Core Functions**:
  - `create_agent_from_prompt_template()`: 从提示词模板创建Agent
  - `get_tool_by_path()`: 通过路径导入工具
  - `import_tools_by_strings()`: 批量导入工具
  - `list_available_agents()`: 列出所有可用Agent

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
- **Structure Example**:
```yaml
agent:
  name: "agent_name"
  description: "Agent描述"
  category: "category"
  environments:
    production:
      max_tokens: 60000
      temperature: 0.3
  versions:
    - version: "latest"
      status: "stable"
      system_prompt: |
        系统提示词内容
  metadata:
    tags: ["tag1", "tag2"]
    tools_dependencies:
      - "strands_tools/calculator"
      - "system_tools/project_manager/project_init"
```

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