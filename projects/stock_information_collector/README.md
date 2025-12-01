# stock_information_collector

## 项目描述
AI智能体项目：stock_information_collector，用于收集股票信息并提供评价

## 项目结构
```
stock_information_collector/
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

#### stock_information_collector
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/stock_information_collector/agents/stock_information_collector/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/stock_information_collector/agents/stock_information_collector/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/stock_information_collector/agents/stock_information_collector/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/stock_information_collector/agents/stock_information_collector/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](projects/stock_information_collector/agents/stock_information_collector/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](projects/stock_information_collector/agents/stock_information_collector/agent_code_developer.json)
- **agent_developer_manager**: ⏳ 待完成

## 附加信息
# 股票信息收集与评价Agent项目文档

## 📋 项目概述

**stock_information_collector** 是一个专业的AI智能体项目，用于自动收集股票信息并提供综合评价。该Agent能够根据用户提供的股票名称或代码，自动收集相关的股票信息（包括基本面数据、市场表现、新闻资讯等），并基于收集到的信息给出综合评价和投资建议。

### 🎯 核心功能

- ✅ **多市场支持**：支持A股、港股、美股市场的股票查询
- ✅ **股票识别**：支持股票代码和公司名称两种查询方式
- ✅ **基本信息收集**：获取公司基本信息（名称、行业、市值等）
- ✅ **实时行情数据**：收集股票的实时价格、涨跌幅、成交量等
- ✅ **财务数据分析**：获取PE、PB、ROE、营收增长等关键指标
- ✅ **新闻资讯整合**：收集与股票相关的最新新闻
- ✅ **综合评价报告**：基于多维度数据生成投资评价和建议
- ✅ **智能缓存管理**：减少API调用，加快查询速度

### 📊 项目信息

| 项目 | 说明 |
|------|------|
| **项目名称** | stock_information_collector |
| **项目版本** | 1.0.0 |
| **Agent数量** | 1 |
| **开发阶段** | 6/7 完成 |
| **当前状态** | 待项目管理审核 |
| **创建时间** | 2025-11-28 |

## 📁 项目目录结构

```
stock_information_collector/
├── agents/
│   └── generated_agents/
│       └── stock_information_collector/
│           └── stock_information_collector.py        # Agent主代码
├── prompts/
│   └── generated_agents_prompts/
│       └── stock_information_collector/
│           └── stock_information_collector.yaml      # 提示词配置
├── tools/
│   └── generated_tools/
│       └── stock_information_collector/
│           └── stock_tools.py                        # 工具实现
├── projects/
│   └── stock_information_collector/
│       ├── agents/
│       │   └── stock_information_collector/
│       │       ├── requirements_analyzer.json        # 需求分析文档
│       │       ├── system_architect.json             # 系统架构文档
│       │       ├── agent_designer.json               # Agent设计文档
│       │       ├── prompt_engineer.json              # 提示词设计文档
│       │       ├── tools_developer.json              # 工具开发文档
│       │       ├── agent_code_developer.json         # 代码开发文档
│       │       └── agent_developer_manager.json      # 项目审核文档（待生成）
│       ├── config.yaml                               # 项目配置
│       ├── README.md                                 # 项目说明（本文件）
│       ├── status.yaml                               # 项目状态
│       ├── requirements.txt                          # Python依赖
│       └── track.md                                  # 开发追踪
```

## 🏗️ Agent架构

### Agent设计

**Agent名称**：stock_information_collector  
**Agent类型**：数据分析类 + 网络工具类（混合型）  
**模型**：Claude Sonnet 4.5 (global.anthropic.claude-sonnet-4-5-20250929-v1:0)  
**运行环境**：Production / Development / Testing

### 核心工具集

Agent集成了5个专用工具用于数据收集和处理：

| 工具 | 功能 | 用途 |
|------|------|------|
| **stock_query_tool** | 股票查询和基本信息获取 | 识别股票、获取公司基本信息 |
| **market_data_tool** | 实时行情数据获取 | 收集股票价格、涨跌幅、成交量等 |
| **financial_data_tool** | 财务数据和关键指标获取 | 获取PE、PB、ROE等财务指标 |
| **news_collection_tool** | 股票相关新闻收集 | 收集最新的股票相关新闻资讯 |
| **cache_manager_tool** | 数据缓存管理 | 管理缓存数据，减少API调用 |

### 系统工具

- **strands_tools/current_time**：获取当前时间
- **strands_tools/calculator**：数学计算工具

### 工作流程

```
用户输入（股票名称/代码）
         ↓
    [股票识别]
         ↓
  ┌──────┴──────┐
  ↓             ↓
