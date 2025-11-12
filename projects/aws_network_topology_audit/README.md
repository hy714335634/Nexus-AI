# aws_network_topology_audit

## 项目描述
AWS网络拓扑审计工具，用于收集和可视化AWS环境中的网络拓扑信息，包括跨区域、跨账户的VPC连接，以及通过TGW、VPC Peering、PrivateLink等方式建立的连接。该工具支持高亮显示网络边界，以满足审计要求。

## 项目结构
```
aws_network_topology_audit/
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

#### aws_network_topology_visualizer
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/aws_network_topology_audit/agents/aws_network_topology_visualizer/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/aws_network_topology_audit/agents/aws_network_topology_visualizer/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/aws_network_topology_audit/agents/aws_network_topology_visualizer/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/aws_network_topology_audit/agents/aws_network_topology_visualizer/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](projects/aws_network_topology_audit/agents/aws_network_topology_visualizer/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](projects/aws_network_topology_audit/agents/aws_network_topology_visualizer/agent_code_developer.json)
- **agent_developer_manager**: ✅ 已完成 - [文档](projects/aws_network_topology_audit/agents/aws_network_topology_visualizer/agent_developer_manager.json)

## 附加信息
# AWS 网络拓扑审计工具

## 项目概述
AWS 网络拓扑审计工具是一个专为满足审计要求而设计的解决方案，能够收集和可视化 AWS 环境中的网络拓扑信息。该工具可以识别和展示各种类型的 VPC 连接，包括跨区域、跨账户的连接，以及通过 TGW、VPC Peering、PrivateLink 等方式建立的连接。工具还支持高亮显示网络边界，帮助审计人员清晰识别潜在的安全风险点。

## 功能特点
- **全面的资源收集**：收集 AWS 网络资源信息（VPC、子网、路由表、安全组等）
- **多种连接类型识别**：识别各种 VPC 连接类型（TGW、VPC Peering、PrivateLink 等）
- **跨区域和跨账户支持**：识别和展示跨区域和跨账户连接
- **网关连接识别**：识别通过 CGW、DXGW 的连接
- **防火墙隔离识别**：识别通过 Network Firewall 隔离的网络
- **网络边界高亮**：高亮显示网络边界，清晰标识安全分区
- **可视化输出**：生成清晰直观的网络拓扑图，支持导出为多种格式

## 项目结构
```
aws_network_topology_audit/
├── agents/
│   └── generated_agents/
│       └── aws_network_topology_audit/
│           └── aws_network_topology_visualizer.py  # 主要 Agent 代码
├── generated_agents_prompts/
│   └── aws_network_topology_audit/
│       └── aws_network_topology_visualizer.yaml    # Agent 提示词模板
├── generated_tools/
│   └── aws_network_topology_audit/
│       ├── boto3_client_tool.py                    # AWS API 客户端工具
│       ├── boto3_resource_tool.py                  # AWS 资源对象工具
│       ├── networkx_graph_tool.py                  # 网络图构建和分析工具
│       ├── graphviz_renderer_tool.py               # 图形渲染工具
│       ├── matplotlib_plotter_tool.py              # 图形绘制工具
│       ├── file_manager_tool.py                    # 文件管理工具
│       └── credential_manager_tool.py              # 凭证管理工具
├── requirements.txt                                # 项目依赖
└── README.md                                       # 项目说明文档
```

## 安装与配置
1. 克隆项目仓库
2. 安装依赖：`pip install -r requirements.txt`
3. 确保已配置有效的 AWS 凭证（访问密钥或角色）

## 使用方法
```bash
# 基本用法
python -m agents.generated_agents.aws_network_topology_audit.aws_network_topology_visualizer --profile <aws-profile> --regions us-east-1,us-west-2

# 指定多个账户
python -m agents.generated_agents.aws_network_topology_audit.aws_network_topology_visualizer --accounts '[{"account_id": "123456789012", "role_name": "CrossAccountRole"}]'

# 指定资源类型
python -m agents.generated_agents.aws_network_topology_audit.aws_network_topology_visualizer --resource-types vpc,subnet,security-group

# 指定输出格式和目录
python -m agents.generated_agents.aws_network_topology_audit.aws_network_topology_visualizer --output-format svg --output-dir ./audit-results

# 不高亮显示网络边界
python -m agents.generated_agents.aws_network_topology_audit.aws_network_topology_visualizer --no-highlight-boundaries

# 仅收集数据不生成可视化
python -m agents.generated_agents.aws_network_topology_audit.aws_network_topology_visualizer --mode collect --output-dir ./collected-data

# 使用已收集的数据生成可视化
python -m agents.generated_agents.aws_network_topology_audit.aws_network_topology_visualizer --mode visualize --input-file ./collected-data/network_data.json
```

## 所需权限
工具需要以下 AWS 权限才能正常工作：
- EC2:Describe*
- VPC:Describe*
- TransitGateway:Describe*
- DirectConnect:Describe*
- NetworkFirewall:Describe*
- RAM:List*
- Organizations:List* (仅用于跨账户分析)

## 开发阶段状态
- [x] 需求分析
- [x] 系统架构设计
- [x] Agent 设计
- [x] 提示词工程
- [x] 工具开发
- [x] Agent 代码开发
- [x] Agent 开发管理

## 注意事项
- 工具仅收集网络配置信息，不会修改任何 AWS 资源
- 对于大型环境，数据收集可能需要较长时间
- 某些连接类型的识别可能需要额外的权限
- 工具遵循最小权限原则，仅请求必要的只读权限

## 技术栈
- Python 3.9+
- AWS SDK for Python (boto3)
- NetworkX (网络分析库)
- Graphviz/PyGraphviz (图形可视化)
- Matplotlib (图形绘制)
- Strands SDK (智能体框架)

## 贡献指南
欢迎提交问题报告和功能请求。如需贡献代码，请先创建问题讨论您的提议。

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-11-11 15:03:17 UTC*
