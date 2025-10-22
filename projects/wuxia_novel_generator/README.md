# wuxia_novel_generator

## 项目描述
武侠小说生成Agent系统，能够根据用户输入的设定（如人物、门派、武功、情节线索等）自动生成符合武侠风格的小说内容，包括完整的故事情节、人物对话、武打场面描写等。具备世界观一致性、情节连贯性、武侠文体风格和创意与套路平衡等特点。

## 项目结构
```
wuxia_novel_generator/
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

#### requirements_analyzer
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/wuxia_novel_generator/agents/requirements_analyzer/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/wuxia_novel_generator/agents/requirements_analyzer/system_architect.json)
- **agent_designer**: ✅ 已完成
- **prompt_engineer**: ✅ 已完成 - [文档](projects/wuxia_novel_generator/agents/requirements_analyzer/prompt_engineer.json)
- **tools_developer**: ✅ 已完成
- **agent_code_developer**: ✅ 已完成 - [文档](projects/wuxia_novel_generator/agents/requirements_analyzer/agent_code_developer.json)
- **agent_developer_manager**: ✅ 已完成 - [文档](projects/wuxia_novel_generator/agents/requirements_analyzer/agent_developer_manager.json)

## 附加信息
# 武侠小说生成Agent

## 项目概述

武侠小说生成Agent是一个专门用于创作武侠小说的智能Agent系统，能够根据用户输入的设定（如人物、门派、武功、情节线索等）自动生成符合武侠风格的小说内容，包括完整的故事情节、人物对话、武打场面描写等。

### 核心特点

1. **世界观一致性**
   - 维护统一的武侠世界观设定（时代背景、江湖势力、武功体系）
   - 确保前后文中的门派、武功、地理位置等设定不冲突
   - 人物性格、能力在整个故事中保持连贯

2. **情节连贯性**
   - 具备长期记忆能力，记住之前章节的关键情节
   - 伏笔和铺垫能在后续章节中呼应
   - 避免情节突兀转折或逻辑矛盾

3. **武侠文体风格**
   - 语言风格符合武侠小说特点（古风、江湖气息）
   - 武打场面描写生动、有画面感
   - 人物对话符合身份和时代背景

4. **创意与套路平衡**
   - 遵循武侠小说的经典套路（如奇遇、复仇、争霸）
   - 同时保持创新元素，避免千篇一律

## 项目结构

```
wuxia_novel_generator/
├── agents/                            # Agent代码目录
│   └── generated_agents/
│       └── wuxia_novel_generator/     # 武侠小说生成Agent
│           └── wuxia_novel_generator.py
├── prompts/                           # 提示词模板目录
│   └── generated_agents_prompts/
│       └── wuxia_novel_generator/
│           └── wuxia_novel_generator_prompt.yaml
├── tools/                             # 工具代码目录
│   └── generated_tools/
│       └── wuxia_novel_generator/     # 武侠小说生成工具
│           ├── character_manager.py   # 角色管理工具
│           ├── character_relationships.py
│           ├── character_search.py
│           ├── character_tools.py
│           ├── character_tools_extended.py
│           ├── character_update.py
│           ├── content_generator.py   # 内容生成工具
│           ├── export_tools.py        # 导出工具
│           ├── novel_manager.py       # 小说管理工具
│           ├── plot_base.py           # 情节基础工具
│           ├── plot_chapters.py       # 章节管理工具
│           ├── plot_manager.py        # 情节管理工具
│           ├── plot_update.py
│           ├── worldbuilding_elements.py # 世界观元素工具
│           └── worldbuilding_manager.py  # 世界观管理工具
├── projects/                          # 项目文档目录
│   └── wuxia_novel_generator/
│       ├── agents/                    # Agent开发文档
│       ├── config.yaml                # 项目配置文件
│       ├── README.md                  # 项目说明文档
│       ├── requirements.txt           # 项目依赖
│       └── status.yaml                # 项目状态文件
```

## 核心功能

1. **角色管理系统**
   - 创建和管理主角、配角的详细档案（姓名、门派、武功、性格、关系网）
   - 确保角色行为符合其设定的性格和能力
   - 支持角色关系网络管理

2. **武功体系管理**
   - 定义和管理各种武功招式、内功心法及其威力等级
   - 支持武功对决和特殊效果描述
   - 维护武功来源和流派的一致性

3. **情节规划系统**
   - 设计故事大纲、章节结构、关键转折点
   - 管理伏笔和铺垫，确保后续呼应
   - 支持多线索并行发展

4. **场景生成系统**
   - 根据情节需要生成不同场景描写（客栈、山林、武馆、密室等）
   - 确保场景描述符合时代背景
   - 维护地理位置的一致性

5. **对话生成系统**
   - 根据人物性格生成符合身份的对话内容
   - 支持多人对话场景
   - 调整对话风格以适应不同场合

6. **战斗编排系统**
   - 设计武打场面的招式对决、胜负走向
   - 生成生动的战斗描写
   - 考虑角色武功特性和战斗环境

7. **小说缓存系统**
   - 管理本地缓存，支持续写和检索
   - 建立章节索引，方便查询
   - 支持导出不同格式

## 使用方式

### 基本使用流程

1. **创建新小说**
   ```
   请帮我创作一部以明朝为背景的武侠小说，主角是一位精通轻功的女侠。
   ```

2. **续写章节**
   ```
   请继续写《飞燕惊鸿》的第二章。
   ```

3. **查询内容**
   ```
   请告诉我《飞燕惊鸿》中李飞燕的武功特点。
   ```

4. **调整设定**
   ```
   请将主角的武功路线改为偏向内功心法。
   ```

### 高级功能

1. **多版本情节选择**
   ```
   请为下一个情节提供三种不同的发展方向。
   ```

2. **风格模仿**
   ```
   请用金庸风格继续创作这部小说。
   ```

3. **导出功能**
   ```
   请将《飞燕惊鸿》导出为txt格式。
   ```

## 技术特点

- **长期记忆机制**：至少记住最近5-10个章节的内容
- **世界观一致性检查**：自动检测和修正设定冲突
- **情节连贯性维护**：确保伏笔和铺垫在后续章节中呼应
- **武侠知识库检索**：查询武侠常见元素（兵器、毒药、穴位、地名等）
- **本地缓存索引**：支持检索和续写已有小说

## 系统要求

- Python 3.13+
- 依赖包详见requirements.txt

## 注意事项

1. 输出格式限定为txt格式
2. 系统会自动审核内容，避免过度暴力、色情等不适内容
3. 生成内容保证原创性，避免抄袭现有作品
4. 在用户未指定小说名字时，系统会自动推荐名称
5. 续写功能需要通过小说名称检索本地缓存

## 开发状态

项目已完成全部开发阶段：
- ✅ 需求分析
- ✅ 系统架构设计
- ✅ Agent设计
- ✅ 工具开发
- ✅ 提示词工程
- ✅ Agent代码开发
- ✅ 开发管理与集成

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-10-20 03:05:09 UTC*
