# GraphRAG 快速启动指南

5分钟快速上手 Agent Template GraphRAG 系统。

## 📦 第一步：安装依赖

```bash
cd /Users/peijiaw/Desktop/git_repos/Nexus-AI/agents/template_agents

pip install -r requirements_graphrag.txt
```

## ⚙️ 第二步：配置环境

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量（必需！）
export NEPTUNE_ENDPOINT="your-cluster.us-east-1.neptune.amazonaws.com:8182"
export VECTOR_STORE_ENDPOINT="https://your-aoss.us-east-1.aoss.amazonaws.com"
export OPENAI_API_KEY="sk-..."
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
```

## 🔨 第三步：构建索引

```bash
# 一键构建
python build_index.py
```

这个过程需要几分钟，会：
1. 读取所有 Agent 配置
2. 使用 LLM 自动提取图结构
3. 构建索引

## 🔍 第四步：开始查询

```bash
# 运行示例
python query_examples.py
```

或者在代码中使用：

```python
from graphrag_config import GraphRAGConfig
from graphrag_query_engine import AgentTemplateQueryEngine

# 初始化
config = GraphRAGConfig.from_env()
engine = AgentTemplateQueryEngine(config)

# 查询
result = engine.query("我需要一个能处理PDF的agent")
print(result.get_answer())
```

## 💡 常用查询示例

```python
# 1. 功能搜索
engine.search_by_function("分析医学文献")

# 2. 行业搜索
engine.search_by_industry("医疗健康")

# 3. 任务推荐
engine.recommend_for_task("从PubMed检索文献然后翻译成中文")

# 4. 查找依赖
engine.find_dependencies("pubmed_literature_agent")

# 5. 自定义查询
engine.query("哪些agent既能处理文档又能生成报告？")
```

## 🎯 下一步

- 📖 查看 [完整文档](README_GRAPHRAG.md)
- 🧪 试试 [12种查询示例](query_examples.py)
- 🔧 自定义你的查询需求

## ❓ 遇到问题？

1. **连接失败**：检查 Neptune 和 AOSS 端点配置
2. **索引构建慢**：使用 `gpt-3.5-turbo` 而不是 `gpt-4`
3. **查询不准确**：优化 Agent 描述，添加更多分类信息

详见 [故障排查](README_GRAPHRAG.md#故障排查)

---

**就这么简单！开始使用 GraphRAG 管理你的 Agent 吧！** 🚀
