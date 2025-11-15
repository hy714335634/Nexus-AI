"""
GraphRAG 查询引擎
使用自然语言查询 agent 模板
"""

from typing import List, Dict, Optional, Any
from graphrag_toolkit.lexical_graph import LexicalGraphIndex
from graphrag_toolkit.lexical_graph import GraphRAGConfig as ToolkitConfig
from graphrag_toolkit.lexical_graph.storage import GraphStoreFactory, VectorStoreFactory
import json

from graphrag_config import GraphRAGConfig


class AgentQueryResult:
    """查询结果封装类"""

    def __init__(self, response: Any):
        """
        初始化查询结果

        Args:
            response: LexicalGraph 的查询响应
        """
        self.response = response
        self.answer = str(response)
        self.source_nodes = getattr(response, 'source_nodes', [])

    def get_answer(self) -> str:
        """获取答案文本"""
        return self.answer

    def get_relevant_agents(self) -> List[Dict]:
        """获取相关的 agent 信息"""
        agents = []
        for node in self.source_nodes:
            metadata = node.node.metadata
            if metadata.get('type') == 'agent_template':
                agents.append({
                    'agent_id': metadata.get('agent_id'),
                    'name': metadata.get('name'),
                    'score': node.score,
                    'metadata': metadata
                })
        return agents

    def print_result(self, show_sources: bool = True, max_sources: int = 5):
        """
        打印查询结果

        Args:
            show_sources: 是否显示来源
            max_sources: 最多显示多少个来源
        """
        print(f"\n{'='*70}")
        print("答案")
        print(f"{'='*70}")
        print(self.answer)

        if show_sources and self.source_nodes:
            print(f"\n{'='*70}")
            print(f"相关来源 (共 {len(self.source_nodes)} 个)")
            print(f"{'='*70}")

            agents = self.get_relevant_agents()[:max_sources]
            for i, agent in enumerate(agents, 1):
                print(f"\n{i}. {agent['name']}")
                print(f"   Agent ID: {agent['agent_id']}")
                print(f"   相关性得分: {agent['score']:.4f}")
                if agent['metadata'].get('industries'):
                    print(f"   行业: {', '.join(agent['metadata']['industries'])}")
                if agent['metadata'].get('application_type'):
                    print(f"   应用类型: {agent['metadata']['application_type']}")

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'answer': self.answer,
            'relevant_agents': self.get_relevant_agents()
        }


