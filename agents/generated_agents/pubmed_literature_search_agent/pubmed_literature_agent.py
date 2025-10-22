#!/usr/bin/env python3
"""
PubMed文献检索和汇总智能体

专门负责学术文献的智能检索、筛选和初步汇总工作，基于PubMed Central (PMC)开放数据。
通过AWS S3访问PMC数据，支持关键词搜索、多维度筛选、相关性排序和结构化报告生成。

功能特点:
- 通过AWS S3访问PubMed Central开放数据
- 关键词和主题检索
- 时间范围、期刊类型和影响因子筛选
- 多维度相关性排序算法
- 文献摘要和关键信息提取
- 多格式引用信息生成
- 结构化文献综述报告生成
- 多语言支持(英文和中文)
- 撤稿状态检查
- 批量文献处理
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置遥测
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

class PubMedLiteratureAgent:
    """PubMed文献检索和汇总智能体类"""
    
    def __init__(self, env: str = "production", version: str = "latest", model_id: str = "default"):
        """
        初始化PubMed文献检索和汇总智能体
        
        Args:
            env (str): 环境配置 (development, production, testing)
            version (str): 智能体版本
            model_id (str): 使用的模型ID
        """
        self.env = env
        self.version = version
        self.model_id = model_id
        
        # 智能体参数
        self.agent_params = {
            "env": self.env,
            "version": self.version,
            "model_id": self.model_id
        }
        
        # 智能体配置路径
        self.agent_config_path = "generated_agents_prompts/pubmed_literature_search_agent/pubmed_literature_agent"
        
        # 创建智能体实例
        self.agent = create_agent_from_prompt_template(
            agent_name=self.agent_config_path,
            **self.agent_params
        )
        
        logger.info(f"PubMed文献检索和汇总智能体初始化完成: {self.agent.name}")
    
    def search_literature(self, query: str) -> str:
        """
        执行文献检索并返回结果
        
        Args:
            query (str): 用户查询文本
            
        Returns:
            str: 智能体响应
        """
        try:
            # 调用智能体处理查询
            result = self.agent(query)
            return result
        except Exception as e:
            logger.error(f"文献检索失败: {str(e)}")
            return f"文献检索过程中发生错误: {str(e)}"
    
    def process_batch_query(self, queries: List[str], max_results_per_query: int = 5) -> str:
        """
        批量处理多个查询
        
        Args:
            queries (List[str]): 查询列表
            max_results_per_query (int): 每个查询的最大结果数
            
        Returns:
            str: 批量处理结果
        """
        try:
            # 构建批量查询输入
            batch_input = f"""
我需要进行批量PubMed文献检索，请处理以下{len(queries)}个查询，每个查询最多返回{max_results_per_query}个结果：

"""
            for i, query in enumerate(queries, 1):
                batch_input += f"查询{i}: {query}\n"
            
            batch_input += "\n请为每个查询生成单独的文献检索结果摘要，并在最后提供一个综合分析。"
            
            # 调用智能体处理批量查询
            result = self.agent(batch_input)
            return result
        except Exception as e:
            logger.error(f"批量查询处理失败: {str(e)}")
            return f"批量查询处理过程中发生错误: {str(e)}"
    
    def generate_literature_review(self, topic: str, time_range: str = "past 10 years", 
                                  journal_filter: str = None, impact_factor_min: float = None) -> str:
        """
        生成文献综述报告
        
        Args:
            topic (str): 研究主题
            time_range (str): 时间范围
            journal_filter (str): 期刊类型过滤条件
            impact_factor_min (float): 最小影响因子
            
        Returns:
            str: 文献综述报告
        """
        try:
            # 构建文献综述请求
            review_input = f"""
我需要进行PubMed文献检索和分析，请根据以下信息帮我查找相关文献并生成综述报告：

研究主题: {topic}
时间范围: {time_range}
"""
            if journal_filter:
                review_input += f"期刊类型: {journal_filter}\n"
            
            if impact_factor_min:
                review_input += f"最小影响因子: {impact_factor_min}\n"
            
            review_input += """
请执行以下步骤:
1. 连接PMC数据源并执行文献检索
2. 应用指定的筛选条件
3. 计算文献相关性并排序
4. 提取关键信息并生成摘要
5. 生成结构化的文献综述报告，包括研究背景、主要发现、研究方法分析、研究趋势和研究差距
6. 提供标准格式的引用列表

我需要一份全面、深入的文献综述报告。
"""
            
            # 调用智能体生成文献综述
            result = self.agent(review_input)
            return result
        except Exception as e:
            logger.error(f"文献综述生成失败: {str(e)}")
            return f"文献综述生成过程中发生错误: {str(e)}"
    
    def generate_citations(self, pmcids: List[str], citation_style: str = "APA") -> str:
        """
        生成指定文献的引用信息
        
        Args:
            pmcids (List[str]): PMC ID列表
            citation_style (str): 引用样式 (APA, MLA, Chicago, Harvard, Vancouver)
            
        Returns:
            str: 引用信息列表
        """
        try:
            # 构建引用生成请求
            citation_input = f"""
我需要为以下PMC ID的文献生成{citation_style}格式的引用信息:

PMCID列表:
{', '.join(pmcids)}

