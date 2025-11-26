#!/usr/bin/env python3
"""
PubMed Literature Editor Assistant

专业的科研期刊主编Agent，能根据用户提供完整文献，结合在线检索PMC文献的工具，
完成杂志主编对文章的评审工作。模拟顶级期刊（如Nature、Science）主编的视角，
对学术文献进行专业评审，提供结构化反馈和修改建议。

功能特点:
- 接收并解析用户提供的文献内容和research_id参数
- 使用PMC文献检索工具查询相关参考资料
- 从顶级期刊主编视角进行内容审核和评估
- 评估研究话题和角度的适合性和吸引力
- 生成结构化JSON格式的评审结果
- 提供具体的修改建议
- 管理工作目录和处理状态

文件路径结构:
- 工作目录: .cache/pmc_literature/<research_id>/
- 状态文件: .cache/pmc_literature/<research_id>/step6.status
- 评审结果: .cache/pmc_literature/<research_id>/feedback/editor/<version>/editor_<version>_<timestamp>.json
- 验证目录: .cache/pmc_literature/<research_id>/feedback/editor/<version>/verification/
"""

import os
import json
import logging
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry
from strands.session.file_session_manager import FileSessionManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置遥测
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

class PubMedLiteratureEditorAssistant:
    """PubMed文献主编评审智能体类"""
    
    def __init__(self, session_manager=None, env: str = "production", version: str = "latest", model_id: str = "default"):
        """
        初始化PubMed文献主编评审智能体
        
        Args:
            session_manager: 会话管理器
            env (str): 环境配置 (development, production, testing)
            version (str): 智能体版本
            model_id (str): 使用的模型ID
        """
        self.env = env
        self.version = version
        self.model_id = model_id
        self.session_manager = session_manager
        
        # 智能体参数
        self.agent_params = {
            "env": self.env,
            "version": self.version,
            "model_id": self.model_id
        }
        
        # 智能体配置路径
        self.agent_config_path = "generated_agents_prompts/pubmed_literature_editor_assistant/pubmed_literature_editor_assistant"
        
        # 创建智能体实例
        self.agent = create_agent_from_prompt_template(
            agent_name=self.agent_config_path,
            session_manager=self.session_manager,
            **self.agent_params
        )
        
        logger.info(f"PubMed文献主编评审智能体初始化完成: {self.agent.name}")
    
    def review_literature(self, literature_content: str, research_id: str, version: str = "v1") -> str:
        """
        执行文献评审并返回结果
        
        Args:
            literature_content (str): 文献内容
            research_id (str): 研究ID，用于指定工作目录
            version (str): 版本号，默认v1
            
        Returns:
            str: 智能体响应
        """
        try:
            # 构建评审请求
            review_request = f"""
我需要对以下学术文献进行专业的期刊主编评审。请从顶级期刊（如Nature、Science）主编的视角，
对这篇文章进行全面评估，并提供结构化的评审反馈和具体的修改建议。

请使用以下参数:
- research_id: {research_id}
- version: {version}

请确保评审结果保存在正确的路径:
.cache/pmc_literature/{research_id}/feedback/editor/{version}/editor_{version}_timestamp.json

请按照以下步骤进行评审:
1. 初始化处理状态
2. 解析文献结构
3. 使用PMC文献检索工具查询相关参考资料
4. 从多个维度评估文献质量
5. 生成决策建议
6. 提供具体的修改建议
7. 生成JSON格式的评审结果
8. 更新处理状态

以下是文献内容:

{literature_content}
"""
            
            # 调用智能体处理评审请求
            result = self.agent(review_request)
            return result
        except Exception as e:
            logger.error(f"文献评审失败: {str(e)}")
            return f"文献评审过程中发生错误: {str(e)}"
    
    def get_review_status(self, research_id: str) -> str:
        """
        获取评审处理状态
        
        Args:
            research_id (str): 研究ID
            
        Returns:
            str: 处理状态信息
        """
        try:
            # 构建状态查询请求
            status_request = f"""
请查询research_id为{research_id}的文献评审处理状态。

请使用file_system_tools/get_status_file工具获取状态文件内容，
状态文件路径为: .cache/pmc_literature/{research_id}/step6.status
"""
            
            # 调用智能体获取状态
            result = self.agent(status_request)
            return result
        except Exception as e:
            logger.error(f"获取评审状态失败: {str(e)}")
            return f"获取评审状态过程中发生错误: {str(e)}"
    
    def get_review_result(self, research_id: str, version: str = "v1", result_file: str = None) -> str:
        """
        获取评审结果
        
        Args:
            research_id (str): 研究ID
            version (str): 版本号，默认v1
            result_file (str): 结果文件名，如果不提供则获取最新的结果
            
        Returns:
            str: 评审结果
        """
        try:
            # 构建结果查询请求
            if result_file:
                result_request = f"""
请获取research_id为{research_id}、version为{version}的文献评审结果。

请使用file_system_tools工具读取以下文件:
.cache/pmc_literature/{research_id}/feedback/editor/{version}/{result_file}
"""
            else:
                result_request = f"""
请获取research_id为{research_id}、version为{version}的最新文献评审结果。

请使用file_system_tools工具列出目录内容，找到最新的评审结果文件，
然后读取该文件内容。评审结果文件应位于:
.cache/pmc_literature/{research_id}/feedback/editor/{version}/
文件名格式为: editor_{version}_timestamp.json
"""
            
            # 调用智能体获取结果
            result = self.agent(result_request)
            return result
        except Exception as e:
            logger.error(f"获取评审结果失败: {str(e)}")
            return f"获取评审结果过程中发生错误: {str(e)}"
    
    def compare_versions(self, research_id: str, version1: str, version2: str) -> str:
        """
        比较两个版本的评审结果
        
        Args:
            research_id (str): 研究ID
            version1 (str): 第一个版本号
            version2 (str): 第二个版本号
            
        Returns:
            str: 比较结果
        """
        try:
            # 构建版本比较请求
            compare_request = f"""
请比较research_id为{research_id}的两个版本评审结果:
- 版本1: {version1}
- 版本2: {version2}

请执行以下步骤:
1. 使用file_system_tools工具获取两个版本的最新评审结果文件
2. 读取两个文件的内容
3. 比较两个版本的评分、决策建议和修改建议的差异
4. 提供详细的比较分析，重点关注改进的方面和仍需改进的方面

评审结果文件应位于:
.cache/pmc_literature/{research_id}/feedback/editor/{version1}/
.cache/pmc_literature/{research_id}/feedback/editor/{version2}/
"""
            
            # 调用智能体比较版本
            result = self.agent(compare_request)
            return result
        except Exception as e:
            logger.error(f"版本比较失败: {str(e)}")
            return f"版本比较过程中发生错误: {str(e)}"

