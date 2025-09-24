# Technology Stack & Build System

## Core Technologies

- **Python 3.13+**: Primary development language (推荐使用虚拟环境)
- **AWS Bedrock**: AI model hosting and inference with multiple model support (Claude 3.5 Haiku, Claude 3.7 Sonnet, Claude Opus 4)
- **AWS AgentCore**: Agent runtime and deployment platform
- **Strands Framework**: Agent orchestration and tool integration with multi-agent support (Graph, Swarm)
- **MCP (Model Context Protocol)**: Standardized tool and service integration
- **UV Package Manager**: Python package management (推荐使用uv替代pip)
- **Jaeger**: Distributed tracing system for monitoring and troubleshooting

## Key Dependencies

- `strands-agents`: Core agent framework with multi-agent capabilities (Graph, Swarm)
- `strands-agents-tools`: Built-in tool collection
- `bedrock-agentcore`: AWS AgentCore integration
- `boto3`: AWS SDK for Python
- `PyYAML`: Configuration management
- `feedparser`: RSS/Atom feed parsing
- `colorama`: Cross-platform colored terminal text
- `uv`: Python package management

## Architecture Components

### Agent Factory System

- **Agent Factory** (`nexus_utils./agent_factory.py`): Dynamic agent creation from prompt templates
- **Prompt Manager** (`nexus_utils./prompts_manager.py`): YAML-based prompt template management with versioning
- **MCP Manager** (`nexus_utils./mcp_manager.py`): MCP server configuration and client management
- **Config Loader** (`nexus_utils./config_loader.py`): Centralized configuration management

### Multimodal Processing System

- **Content Parsing Engine** (`nexus_utils./multimodal_processing/content_parsing_engine.py`): Unified content processing interface
- **File Upload Manager** (`nexus_utils./multimodal_processing/file_upload_manager.py`): File upload and validation handling
- **Image Processor** (`nexus_utils./multimodal_processing/image_processor.py`): Image content analysis and processing
- **Document Processor** (`nexus_utils./multimodal_processing/document_processor.py`): Excel, Word, and text document processing
- **S3 Storage Service** (`nexus_utils./multimodal_processing/s3_storage_service.py`): AWS S3 file storage management
- **Multimodal Model Service** (`nexus_utils./multimodal_processing/multimodal_model_service.py`): AI model integration for content analysis
- **Markdown Generator** (`nexus_utils./multimodal_processing/markdown_generator.py`): Structured markdown output generation

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
pip install uv                        # Install uv package manager
uv pip install -r requirements.txt    # Install dependencies using uv
source venv/bin/activate             # Activate virtual environment (if using venv)

# Jaeger Setup (for tracing)
docker run -d --name jaeger \
  -e COLLECTOR_ZIPKIN_HOST_PORT=:9411 \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 6831:6831/udp -p 6832:6832/udp \
  -p 5778:5778 -p 16686:16686 \
  -p 4317:4317 -p 4318:4318 \
  -p 14250:14250 -p 14268:14268 \
  -p 14269:14269 -p 9411:9411 \
  jaegertracing/all-in-one:latest

# AWS Configuration
aws configure                         # Configure AWS CLI
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-west-2

# Agent Build Workflow Testing
# 交互式模式 - 手动输入需求
python -u agents/system_agents/agent_build_workflow/agent_build_workflow.py | tee logs/temp.log

# 批处理模式 - 直接提供需求
python -u agents/system_agents/agent_build_workflow/agent_build_workflow.py \
  -i "请创建一个Agent帮我完成AWS产品报价工作..." | tee logs/temp.log

# Agent Factory Usage
python -c "from nexus_utils..agent_factory import create_agent_from_prompt_template; agent = create_agent_from_prompt_template('system_agents_prompts/agent_build_workflow/orchestrator')"

# Configuration Testing
python -c "from nexus_utils..config_loader import get_config; config = get_config(); print('AWS配置:', config.get_aws_config())"

# System Agent Testing
python agents/system_agents/magician.py  # Test magician agent

