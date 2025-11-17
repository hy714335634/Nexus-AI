#!/usr/bin/env python3
"""
公司信息搜索与分析智能体

该智能体能够读取Excel表格中的公司信息，通过多种搜索引擎查询公司详细信息，
并将结果输出为Excel表格。支持多搜索引擎集成、深度检索、缓存机制和分批处理输出。

功能特点:
1. 读取Excel文件，提取公司名称信息
2. 通过多种搜索引擎(Google, Bing, Baidu, DuckDuckGo)查询公司详细信息
3. 深度检索网页内容获取更多公司信息
4. 整理和汇总公司信息
5. 分批处理大量公司信息
6. 管理缓存和任务进度
7. 生成输出Excel文件

作者: Nexus-AI平台
版本: 1.0.0
日期: 2025-09-30
"""

import os
import json
import time
import uuid
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from nexus_utils.agent_factory import create_agent_from_prompt_template
from tools.generated_tools.company_info_search_agent.cache_manager import get_task_progress
from strands.telemetry import StrandsTelemetry

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("company_info_search_agent")

# 设置遥测
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

class CompanyInfoSearchAgent:
    """
    公司信息搜索与分析智能体
    
    该类实现了公司信息搜索与分析的核心功能，包括Excel文件读取、
    多搜索引擎查询、深度检索、缓存管理和结果输出等。
    """
    
    def __init__(self, agent_name: str = "generated_agents_prompts/company_info_search_agent/company_info_search_agent"):
        """
        初始化公司信息搜索智能体
        
        Args:
            agent_name: 智能体名称，默认为"generated_agents_prompts/company_info_search_agent/company_info_search_agent"
        """
        self.agent_name = agent_name
        self.agent = self._create_agent()
        self.task_id = None
        self.config = {
            "batch_size": 5,  # 默认批处理大小
            "search_engines": ["google", "bing", "baidu", "duckduckgo"],  # 默认搜索引擎
            "deep_search": True,  # 默认启用深度搜索
            "max_results": 3,  # 每个搜索引擎的最大结果数
            "output_dir": "output",  # 默认输出目录
        }
        
        # 确保输出目录存在
        os.makedirs(self.config["output_dir"], exist_ok=True)
    
    def _create_agent(self) -> Any:
        """
        创建智能体实例
        
        Returns:
            创建的智能体实例
        """
        agent_params = {
            "env": "production",
            "version": "latest", 
            "model_id": "default",
            "enable_logging": True
        }
        
        try:
            agent = create_agent_from_prompt_template(
                agent_name=self.agent_name, 
                **agent_params
            )
            logger.info(f"成功创建智能体: {self.agent_name}")
            return agent
        except Exception as e:
            logger.error(f"创建智能体失败: {str(e)}")
            raise
    
    def process(self, 
                excel_path: str, 
                task_id: Optional[str] = None,
                search_engines: Optional[List[str]] = None,
                api_key: Optional[str] = None,
                batch_size: Optional[int] = None,
                output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        处理公司信息搜索任务
        
        Args:
            excel_path: Excel文件路径
            task_id: 任务ID，用于断点续传，如果不提供则自动生成
            search_engines: 搜索引擎列表，如果不提供则使用默认配置
            api_key: 搜索API密钥，如果不提供则尝试从环境变量获取
            batch_size: 批处理大小，如果不提供则使用默认配置
            output_path: 输出文件路径，如果不提供则自动生成
        
        Returns:
            任务处理结果，包含任务ID、输出文件路径等信息
        """
        # 设置任务ID
        self.task_id = task_id if task_id else f"task_{uuid.uuid4().hex[:8]}"
        
        # 更新配置
        if search_engines:
            self.config["search_engines"] = search_engines
        if batch_size:
            self.config["batch_size"] = batch_size
        if api_key:
            os.environ["SERPAPI_KEY"] = api_key
        
        # 设置输出路径
        if not output_path:
            output_filename = f"company_info_{self.task_id}_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
            output_path = os.path.join(self.config["output_dir"], output_filename)
        
        # 构建请求
        request = {
            "excel_file_path": excel_path,
            "task_id": self.task_id,
            "search_engines": self.config["search_engines"],
            "batch_size": self.config["batch_size"],
            "output_path": output_path,
            "api_key": "已设置" if api_key or os.environ.get("SERPAPI_KEY") else "未设置"
        }
        
        # 发送请求到智能体
        logger.info(f"开始处理任务: {self.task_id}")
        logger.info(f"请求参数: {json.dumps(request, ensure_ascii=False)}")
        
        try:
            # 构建智能体输入
            agent_input = f"""
请处理以下公司信息搜索任务:

Excel文件路径: {excel_path}
任务ID: {self.task_id}
搜索引擎优先级: {', '.join(self.config["search_engines"])}
API密钥状态: {request["api_key"]}
批处理大小: {self.config["batch_size"]}
输出路径: {output_path}

请读取Excel文件中的公司信息，通过多种搜索引擎查询公司详细信息，并将结果输出为Excel表格。
如果任务ID已存在，请从上次处理位置继续。
"""
            # 调用智能体
            response = self.agent(agent_input)
            
            # 解析结果
            result = {
                "task_id": self.task_id,
                "output_path": output_path,
                "status": "completed",
                "message": "公司信息搜索任务已完成",
                "agent_response": response
            }
            
            logger.info(f"任务完成: {self.task_id}")
            return result
            
        except Exception as e:
            logger.error(f"处理任务时出错: {str(e)}")
            return {
                "task_id": self.task_id,
                "output_path": output_path,
                "status": "error",
                "message": f"处理任务时出错: {str(e)}",
                "error": str(e)
            }
    
    def resume_task(self, task_id: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        恢复中断的任务
        
        Args:
            task_id: 要恢复的任务ID
            output_path: 输出文件路径，如果不提供则自动生成
        
        Returns:
            任务恢复结果
        """
        self.task_id = task_id
        
        # 设置输出路径
        if not output_path:
            output_filename = f"company_info_{self.task_id}_resumed_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
            output_path = os.path.join(self.config["output_dir"], output_filename)
        
        # 构建请求
        request = {
            "task_id": self.task_id,
            "output_path": output_path,
            "action": "resume"
        }
        
        # 发送请求到智能体
        logger.info(f"恢复任务: {self.task_id}")
        
        try:
            # 构建智能体输入
            agent_input = f"""
请恢复以下中断的公司信息搜索任务:

任务ID: {self.task_id}
输出路径: {output_path}

请从上次处理位置继续，完成公司信息搜索，并将结果输出为Excel表格。
"""
            # 调用智能体
            response = self.agent(agent_input)
            
            # 解析结果
            result = {
                "task_id": self.task_id,
                "output_path": output_path,
                "status": "resumed",
                "message": "公司信息搜索任务已恢复",
                "agent_response": response
            }
            
            logger.info(f"任务恢复完成: {self.task_id}")
            return result
            
        except Exception as e:
            logger.error(f"恢复任务时出错: {str(e)}")
            return {
                "task_id": self.task_id,
                "output_path": output_path,
                "status": "error",
                "message": f"恢复任务时出错: {str(e)}",
                "error": str(e)
            }
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务状态信息
        """
        # 构建请求
        request = {
            "task_id": task_id,
            "action": "status"
        }
        
        # 发送请求到智能体
        logger.info(f"获取任务状态: {task_id}")
        
        try:
            # 构建智能体输入
            agent_input = f"""
请获取以下公司信息搜索任务的状态:

任务ID: {task_id}

请提供任务进度、已处理公司数量、总公司数量等信息。
"""
            # 调用智能体
            response = self.agent(agent_input)
            
            # 解析结果
            result = {
                "task_id": task_id,
                "status": "success",
                "message": "成功获取任务状态",
                "task_status": response
            }
            
            logger.info(f"获取任务状态成功: {task_id}")
            return result
            
        except Exception as e:
            logger.error(f"获取任务状态时出错: {str(e)}")
            return {
                "task_id": task_id,
                "status": "error",
                "message": f"获取任务状态时出错: {str(e)}",
                "error": str(e)
            }


def main():
    """命令行入口函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='公司信息搜索与分析智能体')
    
    # 创建子命令
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 处理任务子命令
    process_parser = subparsers.add_parser('process', help='处理公司信息搜索任务')
    process_parser.add_argument('--excel', '-e', required=True, help='Excel文件路径')
    process_parser.add_argument('--task-id', '-t', help='任务ID，用于断点续传，如果不提供则自动生成')
    process_parser.add_argument('--search-engines', '-s', nargs='+', 
                              help='搜索引擎列表，例如: google bing baidu duckduckgo')
    process_parser.add_argument('--api-key', '-k', help='搜索API密钥，如果不提供则尝试从环境变量获取')
    process_parser.add_argument('--batch-size', '-b', type=int, help='批处理大小，默认为5')
    process_parser.add_argument('--output', '-o', help='输出文件路径，如果不提供则自动生成')
    
    # 恢复任务子命令
    resume_parser = subparsers.add_parser('resume', help='恢复中断的任务')
    resume_parser.add_argument('--task-id', '-t', required=True, help='要恢复的任务ID')
    resume_parser.add_argument('--output', '-o', help='输出文件路径，如果不提供则自动生成')
    
    # 获取任务状态子命令
    status_parser = subparsers.add_parser('status', help='获取任务状态')
    status_parser.add_argument('--task-id', '-t', required=True, help='任务ID')
    
    args = parser.parse_args()
    

    # 按照当前代码只会创建一次agent并执行一个批次的分析，我希望原有逻辑不变，能够在每次分析结束后执行下一个批次分析，直到所有批次分析完成

    while True:
        # 创建智能体
        agent = CompanyInfoSearchAgent()
        
        # 根据子命令执行相应操作
        if args.command == 'process':
            result = agent.process(
                excel_path=args.excel,
                task_id=args.task_id,
                search_engines=args.search_engines,
                api_key=args.api_key,
                batch_size=args.batch_size,
                output_path=args.output
            )
            print()
            print(json.dumps(str(result), ensure_ascii=False, indent=2))
        
        elif args.command == 'resume':
            result = agent.resume_task(
                task_id=args.task_id,
                output_path=args.output
            )
            print()
            print(json.dumps(str(result), ensure_ascii=False, indent=2))
        
        elif args.command == 'status':
            result = agent.get_task_status(task_id=args.task_id)
            print()
            print(json.dumps(str(result), ensure_ascii=False, indent=2))
            break
        
        else:
            parser.print_help()
            break
        current_progress = json.loads(get_task_progress(args.task_id))
        if current_progress["status"] == "success" and current_progress["progress_data"]["processed_companies"] >= 569:
            break
        time.sleep(60)


if __name__ == "__main__":
    main()