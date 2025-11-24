# short_story_agent

## 项目描述
AI智能体项目：short_story_agent

## 项目结构
```
short_story_agent/
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


## 项目完成情况

### 开发阶段进度

| 阶段 | 状态 | 完成时间 | 说明 |
|------|------|---------|------|
| requirements_analyzer | ✅ 完成 | 2025-11-23 03:02:05 | 需求分析和功能规格定义 |
| system_architect | ✅ 完成 | 2025-11-23 03:03:55 | 系统架构设计和技术方案 |
| agent_designer | ✅ 完成 | 2025-11-23 03:05:13 | Agent结构和交互模式设计 |
| prompt_engineer | ✅ 完成 | 2025-11-23 03:06:43 | 提示词工程和多风格模板设计 |
| tools_developer | ✅ 完成 | 2025-11-23 03:08:23 | 工具集开发规范和接口设计 |
| agent_code_developer | ✅ 完成 | 2025-11-23 03:08:09 | Agent代码架构和实现指南 |
| agent_developer_manager | ✅ 完成 | 2025-11-23 03:08:24 | 项目协调管理和交付 |

**总体进度: 7/7 (100%)**

## 功能概述

### 核心功能
- **场景和关键词输入**：用户输入场景描述（5-500字）和1-10个关键词
- **自动风格检测**：根据场景自动检测合适的文学风格
- **高质量故事生成**：生成800-2000字的完整短篇小说
- **关键词自然融入**：确保所有关键词都自然地融入故事中
- **结构完整性保证**：故事包含明确的开头、发展、高潮、结局
- **多风格支持**：支持现实主义、科幻、悬疑、爱情等多种文学风格
- **错误处理和重试**：完善的错误处理机制和自动重试策略

### 支持的文学风格
1. **现实主义** - 贴近生活、细节真实、人物心理描写深入
2. **科幻** - 想象力丰富、科技元素、未来设定、冒险精神
3. **悬疑** - 紧张刺激、烧脑情节、反转结局、心理战
4. **爱情** - 温暖感人、情感细腻、人物互动、情感冲突
5. **默认风格** - 通用模板，适应各种场景

## 技术架构

### 系统架构
```
用户输入 
  ↓
输入验证 (input_validator)
  ↓
风格检测 (prompt_builder)
  ↓
提示词构建 (prompt_builder)
  ↓
LLM调用 (llm_caller) - AWS Bedrock Claude-Opus
  ↓
内容验证 (content_validator)
  ↓
格式化输出 (output_formatter)
  ↓
用户获得故事
```

### 核心组件

#### 1. 输入验证工具 (input_validator.py)
- 验证场景描述的有效性（5-500字）
- 验证关键词的有效性（1-10个，每个≤20字）
- 提供验证失败时的改进建议

#### 2. 文本处理工具 (text_processor.py)
- 解析多种格式的关键词（逗号、空格、顿号分隔）
- 精确统计中文文本字数
- 文本清理和规范化
- 文本分段处理

#### 3. 提示词构建工具 (prompt_builder.py)
- 5个预设提示词模板（通用、现实主义、科幻、悬疑、爱情）
- 根据场景自动风格检测
- 动态构建系统提示词和用户提示词

#### 4. LLM调用工具 (llm_caller.py)
- 集成AWS Bedrock Claude-Opus模型
- 实现3次自动重试机制
- 支持60秒超时控制
- 详细的错误捕获和日志记录

#### 5. 内容验证工具 (content_validator.py)
- 验证字数范围（800-2000字）
- 检查故事结构完整性
- 验证关键词使用情况
- 内容安全检测

#### 6. 输出格式化工具 (output_formatter.py)
- 提取和格式化故事标题
- 规范化故事正文
- 生成结构化的JSON响应
- 包含生成元数据

### 主Agent类 (story_generator_agent.py)

**核心方法：**
- `generate_story(scene, keywords, style='default')` - 主要生成接口
- `validate_input(scene, keywords)` - 输入验证接口
- `get_available_styles()` - 获取支持的风格列表
- `generate_with_retry(prompt, max_retries=3)` - 带重试的生成

**支持类：**
- `ToolManager` - 管理所有工具
- `PromptManager` - 管理提示词模板
- `GenerationManager` - 管理生成过程和质量验证
- `ErrorHandler` - 统一的错误处理

## 配置和部署

### 环境要求
- Python 3.13+
- AWS账户和Bedrock访问权限
- 必要的Python包（见requirements.txt）

### 安装依赖
```bash
pip install -r requirements.txt
```

### 环境变量配置
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-west-2
export BEDROCK_MODEL_ID=anthropic.claude-opus-4-1-20250805
```

### 基本使用示例

