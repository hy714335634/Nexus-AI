# pubmed_literature_editor_assistant

## 项目描述
专业的科研期刊主编Agent，能根据用户提供完整文献，结合在线检索PMC文献的工具，完成杂志主编对文章的评审工作

## 项目结构
```
pubmed_literature_editor_assistant/
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

#### pubmed_literature_editor_assistant
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/pubmed_literature_editor_assistant/agents/pubmed_literature_editor_assistant/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/pubmed_literature_editor_assistant/agents/pubmed_literature_editor_assistant/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/pubmed_literature_editor_assistant/agents/pubmed_literature_editor_assistant/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/pubmed_literature_editor_assistant/agents/pubmed_literature_editor_assistant/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](projects/pubmed_literature_editor_assistant/agents/pubmed_literature_editor_assistant/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](projects/pubmed_literature_editor_assistant/agents/pubmed_literature_editor_assistant/agent_code_developer.json)
- **agent_developer_manager**: ✅ 已完成 - [文档](projects/pubmed_literature_editor_assistant/agents/pubmed_literature_editor_assistant/agent_developer_manager.json)

## 附加信息
# PubMed Literature Editor Assistant

## 项目概述
PubMed Literature Editor Assistant 是一个专业的科研期刊主编Agent，能够根据用户提供的文献内容，结合PMC文献检索工具，完成顶级期刊杂志主编对文章的专业评审工作，提供结构化反馈和修改建议。

## 项目状态
- ✅ 需求分析：已完成
- ✅ 系统架构设计：已完成
- ✅ Agent设计：已完成
- ✅ 工具开发：已完成
- ✅ 提示词工程：已完成
- ✅ Agent代码开发：已完成
- ✅ 开发管理：已完成

## 功能特点
- 模拟顶级期刊（如Nature、Science）主编的专业视角和评审标准
- 多维度评估文献质量（研究新颖性、方法学严谨性、结果可靠性、讨论深度等）
- 评估研究话题和角度的适合性和吸引力
- 提供具体可操作的修改建议
- 输出结构化JSON格式的评审结果
- 支持research_id参数管理工作目录

## 目录结构
```
pubmed_literature_editor_assistant/
├── agents/
│   └── generated_agents/
│       └── pubmed_literature_editor_assistant/
│           └── pubmed_literature_editor_assistant.py  # Agent主代码
├── generated_agents_prompts/
│   └── pubmed_literature_editor_assistant/
│       └── pubmed_literature_editor_assistant.yaml    # Agent提示词模板
├── generated_tools/
│   └── pubmed_literature_editor_assistant/
│       ├── pmc_literature_tools.py                    # PMC文献检索和处理工具
│       ├── file_system_tools.py                       # 文件系统操作工具
│       └── json_processor.py                          # JSON处理工具
├── requirements.txt                                   # 项目依赖
└── README.md                                          # 项目说明文档
```

## 使用方式
### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行Agent
```bash
python agents/generated_agents/pubmed_literature_editor_assistant/pubmed_literature_editor_assistant.py -f <文献文件路径> -r <research_id> -v <版本号>
```

### 参数说明
- `-f`: 文献文件路径（必需）
- `-r`: 研究ID，如果不提供则自动生成
- `-v`: 版本号，默认为"v1"
- `-m`: 操作模式，默认为"review"
- `--session_id`: 可选，指定session_id
- `--result_file`: 结果文件名（用于result模式）
- `--version1`: 第一个版本号（用于compare模式）
- `--version2`: 第二个版本号（用于compare模式）

## 输出结果
评审结果将以JSON格式保存在以下路径：
```
.cache/pmc_literature/<research_id>/feedback/editor/<version>/editor_<version>_<timestamp>.json
```

处理状态将保存在：
```
.cache/pmc_literature/<research_id>/step6.status
```

## 评审维度
Agent从以下维度对文献进行评估：
1. 原创性与创新性
2. 方法学严谨性
3. 结果可靠性与有效性
4. 讨论深度与洞见
5. 学术影响力与重要性
6. 表达质量与结构
7. 文献引用完整性

## 注意事项
- 本Agent仅提供评审建议，不保证文章一定能被特定期刊接受
- 不进行文献的语法或拼写检查
- 不提供全文改写服务
- 不代替作者进行实质性内容创作
- 不进行抄袭检测

## 技术实现
- 基于Anthropic Claude 3模型
- 集成PMC文献检索工具
- 使用Strands SDK开发
- 结构化JSON输出

## 开发团队
- 需求分析师
- 系统架构师
- Agent设计师
- 工具开发工程师
- 提示词工程师
- Agent代码开发工程师
- Agent开发管理员

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-10-30 18:05:06 UTC*
