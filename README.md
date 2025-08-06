# Nexus-AI
<<<<<<< HEAD
Nexus-AI是一个基于AWS Bedrock构建的开源企业级AI代理开发平台，通过'Agent Build Agent'的创新方法和自举式进化能力，让企业业务人员能够通过自然语言快速构建、部署和管理复杂的AI代理系统。
=======

Nexus-AI是一个基于AWS Bedrock构建的开源企业级AI代理开发平台，通过'Agent Build Agent'的创新方法和自举式进化能力，让企业业务人员能够通过自然语言快速构建、部署和管理复杂的AI代理系统。

## 🌟 核心特性

### 🤖 智能代理构建
- **Agent Build Agent**: 通过自然语言描述自动生成AI代理
- **自举式进化**: 代理系统能够自我优化和迭代
- **多代理协作**: 支持复杂业务场景的多代理协同工作

### 🏗️ 企业级架构
- **AWS Bedrock集成**: 基于AWS Bedrock的强大AI能力
- **MCP协议支持**: 标准化的模型上下文协议
- **模块化设计**: 可扩展的插件化架构

### 🚀 快速部署
- **一键部署**: 自动化部署到AWS AgentCore
- **容器化支持**: Docker容器化部署
- **云端托管**: 支持云端和本地部署

## 📁 项目结构

```
Nexus-AI/
├── agents/                          # 代理系统
│   ├── system_agents/              # 系统级代理
│   │   ├── orchestrator_agent.py   # 编排代理
│   │   ├── code_generator_agent.py # 代码生成代理
│   │   ├── requirements_analyzer_agent.py # 需求分析代理
│   │   └── deployment_manager_agent.py # 部署管理代理
│   └── generated_agents/           # 生成的代理
├── config/                         # 配置文件
│   └── default_config.yaml        # 默认配置
├── mcp/                           # MCP服务器
│   ├── system_mcp_server/         # 系统MCP服务器
│   └── public_mcp_server/         # 公共MCP服务器
├── prompts/                       # 提示词管理
│   ├── system_agents_prompts/     # 系统代理提示词
│   └── generated_agents_prompts/  # 生成代理提示词
├── templates/                     # 模板文件
│   ├── agents/                    # 代理模板
│   ├── tools/                     # 工具模板
│   └── requirements/              # 依赖模板
├── tools/                         # 工具系统
│   ├── system_tools/              # 系统工具
│   └── public_tools/              # 公共工具
├── utils/                         # 工具类
│   ├── agent_build.py            # 代理构建工具
│   ├── mcp_manager.py            # MCP管理器
│   ├── config_loader.py          # 配置加载器
│   └── prompts_manager.py        # 提示词管理器
├── web_application/              # Web应用
├── examples/                     # 示例代码
└── logs/                         # 日志文件
```

## 🚀 快速开始

### 环境要求

- Python 3.13+
- AWS CLI 配置
- Docker (可选，用于容器化部署)

### 安装

1. 克隆仓库
```bash
git clone https://github.com/hy714335634/Nexus-AI.git
cd Nexus-AI
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置AWS凭证
```bash
aws configure
```

### 基本使用

#### 1. 创建代理

```python
from agents.system_agents.orchestrator_agent import OrchestratorAgent

# 创建编排代理
orchestrator = OrchestratorAgent()

# 通过自然语言创建代理
result = orchestrator.create_agent(
    description="创建一个能够分析财务报表的AI助手"
)
```

#### 2. 部署代理

```python
from utils.agent_build import AgentBuilder

# 构建和部署代理
builder = AgentBuilder()
deployment_result = builder.deploy_agent(
    agent_name="financial_analyzer",
    agent_config=result['config']
)
```

#### 3. 使用MCP服务器

```python
from utils.mcp_manager import MCPManager

# 启动MCP服务器
mcp_manager = MCPManager()
mcp_manager.start_server()
```

## 🔧 配置说明

### 默认配置

项目使用YAML格式的配置文件 `config/default_config.yaml`：

```yaml
default-config:
  aws:
    bedrock_region_name: 'us-west-2'
    aws_region_name: 'us-east-1'
  
  bedrock:
    model_id: 'us.anthropic.claude-3-5-sonnet-20240620-v1:0'
    lite_model_id: 'us.anthropic.claude-3-5-haiku-20241022-v1:0'
    pro_model_id: 'us.anthropic.claude-3-7-sonnet-20250219-v1:0'
    
  agentcore:
    execution_role_prefix: 'agentcore'
    ecr_auto_create: True
    runtime_timeout_minutes: 30
```

## 🏗️ 核心组件

### 系统代理

1. **编排代理 (Orchestrator Agent)**
   - 负责整体工作流程的协调
   - 管理其他代理的创建和协作

2. **代码生成代理 (Code Generator Agent)**
   - 根据需求自动生成代理代码
   - 支持多种编程语言和框架

3. **需求分析代理 (Requirements Analyzer Agent)**
   - 分析用户需求并生成技术规格
   - 优化代理设计

4. **部署管理代理 (Deployment Manager Agent)**
   - 自动化部署流程
   - 监控部署状态

### MCP服务器

- **系统MCP服务器**: 提供核心系统功能
- **公共MCP服务器**: 提供公共工具和服务

## 📚 示例

查看 `examples/` 目录获取更多使用示例：

- 基础代理创建
- 多代理协作
- 自定义工具集成
- 部署配置

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🔗 相关链接

- [AWS Bedrock](https://aws.amazon.com/bedrock/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [Strands Agents](https://strandsagents.com/)

## 📞 支持

如果您遇到问题或有建议，请：

1. 查看 [Issues](https://github.com/hy714335634/Nexus-AI/issues)
2. 创建新的 Issue
3. 联系项目维护者

---

**Nexus-AI** - 让AI代理开发变得简单高效 🚀 
>>>>>>> 5317d03 (Initial commit: Nexus-AI enterprise AI agent development platform)
