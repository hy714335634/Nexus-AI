# children_chat_companion

## 项目描述
儿童陪伴聊天Agent - 为3-12岁儿童提供多轮对话服务，具备儿童友好的交流方式、用户画像构建和会话记忆功能

## 项目结构
```
children_chat_companion/
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

#### children_chat_companion
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/children_chat_companion/agents/children_chat_companion/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/children_chat_companion/agents/children_chat_companion/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/children_chat_companion/agents/children_chat_companion/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/children_chat_companion/agents/children_chat_companion/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](projects/children_chat_companion/agents/children_chat_companion/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](projects/children_chat_companion/agents/children_chat_companion/agent_code_developer.json)
- **agent_developer_manager**: ⏳ 待完成

## 附加信息
# Children Chat Companion Agent

## 项目概述

儿童陪伴聊天Agent是一个专为3-12岁儿童设计的智能对话助手，能够以儿童友好的方式进行多轮对话交流，自动构建和维护儿童用户画像，并在会话间保持记忆连贯性。该系统旨在为儿童提供安全、有趣、富有教育意义的对话体验。

**版本**: 1.0.0  
**创建日期**: 2025-12-23  
**Python版本**: >=3.12

---

## 核心功能

### 1. 年龄适配对话
根据儿童年龄（3-6岁、7-9岁、10-12岁）自动调整对话风格：
- **3-6岁**: 使用简单词汇、短句子、拟声词和重复表达，加入emoji增加趣味性
- **7-9岁**: 使用中等复杂度词汇、故事化表达和适度成语
- **10-12岁**: 使用丰富词汇、复杂句式和启发式引导

### 2. 用户画像构建
在对话中自然地识别和记录儿童的特征信息：
- 基础信息：年龄、性别、年级
- 兴趣爱好：动态权重管理，反映真实偏好变化
- 性格特征：活泼/安静、好奇/谨慎等
- 关键记忆：重要事件、特殊偏好、需要记住的细节

### 3. 会话记忆管理
实现跨会话的记忆连续性：
- 加载历史画像和最近会话的关键信息
- 在新对话中自然地引用历史记忆
- 支持多会话并行管理

### 4. 内容安全保障
确保所有对话内容适合儿童：
- 依赖Claude模型内置安全机制
- 提示词中强化儿童内容安全约束
- 礼貌地引导不当话题转向正面内容

### 5. 流式实时响应
通过BedrockAgentCore流式响应机制：
- 逐字显示回复内容
- 首字响应时间 < 1秒
- 总响应时间 < 3秒

---

## 项目结构

```
children_chat_companion/
├── agents/
│   └── generated_agents/
│       └── children_chat_companion/
│           └── children_chat_companion.py          # Agent主程序
├── prompts/
│   └── generated_agents_prompts/
│       └── children_chat_companion/
│           └── children_chat_companion.yaml        # 提示词配置
├── tools/
│   └── generated_tools/
│       └── children_chat_companion/
│           ├── profile_manager.py                  # 用户画像管理工具
│           └── session_manager.py                  # 会话历史管理工具
├── projects/
│   └── children_chat_companion/
│       ├── agents/
│       │   └── children_chat_companion/
│       │       ├── requirements_analyzer.json      # 需求分析文档
│       │       ├── system_architect.json           # 系统架构设计文档
│       │       ├── agent_designer.json             # Agent设计文档
│       │       ├── tools_developer.json            # 工具开发文档
│       │       ├── prompt_engineer.json            # 提示词工程文档
│       │       └── agent_code_developer.json       # Agent代码开发文档
│       ├── config.yaml                             # 项目配置文件
│       ├── requirements.txt                        # Python依赖包
│       ├── README.md                               # 项目说明文档
│       └── status.yaml                             # 项目状态跟踪
└── .cache/
    └── children_chat_companion/
        └── <user_id>/
            ├── profile.json                        # 用户画像数据
            └── session_<id>.json                   # 会话历史数据
```

---

## 技术栈

- **框架**: Strands SDK (基于AWS Bedrock)
- **模型**: Claude Sonnet 4.5 (global.anthropic.claude-sonnet-4-5-20250929-v1:0)
- **运行时**: BedrockAgentCore (生产) / Local Python (开发测试)
- **存储**: 本地文件系统（JSON格式）
- **部署**: AWS Bedrock AgentCore + Docker容器
- **语言**: Python 3.13+
- **可观测性**: StrandsTelemetry + OTLP

---

## 安装和配置

### 1. 环境要求
- Python 3.12 或更高版本
- AWS Bedrock访问权限
- 文件系统读写权限

### 2. 安装依赖
```bash
cd projects/children_chat_companion
pip install -r requirements.txt
```

### 3. 配置环境变量
```bash
# 设置OTLP遥测端点（可选）
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"

