# basketball_qa_agent

## 项目描述
An AI Agent to search and organize online answers to basketball-related questions.

## 项目结构
```
basketball_qa_agent/
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

项目状态和各阶段结果将在开发过程中更新到此文档。

## 附加信息
# basketball_qa_agent - 篮球问答智能体

## 📋 项目概述

**basketball_qa_agent** 是一个专业的AI智能体系统，专门用于处理和回答篮球相关问题。该Agent可以搜索互联网资源，整理提取相关信息，并生成结构化的、高质量的答案。

### 项目特点
- 🔍 **多源信息搜索**：从多个可靠来源获取篮球信息
- 📊 **智能信息整理**：自动去重、分类、摘要处理
- 📝 **结构化输出**：提供清晰、专业的答案格式
- 🎯 **专业知识库**：覆盖篮球规则、技巧、历史、球员等多个领域
- ⚡ **快速响应**：目标响应时间25-30秒以内
- 💾 **智能缓存**：提高重复查询的响应效率

---

## 🏗️ 项目结构

```
basketball_qa_agent/
├── agents/                                    # Agent实现文件目录
│   └── basketball_qa_agent/
│       ├── agent_designer.json               # Agent设计文档
│       ├── tools_developer.json              # 工具规范文档
│       ├── prompt_engineer.json              # 提示词工程文档
│       └── agent_code_developer.json         # Agent代码实现
├── config.yaml                               # 项目配置文件
├── requirements.txt                          # Python依赖文件
├── README.md                                 # 项目说明文档
├── status.yaml                               # 项目状态跟踪文件
└── cache/                                    # 缓存目录
    └── basketball_qa/                        # 搜索结果和内容缓存
```

---

## 🚀 快速开始

### 环境要求
- Python 3.13+
- AWS Bedrock 访问权限
- 互联网连接（用于网络搜索）
- 最少 2GB RAM

### 安装步骤

1. **克隆或获取项目**
```bash
cd basketball_qa_agent
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

4. **初始化Agent**
```python
from basketball_qa_agent import BasketballQAAgent

agent = BasketballQAAgent(
    model_id='us.anthropic.claude-3-7-sonnet-20250219-v1:0',
    tools=[web_search_enhanced, http_request, file_read, file_write, current_time]
)
```

---

## 💡 使用示例

### 基础使用

```python
# 提出篮球问题
question = "什么是篮球中的挡拆战术？"

# 获取答案
answer = agent.process_question(question)

# 打印结果
print(answer)
```

### 带上下文的使用

```python
context = {
    'user_id': 'user123',
    'language': 'zh-CN',
    'preferences': {
        'detail_level': 'detailed',
        'include_statistics': True
    }
}

answer = agent.process_question(question, context=context)
```

---

## 🧠 Agent 功能特性

### 核心功能

1. **问题理解与分析**
   - 准确解析用户的篮球相关问题
   - 识别问题类型和关键概念
   - 提取搜索关键词

2. **信息搜索与收集**
   - 使用web_search_enhanced工具进行多源搜索
   - 使用http_request获取详细网页内容
   - 支持高级搜索语法

3. **内容处理与整理**
   - 自动去重和内容去重
   - 按照类别分组信息
   - 提取关键要点和摘要

4. **结构化答案生成**
   - 生成包含多个部分的完整答案
   - 提供数据、案例和来源引用
   - 格式化输出便于阅读

### 知识领域

Agent专业覆盖以下领域：
- ✓ 篮球规则与裁判规范
- ✓ 篮球技巧与战术体系
- ✓ 篮球历史与发展演变
- ✓ 球员信息与职业统计
- ✓ 篮球装备与训练方法
- ✓ NBA、CBA等主要联赛
- ✓ 国际篮球赛事

---

## 📚 答案格式说明

Agent生成的答案采用以下结构化格式：

```
【问题理解】
对用户问题的理解、关键要点分析和问题背景说明

【快速答案】
简明扼要的直接答案（1-3句话）

【详细解说】
分类组织的详细信息，包含多个小节

【数据/案例】
相关的统计数据、具体案例和实例

【相关资源】
搜索来源和参考链接

【补充说明】
任何额外的重要信息和建议
```

---

## 🔧 开发阶段状态

### ✅ 已完成的阶段

| 阶段 | 名称 | 状态 | 文件 |
|------|------|------|------|
| 1 | requirements_analyzer | ✅ 完成 | 需求分析文档 |
| 2 | system_architect | ✅ 完成 | 系统架构文档 |
| 3 | agent_designer | ✅ 完成 | agents/basketball_qa_agent/agent_designer.json |
| 4 | tools_developer | ✅ 完成 | agents/basketball_qa_agent/tools_developer.json |
| 5 | prompt_engineer | ✅ 完成 | agents/basketball_qa_agent/prompt_engineer.json |
| 6 | agent_code_developer | ✅ 完成 | agents/basketball_qa_agent/agent_code_developer.json |
| 7 | agent_developer_manager | ✅ 完成 | 本文档 |

---

## 🛠️ 核心工具

Agent使用以下5个核心工具：

### 1. web_search_enhanced
- **功能**：多源网络搜索
- **支持**：多搜索引擎整合、高级搜索语法、自动去重
- **速率限制**：10 req/min, 500 req/hour

