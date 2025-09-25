# Nexus-AI 系统部署和使用指南

## 📋 项目概述

Nexus-AI是一个基于AWS Bedrock构建的企业级AI代理开发平台，通过"Agent Build Agent"的创新方法，让业务人员能够通过自然语言快速构建、部署和管理复杂的AI代理系统。

### 🌟 核心特性

- **智能代理构建**: 通过自然语言描述自动生成AI代理
- **自举式进化**: 代理系统能够自我优化和迭代
- **多代理协作**: 支持复杂业务场景的多代理协同工作
- **AWS Bedrock集成**: 基于AWS Bedrock的强大AI能力
- **MCP协议支持**: 标准化的模型上下文协议
- **模块化设计**: 可扩展的插件化架构

## 🏗️ 详细目录结构

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
├── web_application/                  # Web应用
├── requirements.txt                  # Python依赖
├── pyproject.toml                    # 项目配置
└── README.md                        # 项目说明
```

## 🚀 快速开始

### 环境要求

- Python 3.13+
- AWS CLI 已配置
- AWS Bedrock 访问权限
- 推荐使用虚拟环境

### 1. 克隆项目

```bash
git clone https://github.com/hy714335634/Nexus-AI
cd Nexus-AI
```

### 2. 安装依赖

#### 使用 uv 安装（推荐）

```bash
# 安装 uv
pip install uv

# 安装依赖
uv pip install -r requirements.txt
```

### 3. 安装Jaeger
```bash
# Pull and run Jaeger all-in-one container
docker run -d --name jaeger \
  -e COLLECTOR_ZIPKIN_HOST_PORT=:9411 \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 6831:6831/udp \
  -p 6832:6832/udp \
  -p 5778:5778 \
  -p 16686:16686 \
  -p 4317:4317 \
  -p 4318:4318 \
  -p 14250:14250 \
  -p 14268:14268 \
  -p 14269:14269 \
  -p 9411:9411 \
  jaegertracing/all-in-one:latest
```

### 4. 配置AWS凭证

```bash
# 配置AWS CLI
aws configure

# 或设置环境变量
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-west-2
```

### 5. 验证安装

```bash
# 运行测试
python agents/system_agents/magician.py
```

## 🔧 核心模块详解

### 1. Utils 模块 (`utils/`)

#### 1.1 Agent Factory (`agent_factory.py`)

**功能**: Agent工厂，负责动态创建和管理Agent实例

**核心功能**:
- `create_agent_from_prompt_template()`: 从提示词模板创建Agent
- `get_tool_by_path()`: 通过路径导入工具
- `import_tools_by_strings()`: 批量导入工具
- `list_available_agents()`: 列出所有可用Agent

**使用示例**:
```python
from utils.agent_factory import create_agent_from_prompt_template

# 创建Agent
agent = create_agent_from_prompt_template(
    agent_name="system_agents_prompts/agent_build_workflow/orchestrator",
    env="production",
    version="latest",
    model_id="default"
)
```

#### 1.2 Config Loader (`config_loader.py`)

**功能**: 配置加载器，统一管理项目配置

**核心功能**:
- `get_aws_config()`: 获取AWS配置
- `get_bedrock_config()`: 获取Bedrock配置
- `get_strands_config()`: 获取Strands配置
- `get_nested()`: 获取嵌套配置项

**使用示例**:
```python
from utils.config_loader import get_config

config = get_config()
aws_config = config.get_aws_config()
bedrock_config = config.get_bedrock_config()
```

#### 1.3 Prompts Manager (`prompts_manager.py`)

**功能**: 提示词管理器，管理所有Agent的提示词模板

**核心功能**:
- `get_agent()`: 获取Agent提示词
- `get_agent_version()`: 获取指定版本
- `list_all_agent_paths()`: 列出所有Agent路径
- `get_agents_by_category()`: 按类别获取Agent

**使用示例**:
```python
from utils.prompts_manager import get_default_prompt_manager

