#!/usr/bin/env python3
"""
GraphRAG 查询示例脚本

展示各种查询模式的使用方法
"""

import sys
from graphrag_config import GraphRAGConfig
from graphrag_query_engine import AgentTemplateQueryEngine


def print_section_header(title: str):
    """打印章节标题"""
    print("\n\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def example_1_basic_search(engine: AgentTemplateQueryEngine):
    """示例1: 基础搜索"""
    print_section_header("示例 1: 基础功能搜索")

    queries = [
        "我需要一个能处理PDF文档的agent",
        "找一个可以分析数据的agent",
        "有没有能生成内容的agent？"
    ]

    for query in queries:
        engine.query(query, verbose=True)
        input("\n按 Enter 继续下一个查询...")


def example_2_industry_search(engine: AgentTemplateQueryEngine):
    """示例2: 按行业搜索"""
    print_section_header("示例 2: 按行业搜索")

    industries = ["医疗健康", "云计算", "文档管理"]

    for industry in industries:
        engine.search_by_industry(industry)
        input("\n按 Enter 继续下一个查询...")


def example_3_application_type(engine: AgentTemplateQueryEngine):
    """示例3: 按应用类型搜索"""
    print_section_header("示例 3: 按应用类型搜索")

    # 内部提效
    print("\n查询内部提效的 agent:")
    engine.search_by_application_type("内部提效")

    input("\n按 Enter 继续...")

    # 外部赋能
    print("\n查询外部赋能的 agent:")
    engine.search_by_application_type("外部赋能")


def example_4_dependencies(engine: AgentTemplateQueryEngine):
    """示例4: 依赖关系查询"""
    print_section_header("示例 4: 依赖关系查询")

    agent_ids = [
        "pubmed_literature_agent",
        "pdf_extractor_agent",
        "html2pptx_agent"
    ]

    for agent_id in agent_ids:
        print(f"\n查询 {agent_id} 的依赖:")
        engine.find_dependencies(agent_id)
        input("\n按 Enter 继续下一个查询...")


def example_5_tool_search(engine: AgentTemplateQueryEngine):
    """示例5: 按工具搜索"""
    print_section_header("示例 5: 按工具搜索")

    tool_sets = [
        ["file_read", "file_write"],
        ["http_request"],
        ["use_aws"]
    ]

    for tools in tool_sets:
        print(f"\n查询使用工具 {tools} 的 agent:")
        engine.find_by_tools(tools)
        input("\n按 Enter 继续下一个查询...")


def example_6_comparison(engine: AgentTemplateQueryEngine):
    """示例6: Agent 比较"""
    print_section_header("示例 6: Agent 比较")

    comparisons = [
        ("document_processor_agent", "pdf_extractor_agent"),
        ("data_analyzer_agent", "deep_research_agent"),
    ]

    for agent1, agent2 in comparisons:
        print(f"\n比较 {agent1} 和 {agent2}:")
        engine.compare_agents(agent1, agent2)
        input("\n按 Enter 继续下一个比较...")


def example_7_recommendations(engine: AgentTemplateQueryEngine):
    """示例7: 任务推荐"""
    print_section_header("示例 7: 根据任务推荐 Agent")

    tasks = [
        "从PubMed检索医学文献，然后翻译成中文",
        "分析AWS成本并生成报告",
        "将HTML文档转换为PPT演示文稿",
        "处理PDF文件并提取文本内容"
    ]

    for task in tasks:
        print(f"\n任务: {task}")
        engine.recommend_for_task(task)
        input("\n按 Enter 继续下一个任务...")


def example_8_similar_agents(engine: AgentTemplateQueryEngine):
    """示例8: 查找相似 Agent"""
    print_section_header("示例 8: 查找相似 Agent")

    agent_ids = [
        "document_processor_agent",
        "pubmed_literature_agent"
    ]

    for agent_id in agent_ids:
        print(f"\n查找与 {agent_id} 相似的 agent:")
        engine.find_similar_agents(agent_id)
        input("\n按 Enter 继续下一个查询...")


def example_9_agent_details(engine: AgentTemplateQueryEngine):
    """示例9: 获取详细信息"""
    print_section_header("示例 9: 获取 Agent 详细信息")

    agent_ids = [
        "pubmed_literature_agent",
        "aws_pricing_agent",
        "html2pptx_agent"
    ]

    for agent_id in agent_ids:
        print(f"\n查询 {agent_id} 的详细信息:")
        engine.get_agent_details(agent_id)
        input("\n按 Enter 继续下一个查询...")


def example_10_workflow(engine: AgentTemplateQueryEngine):
    """示例10: 工作流查询"""
    print_section_header("示例 10: 工作流规划")

    goals = [
        "分析医学文献并生成中文报告",
        "处理PDF文档，提取内容，然后转换为演示文稿",
        "获取新闻信息，分析内容，生成摘要"
    ]

    for goal in goals:
        print(f"\n目标: {goal}")
        engine.find_workflow(goal)
        input("\n按 Enter 继续下一个目标...")


def example_11_complex_query(engine: AgentTemplateQueryEngine):
    """示例11: 复杂条件查询"""
    print_section_header("示例 11: 复杂条件查询")

    requirements = {
        "task": "分析医学文档",
        "input_format": ["pdf", "docx"],
        "output_format": "markdown",
        "industry": "healthcare",
        "must_have_tools": ["file_read", "file_write"],
        "application_type": "内部提效"
    }

    print("\n复杂查询需求:")
    for key, value in requirements.items():
        print(f"   {key}: {value}")

    engine.complex_query(requirements)


def example_12_custom_queries(engine: AgentTemplateQueryEngine):
    """示例12: 自定义查询"""
    print_section_header("示例 12: 自定义自然语言查询")

    custom_queries = [
        "哪些agent既能处理文档又能生成报告？",
        "我想提高团队效率，推荐3个最有用的agent",
        "列出所有与AWS集成的agent",
        "找出所有单agent模板（不依赖其他agent的）",
        "哪些agent支持批量处理？"
    ]

    for query in custom_queries:
        print(f"\n自定义查询: {query}")
        engine.query(query, verbose=True)
        input("\n按 Enter 继续下一个查询...")


def interactive_mode(engine: AgentTemplateQueryEngine):
    """交互模式"""
    print_section_header("交互模式")
    print("\n在此模式下，你可以输入任何自然语言问题")
    print("输入 'exit' 或 'quit' 退出\n")

    while True:
        try:
            query = input("\n请输入你的问题: ").strip()

            if query.lower() in ['exit', 'quit', 'q', '退出']:
                print("\n再见！")
                break

            if not query:
                continue

            engine.query(query, verbose=True)

        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"\n[ERROR] 查询出错: {e}")