基本信息 ← 缓存检查
  ↓
  ├─→ 行情数据 ──┐
  ├─→ 财务数据 ──┤
  ├─→ 新闻资讯 ──┼→ 数据整合
  └─→ 缓存管理 ──┘
  ↓
综合分析 & 评价生成
  ↓
投资建议输出
```

## 🚀 快速开始

### 环境要求

- **Python 版本**：3.13+
- **操作系统**：Linux / macOS / Windows
- **网络连接**：需要访问外部API

### 安装依赖

```bash
# 方式1：使用requirements.txt
pip install -r projects/stock_information_collector/requirements.txt

# 方式2：手动安装
pip install strands-agents strands-agents-tools bedrock-agentcore yfinance duckduckgo-search requests PyYAML
```

### 本地测试

#### 查询美股示例
```bash
python agents/generated_agents/stock_information_collector/stock_information_collector.py -i "AAPL"
```

#### 查询A股示例
```bash
python agents/generated_agents/stock_information_collector/stock_information_collector.py -i "000001"
```

#### 查询港股示例
```bash
python agents/generated_agents/stock_information_collector/stock_information_collector.py -i "00700"
```

#### 使用公司名称查询
```bash
python agents/generated_agents/stock_information_collector/stock_information_collector.py -i "苹果"
```

#### 高级选项
```bash
# 使用开发环境
python agents/generated_agents/stock_information_collector/stock_information_collector.py -e development -i "MSFT"

# 启用调试模式
python agents/generated_agents/stock_information_collector/stock_information_collector.py -i "AAPL" --debug

# 查看所有选项
python agents/generated_agents/stock_information_collector/stock_information_collector.py --help
```

## 📖 使用指南

### 命令行参数

| 参数 | 简写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--input` | `-i` | str | 无 | 股票名称或代码（必需） |
| `--env` | `-e` | str | production | 运行环境（production/development/testing） |
| `--version` | `-v` | str | latest | Agent版本 |
| `--model` | `-m` | str | claude-sonnet-4-5 | 使用的模型ID |
| `--debug` | 无 | flag | False | 启用调试模式 |

### 支持的市场

#### A股市场
- **上交所**：6位数字代码，60开头（如600000）
- **深交所**：6位数字代码，00/30开头（如000001、300001）
- **例子**：000001（平安银行）、600000（浦发银行）

#### 港股市场
- **港交所**：5位数字代码（如00700）
- **例子**：00700（腾讯）、00939（中国建筑）

#### 美股市场
- **纳斯达克/纽交所**：字母代码（如AAPL、MSFT）
- **例子**：AAPL（苹果）、TSLA（特斯拉）、MSFT（微软）

### 输出示例

系统返回的股票分析报告包括以下内容：

```markdown
# 股票分析报告

## 基本信息
- 股票代码：AAPL
- 公司名称：Apple Inc.
- 市场：美股
- 行业：消费电子
- 市值：3.2万亿美元

## 实时行情
- 当前价格：$182.50
- 涨跌幅：+2.35%
- 成交量：52.3M
- 52周高点：$199.62
- 52周低点：$124.17

## 关键财务指标
- 市盈率（PE）：28.5
- 市净率（PB）：45.2
- ROE：73.4%
- 营收增长：-5.2%
- 净利润增长：+6.8%

## 相关新闻
- [新闻标题1] - 发布时间
- [新闻标题2] - 发布时间
- [新闻标题3] - 发布时间

## 综合评价
### 估值分析
基于PE、PB等指标分析...

### 成长性分析
基于营收、利润增长分析...

### 财务健康度
基于负债率、现金流分析...

### 行业地位
基于市场份额、竞争优势分析...

### 风险评估
识别的主要风险...

## 投资建议
**评级**：持有 / 买入 / 观望 / 回避
**理由**：详细的投资理由...
**目标价格**：$195
**风险提示**：主要风险提示...

---
**免责声明**：本系统提供的信息仅供参考，不构成任何投资建议。投资决策需自行承担风险。
```

## 🔧 配置说明

### 环境变量

```bash
# 绕过工具同意确认（可选）
export BYPASS_TOOL_CONSENT=true

# Docker容器标识（部署时使用）
export DOCKER_CONTAINER=1
```

### 模型配置

