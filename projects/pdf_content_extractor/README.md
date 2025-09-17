# pdf_content_extractor

## 项目描述
一个能够处理PDF文件并提取文本内容的智能Agent，支持PDF转图片、多模态文本提取和断点续传功能。

## 项目结构
```
pdf_content_extractor/
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
# PDF Content Extractor

这是一个能够从PDF文件中提取文本内容的智能Agent。

## 功能特点

1. **PDF处理**：将PDF文件转换为图片，按页码存储在.cache目录中
2. **多模态文本提取**：使用多模态Agent从图片中提取文本内容
3. **断点续传**：支持处理中断后从断点继续的功能
4. **结果合并**：将所有页面的文本内容合并成一个完整的TXT文件

## 处理流程

1. 接收PDF文件路径
2. 检查处理进度，决定是从头开始还是从断点继续
3. 将PDF转换为图片，并存储在.cache目录
4. 使用多模态Agent分析每页图片并提取文本
5. 将所有页面的文本合并成一个完整的TXT文件
6. 返回处理结果

## 技术实现

- 使用Strands SDK构建Agent
- 通过多模态分析Agent提取图片中的文本
- 使用Python进行文件操作和进度管理
- 基于AWS Bedrock作为AI推理引擎

## 用户原始需求

请构建一个文件内容提取Agent，能够根据给定的PDF路径，处理PDF文件，提取每一页的文本内容，并生成最终的txt格式文件。
要求如下：
1. 处理时先将pdf转成图片，存储在.cache目录中，按页码命名
2. 通过多模态agent提取图片内容信息保存成txt，按页码命名
3. 多模态Agent请通过如下方式构建并使用,关键python代码:
   ```python
   multimodal_analyzer = create_agent_from_prompt_template(
       agent_name="system_agents_prompts/multimodal_analysis/multimodal_analyzer_agent", 
       **agent_params
   )
   test_input = "文件分析请求: {文件路径},分析/处理要求: {要求}"
   result = multimodal_analyzer(test_input)
   ```
4. 所有页面处理完成后合并成完整txt文件
5. 需要管理pdf处理进度，当处理中断时，再次运行脚本指定同样pdf路径，应能从断点继续

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-09-12 09:23:07 UTC*