class AgentTemplateQueryEngine:
    """
    Agent 模板查询引擎

    功能：
    1. 使用自然语言查询 agent
    2. 支持多种查询模式
    3. 提供丰富的查询接口
    """

    def __init__(self, config: GraphRAGConfig):
        """
        初始化查询引擎

        Args:
            config: GraphRAG 配置对象
        """
        self.config = config

        print("初始化 AgentTemplateQueryEngine")

        # 配置 GraphRAG Toolkit 模型（必须在创建 LexicalGraphIndex 之前）
        print(f"   配置 LLM 模型: {config.llm_model}")
        ToolkitConfig.extraction_llm = config.llm_model
        ToolkitConfig.response_llm = config.llm_model

        print(f"   配置 Embedding 模型: {config.embedding_model}")
        ToolkitConfig.embed_model = config.embedding_model
        ToolkitConfig.embed_dimensions = config.embedding_dimensions

        # 初始化存储
        print(f"   连接 Neptune: {config.get_neptune_connection_string()}")
        self.graph_store = GraphStoreFactory.for_graph_store(
            config.get_neptune_connection_string()
        )

        print(f"   连接向量存储: {config.get_vector_store_connection_string()}")
        self.vector_store = VectorStoreFactory.for_vector_store(
            config.get_vector_store_connection_string()
        )

        # 创建 LexicalGraphIndex
        print(f"   创建查询引擎")
        graph_index = LexicalGraphIndex(
            self.graph_store,
            self.vector_store
        )

        # 创建查询引擎
        self.query_engine = graph_index.as_query_engine()

        print(f"   [OK] 查询引擎初始化完成\n")

    def query(self, question: str, verbose: bool = True) -> AgentQueryResult:
        """
        使用自然语言查询

        Args:
            question: 查询问题
            verbose: 是否打印详细信息

        Returns:
            AgentQueryResult 对象
        """
        if verbose:
            print(f"\n{'='*70}")
            print(f"问题: {question}")
            print(f"{'='*70}")

        # 执行查询
        response = self.query_engine.query(question)

        # 封装结果
        result = AgentQueryResult(response)

        if verbose:
            result.print_result()

        return result

    # ========== 便捷查询方法 ==========

    def search_by_function(self, description: str) -> AgentQueryResult:
        """
        按功能搜索 agent

        Example:
            search_by_function("处理PDF文档")
            search_by_function("分析医学文献")
        """
        query = f"我需要一个能{description}的agent，请推荐合适的agent。"
        return self.query(query)

    def search_by_industry(self, industry: str) -> AgentQueryResult:
        """
        按行业搜索 agent

        Example:
            search_by_industry("医疗健康")
            search_by_industry("云计算")
        """
        query = f"列出所有属于{industry}行业的agent。"
        return self.query(query)

    def search_by_application_type(self, app_type: str) -> AgentQueryResult:
        """
        按应用类型搜索

        Args:
            app_type: "内部提效" 或 "外部赋能"

        Example:
            search_by_application_type("内部提效")
            search_by_application_type("外部赋能")
        """
        query = f"列出所有用于{app_type}的agent。"
        return self.query(query)

    def find_dependencies(self, agent_id: str) -> AgentQueryResult:
        """
        查找 agent 的依赖关系

        Example:
            find_dependencies("pubmed_literature_agent")
        """
        query = (
            f"{agent_id} 这个agent依赖哪些其他agent？"
            f"同时，有哪些agent依赖于{agent_id}？"
        )
        return self.query(query)

    def find_by_tools(self, tools: List[str]) -> AgentQueryResult:
        """
        根据工具查找 agent

        Example:
            find_by_tools(["file_read", "file_write"])
        """
        tools_str = "、".join(tools)
        query = f"哪些agent使用了这些工具：{tools_str}？"
        return self.query(query)

    def compare_agents(self, agent_id1: str, agent_id2: str) -> AgentQueryResult:
        """
        比较两个 agent

        Example:
            compare_agents("document_processor_agent", "pdf_extractor_agent")
        """
        query = (
            f"比较 {agent_id1} 和 {agent_id2} 这两个agent。"
            f"它们有什么区别？各自的特点是什么？分别适用于什么场景？"
        )
        return self.query(query)

    def recommend_for_task(self, task_description: str) -> AgentQueryResult:
        """
        根据任务描述推荐 agent

        Example:
            recommend_for_task("从PubMed检索医学文献，然后翻译成中文")
        """
        query = (
            f"我需要完成以下任务：{task_description}。"
            f"请推荐合适的agent，并说明它们应该如何配合使用。"
        )
        return self.query(query)

    def find_similar_agents(self, agent_id: str) -> AgentQueryResult:
        """
        查找相似的 agent

        Example:
            find_similar_agents("document_processor_agent")
        """
        query = (
            f"找出与 {agent_id} 相似的其他agent。"
            f"考虑功能、工具、应用场景等方面的相似性。"
        )
        return self.query(query)

    def get_agent_details(self, agent_id: str) -> AgentQueryResult:
        """
        获取 agent 的详细信息

        Example:
            get_agent_details("pubmed_literature_agent")
        """
        query = (
            f"详细介绍 {agent_id} 这个agent。"
            f"包括它的功能、使用的工具、依赖关系、适用场景等。"
        )
        return self.query(query)

    def list_all_agents(self, category: Optional[str] = None) -> AgentQueryResult:
        """
        列出所有 agent

        Args:
            category: 可选的分类过滤

        Example:
            list_all_agents()
            list_all_agents("医疗健康")
        """
        if category:
            query = f"列出所有属于{category}类别的agent，并简要说明每个agent的功能。"
        else:
            query = "列出所有可用的agent，并按类别分组。"

        return self.query(query)

    def find_workflow(self, goal: str) -> AgentQueryResult:
        """
        根据目标查找工作流

        Example:
            find_workflow("分析医学文献并生成报告")
        """
        query = (
            f"我想实现以下目标：{goal}。"
            f"应该使用哪些agent？它们应该按什么顺序执行？"
            f"请给出完整的工作流建议。"
        )
        return self.query(query)

    # ========== 高级查询 ==========

    def complex_query(
        self,
        requirements: Dict[str, Any]
    ) -> AgentQueryResult:
        """
        复杂条件查询

        Example:
            complex_query({
                "task": "分析医学文档",
                "input_format": ["pdf", "docx"],
                "output_format": "markdown",
                "industry": "healthcare",
                "must_have_tools": ["file_read", "file_write"]
            })
        """
        # 构建查询
        query_parts = ["我需要找一个agent，要求如下："]

        if requirements.get('task'):
            query_parts.append(f"- 任务：{requirements['task']}")

        if requirements.get('input_format'):
            formats = "、".join(requirements['input_format'])
            query_parts.append(f"- 输入格式：{formats}")

        if requirements.get('output_format'):
            query_parts.append(f"- 输出格式：{requirements['output_format']}")

        if requirements.get('industry'):
            query_parts.append(f"- 所属行业：{requirements['industry']}")

        if requirements.get('must_have_tools'):
            tools = "、".join(requirements['must_have_tools'])
            query_parts.append(f"- 必须使用的工具：{tools}")

        if requirements.get('application_type'):
            query_parts.append(f"- 应用类型：{requirements['application_type']}")

        query_parts.append("\n请推荐最合适的agent。")

        query = "\n".join(query_parts)
        return self.query(query)

    def batch_query(self, questions: List[str]) -> List[AgentQueryResult]:
        """
        批量查询

        Example:
            batch_query([
                "有哪些医疗相关的agent？",
                "哪些agent可以处理PDF？",
                "推荐一个用于内部提效的agent"
            ])
        """
        results = []
        for i, question in enumerate(questions, 1):
            print(f"\n{'='*70}")
            print(f"批量查询 [{i}/{len(questions)}]")
            print(f"{'='*70}")

            result = self.query(question, verbose=True)
            results.append(result)

        return results


def main():
    """主函数：测试查询"""
    # 加载配置
    config = GraphRAGConfig.from_env()

    # 创建查询引擎
    query_engine = AgentTemplateQueryEngine(config)

    # 测试查询
    print("\n" + "="*70)
    print("开始测试查询")
    print("="*70)

    # 测试1：功能搜索
    print("\n\n【测试1：功能搜索】")
    query_engine.search_by_function("处理PDF文档")

    # 测试2：行业搜索
    print("\n\n【测试2：行业搜索】")
    query_engine.search_by_industry("医疗健康")

    # 测试3：依赖查询
    print("\n\n【测试3：依赖查询】")
    query_engine.find_dependencies("pubmed_literature_agent")

    # 测试4：推荐查询
    print("\n\n【测试4：推荐查询】")
    query_engine.recommend_for_task("从PubMed检索医学文献，然后翻译成中文")


if __name__ == "__main__":
    main()
