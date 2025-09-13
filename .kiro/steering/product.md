# Nexus-AI Product Overview

Nexus-AI is an open-source enterprise-grade AI agent development platform built on AWS Bedrock. It enables business users to quickly build, deploy, and manage complex AI agent systems through natural language using an innovative "Agent Build Agent" approach with advanced multi-agent orchestration capabilities.

## System Overview

Nexus-AI采用7阶段Agent开发流程，通过"Agent Build Agent"的创新方法，让业务人员能够通过自然语言快速构建、部署和管理复杂的AI代理系统。系统支持自举式进化，代理系统能够自我优化和迭代。

## Core Features

### Agent Development System
- **Agent Build Agent**: Automatically generates AI agents through natural language descriptions
- **Agent Factory**: Dynamic agent creation from YAML prompt templates with version management (`utils/agent_factory.py`)
- **Prompt Engineering**: Structured YAML-based prompt templates with metadata and versioning (`utils/prompts_manager.py`)
- **Tool Integration**: Automatic tool dependency resolution and dynamic loading
- **7-Stage Development Pipeline**: Complete automated agent development workflow with specialized roles
- **Template-Driven Development**: Create agents from structured YAML templates with hierarchical organization

### Multi-Agent Orchestration
- **Graph-Based Workflows**: Dependency-driven agent execution with complex workflow support
- **Swarm Intelligence**: Collaborative agent problem-solving with adaptive handoff mechanisms
- **Specialized Workflows**: Pre-built agent workflows for common business scenarios
- **Agent Build Workflow**: Complete automated agent development pipeline with specialized roles:
  - **Requirements Analyzer** (`requirements_analyzer_agent.py`): 分析用户需求，提取关键信息，生成需求文档
  - **System Architect** (`system_architect_agent.py`): 设计系统架构，定义组件关系，生成架构文档
  - **Agent Designer** (`agent_designer_agent.py`): 设计Agent结构，定义Agent能力，生成设计文档
  - **Prompt Engineer** (`prompt_engineer_agent.py`): 设计提示词模板，优化提示词效果，生成提示词文件
  - **Tool Developer** (`tool_developer_agent.py`): 开发工具函数，实现业务逻辑，生成工具代码
  - **Agent Code Developer** (`agent_code_developer_agent.py`): 开发Agent代码，集成工具和提示词，生成完整Agent
  - **Agent Developer Manager** (`agent_developer_manager_agent.py`): 管理开发流程，协调各阶段工作，生成最终文档

### Platform Capabilities
- **Self-bootstrapping Evolution**: Agent systems can self-optimize and iterate
- **Multi-Model Support**: Automatic model selection (Claude 3.5 Haiku, Claude 3.7 Sonnet, Claude Opus 4)
- **AWS Bedrock Integration**: Leverages AWS Bedrock's powerful AI capabilities with intelligent model routing
- **MCP Protocol Support**: Standardized Model Context Protocol for external tool integration
- **Configuration Management**: Hierarchical YAML configuration system with environment support
- **Modular Architecture**: Extensible plugin-based design with dynamic component loading
- **One-click Deployment**: Automated deployment to AWS AgentCore with container support
- **Multimodal Content Processing**: Unified processing of images, documents, Excel, Word files with AI-powered analysis
- **S3 Storage Integration**: Secure file storage and management with automatic cleanup and presigned URLs
- **Structured Output Generation**: Automatic conversion of multimodal content to structured Markdown format

### Developer Experience
- **Template-Driven Development**: Create agents from structured YAML templates
- **Dynamic Tool Discovery**: Automatic tool detection and integration
- **Multi-Environment Support**: Development, production, and testing configurations
- **Comprehensive Testing**: Built-in test suites for multi-agent scenarios
- **Hot Configuration Reload**: Runtime configuration updates without restart

## Target Users

- **Business Users**: Create sophisticated AI agent systems without deep technical knowledge through natural language interfaces
- **Developers**: Build complex multi-agent systems with structured templates and workflows
- **Enterprise Teams**: Deploy scalable agent solutions with proper governance and configuration management
- **AI Researchers**: Experiment with multi-agent collaboration patterns and workflow optimization

## Use Cases

- **Business Process Automation**: Multi-agent workflows for complex business scenarios
- **Software Development**: Automated agent development with specialized workflow roles
- **Customer Service**: Intelligent agent swarms for complex customer inquiries
- **Data Analysis**: Collaborative agents for multi-step analytical processes
- **Content Generation**: Coordinated agents for structured content creation workflows
- **Document Processing**: Automated analysis and processing of multimodal business documents (Excel, Word, PDF, images)
- **Cloud Migration Planning**: AWS pricing and configuration analysis for cloud migration projects (如AWS定价Agent示例)
- **Multimodal Data Integration**: Unified processing of text, images, and structured documents
- **Enterprise AI Solutions**: 企业级AI代理解决方案，支持复杂业务场景
- **自动化工具开发**: 通过自然语言描述自动生成专业工具和Agent

## Key Examples

### AWS Pricing Agent
完整的AWS定价分析Agent示例，支持：
- 计算、存储、网络、数据库四个核心产品
- 根据用户需求推测合理配置
- 使用真实AWS API获取价格数据
- 支持指定区域报价
- 生成清晰的中文报价方案