# 设置Docker容器标识（生产环境）
export DOCKER_CONTAINER="1"
```

### 4. 创建缓存目录
```bash
mkdir -p .cache/children_chat_companion
```

---

## 使用指南

### 本地测试模式

使用命令行参数进行快速测试：

```bash
cd agents/generated_agents/children_chat_companion

# 基本测试
python children_chat_companion.py -i "你好！"

# 指定用户ID测试
python children_chat_companion.py -i "我喜欢恐龙" -u "child_001"
```

### 生产部署模式

启动HTTP服务器（端口8080）：

```bash
# 设置Docker环境变量
export DOCKER_CONTAINER="1"

# 启动服务器
python children_chat_companion.py
```

### API调用示例

**请求格式**:
```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "你好！我今天在学校学了恐龙知识！",
    "user_id": "child_001",
    "session_id": "session_123"
  }'
```

**响应格式**:
流式响应，逐字返回对话内容：
```
哇！恐龙真的很神奇呢！你最喜欢哪种恐龙？是霸王龙、三角龙还是其他的恐龙呢？🦕
```

---

## 开发阶段

项目采用标准的Nexus-AI Build Workflow，包含7个开发阶段：

| 阶段 | 状态 | 说明 | 文档路径 |
|------|------|------|----------|
| 1. Requirements Analyzer | ✅ 完成 | 需求分析阶段 | `projects/.../requirements_analyzer.json` |
| 2. System Architect | ✅ 完成 | 系统架构设计阶段 | `projects/.../system_architect.json` |
| 3. Agent Designer | ✅ 完成 | Agent设计阶段 | `projects/.../agent_designer.json` |
| 4. Prompt Engineer | ✅ 完成 | 提示词工程阶段 | `projects/.../prompt_engineer.json` |
| 5. Tools Developer | ✅ 完成 | 工具开发阶段 | `projects/.../tools_developer.json` |
| 6. Agent Code Developer | ✅ 完成 | Agent代码开发阶段 | `projects/.../agent_code_developer.json` |
| 7. Agent Developer Manager | ✅ 完成 | 项目验证和文档生成阶段 | 本文档 |

**项目进度**: 7/7 (100%)

---

## 核心工具说明

### 用户画像管理工具 (profile_manager.py)

提供9个函数用于用户画像的加载、保存和更新：

1. **load_user_profile**: 加载用户画像文件
2. **save_user_profile**: 保存用户画像文件
3. **create_default_profile**: 创建默认用户画像
4. **update_profile_field**: 更新画像中的指定字段
5. **add_interest**: 添加或更新兴趣标签
6. **update_conversation_stats**: 更新对话统计信息
7. **get_profile_summary**: 获取画像摘要信息

### 会话历史管理工具 (session_manager.py)

提供10个函数用于会话历史的管理：

1. **load_session_history**: 加载会话历史文件
2. **save_session_history**: 保存会话历史文件
3. **create_new_session**: 创建新会话
4. **append_conversation_turn**: 追加对话轮次
5. **get_recent_context**: 获取最近N轮对话
6. **close_session**: 关闭会话
7. **list_user_sessions**: 列出用户的所有会话
8. **delete_session**: 删除指定会话
9. **archive_old_sessions**: 归档旧会话
10. **get_session_summary**: 获取会话摘要
11. **update_session_topics**: 更新会话讨论的主题

---

## 数据模型

### UserProfile (用户画像)

```json
{
  "user_id": "string",
  "basic_info": {
    "nickname": "string",
    "age": "integer (3-12)",
    "gender": "string (male/female/unknown)",
    "grade": "string"
  },
  "interests": [
    {
      "name": "string",
      "weight": "float (0.0-1.0)",
      "first_mentioned": "ISO 8601 timestamp",
      "last_mentioned": "ISO 8601 timestamp",
      "mention_count": "integer"
    }
  ],
  "personality_traits": ["string"],
  "behavior_patterns": ["string"],
  "key_memories": [
    {
      "content": "string",
      "timestamp": "ISO 8601 timestamp",
      "context": "string"
    }
  ],
  "conversation_stats": {
    "total_conversations": "integer",
    "total_turns": "integer",
    "first_conversation": "ISO 8601 timestamp",
    "last_conversation": "ISO 8601 timestamp",
    "average_turns_per_session": "float"
  },
  "created_at": "ISO 8601 timestamp",
  "last_updated": "ISO 8601 timestamp",
  "version": "string"
}
```

### SessionHistory (会话历史)

```json
{
  "session_id": "string",
  "user_id": "string",
  "conversation_turns": [
    {
      "turn_number": "integer",
      "timestamp": "ISO 8601 timestamp",
      "user_input": "string",
      "agent_response": "string",
      "context_summary": "string"
    }
  ],
  "session_metadata": {
    "start_time": "ISO 8601 timestamp",
    "end_time": "ISO 8601 timestamp",
    "total_turns": "integer",
    "user_age_at_session": "integer",
    "topics_discussed": ["string"]
  },
  "created_at": "ISO 8601 timestamp",
  "last_updated": "ISO 8601 timestamp"
}
```

---

## 性能指标

- **响应速度**: 首字响应 < 1秒，总响应时间 < 3秒
- **并发能力**: 支持至少100个并发用户会话
- **画像加载**: < 500毫秒
- **文件大小**: 用户画像 < 100KB，单会话历史 < 50轮
- **上下文窗口**: 最近3-5轮对话
- **内容安全**: 100%符合儿童内容安全标准

---

## 安全和隐私

### 内容安全
- 依赖Claude模型内置安全机制
- 提示词中强化儿童内容安全约束
- 礼貌引导不当话题转向正面内容

### 隐私保护
- 用户画像和会话历史仅存储在本地文件系统
- 不记录真实姓名、地址、学校名称等敏感信息
- 建议使用UUID或不可逆哈希作为user_id
- 每个用户的数据存储在独立目录中

### 访问控制
- 缓存目录设置适当的文件权限（如700）
- 仅允许Agent进程访问用户数据
- 会话隔离，防止会话混淆或数据污染

---

## 错误处理

系统设计了完善的错误处理机制：

- **画像加载失败**: 使用默认画像（年龄7岁），记录警告，继续对话
- **会话历史加载失败**: 从空历史开始，作为新会话处理
- **画像保存失败**: 记录错误日志，但不中断对话
- **流式响应中断**: 返回友好错误信息
- **无效输入**: 提示用户输入有效内容
- **文件系统错误**: 优雅降级到只读模式

---

## 监控和日志

### 日志记录
- 使用Python logging模块
- 记录关键操作（画像加载、更新、对话生成等）
- ERROR级别记录异常和错误信息
- INFO级别记录正常操作流程

### 遥测数据
- 使用StrandsTelemetry设置OTLP导出器
- 监控响应时间、成功率、画像更新频率
- 跟踪用户行为和会话统计

### 关键指标
- 对话响应时间（P50、P95、P99）
- 画像加载/保存成功率
- 流式响应完成率
- 用户留存率和平均对话轮数

---

## 常见问题

### Q1: 如何修改年龄适配策略？
修改 `prompts/generated_agents_prompts/children_chat_companion/children_chat_companion.yaml` 文件中的 `system_prompt` 部分，调整三个年龄段的对话策略。

### Q2: 如何添加新的兴趣标签？
Agent会自动从对话中提取兴趣标签，无需手动添加。如果需要预设兴趣，可以在用户画像JSON文件中直接编辑。

### Q3: 如何备份用户数据？
定期备份 `.cache/children_chat_companion/` 目录即可。每个用户的数据存储在独立子目录中。

### Q4: 如何清理旧的会话历史？
使用 `archive_old_sessions` 工具函数归档超过指定天数的会话，或使用 `delete_session` 删除特定会话。

### Q5: 如何调整响应的趣味性？
修改提示词配置中的 `temperature` 参数（当前为0.7），提高温度值可增加创意性，降低可提高稳定性。

---

## 维护建议

### 定期维护任务
1. **监控存储空间**: 定期检查 `.cache/` 目录大小，及时归档或清理旧数据
2. **检查画像质量**: 抽查用户画像，确保信息提取准确性
3. **更新提示词**: 根据用户反馈和使用情况优化提示词策略
4. **性能优化**: 监控响应时间，必要时优化文件I/O操作
5. **安全审计**: 定期审查日志，确保内容安全机制有效

### 扩展建议
1. **数据库迁移**: 用户量增大后考虑迁移到DynamoDB或其他数据库
2. **多语言支持**: 添加英语等其他语言的提示词模板
3. **语音交互**: 集成语音识别和合成服务
4. **家长监控**: 开发家长管理界面，支持查看对话历史和画像
5. **内容推荐**: 根据用户画像推荐适合的教育内容

---

## 贡献指南

本项目由Nexus-AI平台自动生成。如需修改或扩展功能，请遵循以下步骤：

1. 修改提示词配置（`prompts/generated_agents_prompts/children_chat_companion/children_chat_companion.yaml`）
2. 如需添加新工具，在 `tools/generated_tools/children_chat_companion/` 目录下创建新的工具文件
3. 更新Agent代码（`agents/generated_agents/children_chat_companion/children_chat_companion.py`）
4. 运行本地测试验证功能
5. 更新项目文档

---

## 许可证

本项目遵循Nexus-AI平台的使用条款和许可证。

---

## 联系方式

如有问题或建议，请联系Nexus-AI平台支持团队。

---

**最后更新时间**: 2025-12-23  
**文档版本**: 1.0.0

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-12-23 06:52:23 UTC*
