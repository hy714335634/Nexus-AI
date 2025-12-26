# Nexus-AI

<div align="center">

<img src="architecture/default_logo.png" alt="Nexus-AI Logo" width="200" height="200">

![Nexus-AI Logo](https://img.shields.io/badge/Nexus--AI-Enterprise%20AI%20Platform-blue?style=for-the-badge&logo=aws)

**Agentic AI-Native Platform - 从想法到实现，只需要一句话**

[![Python](https://img.shields.io/badge/Python-3.12+-blue?style=flat-square&logo=python)](https://python.org)
[![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-orange?style=flat-square&logo=amazon-aws)](https://aws.amazon.com/bedrock/)
[![Strands](https://img.shields.io/badge/Strands-Agent%20Framework-green?style=flat-square)](https://strands.ai)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

[快速开始](#快速开始) • [功能特性](#功能特性) • [架构设计](#架构设计) • [使用指南](#使用指南) • [贡献指南](#贡献指南)

</div>

## 🌟 项目概述

Nexus-AI 是一个基于 AWS Bedrock 构建的开源企业级 AI 代理开发平台，通过"Agent Build Agent"的创新方法和自举式进化能力，让企业业务人员能够通过自然语言快速构建、部署和管理复杂的 AI 代理系统。

### 🎯 核心价值

- **🚀 极速构建**：从需求到部署，传统开发需要2-6个月，Nexus-AI仅需2-5天
- **🎨 零代码门槛**：业务人员无需编程知识，通过自然语言描述即可构建AI代理
- **🔄 自举式进化**：系统能够自我优化和迭代，持续提升能力
- **🏗️ 企业级架构**：基于AWS Bedrock，支持大规模生产环境部署

## 🏗️ 核心架构

### 单Agent构建工作流

Nexus-AI 采用分层架构设计，包含7个核心模块：

```mermaid
%%{init: {'themeVariables': {'fontSize': '22px', 'fontFamily': 'Arial, sans-serif', 'primaryColor': '#e1bee7', 'primaryTextColor': '#4a148c', 'primaryBorderColor': '#8e24aa'}}}%%
graph TD
    %% 用户需求输入
    UserReq[用户需求输入] --> IntentRecognition[意图识别<br/>Function Agent Level]
    IntentRecognition --> ReqAnalysisTeam[需求分析团队<br/>Team Level]
    
    %% 第一层分解
    ReqAnalysisTeam --> TaskPlanTeam[研发设计团队<br/>Team Level]
    ReqAnalysisTeam --> ReqAnalysisExpert[需求分析专家<br/>Expert Level]
    ReqAnalysisExpert --> ReqUseCaseExpert[产品测试用例专家<br/>Specialist Level]
    ReqAnalysisTeam --> ReqOrgExpert[需求深度理解专家<br/>Expert Level]
    
    %% 第二层分解
    TaskPlanTeam --> LLMPlanner[Agent应用架构师<br/>Specialist Level]
    TaskPlanTeam --> AgentDesigner[Agent设计师<br/>Specialist Level]
    TaskPlanTeam --> AgentDevTeam[Agent开发团队<br/>Team Level]
    
    %% 第三层执行
    AgentDevTeam --> ProjectDelivery[项目交付经理<br/>Execution Level]
    ProjectDelivery --> AgentCodeDeveloper[Agent开发工程师<br/>Engineer Level]
    ProjectDelivery --> PromptEngineer[提示词工程师<br/>Engineer Level]
    ProjectDelivery --> ToolsDevExpert[工具开发工程师<br/>Engineer Level]
    ContentAuditEngineer --> PoCEngineer[测试工程师<br/>Engineer Level]
    ProjectDelivery --> ContentAuditEngineer[内容审查工程师<br/>Engineer Level]
    ProjectDelivery --> CompleteProject[完整可运行项目]

    
    %% 资产复用决策
    subgraph AssetReuse[智能资产复用推荐]
        AgentLibCheck[Agent库索引]
        ToolLibCheck[工具库索引]
        PromptLibCheck[提示词库索引]
        ReuseDecision[模版推荐<br/>Function Agent Level]
    end
    
    ReqUseCaseExpert -->PoCEngineer
    ToolsDevExpert --> AssetReuse
    PromptEngineer --> AssetReuse
    AgentCodeDeveloper --> AssetReuse
    ReuseDecision -->|工具调用| ToolLibCheck
    ReuseDecision -->|工具调用| AgentLibCheck
    ReuseDecision -->|工具调用| PromptLibCheck

    
    %% 最终输出
    PoCEngineer --> CompleteProject[完整可运行项目]
    
    %% 样式定义
    classDef rawinput fill:#f5f5f5,stroke:#757575,stroke-width:2px,color:#424242,font-size:22px;
    classDef team fill:#e3f2fd,stroke:#0277bd,stroke-width:2px,font-size:22px;
    classDef expert fill:#f1f8e9,stroke:#558b2f,stroke-width:2px,font-size:22px;
    classDef specialist fill:#fce4ec,stroke:#c2185b,stroke-width:2px,font-size:22px;
    classDef engineer fill:#fff8e1,stroke:#ff8f00,stroke-width:2px,font-size:22px;
    classDef reuse fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,font-size:22px;
    classDef notuse fill:#9e9e9e,stroke:#424242,stroke-width:2px,color:#000000,font-size:22px;
    classDef finish fill:#c8e6c9,stroke:#4caf50,stroke-width:3px,color:#2e7d32,font-size:22px;
    
    class ReqAnalysisTeam,TaskPlanTeam,DevTeam,AgentDevTeam team;
    class ReqAnalysisExpert,AgentRoleExpert expert;
    class LLMPlanner,AgentDesigner specialist;
    class PromptEngineer,ToolsDevExpert,AgentCodeDeveloper engineer;
    class AgentLibCheck,PromptLibCheck,ToolLibCheck reuse;
    class ContentAuditEngineer,PoCEngineer,ReqUseCaseExpert,PromptReviewer,ReqOrgExpert notuse;
    class CompleteProject finish
    class UserReq rawinput
```

### 当前实现状态

| 模块 | 状态 | 描述 |
|------|------|------|
| **Agent Build** | ✅ 已完成 | 多Agent协作构建系统，支持7阶段自动化开发流程 |
| **会话模块** | ✅ 已完成 开发中 | 基于Next.js的Web控制台界面 |
| **Agent Management** | 🔄 开发中 | Agent生命周期管理，包括版本控制和更新 |
| **Tools & MCP** | 🔄 开发中 | 工具库管理和MCP协议支持 |
| **Debug & Troubleshooting** | 📋 规划中 | 智能问题诊断和自动修复 |
| **Operations Management** | 📋 规划中 | 运维监控和自动化管理 |
| **Observability** | 📋 规划中 | 系统可观测性和性能分析 |

## 🚀 功能特性

### 🤖 智能代理构建

- **多Agent协作**：8个专业Agent协同工作，从需求分析到代码生成
- **自然语言驱动**：通过自然语言描述自动生成完整的AI代理系统
- **模板化开发**：内置多种Agent模板，支持单Agent和多Agent场景
- **智能资产复用**：自动识别和复用现有Agent、工具和提示词

### 🎯 已构建的Agent示例

Nexus-AI 已经成功构建了多个实用的AI代理，展示了平台的强大能力：

#### 🤖 平台助手Agent

**Nexus-AI问答助手 (Nexus-AI-QA-Assistant)**
- 基于Nexus-AI项目知识库的智能问答服务
- 提供FastAPI Web接口和Workshop实验手册
- 预加载核心项目文件，优化问答响应速度
- 支持多种问答模式：架构、工作流、代码、运维等

#### 📊 AWS相关Agent

**AWS架构图生成器 (aws_architecture_diagram_generator)**
- 将自然语言描述转换为专业的AWS架构图
- 支持IT技术栈映射、架构验证

**AWS网络拓扑分析器 (aws_network_topology_analyzer)**
- 自动化采集AWS网络资源配置信息
- 生成网络架构拓扑图
- 支持合规性评估和多格式输出

**AWS定价代理 (aws_pricing_agent)**
- 根据资源需求提供AWS服务配置推荐
- 支持EC2、EBS、S3、RDS等多种AWS服务

#### 📝 文档处理Agent

**HTML课件生成器 (html_courseware_generator)**
- 智能生成多学科动态交互HTML课件
- 自动生成教案文档
- 支持数学公式、化学方程式渲染
- 提供FastAPI Web服务集成

**HTML转PPT代理 (html2pptx)**
- 将HTML文档转换为PPTX演示文稿
- 保留原始样式、支持自定义模板

**PDF内容提取代理 (pdf_content_extractor)**
- 从PDF文件中提取文本内容
- 支持多模态处理和批量处理

**PPT转Markdown代理 (ppt_to_markdown)**
- 将PPT文件转换为Markdown格式
- 保持结构层次和格式

#### 🔍 检索与分析Agent

**公司信息搜索代理 (company_info_search_agent)**
- 读取Excel表格中的公司信息
- 通过多种搜索引擎查询公司详细信息
- 支持批量处理和结果输出

**股票分析代理 (stock_analysis_agent)**
- 多Agent协作的智能股票分析系统
- 基于DCF估值法计算股票估值
- 盈利预测、风险评估、行业对比分析
- 生成2000+字的专业分析报告

#### 🎨 内容生成Agent

**Logo设计代理 (logo_design_agent)**
- 分析用户需求并生成logo设计
- 生成高质量logo图像和设计说明报告

#### 🔬 医学相关Agent

**医学文档翻译代理 (medical_document_translation_agent)**
- 精准翻译医学专业文档
- 支持医学词库管理和质量控制

**OpenFDA数据查询代理 (openfda_data_agent)**
- 与OpenFDA API交互，查询FDA公开数据
- 支持药物、医疗设备、食品等多领域数据检索
- 自然语言查询理解和智能路由

**药物反馈收集代理 (drug_feedback_collector)**
- 从多个来源收集药物用户反馈信息
- 多源网络信息检索（搜索引擎、医疗论坛、社交媒体）
- 情感分析和主题分类
- 生成全面的反馈分析报告

**临床试验搜索代理 (clinicaltrials_search_agent)**
- 智能搜索ClinicalTrials.gov数据
- 面向临床开发专业人士的专业视角分析
- 多轮深度搜索和结果整合
- 临床开发视角的结果呈现


## 📁 项目结构

```
Nexus-AI/
├── agents/                          # 智能体实现
│   ├── system_agents/               # 核心平台智能体
│   │   └── agent_build_workflow/    # Agent构建工作流
│   ├── template_agents/             # 可复用智能体模板
│   └── generated_agents/            # 动态创建的智能体
├── tools/                           # 工具实现
│   ├── system_tools/                # 核心平台工具
│   ├── template_tools/              # 工具模板
│   └── generated_tools/             # 生成的工具
├── prompts/                         # YAML提示词模板
│   ├── system_agents_prompts/       # 系统智能体提示词
│   ├── template_prompts/            # 模板提示词
│   └── generated_agents_prompts/    # 生成的提示词
├── projects/                        # 用户项目目录
│   └── {project_name}/              # 具体项目
│       ├── agents/                  # Agent开发过程文件
│       ├── config.yaml              # 项目配置
│       ├── status.yaml              # 项目状态
│       └── README.md                # 项目说明
├── web/                             # Web前端界面 (Next.js)
│   ├── app/                         # Next.js App Router
│   ├── components/                  # React组件
│   └── src/                         # 源代码
├── utils/                           # 共享工具
├── config/                          # 配置文件
├── mcp/                             # MCP服务器配置
└── docs/                            # 文档
```

## 🛠️ 技术栈

### 后端技术栈
- **Agent开发框架**: AWS Bedrock, Strands SDK
- **开发语言**: Python 3.12+

## 🚀 快速开始

### 前置要求

- **Python**: 3.12+
- **Node.js**: 已安装（用于前端开发）
- **AWS 账户**: 配置好 AWS 凭证和权限（需要 Amazon Bedrock、DynamoDB 等服务的访问权限）

### 1. 安装基础工具

**Amazon Linux 2023 / RHEL / CentOS:**
```bash
# 安装系统依赖
sudo dnf install -y git wget htop python3.12 nodejs

# 验证安装
python3.12 --version
git --version
```

**其他 Linux 发行版 / macOS:**
```bash
# 安装 Python 3.12+ 和 Node.js
# 请根据您的系统使用相应的包管理器（apt, yum, brew 等）
```

### 2. 安装 uv (Python 包管理器)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 验证安装
uv --version
```


### 3. 拉取代码并进入项目目录
```bash
git clone https://github.com/hy714335634/Nexus-AI.git
cd Nexus-AI
```

### 4. 初始化 Python 环境
```bash
# 创建虚拟环境（使用 Python 3.12）
python3.12 -m venv .nexus-ai

# 激活虚拟环境
source .nexus-ai/bin/activate

# 可选：将激活命令添加到 bashrc（Linux/macOS）
echo 'source $HOME/Nexus-AI/.nexus-ai/bin/activate' >> ~/.bashrc
echo 'cd $HOME/Nexus-AI/' >> ~/.bashrc

### 5. 安装 Python 依赖
```bash
uv pip install --upgrade pip
uv pip install -r requirements.txt
uv pip install strands-agents[otel]
uv pip install -e .
```

> 💡 **国内网络环境提示**: 可在命令后追加 `--index-url https://pypi.tuna.tsinghua.edu.cn/simple`  
> 安装完成后可使用 `uv pip list | head` 验证安装成功

### 6. 配置 AWS 凭证
```bash
aws configure
```

按照提示输入：
- AWS Access Key ID
- Secret Access Key  
- Region: `us-west-2`（推荐）

验证凭证配置：
```bash
aws configure set region us-west-2
aws sts get-caller-identity
```

### 7. 初始化 DynamoDB 数据库
```bash
python api/scripts/setup_tables.py
```

> ✅ 成功后会显示 `✅ All tables created successfully!`  
> ⚠️ **注意**: 确保 IAM 角色或用户具有 DynamoDB 的读写权限

### 8. 启动服务

**启动 FastAPI 后端 API**
```bash
nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &

# 查看日志
tail -f nohup.out

# 验证服务是否启动
curl http://localhost:8000/health
```

- API 服务监听 `0.0.0.0:8000`，可从外部访问
- 访问 API 文档：`http://<服务器IP>:8000/docs`

**启动 Next.js 前端**
```bash
cd web
npm install    # 首次运行需要安装依赖
nohup npm run dev -- -H 0.0.0.0 &
cd ..
```

- 前端服务监听 `0.0.0.0:3000`，可从外部访问
- 访问地址：`http://<服务器IP>:3000`
- 首次运行需要安装依赖，可能需要几分钟

> ⚠️ **安全组配置提醒**（如使用 AWS EC2）:  
> 确保安全组已开放以下端口：
> - `3000` - Next.js 前端
> - `8000` - FastAPI 后端  
> - `8888` - Workshop 材料（如需）

### 9. 启动 Workshop 参考材料（可选）

Workshop 材料提供了详细的动手实验手册：
```bash
nohup python agents/generated_agents/Nexus-AI-QA-Assistant/nexus_qa_assistant_fastapi.py &
```

- 默认启动后通过 `<服务器IP>:8888` 端口访问
- Workshop 包含完整的环境准备、部署、验证和 Agent 构建流程

### 首次使用

1. 确保后端 API 和前端都已启动
2. 打开浏览器访问 `http://<服务器IP>:3000`
3. 在首页输入你的需求描述
4. 点击"开始构建"按钮
5. 观察实时构建进度
6. 构建完成后测试你的Agent

> 💡 **提示**: 如需查看详细的实验手册和最佳实践，建议启动 Workshop 材料（步骤9）

## 🔍 功能与构建验证

- 环境验证示例：`python agents/system_agents/magician.py  -i "aws美东一的m8g.xlarge什么价格"`
- 长任务可采用 `nohup python -u agents/system_agents/agent_build_workflow/agent_build_workflow.py -i "<你的需求>" | tee logs/temp.log &`
- 查看实时日志：`tail -f nohup.out`
- 已生成项目位于 `projects/<project_name>/`，包含 `agents/`、`project_config.json`、`workflow_summary_report.md` 等产物

## 📖 使用指南
### 示例：构建HTML转PPT Agent

```python
# 1. 需求描述

nohup python -u agents/system_agents/agent_build_workflow/agent_build_workflow.py -i '请创建一个能够将HTML文档转换为pptx文档的Agent, 基本功能要求如下:
- 能够基于语义提取和识别关键和非关键信息，并思考PPT内容和故事主线
- PPT中出现的文字、段落内容应与HTML中内容一致
- 能够支持任意标签结构层级的HTML文档，能根据HTML标签结构定义PPT的结构
- 能够支持任意HTML标签的样式，能根据HTML标签样式定义PPT的样式
- PPT内容风格、模版样式应尽可能保持HTML原样式
- 对于HTML中图片内容，能尽可能保留，并以合理的布局展示在PPT中
- 能够使用用户指定的PPT模版
- 必要的文字内容和备注信息应尽可能保留，并存储在指定PPT页的备注中

**注意事项**
- 为避免Token超出限制,请避免使用base64编码方式进行输出
- PPT内容可分页输出
- 当通过模型解析到必要数据后,可缓存在本地.cache目录中,后续工具执行可通过传递缓存文件路径进行处理，避免token过长问题' &

nohup python -u agents/system_agents/agent_build_workflow/agent_build_workflow.py -i '创建一个agent，能够根据客户给定的主题和话题，生成高质量HTML课件，核心需求如下：
1）生成的HTML具备动态交互能力
2）支持各类学科的内容主题，如语文、数学、化学等等
3）能够在生成HTML课件的同时，给老师提供备课教案

关键要求：
1）项目应集成fastapi能力，并代理本地特定的目录
2）生成的html课件和教案应按照文件夹或主题命名后，存储在对应fastapi代理的目录，并自动reload' &


# 2. 系统自动执行构建流程
# 3. 生成完整的Agent系统
```

## 🔧 配置说明

### 基础配置

```yaml
# config/default_config.yaml
default-config:
  aws:
    bedrock_region_name: 'us-west-2'  # Amazon Bedrock API调用区域
    aws_region_name: 'us-west-2'      # 其他AWS服务的默认区域
    aws_profile_name: 'default'       # AWS配置文件名称
    verify: True                      # 验证SSL证书
  
  strands:
    template:
      agent_template_path: 'agents/template_agents'     # Agent模板路径
      prompt_template_path: 'prompts/template_prompts'  # 提示词模板路径
      tool_template_path: 'tools/template_tools'        # 工具模板路径
    generated:
      agent_generated_path: 'agents/generated_agents'   # 生成的Agent路径
      prompt_generated_path: 'prompts/generated_agents_prompts'
      tool_generated_path: 'tools/generated_tools'
    default_tools:
      - 'calculator'    # 计算器工具
      - 'shell'         # Shell命令工具
      - 'file_read'     # 文件读取工具
      - 'file_write'    # 文件写入工具
  
  agentcore:
    execution_role_prefix: 'agentcore'     # IAM执行角色前缀
    ecr_auto_create: True                  # 自动创建ECR仓库
    runtime_timeout_minutes: 30            # Agent运行时超时时间
  
  bedrock:
    model_id: 'us.anthropic.claude-sonnet-4-5-20250929-v1:0'    # 默认模型
    lite_model_id: 'us.anthropic.claude-3-5-haiku-20241022-v1:0' # 轻量模型
    pro_model_id: 'us.anthropic.claude-opus-4-20250514-v1:0'     # 专业模型
  
  logging:
    level: 'INFO'                          # 日志级别
    file_path: 'logs/nexus_ai.log'         # 日志文件路径
```

### MCP服务器配置

```json
// mcp/system_mcp_server.json
{
  "mcpServers": {
    "awslabs.core-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.core-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false
    },
    "awslabs.aws-pricing-mcp-server": {
      "command": "uvx", 
      "args": ["awslabs.aws-pricing-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false
    },
    "awslabs.aws-api-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-api-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "default", 
        "AWS_REGION": "us-west-2"
      },
      "disabled": false
    }
  }
}
```

### 多模态处理配置

```yaml
# config/default_config.yaml (多模态部分)
multimodal_parser:
  aws:
    s3_bucket: "awesome-nexus-ai-file-storage"  # S3存储桶
    s3_prefix: "multimodal-content/"            # S3前缀
    bedrock_region: "us-west-2"                 # Bedrock区域
  
  file_limits:
    max_file_size: "50MB"                       # 最大文件大小
    max_files_per_request: 10                   # 每次请求最大文件数
    supported_formats: ["jpg", "jpeg", "png", "gif", "txt", "xlsx", "docx", "csv"]
  
  processing:
    timeout_seconds: 300                        # 处理超时时间
    retry_attempts: 3                          # 重试次数
    batch_size: 5                              # 批处理大小
  
  model:
    primary_model: "us.anthropic.claude-opus-4-20250514-v1:0"    # 主模型
    fallback_model: "us.anthropic.claude-sonnet-4-5-20250929-v1:0" # 备用模型
    max_tokens: 40000                          # 最大Token数
```

## 🎯 路线图

### 2025 Q4
- ✅ 完成单/多Agent Build模块
- ✅ 完成单Agent功能迭代模块
- ✅ 构建CICD工作流，自动化部署至AWS Bedrock AgentCore
- ✅ 基础Web界面

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 贡献方式

1. **报告问题**: 在GitHub Issues中报告bug或提出功能请求
2. **提交代码**: Fork项目并提交Pull Request
3. **完善文档**: 改进文档和示例
4. **分享经验**: 在Discussions中分享使用经验

---

<div align="center">

**让AI帮你构建AI，开启智能代理开发的新时代**

[![Star](https://img.shields.io/github/stars/hy714335634/nexus-ai?style=social)](https://github.com/hy714335634/nexus-ai)
[![Fork](https://img.shields.io/github/forks/hy714335634ur-org/nexus-ai?style=social)](https://github.com/hy714335634/nexus-ai/fork)
[![Watch](https://img.shields.io/github/watchers/hy714335634/nexus-ai?style=social)](https://github.com/hy714335634/nexus-ai)

</div>