在 `prompts/generated_agents_prompts/stock_information_collector/stock_information_collector.yaml` 中配置：

```yaml
environments:
  production:
    max_tokens: 60000          # 最大令牌数
    temperature: 0.3           # 温度参数（影响创意度）
    streaming: False           # 是否流式输出
  development:
    max_tokens: 4096
    temperature: 0.3
    streaming: False
```

### 缓存配置

缓存数据存储在 `.cache/stock_information_collector/` 目录：

| 数据类型 | 缓存时间 | 说明 |
|---------|---------|------|
| 基本信息 | 24小时 | 公司基本信息较少变化 |
| 行情数据 | 15分钟 | 行情数据实时性强 |
| 财务数据 | 7天 | 财务数据更新频率低 |
| 新闻资讯 | 1小时 | 新闻信息实时性高 |

## 📊 开发阶段进度

| 阶段 | 名称 | 状态 | 完成时间 | 输出文件 |
|------|------|------|---------|---------|
| 1 | 需求分析 | ✅ 完成 | 2025-11-28 09:43 | requirements_analyzer.json |
| 2 | 系统架构 | ✅ 完成 | 2025-11-28 09:45 | system_architect.json |
| 3 | Agent设计 | ✅ 完成 | 2025-11-28 09:48 | agent_designer.json |
| 4 | 提示词工程 | ✅ 完成 | 2025-11-28 09:55 | prompt_engineer.json |
| 5 | 工具开发 | ✅ 完成 | 2025-11-28 09:51 | tools_developer.json |
| 6 | Agent代码 | ✅ 完成 | 2025-11-28 09:57 | agent_code_developer.json |
| 7 | 项目管理 | 🔄 进行中 | - | agent_developer_manager.json |

## 🔍 文件完整性检查

### ✅ Agent代码文件
- **路径**：`agents/generated_agents/stock_information_collector/stock_information_collector.py`
- **状态**：✅ 存在且有效
- **大小**：约12KB
- **语法检查**：✅ 通过
- **特性**：
  - ✅ BedrockAgentCoreApp入口点
  - ✅ @app.entrypoint装饰的handler函数
  - ✅ 完整的错误处理
  - ✅ 详细的日志记录
  - ✅ 命令行参数支持

### ✅ 提示词配置文件
- **路径**：`prompts/generated_agents_prompts/stock_information_collector/stock_information_collector.yaml`
- **状态**：✅ 存在且有效
- **工具数量**：7个（5个自定义 + 2个系统工具）
- **模型支持**：Claude Sonnet 4.5
- **环境配置**：Production / Development / Testing

### ✅ 工具实现文件
- **路径**：`tools/generated_tools/stock_information_collector/stock_tools.py`
- **状态**：✅ 存在且有效
- **工具数量**：5个
- **功能**：
  - ✅ stock_query_tool - 股票查询
  - ✅ market_data_tool - 行情数据
  - ✅ financial_data_tool - 财务数据
  - ✅ news_collection_tool - 新闻收集
  - ✅ cache_manager_tool - 缓存管理

### ✅ 项目配置文件
- **config.yaml**：✅ 存在且有效
- **status.yaml**：✅ 存在且有效
- **requirements.txt**：✅ 存在且有效

### ✅ 开发文档
- **requirements_analyzer.json**：✅ 存在
- **system_architect.json**：✅ 存在
- **agent_designer.json**：✅ 存在
- **prompt_engineer.json**：✅ 存在
- **tools_developer.json**：✅ 存在
- **agent_code_developer.json**：✅ 存在

## 🔗 Python依赖验证

所有Python依赖已验证兼容性：

