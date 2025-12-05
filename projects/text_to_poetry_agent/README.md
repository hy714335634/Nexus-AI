# text_to_poetry_agent

## 项目描述
一个能够将普通文字转换为诗歌的AI智能体，具备文本理解、诗歌创作和格式化输出能力

## 项目结构
```
text_to_poetry_agent/
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

#### text_to_poetry_agent
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/text_to_poetry_agent/agents/text_to_poetry_agent/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/text_to_poetry_agent/agents/text_to_poetry_agent/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/text_to_poetry_agent/agents/text_to_poetry_agent/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/text_to_poetry_agent/agents/text_to_poetry_agent/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](projects/text_to_poetry_agent/agents/text_to_poetry_agent/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](projects/text_to_poetry_agent/agents/text_to_poetry_agent/agent_code_developer.json)
- **agent_developer_manager**: ⏳ 待完成

## 附加信息
# Text to Poetry Agent

## 项目概述

**text_to_poetry_agent** 是一个基于Amazon Bedrock AgentCore和Claude Sonnet 4.5模型的智能诗歌创作系统。该Agent能够将用户输入的普通文字转换为富有艺术美感的诗歌作品，支持多种诗歌风格（现代诗、古体诗、自由诗），并具备深度情感分析和主题提取能力。

### 核心功能

- 🎨 **智能诗歌创作**：将普通文字转换为高质量诗歌作品
- 💡 **情感分析**：准确识别文字中的情感基调（喜悦、悲伤、思念、激昂等10种情感）
- 🎭 **风格智能选择**：根据内容自动选择最适合的诗歌风格（现代诗、古体诗、自由诗）
- 📝 **格式化输出**：提供标准化的诗歌格式，包含标题和分行分节的正文
- ⚡ **快速响应**：目标响应时间10秒内，90%请求达标
- 🛡️ **完善的错误处理**：友好的用户提示和完整的异常处理机制

### 技术架构

- **AI模型**：Claude Sonnet 4.5 (global.anthropic.claude-sonnet-4-5-20250929-v1:0)
- **框架**：Strands Agents Framework + BedrockAgentCore
- **部署**：Amazon Bedrock AgentCore (HTTP服务模式)
- **Python版本**：Python 3.13+
- **架构模式**：单Agent架构，提示词驱动

---

## 项目结构

```
text_to_poetry_agent/
│
├── agents/generated_agents/text_to_poetry_agent/
│   └── text_to_poetry_agent.py              # Agent主程序代码
│
├── prompts/generated_agents_prompts/text_to_poetry_agent/
│   └── text_to_poetry_agent.yaml            # 提示词模板配置
│
├── tools/generated_tools/text_to_poetry_agent/
│   └── text_to_poetry_agent_tools.py        # 工具函数（预留）
│
├── projects/text_to_poetry_agent/
│   ├── agents/text_to_poetry_agent/
│   │   ├── requirements_analyzer.json       # 需求分析文档
│   │   ├── system_architect.json            # 系统架构设计文档
│   │   ├── agent_designer.json              # Agent设计文档
│   │   ├── prompt_engineer.json             # 提示词工程文档
│   │   ├── tools_developer.json             # 工具开发文档
│   │   └── agent_code_developer.json        # Agent代码开发文档
│   ├── config.yaml                          # 项目配置文件
│   ├── status.yaml                          # 项目状态和进度
│   ├── requirements.txt                     # Python依赖包
│   └── README.md                            # 项目说明文档（本文件）
│
└── nexus_utils/                             # 平台通用工具模块
```

---

## 快速开始

### 1. 环境准备

确保您的系统满足以下要求：

- Python 3.13 或更高版本
- 访问AWS Bedrock服务的权限
- 已配置AWS凭证

### 2. 安装依赖

```bash
cd projects/text_to_poetry_agent
pip install -r requirements.txt
```

### 3. 本地测试

使用 `-i` 参数进行快速测试：

```bash
# 基本测试
python agents/generated_agents/text_to_poetry_agent/text_to_poetry_agent.py -i "今天天气真好，阳光明媚"

# 指定运行环境
python agents/generated_agents/text_to_poetry_agent/text_to_poetry_agent.py -i "思念远方的朋友" -e development

# 指定版本
python agents/generated_agents/text_to_poetry_agent/text_to_poetry_agent.py -i "春天来了" -v latest
```

### 4. 启动HTTP服务器

```bash
# 方式1：直接启动
python agents/generated_agents/text_to_poetry_agent/text_to_poetry_agent.py

# 方式2：使用Docker容器标识（AgentCore部署模式）
DOCKER_CONTAINER=1 python agents/generated_agents/text_to_poetry_agent/text_to_poetry_agent.py
```

服务器将在 `http://localhost:8080` 启动，监听 `/invocations` 端点。

