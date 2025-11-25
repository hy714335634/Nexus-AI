#!/usr/bin/env python3
"""Nexus-AI GraphRAG MCP 服务器"""

import os
import yaml
import logging
from pathlib import Path
from graphrag_toolkit.lexical_graph import set_advanced_logging_config
from graphrag_toolkit.lexical_graph.storage import GraphStoreFactory, VectorStoreFactory
from graphrag_toolkit.lexical_graph.protocols import create_mcp_server
from graphrag_toolkit.lexical_graph import GraphRAGConfig as ToolkitConfig

# 设置日志
set_advanced_logging_config(
    logging_level=logging.INFO,
    included_modules={
        logging.INFO: '*',
    },
    excluded_modules={
        logging.INFO: ['opensearch', 'boto', 'urllib', 'mcp', 'httpx'],
    }
)

def load_config():
    """加载配置，优先使用环境变量"""
    config_path = Path(__file__).parent / "config.yaml"
    
    # 加载配置文件
    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)['nexus_graphrag']
    
    # 环境变量覆盖配置文件
    return {
        'neptune_endpoint': os.getenv('NEPTUNE_ENDPOINT', config.get('neptune_endpoint')),
        'vector_endpoint': os.getenv('VECTOR_ENDPOINT', config.get('vector_endpoint')),
        'extraction_llm': os.getenv('EXTRACTION_LLM', config.get('models', {}).get('extraction_llm')),
        'response_llm': os.getenv('RESPONSE_LLM', config.get('models', {}).get('response_llm'))
    }

def create_nexus_mcp_server():
    """创建 Nexus-AI GraphRAG MCP 服务器"""
    
    config = load_config()
    
    print(f"Neptune: {config['neptune_endpoint']}")
    print(f"Vector: {config['vector_endpoint']}")
    
    # 配置 GraphRAG Toolkit 模型
    ToolkitConfig.extraction_llm = config['extraction_llm']
    ToolkitConfig.response_llm = config['response_llm']
    
    # 创建存储连接
    graph_store = GraphStoreFactory.for_graph_store(config['neptune_endpoint'])
    vector_store = VectorStoreFactory.for_vector_store(config['vector_endpoint'])
    
    # 创建 MCP 服务器
    mcp_server = create_mcp_server(graph_store, vector_store)
    
    return mcp_server

def run_server():
    """运行 MCP 服务器"""
    print("初始化 Nexus-AI GraphRAG MCP 服务器...")
    
    try:
        mcp_server = create_nexus_mcp_server()
        print("Nexus-AI GraphRAG MCP 服务器初始化成功")
        print("启动服务器在 http://localhost:8000/mcp/")
        
        # 启动服务器
        mcp_server.run(transport='streamable-http', log_level='warning')
        
    except Exception as e:
        print(f"服务器启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_server()
