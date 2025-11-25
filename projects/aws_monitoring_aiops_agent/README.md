# aws_monitoring_aiops_agent

## 项目描述
智能监控与AIOps Agent，自动监控AWS CloudWatch指标、分析日志并生成自愈脚本

## 项目结构
```
aws_monitoring_aiops_agent/
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

#### aws_monitoring_aiops_agent
- **requirements_analyzer**: ✅ 已完成 - [文档](agents/aws_monitoring_aiops_agent/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](agents/aws_monitoring_aiops_agent/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](agents/aws_monitoring_aiops_agent/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](agents/aws_monitoring_aiops_agent/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](agents/aws_monitoring_aiops_agent/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](agents/aws_monitoring_aiops_agent/agent_code_developer.json)
- **agent_developer_manager**: ✅ 已完成 - [文档](agents/aws_monitoring_aiops_agent/agent_developer_manager.json)

## 附加信息
# AWS 监控与 AIOps Agent

## 项目概述

AWS 监控与 AIOps Agent 是一个智能监控系统，能够自动监控 AWS CloudWatch 指标、分析日志数据，检测异常，进行根因分析，并生成自愈脚本，帮助运维团队快速响应和解决 AWS 环境中的问题。

## 核心功能

- **监控指标获取**：实时或定期拉取 AWS CloudWatch 关键监控指标（CPU 使用率、内存使用率、错误率、延迟、请求数等）
- **异常检测**：基于配置的阈值或智能算法自动检测指标异常和告警事件
- **多维度监控**：支持监控 EC2 实例、Lambda 函数、RDS 数据库、ECS 容器、API Gateway、ALB/ELB 等多种 AWS 服务
- **根因分析**：当检测到问题时，自动查询对应服务的 CloudWatch Logs，分析日志内容以确定根本原因
- **日志深度分析**：支持日志过滤、关键词提取、错误堆栈分析、时间序列关联分析等，找出导致问题的具体错误或异常模式
- **上下文关联**：分析问题发生前后的相关日志和指标变化，建立因果关系链
- **自愈脚本生成**：基于根因分析结果，自动生成针对性的修复脚本（Shell、Python、AWS CLI 命令等），但不自动执行，需人工审核
- **历史记录与缓存**：每次分析任务生成唯一 ID，缓存监控数据、日志分析结果和生成的脚本，支持断点续传和历史查询
- **输出格式化报告**：生成结构化的分析报告（JSON/Markdown 格式），包含问题摘要、受影响资源、根因分析、推荐操作、自愈脚本

## 技术实现

- **集成多种监控方式**：
  - AWS CloudWatch API（获取指标和告警）
  - CloudWatch Logs Insights（结构化日志查询）
  - CloudWatch Logs API（流式日志获取）
- **支持多区域监控**：可配置监控多个 AWS 区域
- **智能日志查询**：根据告警类型自动构建合适的 Logs Insights 查询语句，提取关键错误信息
- **LLM 增强分析**：利用大语言模型理解复杂日志内容，识别非结构化错误信息，生成人类可读的分析结论
- **分批处理机制**：支持分批处理避免超时或 token 限制
- **配置驱动**：支持通过配置文件定义监控范围、阈值、检查频率等参数

## 项目结构

```
aws_monitoring_aiops_agent/
├── agents/
│   └── generated_agents/
│       └── aws_monitoring_aiops_agent/
│           └── aws_monitoring_aiops_agent.py  # 主 Agent 代码
├── generated_agents_prompts/
│   └── aws_monitoring_aiops_agent/
│       └── aws_monitoring_aiops_agent.yaml    # Agent 提示词模板
├── generated_tools/
│   └── aws_monitoring_aiops_agent/
│       ├── aws_cloudwatch_tools.py            # CloudWatch 相关工具
│       ├── log_analysis_tools.py              # 日志分析工具
│       └── task_cache_tools.py                # 任务管理和缓存工具
├── config.yaml                                # 项目配置文件
├── README.md                                  # 项目说明文档
└── requirements.txt                           # Python 依赖库
```

## 运行模式

Agent 支持两种运行模式：

1. **一次性分析模式**：响应特定告警进行根因分析
2. **持续监控模式**：定期轮询 CloudWatch，主动发现问题

## 使用方法

### 前提条件

- Python 3.8 或更高版本
- AWS 账户和适当的 IAM 权限
- 已配置的 AWS 凭证（Access Key ID 和 Secret Access Key）或 IAM Role

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

创建配置文件（例如 `config.yaml`）：

```yaml
aws:
  regions:
    - us-east-1
    - us-west-2
  credentials:
    use_iam_role: true  # 或者设置为 false 并提供 access_key 和 secret_key

monitoring:
  services:
    - type: ec2
      resources: ["i-12345678", "i-87654321"]
    - type: rds
      resources: ["my-database-1", "my-database-2"]
    - type: lambda
      resources: ["function-1", "function-2"]
  
  metrics:
    ec2:
      - name: CPUUtilization
        namespace: AWS/EC2
        threshold: 80
        period: 300
    rds:
      - name: CPUUtilization
        namespace: AWS/RDS
        threshold: 75
        period: 300

analysis:
  time_window: 6  # 小时
  log_query_limit: 10000  # 日志条数限制
  cache_retention: 30  # 天
```

### 运行

#### 一次性分析模式

```bash
python -m aws_monitoring_aiops_agent --config config.yaml --alarm-id "arn:aws:cloudwatch:us-east-1:123456789012:alarm:HighCPUAlarm" --description "高 CPU 使用率告警" --resources "i-12345678,i-87654321" --time-window 6
```

#### 持续监控模式

```bash
python -m aws_monitoring_aiops_agent --config config.yaml --resources-file resources.json --duration 60
```

其中 `resources.json` 包含要监控的资源列表：

```json
{
  "ec2": ["i-12345678", "i-87654321"],
  "rds": ["my-database-1", "my-database-2"],
  "lambda": ["function-1", "function-2"]
}
```

## 输出

Agent 将生成以下输出：

1. **告警通知**：检测到问题时的实时告警
2. **分析报告**：包含时间线、指标图表链接、日志摘要、根因推断的详细报告（Markdown 格式）
3. **自愈脚本**：针对检测到的问题生成的修复脚本，包含执行说明和风险提示
4. **总结报告**：汇总所有发现的问题和建议操作的 Markdown 报告

## 注意事项

- **AWS 权限**：Agent 需要以下 AWS 权限：
  - `cloudwatch:GetMetricData`、`cloudwatch:DescribeAlarms`
  - `logs:FilterLogEvents`、`logs:StartQuery`、`logs:GetQueryResults`
  - 相关服务的只读权限（`ec2:Describe*`、`lambda:Get*` 等）
- **成本控制**：CloudWatch Logs Insights 查询有成本，建议设置查询数据量上限
- **脚本审核**：生成的自愈脚本必须经过人工审核才能执行，避免自动化操作引入新问题
- **安全考虑**：
  - 敏感信息不会出现在日志或报告中
  - 生成的脚本包含安全检查和回滚机制
  - 对生产环境的操作需要额外的确认步骤

## 开发状态

项目开发已完成，所有阶段均已完成：

- [x] 需求分析
- [x] 系统架构设计
- [x] Agent 设计
- [x] 提示词工程
- [x] 工具开发
- [x] Agent 代码开发
- [x] 开发管理

## 许可证

[MIT License](LICENSE)

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-11-09 09:00:11 UTC*
