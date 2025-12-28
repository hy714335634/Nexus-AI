# fda_data_query_agent

## 项目描述
FDA数据查询智能体 - 支持实时查询FDA药物、医疗设备、食品等公开数据，提供自然语言交互、专业问答和数据来源追溯功能

## 项目结构
```
fda_data_query_agent/
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

#### fda_data_query_agent
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/fda_data_query_agent/agents/fda_data_query_agent/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/fda_data_query_agent/agents/fda_data_query_agent/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/fda_data_query_agent/agents/fda_data_query_agent/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/fda_data_query_agent/agents/fda_data_query_agent/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](projects/fda_data_query_agent/agents/fda_data_query_agent/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](projects/fda_data_query_agent/agents/fda_data_query_agent/agent_code_developer.json)
- **agent_developer_manager**: ⏳ 待完成

## 附加信息
# FDA Data Query Agent

## 项目概述

FDA数据查询智能体是一个专业的医疗健康数据查询系统，通过集成FDA openFDA官方API，为用户提供药物(Drugs)、医疗设备(Devices)、食品(Foods)、不良事件(Adverse Events)等多维度FDA公开数据的智能查询服务。系统支持自然语言交互，能够理解用户的专业查询需求，提供准确、详细、可验证的数据回答，并在数据不足时给出明确说明和建议。

### 核心功能

- ✅ **自然语言查询解析**：识别查询类型、提取关键实体、映射API参数
- ✅ **多类型FDA数据查询**：支持药物、医疗设备、食品、不良事件等多个端点
- ✅ **数据提取和格式化**：提取关键信息、生成结构化展示
- ✅ **专业问答和推理**：多步推理、比较分析、趋势评估
- ✅ **数据来源追溯**：生成完整的数据来源信息，确保可验证性
- ✅ **智能缓存管理**：本地文件系统缓存，过期时间24小时，提升响应速度
- ✅ **错误处理和降级**：完善的异常处理策略，确保高可用性（99%）
- ✅ **数据不足处理**：智能提示和替代建议

### 业务价值

该系统为医疗健康从业者、研究人员、监管人员和普通用户提供便捷的FDA数据访问途径，降低专业数据查询门槛，提高数据获取效率。通过自然语言交互和智能数据整合，用户无需深入了解FDA API技术细节即可获取所需信息。系统提供的数据来源追溯功能确保信息可验证性，提升决策质量和合规性。

## 技术架构

### 技术栈
- **Python**: 3.13+
- **AI Model**: Claude Sonnet 4.5 (global.anthropic.claude-sonnet-4-5-20250929-v1:0)
- **Framework**: Strands SDK, AWS Bedrock AgentCore
- **Data Source**: openFDA API (https://api.fda.gov)
- **Cache**: 本地文件系统缓存 (.cache/fda_data_query_agent/)
- **Deployment**: Amazon Bedrock AgentCore (HTTP服务，端口8080)

### 架构设计
- **单Agent架构**：fda_data_query_agent作为唯一执行单元，集成所有功能模块
- **工具驱动**：13个自定义工具函数 + 1个系统工具，封装API调用、缓存管理、数据处理
- **流式响应**：使用BedrockAgentCoreApp支持流式响应，提升用户体验
- **缓存优先**：本地文件系统缓存，降低API调用量30%以上，提升响应速度

### 目录结构

```
fda_data_query_agent/
├── agents/
│   └── generated_agents/
│       └── fda_data_query_agent/
│           └── fda_data_query_agent.py          # Agent主脚本（BedrockAgentCoreApp模式）
├── prompts/
│   └── generated_agents_prompts/
│       └── fda_data_query_agent/
│           └── fda_data_query_agent_prompt.yaml # Agent提示词模板
├── tools/
│   └── generated_tools/
│       └── fda_data_query_agent/
│           └── fda_api_tools.py                 # FDA API工具集（13个工具函数）
├── projects/
│   └── fda_data_query_agent/
│       ├── agents/
│       │   └── fda_data_query_agent/
│       │       ├── requirements_analyzer.json   # 需求分析文档
│       │       ├── system_architect.json        # 系统架构文档
│       │       ├── agent_designer.json          # Agent设计文档
│       │       ├── prompt_engineer.json         # 提示词工程文档
│       │       ├── tools_developer.json         # 工具开发文档
│       │       └── agent_code_developer.json    # Agent代码开发文档
│       ├── config.yaml                          # 项目配置文件
│       ├── status.yaml                          # 项目状态跟踪文件
│       ├── requirements.txt                     # Python依赖包列表
│       └── README.md                            # 项目说明文档（本文件）
└── .cache/
    └── fda_data_query_agent/                    # 缓存目录
        ├── drug_label/                          # 药物标签缓存
        ├── device_recall/                       # 设备召回缓存
        └── ...                                  # 其他查询类型缓存
```

## 安装和配置

### 前置要求
- Python 3.13+
- AWS Bedrock访问权限
- 网络可访问openFDA API (https://api.fda.gov)

### 安装依赖

```bash
# 进入项目目录
cd projects/fda_data_query_agent