manager = get_default_prompt_manager()
agent = manager.get_agent("requirements_analyzer")
latest_version = agent.get_version("latest")
```

#### 1.4 Multimodal Processing (`multimodal_processing/`)

**功能**: 多模态内容处理模块

**核心组件**:
- `content_parsing_engine.py`: 内容解析引擎
- `multimodal_model_service.py`: 多模态模型服务
- `s3_storage_service.py`: S3存储服务
- `file_upload_manager.py`: 文件上传管理器
- `document_processor.py`: 文档处理器
- `image_processor.py`: 图像处理器
- `text_processor.py`: 文本处理器

**支持格式**:
- 图像: JPG, PNG, GIF
- 文档: Excel, Word, PDF
- 文本: TXT, MD, JSON

**使用示例**:
```python
from utils.multimodal_processing import get_content_parsing_engine

parsing_engine = get_content_parsing_engine()()
file_list = [file_metadata1, file_metadata2]
results = parsing_engine.parse_files(file_list)
```

### 2. System Tools 模块 (`tools/system_tools/`)

#### 2.1 Agent Build Workflow Tools (`agent_build_workflow/`)

**功能**: Agent构建工作流相关工具

##### 2.1.1 Project Manager (`project_manager.py`)

**功能**: 项目管理工具，提供完整的项目生命周期管理

**核心功能**:
- `project_init`: 项目初始化
- `update_project_config`: 更新项目配置
- `get_project_status`: 获取项目状态
- `update_project_status`: 更新项目状态
- `update_agent_artifact_path`: 更新Agent制品路径
- `generate_content`: 生成内容文件

**使用示例**:
```python
from tools.system_tools.agent_build_workflow.project_manager import project_init

# 初始化项目
result = project_init("my_new_agent")
print(result)
```

##### 2.1.2 Template Providers

**Agent Template Provider** (`agent_template_provider.py`):
- 提供Agent模板管理功能
- 验证Agent文件格式
- 列出可用Agent模板

**Prompt Template Provider** (`prompt_template_provider.py`):
- 管理提示词模板
- 验证提示词文件
- 提供模板搜索功能

**Tool Template Provider** (`tool_template_provider.py`):
- 管理工具模板
- 验证工具文件
- 提供工具分类和搜索

#### 2.2 Multimodal Content Parser (`multimodal_content_parser.py`)

**功能**: 多模态内容解析系统工具

**核心功能**:
- `parse_multimodal_content`: 解析多模态内容
- `get_supported_formats`: 获取支持格式
- `validate_files`: 验证文件
- `get_processing_status`: 获取处理状态

**使用示例**:
```python
from tools.system_tools.multimodal_content_parser import parse_multimodal_content

# 解析多模态内容
result = parse_multimodal_content(
    files=[{"name": "test.jpg", "content": "base64_content"}],
    processing_options={"format": "markdown"}
)
```

### 3. System Agents 模块 (`agents/system_agents/`)

#### 3.1 Agent Build Workflow (`agent_build_workflow/`)

**功能**: Agent构建工作流，包含7个阶段的Agent

##### 3.1.1 主工作流编排器 (`agent_build_workflow.py`)

**功能**: 协调整个Agent构建流程

**核心特性**:
- 使用Strands MultiAgent GraphBuilder
- 支持7个阶段的Agent协作
- 提供意图分析和项目初始化
- 支持交互式和批处理模式

**使用示例**:
```bash
# 交互式模式
python -u agents/system_agents/agent_build_workflow/agent_build_workflow.py | tee logs/temp.log

# 批处理模式
python -u agents/system_agents/agent_build_workflow/agent_build_workflow.py \
  -i "请创建一个Agent帮我完成AWS产品报价工作..." | tee logs/temp.log
```

##### 3.1.2 各阶段Agent

1. **Requirements Analyzer** (`requirements_analyzer_agent.py`)
   - 分析用户需求
   - 提取关键信息
   - 生成需求文档

2. **System Architect** (`system_architect_agent.py`)
   - 设计系统架构
   - 定义组件关系
   - 生成架构文档

3. **Agent Designer** (`agent_designer_agent.py`)
   - 设计Agent结构
   - 定义Agent能力
   - 生成设计文档

4. **Prompt Engineer** (`prompt_engineer_agent.py`)
   - 设计提示词模板
   - 优化提示词效果
   - 生成提示词文件

5. **Tool Developer** (`tool_developer_agent.py`)
   - 开发工具函数
   - 实现业务逻辑
   - 生成工具代码

6. **Agent Code Developer** (`agent_code_developer_agent.py`)
   - 开发Agent代码
   - 集成工具和提示词
   - 生成完整Agent

7. **Agent Developer Manager** (`agent_developer_manager_agent.py`)
   - 管理开发流程
   - 协调各阶段工作
   - 生成最终文档

#### 3.2 其他系统Agent

##### 3.2.1 Magician (`magician.py`)
- 提供高级AI功能
- 支持复杂任务处理

##### 3.2.2 Multimodal Analysis (`multimodal_analysis/`)
- 多模态内容分析
- 支持图像、文档、文本处理

## 🧪 测试指南

### 测试Nexus-AI核心功能

#### 1. Agent构建工作流测试

```bash
# 交互式模式 - 手动输入需求
python -u agents/system_agents/agent_build_workflow/agent_build_workflow.py | tee logs/temp.log

