# aws_network_analyzer

## 项目描述
AWS网络架构分析Agent，用于自动化采集AWS资源配置信息并生成网络架构拓扑图，满足NIST CSF 2.0 ID.AM-03和CISA CPGs 2.P合规要求

## 项目结构
```
aws_network_analyzer/
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

#### aws_network_analyzer_agent
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/aws_network_analyzer/agents/aws_network_analyzer_agent/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/aws_network_analyzer/agents/aws_network_analyzer_agent/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/aws_network_analyzer/agents/aws_network_analyzer_agent/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/aws_network_analyzer/agents/aws_network_analyzer_agent/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](projects/aws_network_analyzer/agents/aws_network_analyzer_agent/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](projects/aws_network_analyzer/agents/aws_network_analyzer_agent/agent_code_developer.json)
- **agent_developer_manager**: ✅ 已完成 - [文档](projects/aws_network_analyzer/agents/aws_network_analyzer_agent/agent_developer_manager.json)

## 附加信息
# AWS Network Architecture Analyzer

## 项目概述

AWS Network Architecture Analyzer是一个自动化工具，能够采集用户在AWS上的资源和配置信息，并生成AWS账号内指定Region的完整逻辑网络架构拓扑图。该工具旨在满足NIST CSF 2.0 ID.AM-03和CISA CPGs 2.P合规要求，帮助用户全面了解其AWS网络基础设施。

## 项目状态

✅ 需求分析阶段 - 已完成  
✅ 系统架构设计阶段 - 已完成  
✅ Agent设计阶段 - 已完成  
✅ 提示词工程阶段 - 已完成  
✅ 工具开发阶段 - 已完成  
✅ Agent代码开发阶段 - 已完成  
✅ Agent开发管理阶段 - 已完成  

## 功能特性

### 资源发现和映射范围

**Region 内资源：**
- VPC（所有 VPC 及其 CIDR 块）
- Subnets（公有/私有子网及其关联的 AZ）
- Route Tables（路由表及其路由条目）
- Internet Gateway (IGW)
- NAT Gateway / NAT Instance
- Transit Gateway (TGW) 及其附件
- VPC Endpoints (Interface / Gateway / Gateway Load Balancer)
- Security Groups（显示关联关系和关键规则）
- Network ACLs
- Elastic Load Balancers (ALB/NLB/CLB/GWLB)
- EC2 实例（含网络接口 ENI）
- Lambda（VPC 配置的函数）
- RDS/Aurora/Redshift 等数据库实例
- ElastiCache、ECS/EKS 网络配置

**跨 Region 连接：**
- Inter-Region VPC Peering
- Inter-Region Transit Gateway Peering
- Inter-Region PrivateLink (跨区域端点服务)

**混合云连接：**
- Direct Connect (DX) - 虚拟接口、连接位置
- Site-to-Site VPN（VPN Gateway/Transit Gateway VPN）
- Client VPN Endpoints
- AWS VPN CloudHub 配置

**其他关键组件：**
- Route 53 Resolver (Inbound/Outbound Endpoints)
- AWS PrivateLink 连接
- VPC Peering (同 Region)
- Egress-Only Internet Gateway (IPv6)
- NAT Gateway
- Network Firewall
- AWS WAF 关联

### 可视化输出

**图形元素：**
- 使用不同颜色/形状区分组件类型
- 显示层次结构（Region → VPC → Subnet → Resource）
- 标注 CIDR 块、可用区、连接类型
- 高亮显示关键路径和安全边界
- 支持交互式导航（点击查看详细配置）

**输出格式：**
- 静态图：PNG/SVG/PDF
- 交互式图：HTML
- 机器可读格式：JSON/YAML
- 可选：集成 draw.io / Lucidchart 格式

## 目录结构

```
aws_network_analyzer/
├── agents/
│   └── generated_agents/
│       └── aws_network_analyzer/
│           └── aws_network_analyzer_agent.py
├── prompts/
│   └── generated_agents_prompts/
│       └── aws_network_analyzer/
│           └── aws_network_analyzer_agent.yaml
├── tools/
│   └── generated_tools/
│       └── aws_network_analyzer/
│           ├── aws_boto3_tools.py
│           ├── network_graph_tools.py
│           ├── data_processor_tools.py
│           └── file_utils.py
├── .cache/
│   └── aws_network_analyzer_agent/
│       └── <analysis_id>/
├── requirements.txt
└── README.md
```

## 使用方法

### 安装依赖

```bash
pip install -r requirements.txt
```

### 基本用法

```bash
python agents/generated_agents/aws_network_analyzer/aws_network_analyzer_agent.py --region us-east-1
```

### 高级用法

```bash
python agents/generated_agents/aws_network_analyzer/aws_network_analyzer_agent.py \
  --profile my-aws-profile \
  --region us-east-1 \
  --output-format HTML \
  --cache-option "强制刷新" \
  --detail-level "详细" \
  --additional "请特别关注安全组规则和VPC Peering连接"
```

### 参数说明

- `--profile`: AWS Profile名称，默认使用默认Profile
- `--region`: AWS Region名称（必需）
- `--output-format`: 输出格式选项，默认为PNG
- `--cache-option`: 缓存选项，默认为"使用缓存"
- `--detail-level`: 详细程度选项，默认为"标准"
- `--comparison-id`: 历史比较选项(比较目标ID)
- `--additional`: 附加说明和要求

## 输出文件

默认输出/缓存位置在 `.cache/<agent_name>/<analysis_id>/`，包括：

- 网络拓扑图（PNG/SVG/PDF/HTML格式）
- 资源清单（JSON/YAML格式）
- 合规性评估报告
- 执行日志和错误报告

## 合规支持

本工具旨在满足以下合规标准的要求：

- NIST CSF 2.0 ID.AM-03：组织物理设备、系统和软件平台的清单
- CISA CPGs 2.P：资产清单和漏洞管理

## 注意事项

- 确保使用的AWS凭证具有足够的只读权限
- 大型AWS环境（1000+资源）可能需要较长的扫描时间
- 交互式HTML输出需要现代浏览器支持
- 所有缓存数据会加密存储在本地
- 该工具不会修改任何AWS资源配置

## 依赖库

- boto3: AWS SDK for Python
- networkx: 网络图形分析库
- graphviz: 图形可视化库
- matplotlib: 数据可视化库
- pandas: 数据分析库
- 其他依赖详见requirements.txt

## 贡献与支持

如有问题或建议，请提交issue或联系项目维护者。

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-10-31 05:28:42 UTC*