请使用citation_generator工具生成标准的{citation_style}格式引用。
"""
            
            # 调用智能体生成引用
            result = self.agent(citation_input)
            return result
        except Exception as e:
            logger.error(f"引用生成失败: {str(e)}")
            return f"引用生成过程中发生错误: {str(e)}"
    
    def extract_key_information(self, pmcid: str) -> str:
        """
        从指定文献中提取关键信息
        
        Args:
            pmcid (str): PMC ID
            
        Returns:
            str: 提取的关键信息
        """
        try:
            # 构建信息提取请求
            extract_input = f"""
我需要从PMCID为{pmcid}的文献中提取关键信息，请提供以下内容:

1. 文章标题、作者和期刊信息
2. 发表时间和DOI
3. 摘要内容
4. 研究方法概述
5. 主要研究发现
6. 结论和建议
7. 关键词列表

请使用pmc_metadata_parser工具提取这些信息，并以结构化格式呈现。
"""
            
            # 调用智能体提取信息
            result = self.agent(extract_input)
            return result
        except Exception as e:
            logger.error(f"关键信息提取失败: {str(e)}")
            return f"关键信息提取过程中发生错误: {str(e)}"

def get_pubmed_literature_agent(env: str = "production", version: str = "latest", model_id: str = "default") -> PubMedLiteratureAgent:
    """
    获取PubMed文献检索和汇总智能体实例
    
    Args:
        env (str): 环境配置 (development, production, testing)
        version (str): 智能体版本
        model_id (str): 使用的模型ID
        
    Returns:
        PubMedLiteratureAgent: 智能体实例
    """
    return PubMedLiteratureAgent(env, version, model_id)

# 直接使用agent_factory创建智能体的便捷方法
def create_pubmed_literature_agent(env: str = "production", version: str = "latest", model_id: str = "default"):
    """
    创建PubMed文献检索和汇总智能体
    
    Args:
        env (str): 环境配置 (development, production, testing)
        version (str): 智能体版本
        model_id (str): 使用的模型ID
        
    Returns:
        Agent: Strands智能体实例
    """
    # 智能体参数
    agent_params = {
        "env": env,
        "version": version,
        "model_id": model_id
    }
    
    # 使用agent_factory创建智能体
    return create_agent_from_prompt_template(
        agent_name="generated_agents_prompts/pubmed_literature_search_agent/pubmed_literature_agent",
        **agent_params
    )

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='PubMed文献检索和汇总智能体')
    parser.add_argument('-q', '--query', type=str, 
                       default="请检索关于COVID-19疫苗有效性的最新研究",
                       help='检索查询')
    parser.add_argument('-t', '--time', type=str, 
                       default="past 2 years",
                       help='时间范围')
    parser.add_argument('-j', '--journal', type=str, 
                       default=None,
                       help='期刊类型过滤')
    parser.add_argument('-i', '--impact', type=float, 
                       default=None,
                       help='最小影响因子')
    parser.add_argument('-m', '--mode', type=str,
                       choices=['search', 'review', 'citation', 'extract'],
                       default='search',
                       help='操作模式')
    parser.add_argument('--ncbi_api_key', type=str,
                       default=None,
                       help='可选：指定NCBI_API_KEY以提升PubMed API吞吐（也可通过环境变量NCBI_API_KEY设置）')
    parser.add_argument('-p', '--pmcid', type=str,
                       default=None,
                       help='PMC ID (用于citation和extract模式)')
    args = parser.parse_args()
    
    # 创建智能体
    agent_params = {
        "env": "production",
        "version": "latest",
        "model_id": "default"
    }
    
    # 注入 NCBI_API_KEY（命令行优先，其次环境变量）
    if args.ncbi_api_key:
        os.environ['NCBI_API_KEY'] = args.ncbi_api_key
        print('🔑 已设置 NCBI_API_KEY 来自命令行参数')
    else:
        if os.environ.get('NCBI_API_KEY'):
            print('🔑 检测到环境变量 NCBI_API_KEY，将用于 PubMed API 请求')
        else:
            print('ℹ️ 未设置 NCBI_API_KEY。可通过导出环境变量或 --ncbi_api_key 指定以提升API配额与吞吐')

    # 使用类封装创建智能体（方案A）
    agent_class = PubMedLiteratureAgent(**agent_params)
    print(f"✅ PubMed文献检索和汇总智能体创建成功: {agent_class.agent.name}")
    
    # 根据模式执行不同操作
    if args.mode == 'search':
        print(f"🔍 执行文献检索: {args.query}")
        result = agent_class.search_literature(args.query)
        
    elif args.mode == 'review':
        print(f"📑 生成文献综述: {args.query}")
        result = agent_class.generate_literature_review(
            topic=args.query,
            time_range=args.time,
            journal_filter=args.journal,
            impact_factor_min=args.impact
        )
        
    elif args.mode == 'citation':
        if not args.pmcid:
            print("❌ 需要提供PMC ID")
            exit(1)
            
        pmcids = [p.strip() for p in args.pmcid.split(',')]
        print(f"📝 生成引用信息: {', '.join(pmcids)}")
        
        result = agent_class.generate_citations(pmcids, citation_style="APA")
        
    elif args.mode == 'extract':
        if not args.pmcid:
            print("❌ 需要提供PMC ID")
            exit(1)
            
        print(f"📋 提取关键信息: {args.pmcid}")
        
        result = agent_class.extract_key_information(args.pmcid)
    
    print(f"📋 智能体响应:\n{result}")