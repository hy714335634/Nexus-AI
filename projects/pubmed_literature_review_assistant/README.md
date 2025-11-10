# pubmed_literature_review_agent

## 项目描述
专业的科研文献/报告审核Agent，能根据用户提供完整文献，结合在线检索PMC文献的工具，进行犀利的评价与反馈

## 项目结构
```
pubmed_literature_review_agent/
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

#### pubmed_literature_reviewer
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/pubmed_literature_review_agent/agents/pubmed_literature_reviewer/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/pubmed_literature_review_agent/agents/pubmed_literature_reviewer/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/pubmed_literature_review_agent/agents/pubmed_literature_reviewer/agent_designer.json)
- **prompt_engineer**: ✅ 已完成
- **tools_developer**: ✅ 已完成
- **agent_code_developer**: ✅ 已完成
- **agent_developer_manager**: ✅ 已完成

## 附加信息
# PubMed Literature Review Agent

## 项目概述
PubMed Literature Review Agent 是一个专业的科研文献/报告审核智能体，能够根据用户提供的完整文献，结合在线检索PMC文献的工具，进行犀利的评价与反馈。该智能体从审稿人的角度对科研文献进行全面评估，提供结构化的反馈，帮助作者改进文献质量。

## 核心功能
- **多维度评估**：从科学准确性、方法论合理性、结论有效性、创新性、完整性等多个维度评估文献质量
- **PMC文献验证**：利用PMC文献检索工具验证文献中的关键声明和数据
- **幻觉检测**：识别文献中可能存在的幻觉或未经验证的声明
- **JSON结构化输出**：提供结构化的评估结果，便于理解和处理
- **修正指导**：为作者提供具体的修正和更新建议
- **研究ID支持**：通过research_id参数指定缓存和上下文工作目录，实现多次交互的连贯性

## 项目结构
```
pubmed_literature_review_agent/
├── agents/
│   └── pubmed_literature_reviewer.py     # 主Agent代码
├── prompts/
│   └── pubmed_literature_reviewer_prompt.yaml  # Agent提示词模板
├── tools/
│   ├── pmc_literature_search.py          # PMC文献检索工具
│   ├── literature_analyzer.py            # 文献分析工具
│   └── assessment_formatter.py           # 评估结果格式化工具
├── config.yaml                           # 项目配置文件
├── requirements.txt                      # Python依赖文件
└── README.md                             # 项目说明文档
```

## 使用方法

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行Agent
```bash
python agents/pubmed_literature_reviewer.py -f <文献文件路径> -r <研究ID> -m <操作模式>
```

### 参数说明
- `-f, --file`: 文献文件路径
- `-c, --claim`: 需要验证的声明，多个声明用逗号分隔
- `-r, --research_id`: 研究ID，用于指定缓存和上下文工作目录
- `-m, --mode`: 操作模式
  - `review`: 评审文献（默认）
  - `verify`: 验证特定声明
  - `history`: 查看评估历史
  - `compare`: 比较两篇文献
- `-c1, --compare1`: 比较模式下的第一篇文献文件路径
- `-c2, --compare2`: 比较模式下的第二篇文献文件路径
- `--session_id`: 可选：指定session_id

### 示例
1. 评审文献
```bash
python agents/pubmed_literature_reviewer.py -f path/to/paper.txt -r research123
```

2. 验证特定声明
```bash
python agents/pubmed_literature_reviewer.py -c "该药物可以显著降低血压" -r research123 -m verify
```

3. 查看评估历史
```bash
python agents/pubmed_literature_reviewer.py -r research123 -m history
```

4. 比较两篇文献
```bash
python agents/pubmed_literature_reviewer.py -m compare -c1 path/to/paper1.txt -c2 path/to/paper2.txt -r research123
```

## 输出格式
Agent返回的评估结果采用JSON格式，包含以下主要字段：
- `overall_score`: 文献总体评分（0-100）
- `dimensions`: 各维度评分和详细分析
  - `scientific_accuracy`: 科学准确性
  - `methodology`: 方法论合理性
  - `conclusion_validity`: 结论有效性
  - `innovation`: 创新性
  - `completeness`: 完整性
- `issues`: 发现的问题列表，包括位置、描述和严重程度
- `suggestions`: 修正建议列表，包括针对的问题和具体建议
- `metadata`: 评估元数据，包括评估时间、文献标题等

## 缓存机制
当提供research_id参数时，Agent会在`.cache/pmc_literature/<research_id>/`目录下存储相关数据，包括：
- 文献内容
- PMC检索结果
- 评估结果
- 历史记录

这使得用户可以在多次交互中保持上下文连贯性，并查看历史评估记录。

## 注意事项
- Agent依赖PMC文献检索工具的可用性和准确性
- 受限于大语言模型的上下文长度限制，超长文献可能需要分段处理
- Agent不能替代人类专家的专业审稿，仅作为辅助工具
- 仅支持文本格式的文献内容，不支持图表和图像的直接分析

## 开发状态
- [x] 需求分析
- [x] 系统架构设计
- [x] Agent设计
- [x] 提示词工程
- [x] 工具开发
- [x] Agent代码开发
- [x] Agent开发管理

## 许可证
MIT License

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-10-29 02:53:09 UTC*