def get_pubmed_literature_editor_assistant(env: str = "production", version: str = "latest", model_id: str = "default") -> PubMedLiteratureEditorAssistant:
    """
    获取PubMed文献主编评审智能体实例
    
    Args:
        env (str): 环境配置 (development, production, testing)
        version (str): 智能体版本
        model_id (str): 使用的模型ID
        
    Returns:
        PubMedLiteratureEditorAssistant: 智能体实例
    """
    return PubMedLiteratureEditorAssistant(env=env, version=version, model_id=model_id)

# 直接使用agent_factory创建智能体的便捷方法
def create_pubmed_literature_editor_assistant(env: str = "production", version: str = "latest", model_id: str = "default"):
    """
    创建PubMed文献主编评审智能体
    
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
        agent_name="generated_agents_prompts/pubmed_literature_editor_assistant/pubmed_literature_editor_assistant",
        **agent_params
    )

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='PubMed文献主编评审智能体')
    parser.add_argument('-f', '--file', type=str, 
                       help='文献文件路径')
    parser.add_argument('-r', '--research_id', type=str, 
                       default=None,
                       help='研究ID，如果不提供则自动生成')
    parser.add_argument('-v', '--version', type=str, 
                       default="v1",
                       help='版本号')
    parser.add_argument('-m', '--mode', type=str,
                       choices=['review', 'status', 'result', 'compare'],
                       default='review',
                       help='操作模式')
    parser.add_argument('--session_id', type=str,
                       default=None,
                       help='可选：指定session_id')
    parser.add_argument('--result_file', type=str,
                       default=None,
                       help='结果文件名（用于result模式）')
    parser.add_argument('--version1', type=str,
                       default=None,
                       help='第一个版本号（用于compare模式）')
    parser.add_argument('--version2', type=str,
                       default=None,
                       help='第二个版本号（用于compare模式）')
    args = parser.parse_args()
    
    # 生成或使用提供的session_id
    session_id = args.session_id if args.session_id else str(uuid.uuid4())
    if not args.session_id:
        print(f"🔑 未指定session_id，生成新的session_id: {session_id}")
    
    # 创建会话管理器
    session_manager = FileSessionManager(
        session_id=session_id,
        storage_dir="./.cache/session_cache"
    )
    
    # 生成或使用提供的research_id
    research_id = args.research_id if args.research_id else f"research_{uuid.uuid4().hex[:8]}"
    if not args.research_id:
        print(f"📋 未指定research_id，生成新的research_id: {research_id}")
    
    # 创建智能体
    agent_params = {
        "env": "production",
        "version": "latest",
        "model_id": "default"
    }
    
    # 使用类封装创建智能体
    agent_class = PubMedLiteratureEditorAssistant(session_manager=session_manager, **agent_params)
    print(f"✅ PubMed文献主编评审智能体创建成功: {agent_class.agent.name}")
    
    # 根据模式执行不同操作
    if args.mode == 'review':
        if not args.file:
            print("❌ 需要提供文献文件路径")
            exit(1)
            
        print(f"📝 执行文献评审: {args.file}")
        
        # 读取文献文件
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                literature_content = f.read()
        except Exception as e:
            print(f"❌ 读取文献文件失败: {str(e)}")
            exit(1)
        
        # 执行评审
        result = agent_class.review_literature(
            literature_content=literature_content,
            research_id=research_id,
            version=args.version
        )
        
    elif args.mode == 'status':
        print(f"🔍 获取评审状态: {research_id}")
        result = agent_class.get_review_status(research_id)
        
    elif args.mode == 'result':
        print(f"📋 获取评审结果: {research_id}, 版本: {args.version}")
        result = agent_class.get_review_result(
            research_id=research_id,
            version=args.version,
            result_file=args.result_file
        )
        
    elif args.mode == 'compare':
        if not args.version1 or not args.version2:
            print("❌ 需要提供两个版本号进行比较")
            exit(1)
            
        print(f"🔍 比较评审版本: {research_id}, 版本1: {args.version1}, 版本2: {args.version2}")
        result = agent_class.compare_versions(
            research_id=research_id,
            version1=args.version1,
            version2=args.version2
        )
    
    print(f"📋 智能体响应:\n{result}")