### 2. http_request
- **功能**：直接HTTP请求获取网页内容
- **支持**：多种HTTP方法、自定义请求头、重定向处理
- **速率限制**：20 req/min

### 3. file_read
- **功能**：读取本地文件
- **支持**：多种文件格式、部分读取、编码检测
- **限制**：仅访问项目目录内的文件

### 4. file_write
- **功能**：写入本地文件
- **支持**：多种写入模式、自动目录创建、原子写入
- **限制**：仅写入项目目录内的文件

### 5. current_time
- **功能**：获取当前时间戳
- **支持**：多时区、多种时间格式、毫秒级精度

---

## ⚙️ 配置说明

### 环境变量

```bash
# AWS配置
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# Agent配置
AGENT_MODEL_ID=us.anthropic.claude-3-7-sonnet-20250219-v1:0
CACHE_PATH=cache/basketball_qa
LOG_LEVEL=INFO

# 搜索配置
SEARCH_TIMEOUT=15
MAX_SEARCH_RESULTS=10
SEARCH_LANGUAGE=zh-CN
```

### 缓存配置

```yaml
cache:
  enabled: true
  ttl: 3600              # 搜索结果缓存时间（秒）
  path: cache/basketball_qa
  operations:
    search_results: 3600
    web_content: 86400
    processed_answers: 7200
```

---

## 📊 性能指标

### 目标指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 响应时间 | 25-30秒 | 平均响应时间 |
| 缓存命中率 | >70% | 缓存有效性 |
| 搜索结果质量 | >80% | 结果相关度 |
| 错误率 | <5% | 系统稳定性 |
| 答案准确率 | >85% | 内容准确度 |

### 优化策略

1. **缓存优化**：使用本地缓存减少重复查询
2. **并行处理**：并行化搜索请求
3. **增量加载**：智能加载内容
4. **超时管理**：自适应超时配置

---

## ⚠️ 注意事项

### 使用限制

- ❌ 不提供实时比赛数据（需要实时数据源）
- ❌ 不进行视频内容分析
- ❌ 不提供个性化推荐
- ❌ 不支持多轮对话上下文记忆（超过单次会话）
- ❌ 不进行图像识别和分析

### 最佳实践

1. **搜索查询**：使用清晰、具体的搜索词
2. **错误处理**：实现适当的错误处理和重试逻辑
3. **缓存管理**：定期清理过期缓存
4. **日志记录**：启用详细的日志用于调试
5. **速率限制**：遵守API速率限制

### 常见问题

**Q: 搜索失败怎么办？**
A: Agent会自动尝试备选搜索引擎，并提供重试建议。检查网络连接和API配额。

**Q: 如何提高响应速度？**
A: 启用缓存、使用更具体的搜索词、减少搜索结果数量。

**Q: 如何处理信息冲突？**
A: Agent会识别冲突并提供最可靠的来源信息。

---

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行覆盖率测试
pytest --cov=basketball_qa_agent tests/

# 运行特定测试
pytest tests/test_agent.py -v
```

### 测试用例

1. **TC001**: 什么是篮球中的"挡拆"战术？
2. **TC002**: 乔丹职业生涯的主要成就有哪些？
3. **TC003**: 如何提高篮球投篮的准确度？

---

## 📖 技术文档

### 设计文档
- **Agent设计**：`agents/basketball_qa_agent/agent_designer.json`
- **工具规范**：`agents/basketball_qa_agent/tools_developer.json`
- **提示词工程**：`agents/basketball_qa_agent/prompt_engineer.json`
- **代码实现**：`agents/basketball_qa_agent/agent_code_developer.json`

### 项目配置
- **项目配置**：`config.yaml`
- **项目状态**：`status.yaml`
- **依赖管理**：`requirements.txt`

---

## 🔄 工作流程

```
用户输入问题
    ↓
Agent分析问题
    ↓
制定搜索策略
    ↓
执行网络搜索
    ↓
获取网页内容
    ↓
处理和整理信息
    ↓
生成结构化答案
    ↓
返回用户答案
```

---

## 🤝 贡献指南

### 如何改进Agent

1. **提交问题**：报告发现的bug或建议改进
2. **提交代码**：提交代码改进或新功能
3. **改进文档**：完善项目文档和说明
4. **测试**：添加更多测试用例

---

## 📞 支持与联系

### 获取帮助

- 📧 Email: support@basketball-qa.local
- 🐛 Bug报告: 提交GitHub issue
- 💬 讨论: 参与项目讨论

---

## 📄 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

---

## 🎉 致谢

感谢所有为该项目做出贡献的开发者和用户！

---

## 📅 项目信息

| 项目属性 | 说明 |
|---------|------|
| 项目名称 | basketball_qa_agent |
| 项目版本 | 1.0.0 |
| 创建日期 | 2025-11-23 |
| 最后更新 | 2025-11-23 |
| 主要语言 | Python 3.13+ |
| 框架 | Strands Framework with AWS Bedrock |
| 开发状态 | ✅ 完成 |

---

*本项目由Agent开发管理器完整协调开发，确保了高质量的设计和实现。*

**最后更新时间**: 2025-11-23 09:12 UTC

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-11-23 09:13:21 UTC*