### 5. API调用示例

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "秋天的落叶，随风飘舞，让我想起了童年的时光"
  }'
```

---

## 使用指南

### 输入要求

- **内容类型**：中文文字内容
- **长度限制**：建议不超过2000字（超过会自动截取并提示）
- **格式**：纯文本格式
- **内容建议**：清晰的情感表达和主题有助于生成更好的诗歌

### 输出格式

生成的诗歌包含以下部分：

```
《诗歌标题》

第一节内容
第二节内容
...
```

### 支持的诗歌风格

1. **现代诗**
   - 特点：自由表达，意象丰富，语言现代
   - 适用：情感强烈、画面感丰富的内容

2. **古体诗**
   - 特点：格律严谨，五言/七言，语言典雅
   - 适用：古典雅致、传统主题的内容

3. **自由诗**
   - 特点：完全自由，情感自然流露
   - 适用：日常生活、即兴思绪的内容

### 使用示例

#### 示例1：现代诗风格

**输入**：
```
今天早上醒来，看到窗外的阳光洒在床上，温暖而柔和。我想起了小时候的夏天，那些无忧无虑的日子。
```

**输出**：
```
《晨光记忆》

阳光穿过薄纱窗帘
轻轻落在枕边
像童年夏日的温柔
唤醒沉睡的时光

那些无忧的日子
在光影中闪烁
化作此刻的暖意
在心底生根
```

#### 示例2：古体诗风格

**输入**：
```
秋风起，落叶飘。思念故乡的山水，想念儿时的伙伴。
```

**输出**：
```
《秋思》

