# Nexus-AI GraphRAG MCP Server

基于AWS GraphRAG Toolkit的MCP服务器，为Nexus-AI平台提供Agent发现和推荐服务。

## 文件说明

### 核心文件
- `nexus_graphrag_mcp_server_fixed.py` - 修正版MCP服务器（推荐使用）
- `nexus_graphrag_mcp_server.py` - 原始版本MCP服务器
- `test_mcp_client.py` - MCP客户端测试脚本

### 配置文件
- `nexus_graphrag_mcp_config.json` - MCP服务器配置
- `nexus_graphrag_mcp_server_simple.py` - 简化版服务器

## 使用方法

### 1. 启动MCP服务器

```bash
cd /path/to/Nexus-AI/agents/template_agents
source .venv/bin/activate
export AWS_DEFAULT_REGION=us-east-1
cd ../../mcp
python nexus_graphrag_mcp_server_fixed.py
```

### 2. 测试MCP客户端

```bash
cd /path/to/Nexus-AI/agents/template_agents
source .venv/bin/activate
export AWS_DEFAULT_REGION=us-east-1
cd ../../mcp
python test_mcp_client.py
```

## 配置要求

### 环境变量
- `AWS_DEFAULT_REGION=us-east-1`
- 确保AWS凭证已配置

### 依赖包
- `fastmcp`
- `strands-agents`
- `graphrag-toolkit`

### 网络连接
- Neptune: `graphrag-toolkit-cluster.cluster-c9m8ameewg4p.us-east-1.neptune.amazonaws.com`
- OpenSearch Serverless: `https://e7d817u9qpa3uf4pbtmk.us-east-1.aoss.amazonaws.com`

## 功能特性

### MCP工具
1. **default_** - 主要的GraphRAG查询工具
   - 企业AI Agent系统知识库
   - 支持文档处理、数据分析、API集成等领域查询
   
2. **search_** - 搜索工具推荐器
   - 根据搜索词推荐相关工具

### 查询示例
- "找一个把html转化为pdf的工具"
- "我需要处理医学文档的Agent"
- "有没有能做AWS架构设计的Agent？"

## 测试结果

✅ MCP连接成功
✅ GraphRAG查询成功
✅ 智能Agent推荐成功
✅ 支持自然语言查询
✅ 提供详细使用建议

## 架构说明

```
MCP Client (Strands Agent) 
    ↓ HTTP
MCP Server (FastMCP)
    ↓ GraphRAG Toolkit
Neptune (图数据库) + OpenSearch Serverless (向量数据库)
```

服务器地址: `http://localhost:8000/mcp/`