```python
from short_story_agent import StoryGeneratorAgent

# 初始化Agent
agent = StoryGeneratorAgent()

# 生成故事
result = agent.generate_story(
    scene_description="2050年的火星基地，一个孤独的宇航员",
    keywords=["秘密", "救赎", "希望", "回家"],
    style="scifi"
)

# 处理结果
if result['success']:
    print(f"标题: {result['data']['title']}")
    print(f"字数: {result['data']['word_count']}")
    print(f"风格: {result['data']['style']}")
    print(f"内容:\n{result['data']['content']}")
else:
    print(f"错误: {result['error']['message']}")
    if 'suggestions' in result['error']:
        print(f"建议: {result['error']['suggestions']}")
```

## 质量标准

### 生成质量指标
- **字数完整性**：800-2000字范围内
- **结构完整性**：包含开头、发展、高潮、结局
- **关键词融入**：所有关键词都被自然使用
- **语言质量**：流畅、符合中文表达习惯
- **内容安全**：符合道德和法律规范

### 性能指标
- **响应时间**：60秒内完成生成
- **成功率**：≥95%
- **重试率**：<5%（第一次成功率≥95%）
- **质量评分**：≥70分为合格

## 文件结构

```
projects/short_story_agent/
├── agents/
│   ├── requirements_analyzer/
│   │   ├── requirements_analyzer.json          # 需求分析文档
│   │   ├── system_architect.json              # 系统架构设计
│   │   ├── agent_designer.json                # Agent设计
│   │   ├── prompt_engineer.json               # 提示词工程
│   │   ├── tools_developer.json               # 工具开发规范
│   │   └── agent_code_developer.json          # Agent代码实现
│   └── generated_agents/
│       └── short_story_agent/
│           ├── story_generator_agent.py       # 主Agent类
│           ├── tool_manager.py                # 工具管理器
│           ├── prompt_manager.py              # 提示词管理器
│           ├── generation_manager.py          # 生成管理器
│           └── error_handler.py               # 错误处理器
├── tools/
│   └── generated_tools/
│       ├── input_validator.py                 # 输入验证工具
│       ├── text_processor.py                  # 文本处理工具
│       ├── prompt_builder.py                  # 提示词构建工具
│       ├── llm_caller.py                      # LLM调用工具
│       ├── content_validator.py               # 内容验证工具
│       └── output_formatter.py                # 输出格式化工具
├── prompts/
│   └── generated_agents_prompts/
│       └── story_generator_prompt_template.yaml    # 提示词模板
├── config.yaml                                # 项目配置
├── requirements.txt                           # Python依赖
├── README.md                                  # 项目说明（本文档）
└── status.yaml                                # 项目状态追踪

```

## 开发文档

### 设计文档位置
- **需求分析**：`projects/short_story_agent/agents/requirements_analyzer/requirements_analyzer.json`
- **系统架构**：`projects/short_story_agent/agents/requirements_analyzer/system_architect.json`
- **Agent设计**：`projects/short_story_agent/agents/requirements_analyzer/agent_designer.json`
- **提示词工程**：`projects/short_story_agent/agents/requirements_analyzer/prompt_engineer.json`
- **工具开发**：`projects/short_story_agent/agents/requirements_analyzer/tools_developer.json`
- **代码开发**：`projects/short_story_agent/agents/requirements_analyzer/agent_code_developer.json`

## 后续开发建议

### 短期优化（Phase 2）
1. 实现实际的Python代码文件（当前为设计文档）
2. 进行单元测试和集成测试
3. 优化提示词模板，提高生成质量
4. 添加更多文学风格模板

### 中期扩展（Phase 3）
1. 支持多轮交互和故事修改
2. 添加用户反馈机制
3. 实现故事评分和排名功能
4. 支持批量故事生成

### 长期规划（Phase 4）
1. 支持其他语言（英文、日文等）
2. 与内容平台集成
3. 实现故事推荐系统
4. 开发Web/移动应用前端

## 测试清单

### 功能测试
- [ ] 有效输入的故事生成
- [ ] 边界条件测试（最小/最大字数、关键词数）
- [ ] 错误输入处理
- [ ] 各种文学风格生成
- [ ] 关键词融入验证

### 性能测试
- [ ] 响应时间测试（目标<60秒）
- [ ] 并发请求处理
- [ ] 内存使用情况
- [ ] API调用成本监控

### 质量测试
- [ ] 生成内容的可读性
- [ ] 故事结构完整性
- [ ] 关键词自然融入度
- [ ] 内容安全检测

## 注意事项

1. **API成本控制**：使用Claude-Opus会产生较高的API调用成本，建议监控使用情况
2. **超时处理**：生成超过60秒会返回超时错误，建议用户重试或调整输入
3. **内容安全**：系统包含内容安全检测，但仍建议在生产环境中进行额外的审核
4. **并发限制**：建议控制并发请求数量，避免API限流
5. **关键词质量**：关键词质量直接影响故事生成质量，建议选择有意义的关键词

## 联系和支持

如有问题或建议，请参考设计文档或联系项目维护者。

---

**项目状态**: ✅ 设计完成  
**最后更新**: 2025-11-23  
**版本**: 1.0.0


## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-11-23 03:09:03 UTC*