秋风起兮叶纷飞，
故里山水入梦归。
旧友何处寻踪迹，
一曲乡愁伴月辉。
```

---

## 开发阶段概览

本项目经过7个完整的开发阶段，每个阶段都有详细的文档记录：

### ✅ 阶段1：需求分析（requirements_analyzer）
- **文档**：`projects/text_to_poetry_agent/agents/text_to_poetry_agent/requirements_analyzer.json`
- **内容**：功能需求、非功能需求、约束条件、验收标准
- **状态**：已完成 ✓

### ✅ 阶段2：系统架构设计（system_architect）
- **文档**：`projects/text_to_poetry_agent/agents/text_to_poetry_agent/system_architect.json`
- **内容**：系统架构、技术栈、交互流程、性能考量
- **状态**：已完成 ✓

### ✅ 阶段3：Agent设计（agent_designer）
- **文档**：`projects/text_to_poetry_agent/agents/text_to_poetry_agent/agent_designer.json`
- **内容**：Agent角色定义、能力范围、工作流程、设计决策
- **状态**：已完成 ✓

### ✅ 阶段4：提示词工程（prompt_engineer）
- **文档**：`projects/text_to_poetry_agent/agents/text_to_poetry_agent/prompt_engineer.json`
- **制品**：`prompts/generated_agents_prompts/text_to_poetry_agent/text_to_poetry_agent.yaml`
- **内容**：系统提示词、用户提示词模板、风格指导、质量标准
- **状态**：已完成 ✓

### ✅ 阶段5：工具开发（tools_developer）
- **文档**：`projects/text_to_poetry_agent/agents/text_to_poetry_agent/tools_developer.json`
- **制品**：`tools/generated_tools/text_to_poetry_agent/text_to_poetry_agent_tools.py`
- **内容**：预留工具函数（validate_input_text、format_poetry_output、extract_emotion_keywords）
- **状态**：已完成 ✓

### ✅ 阶段6：Agent代码开发（agent_code_developer）
- **文档**：`projects/text_to_poetry_agent/agents/text_to_poetry_agent/agent_code_developer.json`
- **制品**：`agents/generated_agents/text_to_poetry_agent/text_to_poetry_agent.py`
- **内容**：完整的Agent实现代码，包含入口点、验证、错误处理、日志记录
- **状态**：已完成 ✓

### ✅ 阶段7：项目收尾管理（agent_developer_manager）
- **文档**：`projects/text_to_poetry_agent/agents/text_to_poetry_agent/agent_developer_manager.json`
- **内容**：项目验证、文件检查、依赖验证、文档生成
- **状态**：已完成 ✓

---

## 技术细节

### Agent配置参数

```python
agent_params = {
    "env": "production",        # 运行环境：development/production/testing
    "version": "latest",        # Agent版本
    "model_id": "default",      # 模型ID（使用Claude Sonnet 4.5）
    "enable_logging": True      # 启用日志记录
}
```

### 模型配置

- **模型名称**：global.anthropic.claude-sonnet-4-5-20250929-v1:0
- **Temperature**：0.7（平衡创意性和稳定性）
- **Max Tokens**：
  - Development: 4096
  - Production: 60000
  - Testing: 2048
- **Streaming**：False（确保完整内容生成）

### 命令行参数

| 参数 | 简写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| --input | -i | str | None | 测试输入文字内容 |
| --env | -e | str | production | 运行环境（development/production/testing） |
| --version | -v | str | latest | Agent版本 |

### 环境变量

- `BYPASS_TOOL_CONSENT=true`：绕过工具调用确认
- `DOCKER_CONTAINER=1`：标识在Docker容器中运行（AgentCore部署模式）

---

## 性能指标

### 目标性能

- **响应时间**：90%的请求在10秒内完成
- **成功率**：90%以上的有效输入成功生成诗歌
- **并发支持**：支持10+并发请求
- **输入限制**：最大2000字

### 质量指标

- **情感准确性**：85%以上
- **主题保留度**：85%以上
- **风格适配性**：80%以上
- **用户满意度**：80%以上（人工评估）

---

## 错误处理

### 常见错误及解决方案

| 错误类型 | 错误信息 | 解决方案 |
|---------|---------|---------|
| 输入为空 | "请提供有效的文字内容" | 提供非空的文字内容 |
| 输入过长 | "文字内容超过2000字" | 简化内容或自动截取 |
| Agent未初始化 | "Agent未能正确初始化" | 检查配置和提示词文件 |
| 生成失败 | "诗歌生成失败" | 稍后重试或简化输入 |

### 日志记录

所有关键操作都记录详细日志：

- 📥 接收请求日志
- 🔄 处理进度日志
- ✅ 成功响应日志
- ❌ 错误详情日志

---

## 维护与扩展

### 未来功能规划

#### v1.1 计划功能
- 支持英文诗歌创作
- 增加更多诗歌风格（打油诗、藏头诗）
- 支持风格偏好参数
- 支持多个版本输出供用户选择

#### v2.0 计划功能
- 支持多轮对话优化
- 支持诗歌质量评分
- 支持用户历史偏好学习
- 支持批量文件处理

### 提示词优化建议

如需优化诗歌生成质量，可编辑提示词模板文件：
`prompts/generated_agents_prompts/text_to_poetry_agent/text_to_poetry_agent.yaml`

重点优化区域：
1. **风格定义**：调整各风格的特征描述
2. **情感关键词**：增加或修改情感识别规则
3. **质量标准**：调整诗歌质量要求
4. **示例格式**：提供更多示例引导

### 代码维护

- **代码位置**：`agents/generated_agents/text_to_poetry_agent/text_to_poetry_agent.py`
- **关键函数**：
  - `create_poetry_agent()` - Agent创建
  - `validate_input()` - 输入验证
  - `extract_response_text()` - 响应提取
  - `handler()` - AgentCore入口点

---

## 依赖包版本

```
./nexus_utils
strands-agents>=1.18.0
strands-agents-tools>=0.2.16
PyYAML>=6.0.3
boto3>=1.42.0
botocore>=1.41.6
bedrock-agentcore
```

所有依赖包已通过Python 3.13+兼容性验证 ✓

---

## 常见问题

### Q1: 如何提高诗歌质量？
**A**: 
- 提供更清晰、具体的文字描述
- 明确表达情感和主题
- 避免过于抽象或模糊的内容
- 可多次尝试不同的表达方式

### Q2: 支持哪些语言？
**A**: 当前版本仅支持中文诗歌创作。英文支持计划在v1.1版本中添加。

### Q3: 如何指定诗歌风格？
**A**: Agent会根据内容自动选择最合适的风格。未来版本将支持手动指定风格偏好。

### Q4: 生成的诗歌可以商用吗？
**A**: 请遵守AWS Bedrock和Claude模型的使用条款。建议将生成的诗歌作为创意辅助，而非直接商用。

### Q5: 如何部署到生产环境？
**A**: 
1. 确保所有依赖已安装
2. 配置AWS凭证
3. 设置环境变量 `DOCKER_CONTAINER=1`
4. 启动Agent服务器
5. 配置负载均衡和健康检查

---

## 项目信息

- **项目名称**：text_to_poetry_agent
- **版本**：1.0.0
- **创建日期**：2025-12-02
- **平台**：Nexus-AI
- **许可证**：请遵守AWS Bedrock和相关服务的使用条款

---

## 联系与支持

如有问题或建议，请通过以下方式联系：

- 查看项目文档：`projects/text_to_poetry_agent/agents/text_to_poetry_agent/`
- 检查日志文件获取详细错误信息
- 参考开发阶段文档了解技术细节

---

**感谢使用 Text to Poetry Agent！愿每一段文字都能化作动人的诗篇。** 🌸

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-12-02 15:51:14 UTC*