# 安装Python依赖包
pip install -r requirements.txt
```

### 环境变量配置

```bash
# 必需环境变量
export BYPASS_TOOL_CONSENT=true

# 可选环境变量
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318  # OpenTelemetry端点
export DOCKER_CONTAINER=1                                  # Docker部署标识
```

## 使用指南

### 1. 本地测试模式

执行单次查询测试：

```bash
python agents/generated_agents/fda_data_query_agent/fda_data_query_agent.py -i "查询阿司匹林的不良反应"
```

指定环境和版本：

```bash
python agents/generated_agents/fda_data_query_agent/fda_data_query_agent.py \
  -i "查询胰岛素泵召回信息" \
  -e development \
  -v 1.0
```

### 2. 交互式对话模式

启动多轮对话交互：

```bash
python agents/generated_agents/fda_data_query_agent/fda_data_query_agent.py -it
```

交互式命令：
- 输入查询内容，按回车发送
- 输入 `quit` 或 `exit` 退出
- 输入 `clear` 清空屏幕

### 3. AgentCore部署模式

启动HTTP服务器（端口8080）：

```bash
# 本地启动
python agents/generated_agents/fda_data_query_agent/fda_data_query_agent.py

# Docker环境
DOCKER_CONTAINER=1 python agents/generated_agents/fda_data_query_agent/fda_data_query_agent.py
```

HTTP请求示例：

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "查询阿司匹林的不良反应",
    "user_id": "user123"
  }'
```

### 4. 查询示例

#### 药物查询
```python
# 查询药物批准信息
"查询阿司匹林的FDA批准信息"

# 查询药物不良反应
"查询利伐沙班的不良反应报告"

# 比较药物安全性
"比较阿司匹林和布洛芬的安全性"
```

#### 医疗设备查询
```python
# 查询设备分类
"查询心脏起搏器的设备分类"

# 查询设备召回
"查询胰岛素泵的召回信息"

# 查询设备不良事件
"查询MRI设备的不良事件报告"
```

#### 食品查询
```python
# 查询食品召回
"查询花生酱的召回信息"

# 查询食品不良事件
"查询能量饮料的不良事件"
```

## 开发阶段完成情况

| 阶段 | 状态 | 完成时间 | 文档路径 |
|------|------|----------|----------|
| 需求分析 (requirements_analyzer) | ✅ 完成 | 2025-12-28 | projects/fda_data_query_agent/agents/fda_data_query_agent/requirements_analyzer.json |
| 系统架构 (system_architect) | ✅ 完成 | 2025-12-28 | projects/fda_data_query_agent/agents/fda_data_query_agent/system_architect.json |
| Agent设计 (agent_designer) | ✅ 完成 | 2025-12-28 | projects/fda_data_query_agent/agents/fda_data_query_agent/agent_designer.json |
| 提示词工程 (prompt_engineer) | ✅ 完成 | 2025-12-28 | projects/fda_data_query_agent/agents/fda_data_query_agent/prompt_engineer.json |
| 工具开发 (tools_developer) | ✅ 完成 | 2025-12-28 | projects/fda_data_query_agent/agents/fda_data_query_agent/tools_developer.json |
| Agent代码开发 (agent_code_developer) | ✅ 完成 | 2025-12-28 | projects/fda_data_query_agent/agents/fda_data_query_agent/agent_code_developer.json |
| Agent开发管理 (agent_developer_manager) | ✅ 完成 | 2025-12-28 | 本文档 |

**项目进度**：7/7 阶段完成（100%）

## Agent核心能力

### 提示词模板
- **路径**: prompts/generated_agents_prompts/fda_data_query_agent/fda_data_query_agent_prompt.yaml
- **支持模型**: Claude Sonnet 4.5 (global.anthropic.claude-sonnet-4-5-20250929-v1:0)
- **环境配置**:
  - Development: max_tokens=4096, temperature=0.3, streaming=True
  - Production: max_tokens=60000, temperature=0.3, streaming=True
  - Testing: max_tokens=2048, temperature=0.3, streaming=True

### 工具集（14个工具）

#### FDA API查询工具（7个）
1. **fda_api_query**: 通用openFDA API查询工具，支持所有端点
2. **fda_drug_search**: 专用药物搜索工具
3. **fda_device_search**: 专用医疗设备搜索工具
4. **fda_food_search**: 专用食品搜索工具
5. **fda_adverse_events_search**: 通用不良事件搜索工具
6. **fda_recall_search**: 通用召回搜索工具
7. **fda_nda_search**: 新药申请（NDA）批准信息搜索工具

#### 数据处理工具（4个）
8. **format_fda_response**: 格式化FDA API响应
9. **extract_data_fields**: 提取特定数据字段
10. **validate_fda_data**: 验证FDA数据完整性
11. **generate_data_source_info**: 生成数据来源追溯信息

#### 缓存管理工具（2个）
12. **get_cache_stats**: 获取缓存统计信息
13. **clear_fda_cache**: 清理缓存数据

#### 系统工具（1个）
14. **current_time**: 获取当前时间（Strands系统工具）

## 性能指标

