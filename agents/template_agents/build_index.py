#!/usr/bin/env python3
"""
构建 GraphRAG 索引的脚本
使用 Agent Classifier 自动分类

使用方法:
    python build_index.py

环境变量配置:
    export NEPTUNE_ENDPOINT="neptune-db://your-cluster.region.neptune.amazonaws.com:8182"
    export VECTOR_STORE_ENDPOINT="aoss://https://your-aoss.region.aoss.amazonaws.com"
    export AGENT_CONFIG_PATH="agent_templates_config.yaml"
"""

import sys
import os
from pathlib import Path

# 加载 .env 文件
from dotenv import load_dotenv

# 加载当前目录的 .env 文件
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

print(f"[INFO] 已加载环境变量文件: {env_path}")
print(f"[INFO] NEPTUNE_ENDPOINT: {os.getenv('NEPTUNE_ENDPOINT', 'NOT SET')}")
print(f"[INFO] VECTOR_STORE_ENDPOINT: {os.getenv('VECTOR_STORE_ENDPOINT', 'NOT SET')}\n")

from graphrag_config import GraphRAGConfig
from graphrag_indexer import AgentTemplateIndexer


def main():
    """主函数"""
    print("开始构建 Agent Template GraphRAG 索引 (使用 Agent Classifier)\n")

    # 1. 加载配置
    print("加载配置...")
    config = GraphRAGConfig.from_env()
    config.print_config()

    # 2. 验证配置
    print("\n验证配置...")
    if not config.validate():
        print("\n[ERROR] 配置验证失败！")
        print("\n请确保设置了以下环境变量：")
        print("  - NEPTUNE_ENDPOINT: Neptune 集群端点")
        print("  - VECTOR_STORE_ENDPOINT: 向量存储端点")
        print("  - AGENT_CONFIG_PATH: Agent 配置文件路径（可选）")
        print("\n示例：")
        print('  export NEPTUNE_ENDPOINT="neptune-db://my-cluster.us-east-1.neptune.amazonaws.com:8182"')
        print('  export VECTOR_STORE_ENDPOINT="aoss://https://my-aoss.us-east-1.aoss.amazonaws.com"')
        sys.exit(1)

    print("[OK] 配置验证通过")

    # 3. 创建索引器
    print("\n创建索引器（使用 Agent Classifier）...")
    try:
        indexer = AgentTemplateIndexer(config)
    except Exception as e:
        print(f"\n[ERROR] 创建索引器失败: {e}")
        sys.exit(1)

    # 4. 构建索引
    print("\n开始构建索引...")
    print("特性:")
    print("   - 使用 LLM 驱动的 Agent Classifier 自动分类")
    print("   - 更智能、更准确的分类")
    print("   - 自动生成高质量文档")
    print()

    success = indexer.build_index(show_progress=True)

    # 5. 输出结果
    if success:
        print("\n" + "="*70)
        print("[SUCCESS] 索引构建成功！")
        print("="*70)
        print("\n功能特性:")
        print("  * 使用 Agent Classifier 智能分类")
        print("  * LLM 驱动，理解语义和上下文")
        print("  * 分类更准确，文档质量更高")
        print("\n下一步:")
        print("  1. 使用 query_examples.py 测试查询")
        print("  2. 或在你的代码中导入 AgentTemplateQueryEngine 进行查询")
        print("\n示例:")
        print("  python query_examples.py")
    else:
        print("\n" + "="*70)
        print("[ERROR] 索引构建失败")
        print("="*70)
        sys.exit(1)


if __name__ == "__main__":
    main()