# MCP Server Management
uvx awslabs.aws-api-mcp-server@latest  # Run AWS API MCP server
uvx strands-agents-mcp-server          # Run Strands MCP server
```

## Configuration

### Main Configuration Files
- `config/default_config.yaml`: Main system configuration with model settings
- `config/logging_config.yaml`: Logging configuration
- `prompts/`: YAML-based prompt templates with hierarchical structure
  - `system_agents_prompts/`: System agent prompts
  - `template_prompts/`: Template agent prompts  
  - `generated_agents_prompts/`: Generated agent prompts
- `mcp/*.json`: MCP server configurations with auto-approval settings

### Key Configuration Structure
```yaml
default-config:
  aws:
    bedrock_region_name: 'us-west-2'
    aws_region_name: 'us-west-2'
    aws_profile_name: 'default'
  strands:
    template:
      agent_template_path: 'agents/template_agents'
      prompt_template_path: 'prompts/template_prompts'
      tool_template_path: 'tools/template_tools'
    generated:
      agent_generated_path: 'agents/generated_agents'
      prompt_generated_path: 'prompts/generated_agents_prompts'
      tool_generated_path: 'tools/generated_tools'
  bedrock:
    model_id: 'us.anthropic.claude-3-7-sonnet-20250219-v1:0'
    lite_model_id: 'us.anthropic.claude-3-5-haiku-20241022-v1:0'
    pro_model_id: 'us.anthropic.claude-opus-4-20250514-v1:0'
  multimodal_parser:
    aws:
      s3_bucket: "awesome-nexus-ai-file-storage"
      s3_prefix: "multimodal-content/"
    file_limits:
      max_file_size: "50MB"
      max_files_per_request: 10
      supported_formats: ["jpg", "jpeg", "png", "gif", "txt", "xlsx", "docx", "csv"]
```

### Environment Variables
```bash
# AWS配置
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-west-2

# Bedrock配置
export BEDROCK_REGION=us-west-2

# 工具配置
export BYPASS_TOOL_CONSENT=true

# 遥测配置
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

## Key Features

- **Dynamic Agent Creation**: Create agents from YAML prompt templates
- **Multi-Model Support**: Automatic model selection based on agent requirements
- **Tool Integration**: Dynamic tool loading and dependency management
- **Configuration Management**: Hierarchical YAML configuration system
- **MCP Integration**: Standardized protocol for external tool integration
- **Multi-Agent Workflows**: Graph and swarm-based agent collaboration
- **Multimodal Content Processing**: Unified processing of images, documents, and text files
- **S3 Storage Integration**: Secure file storage and management with AWS S3
- **Structured Output Generation**: Automatic markdown generation from processed content

## Development Workflow

### Agent开发流程
Nexus-AI采用7阶段Agent开发流程：

1. **需求分析** (requirements_analyzer): 分析用户需求，提取关键信息，生成需求文档
2. **系统架构设计** (system_architect): 设计系统架构，定义组件关系，生成架构文档
3. **Agent设计** (agent_designer): 设计Agent结构，定义Agent能力，生成设计文档
4. **提示词工程** (prompt_engineer): 设计提示词模板，优化提示词效果，生成提示词文件
5. **工具开发** (tool_developer): 开发工具函数，实现业务逻辑，生成工具代码
6. **Agent代码开发** (agent_code_developer): 开发Agent代码，集成工具和提示词，生成完整Agent
7. **Agent开发管理** (agent_developer_manager): 管理开发流程，协调各阶段工作，生成最终文档

### 工具开发指南
- 工具位于 `tools/` 目录下，分为三类：
  - **系统工具** (`system_tools/`): 基础系统功能
  - **模板工具** (`template_tools/`): 工具模板
  - **生成工具** (`generated_tools/`): 自动生成的工具
- 使用 `@tool` 装饰器定义工具函数
- 在工具模板提供器中注册工具
- 在Agent提示词中引用工具

### 添加新Agent步骤
1. 在 `agents/template_agents/` 创建Agent模板
2. 在 `prompts/template_prompts/` 创建提示词模板
3. 在 `tools/template_tools/` 创建工具模板
4. 使用Agent Build Workflow生成完整Agent