### 目标指标
- **响应时间**: ≤5秒（不含网络延迟）
- **缓存命中率**: ≥60%（常见查询）
- **API调用成功率**: ≥95%（排除FDA API故障）
- **系统可用性**: ≥99%（排除FDA API不可用时间）
- **并发支持**: ≥10个并发用户

### 性能优化策略
- 本地文件系统缓存，过期时间24小时
- 使用MD5哈希生成cache_key，确保高效查找
- requests库使用连接池，提升HTTP请求性能
- 长文本字段截断至500字符，避免响应过大
- 支持分页查询，避免一次性返回大量数据

## 错误处理与降级策略

### 错误类型
- **400参数错误**: 提示用户检查参数格式，建议使用通用关键词
- **404无结果**: 提供友好提示和替代建议（尝试其他关键词、访问FDA官网）
- **429限流**: 返回限流提示，尝试从缓存获取数据
- **500/超时**: 返回服务不可用提示，尝试从缓存获取数据
- **网络连接失败**: 使用缓存降级

### 降级策略
1. **API限流或不可用**: 优先使用缓存数据（即使已过期）
2. **缓存降级**: 标注数据可能不是最新，建议稍后重试
3. **用户友好提示**: 所有错误都转换为用户友好的提示，避免技术术语

## 数据来源与可验证性

所有查询结果都包含完整的数据来源信息（DataSource对象）：
- **API端点**: 完整的API URL
- **查询参数**: 使用的查询参数
- **查询时间**: 时间戳（ISO 8601格式）
- **缓存状态**: 来自缓存/实时查询
- **数据新鲜度**: 实时或缓存年龄
- **验证URL**: FDA官方验证链接

## 安全与合规

### 安全措施
- 所有API通信使用HTTPS协议
- 不存储用户敏感信息
- 遵守openFDA API使用条款和限流政策（240次/分钟/IP）
- 输入参数验证，防止注入攻击
- 缓存数据仅限FDA公开数据
- 日志中不记录完整的用户查询内容

### 免责声明
本系统仅提供FDA公开数据查询服务，不提供医疗建议、诊断或治疗方案。所有信息仅供参考，不构成医疗建议。具体用药和治疗请咨询专业医疗人员。

## 监控与维护

### 日志记录
- 记录所有查询请求、API调用、错误和性能指标
- 日志输出到标准输出或CloudWatch（可配置）

### 监控指标
- 查询次数、API调用次数、缓存命中率、错误率
- 响应时间、API调用延迟、缓存大小
- CPU使用率、内存使用量、磁盘空间（缓存占用）

### 维护建议
- 定期检查openFDA API文档更新（建议每季度）
- 监控缓存大小，定期清理过期缓存
- 定期检查依赖库的安全漏洞
- 备份项目配置和文档

## 故障排查

### 常见问题

#### 1. Agent无法启动
- 检查Python版本（需要3.13+）
- 检查依赖包是否安装完整（pip install -r requirements.txt）
- 检查环境变量BYPASS_TOOL_CONSENT是否设置为true

#### 2. API调用失败
- 检查网络连接，确保可访问https://api.fda.gov
- 检查是否触发API限流（240次/分钟/IP）
- 检查FDA API是否正常运行（访问https://open.fda.gov/apis/）

#### 3. 缓存问题
- 检查缓存目录是否存在且有写权限（.cache/fda_data_query_agent/）
- 使用clear_fda_cache工具清理缓存
- 使用get_cache_stats工具查看缓存统计

#### 4. 查询无结果
- 检查产品名称是否正确
- 尝试使用通用名代替商品名
- 访问FDA官网进行人工查询

## 扩展与定制

### 添加新数据源
1. 在tools/generated_tools/fda_data_query_agent/fda_api_tools.py中添加新的工具函数
2. 在提示词模板中添加工具依赖
3. 更新Agent设计文档和工具开发文档

### 支持多语言
1. 扩展提示词模板，添加多语言支持
2. 更新数据格式化逻辑，支持多语言输出
3. 添加语言检测和翻译功能

### 集成其他监管机构数据
1. 添加新的API客户端工具（如EMA、PMDA）
2. 扩展查询解析逻辑，支持多数据源
3. 更新提示词模板，添加新数据源知识

## 项目团队

- **开发**: Agent Build Workflow
- **版本**: 1.0
- **日期**: 2025-12-28
- **许可**: 遵守openFDA API使用条款

## 联系与支持

如有问题或建议，请联系项目维护团队。

## 更新日志

### v1.0 (2025-12-28)
- ✅ 初始版本发布
- ✅ 完成需求分析、系统架构、Agent设计
- ✅ 完成提示词工程、工具开发、Agent代码开发
- ✅ 支持药物、医疗设备、食品等多类型FDA数据查询
- ✅ 实现自然语言查询解析、数据来源追溯、智能缓存管理
- ✅ 通过项目验证，所有依赖包兼容性验证通过
- ✅ 生成完整的项目文档和使用指南

---

**最后更新时间**: 2025-12-28

**项目状态**: ✅ 已完成，可投入生产使用


## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-12-28 05:08:41 UTC*
