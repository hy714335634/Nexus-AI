# tv_show_search

## 项目描述
一个帮助用户搜索电视节目的智能体，可以根据用户需求查找相关电视节目信息

## 项目结构
```
tv_show_search/
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
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/tv_show_search/agents/requirements_analyzer/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/tv_show_search/agents/requirements_analyzer/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/tv_show_search/agents/requirements_analyzer/agent_designer.json)
- **prompt_engineer**: ✅ 已完成
- **tools_developer**: ✅ 已完成
- **agent_code_developer**: ✅ 已完成
- **agent_developer_manager**: ✅ 已完成

## 附加信息
# TV Show Search Agent

## 项目概述
TV Show Search Agent是一个智能助手，帮助用户搜索和获取电视节目信息。该Agent可以通过节目名称和类型进行搜索，提供电视节目的详细信息，包括播出时间、频道、剧情简介等内容，并以用户友好的方式展示结果。

## 功能特点
- **节目名称搜索**：通过节目名称或关键词搜索电视节目
- **类型搜索**：通过节目类型/类别（如综艺、新闻、剧集等）搜索电视节目
- **详细信息展示**：提供节目的详细信息，包括播出时间、频道、剧情简介、演员/主持人等
- **结果排序**：支持按相关性或播出时间排序搜索结果
- **错误处理**：优雅处理API错误和无结果情况，提供搜索建议

## 项目结构
```
tv_show_search/
├── agents/
│   └── tv_show_search_agent.py    # Agent主要实现代码
├── tools/
│   └── tv_show_api.py             # 电视节目搜索API工具
├── prompts/
│   └── tv_show_search_agent_prompt.txt  # Agent提示词模板
├── requirements.txt               # 项目依赖
└── README.md                      # 项目说明文档
```

## 技术架构
- **框架**：Strands SDK
- **模型**：Anthropic Claude 3 Sonnet
- **数据源**：模拟电视节目数据（可替换为真实API）
- **主要依赖**：
  - strands>=0.1.0
  - requests>=2.28.0
  - python-dateutil>=2.8.2

## 安装指南
1. 克隆项目仓库到本地
2. 进入项目目录: `cd tv_show_search`
3. 安装依赖: `pip install -r requirements.txt`
4. 确保所有文件在正确的路径下

## 使用示例
以下是一些使用示例：

1. **搜索综艺节目**
   ```
   用户: "我想看综艺节目"
   Agent: *调用tv_show_api搜索综艺类型节目*
   Agent: "我找到了以下综艺节目：
   1. 天天向上 - 湖南卫视，周日 20:00
   2. 奔跑吧 - 浙江卫视，周五 20:30
   3. 王牌对王牌 - 浙江卫视，周五 20:30
   您对哪个节目感兴趣？我可以提供更详细的信息。"
   ```

2. **获取节目详情**
   ```
   用户: "给我介绍一下天天向上"
   Agent: *调用tv_show_api获取节目详情*
   Agent: "《天天向上》是湖南卫视的一档综艺节目，每周日晚上20:00播出。这是一档以年轻人的生活方式为中心的文化类脱口秀节目。主持人包括汪涵、钱枫和大张伟。该节目已经播出了15季。"
   ```

3. **查询节目类型**
   ```
   用户: "有哪些类型的电视节目"
   Agent: *调用tv_show_api获取所有节目类型*
   Agent: "可用的电视节目类型（共7种）：
   
   综艺、新闻、剧集、文化、脱口秀、纪录片、真人秀
   
   您可以输入"搜索[类型名称]类型的节目"来查看特定类型的节目。"
   ```

## 开发状态
项目已完成所有开发阶段：
- ✅ 需求分析
- ✅ 系统架构设计
- ✅ Agent设计
- ✅ 工具开发
- ✅ 提示词工程
- ✅ Agent代码开发
- ✅ 开发管理与集成测试

## 注意事项
- 当前版本使用模拟数据，实际应用中应替换为真实的电视节目数据API
- 缓存仅在内存中，重启后会丢失
- 搜索算法相对简单，可以进一步优化

## 未来计划
- 集成真实的电视节目数据API
- 实现个性化推荐功能
- 添加更多筛选选项（如按时间段、频道等）
- 实现节目提醒功能
- 优化搜索算法和结果展示

## 贡献指南
欢迎对项目进行改进和扩展。请遵循以下步骤：
1. Fork项目仓库
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 许可证
[MIT License](LICENSE)

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-09-24 13:06:59 UTC*