# 批处理模式 - 直接提供需求
python -u agents/system_agents/agent_build_workflow/agent_build_workflow.py \
  -i "请创建一个Agent帮我完成AWS产品报价工作，我会提供tsv格式的其他云平台账单或IDC配置清单，请找到正确的AWS配置并告诉我真实价格，具体要求如下：
1、需要至少支持计算、存储、网络、数据库四个核心产品
2、在用户提出的描述不清晰时，需要能够根据用户需求推测合理配置
3、需要使用真实价格数据，通过aws接口获取真实数据
4、能够支持根据客户指定区域进行报价
5、能够按照销售的思维分析用户提供的数据，生成清晰且有逻辑的报价方案
6、报价文档尽量使用中文" | tee logs/temp.log
```

#### 3. 配置管理测试

```bash
# 测试配置加载
python -c "
from utils.config_loader import get_config
config = get_config()
print('AWS配置:', config.get_aws_config())
print('Bedrock配置:', config.get_bedrock_config())
"
```

#### 4. Agent工厂测试

```bash
# 测试Agent创建
python -c "
from utils.agent_factory import create_agent_from_prompt_template
agent = create_agent_from_prompt_template('system_agents_prompts/agent_build_workflow/orchestrator')
print('Agent创建成功:', agent is not None)
"
```

## ⚙️ 配置说明

### 主要配置文件

#### `config/default_config.yaml`

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
      bedrock_region: "us-west-2"
    file_limits:
      max_file_size: "50MB"
      max_files_per_request: 10
      supported_formats: ["jpg", "jpeg", "png", "gif", "txt", "xlsx", "docx", "csv"]
```

### 环境变量

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

## 🔧 开发指南

### 项目架构说明

#### Agent开发流程

Nexus-AI采用7阶段Agent开发流程：

1. **需求分析** (`requirements_analyzer`)
   - 分析用户需求
   - 提取关键信息
   - 生成需求文档

2. **系统架构设计** (`system_architect`)
   - 设计系统架构
   - 定义组件关系
   - 生成架构文档

3. **Agent设计** (`agent_designer`)
   - 设计Agent结构
   - 定义Agent能力
   - 生成设计文档

4. **提示词工程** (`prompt_engineer`)
   - 设计提示词模板
   - 优化提示词效果
   - 生成提示词文件

5. **工具开发** (`tool_developer`)
   - 开发工具函数
   - 实现业务逻辑
   - 生成工具代码

6. **Agent代码开发** (`agent_code_developer`)
   - 开发Agent代码
   - 集成工具和提示词
   - 生成完整Agent

7. **Agent开发管理** (`agent_developer_manager`)
   - 管理开发流程
   - 协调各阶段工作
   - 生成最终文档

#### 工具开发

工具位于 `tools/` 目录下，分为三类：

- **系统工具** (`system_tools/`): 基础系统功能
- **模板工具** (`template_tools/`): 工具模板
- **生成工具** (`generated_tools/`): 自动生成的工具

#### 提示词管理

提示词位于 `prompts/` 目录下，使用YAML格式：

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

### 添加新Agent

1. 在 `agents/template_agents/` 创建Agent模板
2. 在 `prompts/template_prompts/` 创建提示词模板
3. 在 `tools/template_tools/` 创建工具模板
4. 使用Agent Build Workflow生成完整Agent

### 添加新工具

1. 在 `tools/template_tools/` 创建工具模板
2. 使用 `@tool` 装饰器定义工具函数
3. 在工具模板提供器中注册工具
4. 在Agent提示词中引用工具

---

*最后更新时间: 2025-09-05*

**注意**: 本指南基于当前项目状态编写，随着项目发展会持续更新。如有问题请参考项目文档或提交Issue。
