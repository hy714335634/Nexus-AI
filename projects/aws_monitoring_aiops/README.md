# aws_monitoring_aiops

## 项目描述
AWS CloudWatch智能监控与AIOps系统，用于自动监控指标、分析日志并生成自愈脚本

## 项目结构
```
aws_monitoring_aiops/
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
- **requirements_analyzer**: ⏳ 待完成 - [文档](agents/aws_monitoring_aiops_agent/requirements_analyzer.json)
- **system_architect**: ⏳ 待完成
- **agent_designer**: ⏳ 待完成
- **prompt_engineer**: ⏳ 待完成
- **tools_developer**: ⏳ 待完成
- **agent_code_developer**: ⏳ 待完成
- **agent_developer_manager**: ⏳ 待完成

## 附加信息
# AWS监控与AIOps智能体

## 项目概述
该项目旨在创建一个智能监控与AIOps功能的Agent，用于自动监控AWS CloudWatch指标、分析日志并生成自愈脚本。系统能够实时监控AWS资源，检测异常，进行根因分析，并提供修复建议。

## 用户原始需求

### 核心功能要求

- **监控指标获取**：Agent需要能够访问AWS CloudWatch，实时或定期拉取关键监控指标（CPU使用率、内存使用率、错误率、延迟、请求数等）
- **异常检测**：基于配置的阈值或智能算法（如统计分析、机器学习）自动检测指标异常和告警事件
- **多维度监控**：支持监控EC2实例、Lambda函数、RDS数据库、ECS容器、API Gateway、ALB/ELB等多种AWS服务
- **根因分析**：当检测到问题时，自动查询对应服务的CloudWatch Logs，分析日志内容以确定根本原因
- **日志深度分析**：支持日志过滤、关键词提取、错误堆栈分析、时间序列关联分析等，找出导致问题的具体错误或异常模式
- **上下文关联**：分析问题发生前后的相关日志和指标变化，建立因果关系链
- **自愈脚本生成**：基于根因分析结果，自动生成针对性的修复脚本（Shell、Python、AWS CLI命令等），但不自动执行，需人工审核
- **脚本类型多样**：支持生成重启服务、扩容资源、清理缓存、回滚配置、修改安全组规则等不同类型的修复脚本
- **历史记录与缓存**：每次分析任务生成唯一ID，缓存监控数据、日志分析结果和生成的脚本，支持断点续传和历史查询
- **增量处理**：避免重复分析已处理的告警，通过任务ID追踪处理进度
- **输出格式化报告**：生成结构化的分析报告（JSON/Markdown格式），包含：问题摘要、受影响资源、根因分析、推荐操作、自愈脚本

### 技术实现要求

- **集成多种监控方式**：
  - AWS CloudWatch API（获取指标和告警）
  - CloudWatch Logs Insights（结构化日志查询）
  - CloudWatch Logs API（流式日志获取）
- **支持多区域监控**：可配置监控多个AWS区域（us-east-1、us-west-2、ap-northeast-1等）
- **智能日志查询**：根据告警类型自动构建合适的Logs Insights查询语句，提取关键错误信息
- **LLM增强分析**：利用大语言模型理解复杂日志内容，识别非结构化错误信息，生成人类可读的分析结论
- **分批处理机制**：如果监控资源数量很多，支持分批处理避免超时或token限制
- **配置驱动**：支持通过配置文件定义监控范围、阈值、检查频率等参数

### 输出要求

- **实时告警通知**：检测到问题时立即输出告警摘要
- **详细分析报告**：包含时间线、指标图表链接、日志摘要、根因推断
- **自愈脚本文件**：每个问题生成独立的脚本文件（如fix_high_cpu_i-12345_20250103.sh）
- **执行说明**：为每个脚本提供清晰的使用说明、前置条件检查和风险提示
- **Markdown总结**：最终生成完整的AIOps运行报告，汇总所有发现的问题和建议操作

### 重要信息

- **AWS凭证配置**：需要提供AWS Access Key ID、Secret Access Key和默认Region，或使用IAM Role进行认证
- **IAM权限要求**：Agent需要以下权限：
  - cloudwatch:GetMetricData、cloudwatch:DescribeAlarms
  - logs:FilterLogEvents、logs:StartQuery、logs:GetQueryResults
  - 相关服务的只读权限（ec2:Describe*、lambda:Get*等）
- **大规模监控**：如果监控的资源数量非常多（数百个实例/服务），需要：
  - 实现分页和分批处理
  - 使用缓存避免重复查询
  - 设置优先级，优先处理关键服务
- **时间窗口**：可配置监控的时间范围（如最近5分钟、1小时），日志查询时间窗口建议不超过24小时
- **成本控制**：CloudWatch Logs Insights查询有成本，建议设置每次查询的日志数据量上限
- **脚本审核机制**：生成的自愈脚本必须经过人工审核才能执行，避免自动化操作引入新问题
- **安全考虑**：
  - 敏感信息（如密码、密钥）不应出现在日志或报告中
  - 生成的脚本应包含安全检查和回滚机制
  - 对生产环境的操作需要额外的确认步骤
- **持续监控模式**：Agent可以运行在两种模式：
  - 一次性分析：响应特定告警进行根因分析
  - 持续监控：定期轮询CloudWatch，主动发现问题

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-11-09 07:36:16 UTC*
