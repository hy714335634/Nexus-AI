# news_retrieval_agent

## 项目描述
一个能够根据用户关注话题检索热门新闻的智能体，支持从百度、新浪、澎湃等主流媒体获取新闻信息。

## 项目结构
```
news_retrieval_agent/
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

#### news_agent
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/news_retrieval_agent/agents/news_agent/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/news_retrieval_agent/agents/news_agent/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/news_retrieval_agent/agents/news_agent/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/news_retrieval_agent/agents/news_agent/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](projects/news_retrieval_agent/agents/news_agent/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](projects/news_retrieval_agent/agents/news_agent/agent_code_developer.json)
- **agent_developer_manager**: ✅ 已完成 - [文档](projects/news_retrieval_agent/agents/news_agent/agent_developer_manager.json)

## 附加信息
# News Retrieval Agent

## Project Overview
News Retrieval Agent is an intelligent agent that retrieves hot news based on user topics of interest from multiple mainstream media platforms including Baidu, Sina, ThePaper, and others. The agent provides news aggregation, heat-based sorting, and summary generation capabilities to help users stay informed about their topics of interest without information overload.

## Project Status
✅ Requirements Analysis: Completed  
✅ System Architecture: Completed  
✅ Agent Design: Completed  
✅ Tools Development: Completed  
✅ Prompt Engineering: Completed  
✅ Agent Code Development: Completed  
✅ Agent Development Management: Completed  

## Features
- **Topic Management**: Add, view, and delete topics of interest
- **Multi-Platform News Retrieval**: Get news from Baidu, Sina, ThePaper, and other mainstream media
- **Heat-Based Sorting**: News is sorted by popularity based on read count, comments, and publish time
- **News Summary Generation**: Concise summaries of news articles
- **User-Friendly Interaction**: Simple text-based interface for easy interaction

## Directory Structure
```
news_retrieval_agent/
├── README.md
├── config.yaml
├── agents/
│   └── news_agent/
│       ├── news_agent.py                # Main agent code
│       ├── tools/
│       │   ├── news_fetcher.py          # Tool for retrieving news from platforms
│       │   ├── heat_calculator.py       # Tool for calculating news popularity
│       │   ├── summary_generator.py     # Tool for generating news summaries
│       │   └── topic_manager.py         # Tool for managing user topics
│       ├── prompts/
│       │   └── news_agent_prompt.txt    # Agent prompt template
│       └── docs/
│           ├── requirements_analyzer.json
│           ├── system_architect.json
│           ├── agent_designer.json
│           ├── tools_developer.json
│           ├── prompt_engineer.json
│           ├── agent_code_developer.json
│           └── agent_developer_manager.json
```

## Usage Guide

### Starting the Agent
```python
from news_agent import NewsAgent

# Initialize the agent
agent = NewsAgent()

# Start interaction
agent.start()
```

### Managing Topics
```
# Add a topic
> add topic "artificial intelligence"

# View all topics
> show topics

# Delete a topic
> delete topic "artificial intelligence"
```

### Retrieving News
```
# Get news for a specific topic
> get news about "climate change"

# Get news for all followed topics
> get latest news

# Get more news for current topic
> show more news
```

## Technical Details

### Tools
1. **news_fetcher**: Retrieves news from multiple platforms with error handling for unavailable platforms
2. **heat_calculator**: Calculates and sorts news by popularity based on read count, comments, and publish time
3. **summary_generator**: Generates concise news summaries using LLM capabilities
4. **topic_manager**: Manages user topics with local storage

### Agent Capabilities
- Professional, efficient, objective news retrieval and presentation
- Multi-platform data integration and format standardization
- Heat algorithm based on read count, comments, and publish time
- Intelligent summary generation extracting core news content
- Error handling for platform unavailability and network issues

## Limitations and Future Improvements

### Current Limitations
- Limited to text-based interaction
- No historical news archiving
- No personalized news recommendations
- No complex sentiment analysis

### Future Improvements
- Add support for more news platforms
- Implement news categorization by topic
- Develop a graphical user interface
- Add personalized news recommendation features
- Implement historical news archiving and trends analysis

## Requirements
- Python 3.13+
- Strands SDK
- Internet connection for accessing news platforms

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-09-10 14:50:39 UTC*
