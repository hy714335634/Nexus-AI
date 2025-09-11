# aws_pricing_assistant

## 项目描述
AWS产品报价助手，用于分析云平台账单或IDC配置清单，推荐合理的AWS配置并提供真实价格信息。支持EC2、EBS、S3、网络流量、负载均衡器、RDS、ElastiCache、Opensearch等AWS产品的实时报价。

## 项目结构
```
aws_pricing_assistant/
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

#### aws_pricing_agent
- **requirements_analyzer**: ✅ 已完成 - [文档](agents/aws_pricing_agent/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](agents/aws_pricing_agent/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](agents/aws_pricing_agent/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](agents/aws_pricing_agent/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](agents/aws_pricing_agent/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](agents/aws_pricing_agent/agent_code_developer.json)
- **agent_developer_manager**: ⏳ 待完成

## 附加信息
# AWS产品报价助手

## 项目概述
AWS产品报价助手是一个专业的云计算配置推荐与报价系统，能够根据用户提供的自然语言描述的配置需求或其他云平台账单，分析并推荐合理的AWS配置方案，并提供准确的价格信息。该系统支持多种AWS产品的实时报价，能够根据不完整的需求描述进行智能推断，并生成专业的销售报价方案。

## 项目状态
- **状态**: 已完成
- **版本**: 1.0.0
- **完成日期**: 2025-09-11

### 开发阶段状态
| 阶段 | 状态 | 完成日期 |
|------|------|----------|
| 需求分析 | ✅ 已完成 | 2025-09-11 |
| 系统架构设计 | ✅ 已完成 | 2025-09-11 |
| Agent设计 | ✅ 已完成 | 2025-09-11 |
| 提示词工程 | ✅ 已完成 | 2025-09-11 |
| 工具开发 | ✅ 已完成 | 2025-09-11 |
| Agent代码开发 | ✅ 已完成 | 2025-09-11 |
| Agent开发管理 | ✅ 已完成 | 2025-09-11 |

## 功能特点
1. **多AWS产品支持**:
   - EC2实例配置与报价
   - EBS存储配置与报价
   - S3对象存储配置与报价
   - 网络流量费用计算
   - 负载均衡器(ALB/NLB/CLB)配置与报价
   - RDS数据库配置与报价
   - ElastiCache缓存配置与报价
   - Opensearch服务配置与报价

2. **智能配置推荐**:
   - 从不完整或模糊的描述中推测合理配置
   - 根据AWS最佳实践推荐配置方案
   - 避免在生产环境中推荐t系列实例(除非用户明确指定)
   - 基于用户需求进行合理的资源规划

3. **实时价格查询**:
   - 通过AWS Pricing API获取最新价格数据
   - 支持按需实例和预留实例(RI)价格计算
   - 支持全球各区域报价，包括中国区
   - 处理API不可用等异常情况

4. **专业报价生成**:
   - 生成清晰、结构化的销售报价方案
   - 使用中文输出报价文档
   - 包含资源配置详情、单价、数量、小计和总计
   - 对无法获取价格的资源进行明确标注

## 项目结构
```
aws_pricing_assistant/
├── agents/
│   ├── aws_pricing_agent/
│   │   ├── requirements_analyzer.json  # 需求分析文档
│   │   ├── system_architect.json       # 系统架构设计文档
│   │   ├── agent_designer.json         # Agent设计文档
│   │   ├── prompt_engineer.json        # 提示词工程文档
│   │   ├── tools_developer.json        # 工具开发文档
│   │   └── agent_code_developer.json   # Agent代码开发文档
│   └── generated_agents/
│       └── aws_pricing_assistant/
│           └── aws_pricing_agent.py     # 生成的Agent代码
├── prompts/
│   └── generated_agents_prompts/
│       └── aws_pricing_assistant/
│           └── aws_pricing_agent.yaml   # 生成的提示词模板
├── tools/
│   └── generated_tools/
│       └── aws_pricing_assistant/
│           ├── __init__.py              # 工具包初始化文件
│           ├── aws_pricing_api.py       # AWS价格API交互工具
│           ├── aws_recommendation.py    # AWS配置推荐工具
│           ├── aws_sales_proposal.py    # 销售报价生成工具
│           └── aws_utils.py             # 通用工具函数
├── config.yaml                          # 项目配置文件
├── README.md                            # 项目说明文档
└── status.yaml                          # 项目状态跟踪文件
```

## 使用方式
AWS产品报价助手可以通过以下方式使用：

1. **直接询问配置需求**:
   ```
   请为我推荐一个适合运行生产环境数据库的AWS配置，需要4核CPU，16GB内存，MySQL数据库，100GB存储空间。
   ```

2. **提供其他云平台账单或IDC配置清单**:
   ```
   服务器实例
   CPU    内存    操作系统    付费类型    数量
   8核    16G    Linux/UNIX    无前期费用(标准1年)    1
   4核    16G    Linux/UNIX    按需实例    1
   ...
   
   主机存储
   存储容量配置    其他配置
   500GB    无特殊要求
   ...
   ```

3. **指定区域和付费类型**:
   ```
   请帮我在中国区为一个Web应用生成AWS配置报价，需要2台应用服务器和1个MySQL数据库，使用预留实例1年期付费方式。
   ```

## 注意事项
1. 系统通过AWS API获取实时价格数据，如遇API不可用情况，部分价格可能无法获取。
2. 在生产环境中，系统默认避免推荐t系列实例，除非用户明确指定。
3. 对于不完整的需求描述，系统会进行合理推测，但可能需要用户确认。
4. 中国区AWS服务可能与全球区域有所不同，系统会考虑这些差异。
5. 价格信息随时可能变动，系统提供的是查询时的最新价格。

## 技术实现
AWS产品报价助手基于以下技术实现：
- **框架**: Strands SDK
- **模型**: Claude 3.7 Sonnet
- **API集成**: AWS Pricing API, AWS SDK for Python (boto3)
- **语言**: Python 3.13+
- **架构**: 单Agent架构，集中处理所有报价相关功能

## 开发团队
由Nexus-AI平台自动生成，包括：
- 需求分析师
- 系统架构师
- Agent设计师
- 提示词工程师
- 工具开发工程师
- Agent代码开发工程师
- Agent开发管理器

## 后续优化方向
1. 添加更多AWS服务的支持，如Lambda、DynamoDB等
2. 实现历史价格趋势分析功能
3. 添加竞品价格对比分析
4. 开发长期成本预测与TCO分析功能
5. 优化配置推荐算法，提高准确性
6. 增强处理复杂配置需求的能力

---
*最后更新时间: 2025-09-11 06:41:04 UTC*

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-09-11 06:41:45 UTC*