| 包名 | 版本 | Python要求 | 兼容性 | PyPI链接 |
|------|------|-----------|--------|---------|
| strands-agents | 1.18.0 | >=3.10 | ✅ 兼容 | [link](https://pypi.org/project/strands-agents/) |
| bedrock-agentcore | 1.0.7 | >=3.10 | ✅ 兼容 | [link](https://pypi.org/project/bedrock-agentcore/) |
| yfinance | 0.2.66 | 未指定 | ✅ 兼容 | [link](https://pypi.org/project/yfinance/) |
| duckduckgo-search | 8.1.1 | >=3.9 | ✅ 兼容 | [link](https://pypi.org/project/duckduckgo-search/) |
| PyYAML | latest | - | ✅ 兼容 | [link](https://pypi.org/project/PyYAML/) |
| requests | latest | - | ✅ 兼容 | [link](https://pypi.org/project/requests/) |

## ⚠️ 使用注意事项

### 数据来源与准确性
- 系统数据来源于Yahoo Finance、DuckDuckGo等第三方API
- 数据可能存在15分钟延迟（行情数据）
- 财务数据可能存在1-2个季度的滞后
- 请勿完全依赖系统提供的数据做出投资决策

### API调用限制
- Yahoo Finance API有调用频率限制
- DuckDuckGo搜索API有请求限制
- 系统实现了缓存机制以减少API调用
- 短时间内的重复查询会使用缓存数据

### 市场覆盖范围
- **A股**：支持上交所和深交所
- **港股**：支持港交所上市公司
- **美股**：支持纳斯达克和纽交所
- 其他市场的股票可能无法正确识别

### 免责声明
**重要**：本系统提供的信息仅供参考，不构成任何投资建议。投资决策需自行承担风险。系统生成的评价和建议仅基于历史数据和公开信息，不能保证准确性和完整性。请在做出投资决策前进行充分的独立研究。

## 🐛 常见问题与解决方案

### Q1：查询时显示"stock not found"

**原因**：股票代码或名称输入不正确，或该股票不存在  
**解决方案**：
- 检查股票代码是否正确（A股6位数字、港股5位数字、美股字母）
- 确保股票在对应市场上市
- 尝试使用公司全名而非简称

### Q2：查询很慢或超时

**原因**：首次查询需要下载数据；网络连接不稳定  
**解决方案**：
- 等待首次查询完成，后续查询会使用缓存加快速度
- 检查网络连接
- 尝试增加超时时间：`--timeout 30`

### Q3：某些数据显示"N/A"

**原因**：该数据来源暂未提供或不可用  
**解决方案**：
- 这是正常现象，系统会继续处理其他可用数据
- 查看系统日志了解具体原因
- 稍后重新查询可能会获得数据

### Q4：缓存文件占用太多空间

**原因**：长期使用后缓存数据累积  
**解决方案**：
```bash
# 清理所有缓存
python -c "from tools.generated_tools.stock_information_collector.stock_tools import cache_manager_tool; print(cache_manager_tool('clear', ''))"

# 或手动删除缓存目录
rm -rf .cache/stock_information_collector/
```

### Q5：如何在AgentCore上部署？

**方案**：
1. 将Agent代码打包为Docker镜像
2. 在Dockerfile中设置环境变量 `DOCKER_CONTAINER=1`
3. 部署到AWS Bedrock AgentCore
4. 通过HTTP POST请求调用 `/invocations` 端点

示例请求：
```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "查询苹果股票"}'
```

## 🎓 技术细节

### Agent创建流程

```python
from nexus_utils.agent_factory import create_agent_from_prompt_template

agent = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/stock_information_collector/stock_information_collector",
    env="production",
    version="latest",
    model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    enable_logging=True
)
```

### 工具调用示例

```python
# Agent自动调用工具，无需手动调用
# 以下是工具返回的数据格式示例

# stock_query_tool返回
{
    "success": True,
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "market": "美股",
    "market_cap": 3200000000000
}

# market_data_tool返回
{
    "success": True,
    "symbol": "AAPL",
    "current_price": 182.50,
    "change_percent": 2.35,
    "volume": 52300000
}
```

### 响应处理

Agent支持多种返回格式的自动解析：

```python
# 系统自动适配以下格式
if hasattr(result, 'message') and result.message:
    # Strands Agent格式
    content = result.message.get('content', [])
elif hasattr(result, 'content') and result.content:
    # 直接content属性
    response = result.content
elif isinstance(result, str):
    # 字符串格式
    response = result
```

## 📞 支持与反馈

- 如有问题或建议，请查看项目文档
- 检查日志文件了解详细错误信息
- 启用调试模式获取更详细的运行信息：`--debug`

## 📝 更新日志

### v1.0.0 (2025-11-28)
- ✅ 初始版本发布
- ✅ 支持A股、港股、美股查询
- ✅ 集成5个专用工具
- ✅ 完整的评价报告生成
- ✅ 智能缓存管理
- ✅ BedrockAgentCore兼容

## 📄 许可证

本项目遵循Nexus-AI平台的开发规范和许可条款。

---

**项目完成时间**：2025-11-28  
**最后更新**：2025-11-28  
**开发状态**：✅ 开发完成，待项目管理审核

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-11-28 09:59:23 UTC*
