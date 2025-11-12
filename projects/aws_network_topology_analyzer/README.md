# aws_network_topology_analyzer

## 项目描述
AWS网络拓扑分析Agent，帮助客户了解AWS账号中核心资源的网络拓扑，并辅助客户做后续的网络、安全分析工作。

## 项目结构
```
aws_network_topology_analyzer/
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

#### aws_network_topology_analyzer
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/aws_network_topology_analyzer/agents/aws_network_topology_analyzer/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/aws_network_topology_analyzer/agents/aws_network_topology_analyzer/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/aws_network_topology_analyzer/agents/aws_network_topology_analyzer/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/aws_network_topology_analyzer/agents/aws_network_topology_analyzer/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](projects/aws_network_topology_analyzer/agents/aws_network_topology_analyzer/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](projects/aws_network_topology_analyzer/agents/aws_network_topology_analyzer/agent_code_developer.json)
- **agent_developer_manager**: ✅ 已完成

## 附加信息
# AWS Network Topology Analyzer

## 项目概述
AWS网络拓扑分析Agent是一个专门用于分析AWS账号中网络资源拓扑结构的智能Agent。它通过集成AWS Boto3 SDK扫描指定区域的网络组件和计算资源，将资源关系存储在Neo4j图数据库中，并提供基于自然语言的查询和分析能力，帮助用户理解其AWS网络架构并进行安全分析。

## 功能特点
- **AWS资源扫描**：扫描指定区域的所有网络组件资源以及EC2、RDS资源
- **网络拓扑建模**：在Neo4j图数据库中创建资源节点和关系
- **层级结构组织**：按照Account->Region->Network Service->VPC->Routetable->Security Group->EC2/RDS等层级组织资源
- **自然语言查询**：支持通过自然语言问题进行对话和问答
- **网络路径分析**：分析资源间的网络路径和可达性
- **安全配置评估**：分析网络安全配置和潜在风险
- **可视化展示**：可视化网络拓扑结构

## 项目结构
```
aws_network_topology_analyzer/
├── agents/
│   └── generated_agents/
│       └── aws_network_topology_analyzer/
│           └── aws_network_topology_analyzer.py  # Agent主代码
├── generated_agents_prompts/
│   └── aws_network_topology_analyzer/
│       └── aws_network_topology_analyzer.yaml    # Agent提示词模板
├── generated_tools/
│   └── aws_network_topology_analyzer/
│       ├── aws_profile_manager.py                # AWS配置文件管理工具
│       ├── aws_resource_scanner.py               # AWS资源扫描工具
│       ├── neo4j_database_connector.py           # Neo4j数据库连接工具
│       ├── neo4j_node_creator.py                 # Neo4j节点创建工具
│       ├── neo4j_edge_creator.py                 # Neo4j边创建工具
│       ├── neo4j_query_executor.py               # Neo4j查询执行工具
│       ├── neo4j_path_analyzer.py                # Neo4j路径分析工具
│       ├── neo4j_topology_visualizer.py          # Neo4j拓扑可视化工具
│       ├── natural_language_to_cypher_converter.py # 自然语言转Cypher查询工具
│       └── error_analyzer_and_resolver.py        # 错误分析和解决工具
├── config.yaml                                   # 项目配置文件
├── requirements.txt                              # Python依赖包
├── README.md                                     # 项目说明文档
└── status.yaml                                   # 项目状态文件
```

## 安装与配置
1. 克隆项目仓库
```bash
git clone <repository-url>
cd aws_network_topology_analyzer
```

2. 安装依赖包
```bash
pip install -r requirements.txt
```

3. 配置AWS凭证
确保已正确配置AWS CLI凭证，或在`~/.aws/credentials`文件中添加配置。

4. 配置Neo4j数据库
确保Neo4j数据库已正确安装和启动，默认连接信息：
- 地址：neo4j://localhost:7687
- 用户名：neo4j
- 密码：neo4jneo4j

## 使用方法

### 扫描AWS资源
```bash
python aws_network_topology_analyzer.py scan --profile <profile-name> --region <region-name>
```

### 查询网络拓扑
```bash
python aws_network_topology_analyzer.py query --question "列出所有VPC及其子网"
```

### 分析网络路径
```bash
python aws_network_topology_analyzer.py path --source <source-id> --destination <destination-id>
```

### 可视化网络拓扑
```bash
python aws_network_topology_analyzer.py visualize --scope vpc --resource-id <vpc-id>
```

### 分析安全配置
```bash
python aws_network_topology_analyzer.py security --vpc-id <vpc-id>
```

### 执行自定义查询
```bash
python aws_network_topology_analyzer.py custom --query "MATCH (n:VPC) RETURN n LIMIT 10"
```

### 交互模式
```bash
python aws_network_topology_analyzer.py interactive
```

## 开发状态
- [x] 需求分析
- [x] 系统架构设计
- [x] Agent设计
- [x] 工具开发
- [x] 提示词工程
- [x] Agent代码开发
- [x] Agent开发管理

## 技术栈
- Python 3.13+
- AWS Boto3 SDK
- Neo4j图数据库
- Strands SDK
- AWS Bedrock

## 注意事项
- 确保有足够的AWS API权限查看所需资源
- 大型AWS环境扫描可能需要较长时间
- 建议为Neo4j数据库分配足够的内存，特别是对于大型网络拓扑

## 贡献指南
欢迎提交问题报告、功能请求和代码贡献。请遵循以下步骤：
1. Fork项目仓库
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证
[MIT License](LICENSE)

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-11-11 15:06:01 UTC*
