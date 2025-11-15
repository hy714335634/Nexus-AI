"""
GraphRAG 索引构建器
使用 Agent Classifier Agent 自动分类和生成文档
"""

import yaml
import os
import sys
import asyncio
from typing import Dict, List
from llama_index.core import Document
from graphrag_toolkit.lexical_graph import LexicalGraphIndex
from graphrag_toolkit.lexical_graph import GraphRAGConfig as ToolkitConfig
from graphrag_toolkit.lexical_graph.storage import GraphStoreFactory, VectorStoreFactory
from graphrag_toolkit.lexical_graph import IndexingConfig
from llama_index.core.node_parser import SentenceSplitter
import nest_asyncio

from graphrag_config import GraphRAGConfig

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入 Agent Classifier
from agents.system_agents.agent_classifier.agent_classifier import agent_classifier

# 允许嵌套事件循环
nest_asyncio.apply()


class AgentTemplateIndexer:
    """
    Agent 模板索引构建器

    功能：
    1. 使用 Agent Classifier Agent 自动分类
    2. LLM 驱动的分类，更智能、更准确
    3. 自动生成高质量文档
    4. 构建图索引和向量索引
    """

    def __init__(self, config: GraphRAGConfig):
        """
        初始化索引构建器

        Args:
            config: GraphRAG 配置对象
        """
        self.config = config

        print("初始化 AgentTemplateIndexer")
        print(f"   配置文件: {config.agent_config_path}")

        # 配置 GraphRAG Toolkit 模型（必须在创建 LexicalGraphIndex 之前）
        print(f"   配置 LLM 模型: {config.llm_model}")
        ToolkitConfig.extraction_llm = config.llm_model
        ToolkitConfig.response_llm = config.llm_model

        print(f"   配置 Embedding 模型: {config.embedding_model}")
        ToolkitConfig.embed_model = config.embedding_model
        ToolkitConfig.embed_dimensions = config.embedding_dimensions

        # 初始化 Graph Store
        print(f"   连接 Neptune: {config.get_neptune_connection_string()}")
        self.graph_store = GraphStoreFactory.for_graph_store(
            config.get_neptune_connection_string()
        )

        # 初始化 Vector Store
        print(f"   连接向量存储: {config.get_vector_store_connection_string()}")
        self.vector_store = VectorStoreFactory.for_vector_store(
            config.get_vector_store_connection_string()
        )

        # 初始化 LexicalGraphIndex
        print(f"   创建 LexicalGraphIndex")
        self.graph_index = LexicalGraphIndex(
            self.graph_store,
            self.vector_store
        )

        # 初始化 Agent Classifier
        print(f"   初始化 Agent Classifier")
        self.classifier = agent_classifier

        # 加载配置
        self.agent_config = self._load_agent_config()
        print(f"   [OK] 加载了 {len(self.agent_config.get('templates', {}))} 个 agent 模板\n")

    def _load_agent_config(self) -> Dict:
        """加载 agent 配置文件"""
        config_path = self.config.agent_config_path

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    async def _classify_and_document_agent(
        self,
        agent_id: str,
        agent_data: Dict
    ) -> Document:
        """
        使用 Agent Classifier 分类并生成文档

        Args:
            agent_id: Agent ID
            agent_data: Agent 配置数据

        Returns:
            Document 对象
        """
        # 调用 Agent Classifier
        result = await self.classifier.classify_and_document(
            agent_id=agent_id,
            agent_config=agent_data
        )

        # 提取分类信息
        classification = result['classification']
        document_text = result['document']

        # 创建 Document 对象
        # 元数据用于过滤，文本用于检索和生成
        metadata = {
            'agent_id': agent_id,
            'name': agent_data['name'],
            'type': 'agent_template',
            'tags': agent_data.get('tags', []),
            # 分类信息
            'core_functions': classification.get('core_functions', []),
            'business_scenario': classification.get('business_scenario', ''),
            'business_scenario_cn': classification.get('business_scenario_cn', ''),
            'industries': classification.get('industries', []),
            'subcategories': classification.get('subcategories', []),
            'use_cases': classification.get('use_cases', [])
        }

        return Document(
            text=document_text,
            metadata=metadata,
            id_=agent_id
        )

    def build_index(self, show_progress: bool = True) -> bool:
        """
        构建 GraphRAG 索引

        流程：
        1. 使用 Agent Classifier 分类每个 agent
        2. 生成高质量文档
        3. 调用 LexicalGraph.extract_and_build()
        4. LLM 自动提取实体、关系、statements
        5. 构建图结构和向量索引

        Args:
            show_progress: 是否显示进度

        Returns:
            是否成功
        """
        print("=" * 70)
        print("开始构建 Agent Template GraphRAG 索引")
        print("=" * 70)

        # 转换所有 agent 为文档
        documents = []
        templates = self.agent_config.get('templates', {})

        print(f"\n步骤 1/2: 使用 Agent Classifier 分类并生成文档")
        print(f"   共 {len(templates)} 个 agent 模板\n")

        # 创建异步任务
        async def process_all_agents():
            tasks = []
            agent_list = list(templates.items())

            for i, (agent_id, agent_data) in enumerate(agent_list, 1):
                print(f"   [{i:2d}/{len(templates)}] 处理 {agent_id:40s}")

                try:
                    # 调用 Agent Classifier（异步）
                    doc = await self._classify_and_document_agent(agent_id, agent_data)
                    documents.append(doc)

                    # 显示分类结果
                    if doc.metadata.get('core_functions'):
                        print(f"        |-- 核心功能: {', '.join(doc.metadata['core_functions'][:2])}")
                    if doc.metadata.get('business_scenario_cn'):
                        print(f"        |-- 业务场景: {doc.metadata['business_scenario_cn']}")
                    if doc.metadata.get('industries'):
                        print(f"        `-- 行业领域: {', '.join(doc.metadata['industries'][:2])}")

                    print(f"   [{i:2d}/{len(templates)}] [OK] {agent_id:40s}\n")

                except Exception as e:
                    print(f"   [{i:2d}/{len(templates)}] [ERROR] {agent_id:40s} - 错误: {e}\n")

        # 运行异步任务
        asyncio.run(process_all_agents())

        if not documents:
            print("\n[ERROR] 没有文档可以索引")
            return False

        # 使用 LexicalGraph 自动提取并构建图
        print(f"\n步骤 2/2: 使用 LLM 自动提取图结构并构建索引")
        print("   这个过程会：")
        print("   1. 使用 LLM 分析每个文档")
        print("   2. 自动提取实体（agents, tools, categories）")
        print("   3. 自动识别关系（depends_on, uses, belongs_to）")
        print("   4. 构建层次化图结构")
        print("   5. 生成向量嵌入用于语义搜索")
        print(f"\n   开始处理（共 {len(documents)} 个文档）...\n")

        try:
            # extract_and_build 会自动完成所有工作
            self.graph_index.extract_and_build(
                documents,
                show_progress=show_progress
            )

            print("\n" + "=" * 70)
            print("[SUCCESS] 索引构建完成！")
            print("=" * 70)
            print(f"\n统计信息:")
            print(f"   * 处理文档数: {len(documents)}")
            print(f"   * 使用 Agent Classifier: 是")
            print(f"   * 图结构: 已自动提取")
            print(f"   * 向量索引: 已构建")
            print(f"\n现在可以使用自然语言查询了！")

            return True

        except Exception as e:
            print(f"\n[ERROR] 索引构建失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_agent(self, agent_id: str) -> bool:
        """
        增量更新单个 agent

        Args:
            agent_id: 要更新的 agent ID

        Returns:
            是否成功
        """
        templates = self.agent_config.get('templates', {})

        if agent_id not in templates:
            print(f"[ERROR] Agent {agent_id} 不存在")
            return False

        print(f"更新 agent: {agent_id}")

        # 删除旧的
        try:
            self.graph_index.delete(doc_id=agent_id)
            print(f"   [OK] 删除旧索引")
        except Exception as e:
            print(f"   [WARNING] 删除旧索引失败: {e}")

        # 创建新文档
        agent_data = templates[agent_id]

        async def update_single_agent():
            doc = await self._classify_and_document_agent(agent_id, agent_data)
            return doc

        doc = asyncio.run(update_single_agent())

        # 插入新的
        try:
            self.graph_index.insert([doc])
            print(f"   [OK] 插入新索引")
            return True
        except Exception as e:
            print(f"   [ERROR] 插入新索引失败: {e}")
            return False


def main():
    """主函数：构建索引"""
    # 加载配置
    config = GraphRAGConfig.from_env()
    config.print_config()

    # 验证配置
    if not config.validate():
        print("\n[ERROR] 配置验证失败，请检查环境变量")
        return

    # 创建索引器
    indexer = AgentTemplateIndexer(config)

    # 构建索引
    success = indexer.build_index(show_progress=True)

    if success:
        print("\n[SUCCESS] 索引构建成功！")
    else:
        print("\n[ERROR] 索引构建失败")


if __name__ == "__main__":
    main()