def main():
    """主函数"""
    print("GraphRAG 查询示例\n")

    # 加载配置
    config = GraphRAGConfig.from_env()

    # 验证配置
    if not config.validate():
        print("\n[ERROR] 配置验证失败！")
        print("\n请先运行 build_index.py 构建索引")
        sys.exit(1)

    # 创建查询引擎
    print("初始化查询引擎...")
    try:
        engine = AgentTemplateQueryEngine(config)
    except Exception as e:
        print(f"\n[ERROR] 初始化查询引擎失败: {e}")
        print("\n请确保：")
        print("  1. 已经运行 build_index.py 构建了索引")
        print("  2. Neptune 和向量存储服务正常运行")
        print("  3. 环境变量配置正确")
        sys.exit(1)

    # 显示菜单
    while True:
        print("\n" + "="*70)
        print("  选择要运行的示例")
        print("="*70)
        print("  1.  基础功能搜索")
        print("  2.  按行业搜索")
        print("  3.  按应用类型搜索")
        print("  4.  依赖关系查询")
        print("  5.  按工具搜索")
        print("  6.  Agent 比较")
        print("  7.  任务推荐")
        print("  8.  查找相似 Agent")
        print("  9.  获取详细信息")
        print("  10. 工作流规划")
        print("  11. 复杂条件查询")
        print("  12. 自定义查询")
        print("  13. 交互模式")
        print("  14. 运行所有示例")
        print("  0.  退出")
        print("="*70)

        try:
            choice = input("\n请选择 (0-14): ").strip()

            if choice == '0':
                print("\n再见！")
                break
            elif choice == '1':
                example_1_basic_search(engine)
            elif choice == '2':
                example_2_industry_search(engine)
            elif choice == '3':
                example_3_application_type(engine)
            elif choice == '4':
                example_4_dependencies(engine)
            elif choice == '5':
                example_5_tool_search(engine)
            elif choice == '6':
                example_6_comparison(engine)
            elif choice == '7':
                example_7_recommendations(engine)
            elif choice == '8':
                example_8_similar_agents(engine)
            elif choice == '9':
                example_9_agent_details(engine)
            elif choice == '10':
                example_10_workflow(engine)
            elif choice == '11':
                example_11_complex_query(engine)
            elif choice == '12':
                example_12_custom_queries(engine)
            elif choice == '13':
                interactive_mode(engine)
            elif choice == '14':
                # 运行所有示例
                for i in range(1, 13):
                    eval(f"example_{i}_{['basic_search', 'industry_search', 'application_type', 'dependencies', 'tool_search', 'comparison', 'recommendations', 'similar_agents', 'agent_details', 'workflow', 'complex_query', 'custom_queries'][i-1]}(engine)")
                    input("\n\n按 Enter 继续下一个示例...")
            else:
                print("\n[ERROR] 无效的选择，请重试")

        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"\n[ERROR] 出错: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
