# aws_pricing_agent

## 项目描述
AWS产品报价智能体，能够根据自然语言描述的资源需求，分析并推荐合理的AWS服务和配置，提供实时报价并生成专业的报价方案。支持EC2、EBS、S3、网络流量、ELB、RDS、ElastiCache、Opensearch等多种AWS产品的价格查询。

## 项目结构
```
aws_pricing_agent/
├── agents/          # Agent实现文件
├── config.yaml      # 项目配置文件
├── README.md        # 项目说明文档
└── status.yaml      # 项目状态跟踪文件
```

## Agent开发阶段

### 阶段说明
1. **requirements_analyzer**: 需求分析阶段
2. **system_architect**: 系统架构设计阶段
3. **agent_designer**: Agent设计阶段
4. **prompt_engineer**: 提示词工程阶段
5. **tools_developer**: 工具开发阶段
6. **agent_code_developer**: Agent代码开发阶段
7. **agent_developer_manager**: Agent开发管理阶段

### 各Agent阶段结果

#### requirements_analyzer
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/aws_pricing_agent/agents/requirements_analyzer/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/aws_pricing_agent/agents/requirements_analyzer/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/aws_pricing_agent/agents/requirements_analyzer/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/aws_pricing_agent/agents/requirements_analyzer/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](projects/aws_pricing_agent/agents/requirements_analyzer/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](projects/aws_pricing_agent/agents/requirements_analyzer/agent_code_developer.json)
- **agent_developer_manager**: ✅ 已完成 - [文档](projects/aws_pricing_agent/agents/requirements_analyzer/agent_developer_manager.json)

## 附加信息
# AWS Pricing Agent

## 项目概述

AWS Pricing Agent 是一个专业的智能体，能够根据用户提供的自然语言描述资源需求，分析并推荐合理的AWS服务和配置，提供实时报价并生成专业的报价方案。该智能体集成了AWS价格API，支持多种AWS服务的实时价格查询，并具备销售思维分析能力。

## 项目状态

✅ 需求分析：已完成  
✅ 系统架构设计：已完成  
✅ 智能体设计：已完成  
✅ 工具开发：已完成  
✅ 提示词工程：已完成  
✅ 智能体代码开发：已完成  
✅ 智能体开发管理：已完成  

**项目进度**：7/7 阶段完成 (100%)

## 核心功能

- **自然语言需求解析**：理解用户的资源需求描述，提取关键信息
- **AWS服务配置推荐**：根据需求推荐合适的AWS服务和配置
- **实时价格查询**：通过AWS价格API获取实时准确的价格信息
- **专业报价方案生成**：生成清晰、有逻辑的报价方案

## 支持的AWS服务

- **EC2**：计算实例推荐与价格查询
- **EBS**：块存储配置与价格查询
- **S3**：对象存储配置与价格查询
- **ELB**：负载均衡配置与价格查询
- **网络流量**：数据传输费用计算
- **RDS**：关系型数据库服务配置与价格查询
- **ElastiCache**：内存缓存服务配置与价格查询
- **OpenSearch**：搜索服务配置与价格查询

## 特性

- 支持按需实例和预留实例价格查询
- 支持所有AWS商业区域和中国区域的价格查询
- 在同系列同配置情况下，优先推荐最新一代实例
- 根据用户需求推测合理配置，处理不明确的需求
- 采用销售思维分析用户需求，生成专业报价方案
- 在价格获取失败时明确标注

## 系统架构

AWS Pricing Agent 采用单智能体架构，内部分为四个主要功能模块：

1. **需求解析模块**：解析用户的自然语言需求，提取关键资源需求信息
2. **配置推荐模块**：根据用户需求推荐合适的AWS服务配置
3. **价格查询模块**：通过AWS价格API获取推荐配置的实时价格
4. **报价方案生成模块**：生成专业的报价方案

## 技术实现

- **基础模板**：api_integration_agent
- **核心工具**：use_aws（AWS服务交互工具）
- **模型要求**：Claude 3.5 Sonnet
- **外部接口**：AWS Price List API, AWS Service Catalog, AWS SDK for Python (boto3)

## 使用方法

1. **提供需求描述**：向智能体描述您的AWS资源需求，可以包括计算、存储、数据库等需求
2. **指定区域（可选）**：指定您希望部署的AWS区域
3. **提供补充信息**：根据智能体的澄清问题提供额外信息
4. **获取报价方案**：智能体将生成包含配置建议和价格明细的完整报价方案

## 示例输入

```
我需要部署一个电商网站，预计日访问量10万，需要3台Web服务器，一个MySQL数据库，100GB存储空间，以及适当的负载均衡。请在us-east-1区域进行报价。
```

## 使用限制

- 不执行AWS服务的实际部署和配置
- 不提供AWS账户管理功能
- 不分析历史价格趋势
- 不提供竞品价格对比
- 不支持多云环境的价格比较

## 最佳实践

- 提供尽可能详细的资源需求描述
- 明确指定关键性能参数和数量
- 指定目标AWS区域以获取准确的价格和可用性信息
- 对于复杂架构，考虑分阶段请求不同组件的报价

## 维护计划

- 定期更新AWS服务目录信息
- 跟踪AWS价格API的变更
- 更新配置推荐逻辑以适应新的AWS服务和实例类型
- 监控价格API调用成功率和响应时间
- 收集用户反馈，持续改进系统性能和准确性

## 项目目录结构

```
Nexus-AI/
├── projects/
│   └── aws_pricing_agent/    # AWS定价智能体项目目录
│       ├── README.md         # 项目说明文档
│       ├── config.yaml       # 项目配置文件
│       ├── status.yaml       # 项目状态文件
│       ├── workflow_summary_report.md # 工作流总结报告
│       └── agents/
│           └── requirements_analyzer/
│               ├── requirements_analyzer.json    # 需求分析文档
│               ├── system_architect.json         # 系统架构设计文档
│               ├── agent_designer.json           # 智能体设计文档
│               ├── tools_developer.json          # 工具开发文档
│               ├── prompt_engineer.json          # 提示词工程文档
│               ├── agent_code_developer.json     # 智能体代码开发文档
│               └── agent_developer_manager.json  # 智能体开发管理总结文档
├── tools/
│   └── generated_tools/
│       └── aws_pricing_agent/
│           └── aws_pricing_tool.py   # AWS定价服务交互工具
├── prompts/
│   └── generated_agents_prompts/
│       └── aws_pricing_agent/
│           └── aws_pricing_agent.yaml # 智能体提示词模板
└── agents/
    └── generated_agents/
        └── aws_pricing_agent/
            └── aws_pricing_agent.py  # 智能体代码实现
```

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-09-14 04:21:10 UTC*
