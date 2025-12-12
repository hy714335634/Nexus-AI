#!/usr/bin/env python3
"""
PDF内容提取Agent

专业的PDF内容提取专家，能够处理PDF文件，将其转换为图片，调用多模态Agent提取文本内容，
并生成TXT文件，支持断点续传功能。

功能:
1. 将PDF文件转换为图片，存储在.cache目录
2. 调用多模态Agent提取图片中的文本内容
3. 合并所有页面的文本内容生成TXT文件
4. 支持断点续传功能，当处理中断时能从断点继续

作者: Nexus-AI
版本: 1.0.0
日期: 2025-09-12
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import argparse

from nexus_utils.agent_factory import create_agent_from_prompt_template

# 导入工具函数
from tools.generated_tools.pdf_content_extractor.pdf_processing_tools import (
    pdf_to_images,
    manage_processing_state,
    merge_text_content,
    initialize_pdf_extraction,
    cleanup_extraction_files
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pdf_extractor_agent")

from strands.telemetry import StrandsTelemetry
from nexus_utils.config_loader import ConfigLoader
loader = ConfigLoader()
# 设置环境变量
os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")
otel_endpoint = loader.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

class PDFExtractorAgent:
    """PDF内容提取Agent，处理PDF文件并提取文本内容"""
    
    def __init__(self, cache_dir: str = ".cache", env: str = "production", version: str = "latest", model_id: str = "default"):
        """
        初始化PDF提取Agent
        
        Args:
            cache_dir: 缓存目录路径，用于存储临时文件
        """
        self.cache_dir = cache_dir
        self.multimodal_agent = None
        self.state = {}
        self.env = env
        self.version = version
        self.model_id = model_id
        
        # 创建缓存目录
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"PDF提取Agent初始化完成，缓存目录: {cache_dir}")
    
    def _initialize_multimodal_agent(self) -> None:
        """初始化多模态Agent"""
        if self.multimodal_agent is None:
            logger.info("初始化多模态Agent...")
            
            # 创建 agent 的通用参数
            agent_params = {
                "env": self.env,
                "version": self.version, 
                "model_id": self.model_id,
                "enable_logging": True
            }
            
            # 使用 agent_factory 创建多模态分析 agent
            self.multimodal_agent = create_agent_from_prompt_template(
                agent_name="system_agents_prompts/multimodal_analysis/multimodal_analyzer_agent", 
                **agent_params
            )
            
            logger.info("多模态Agent初始化完成")
    
    def process_pdf(self, pdf_path: str, output_file: Optional[str] = None, 
                   force_restart: bool = False, dpi: int = 300, 
                   cleanup: bool = True) -> Dict[str, Any]:
        """
        处理PDF文件，提取文本内容
        
        Args:
            pdf_path: PDF文件路径
            output_file: 输出文本文件路径，如果不提供则自动生成
            force_restart: 是否强制重新开始处理
            dpi: 图像分辨率
            cleanup: 是否在处理完成后清理临时文件
            
        Returns:
            处理结果字典
        """
        try:
            # 验证和修正输出文件路径
            if output_file and os.path.isdir(output_file):
                # 如果输出路径是目录，自动生成文件名
                pdf_filename = os.path.basename(pdf_path)
                base_name = os.path.splitext(pdf_filename)[0]
                output_file = os.path.join(output_file, f"{base_name}.md")
                logger.info(f"输出路径是目录，自动生成文件名: {output_file}")
            
            # 初始化多模态Agent
            self._initialize_multimodal_agent()
            
            # 初始化PDF提取过程
            init_result = json.loads(initialize_pdf_extraction(
                pdf_path=pdf_path,
                output_dir=self.cache_dir,
                output_file=output_file,
                force_restart=force_restart
            ))
            
            if not init_result["success"]:
                logger.error(f"初始化失败: {init_result['message']}")
                return {"success": False, "message": init_result["message"]}
            
            logger.info(f"PDF提取初始化完成: {init_result['message']}")
            
            # 获取PDF信息和状态
            pdf_info = init_result["pdf_info"]
            is_resumed = init_result["is_resumed"]
            output_file = init_result["output_file"]
            
            # 读取处理状态
            state_result = json.loads(manage_processing_state(
                action="read",
                pdf_path=pdf_path,
                state_dir=self.cache_dir
            ))
            
            if not state_result["success"]:
                logger.error(f"读取状态失败: {state_result['message']}")
                return {"success": False, "message": state_result["message"]}
            
            self.state = state_result["state_data"]
            total_pages = self.state["processing_status"]["total_pages"]
            processed_pages = self.state["processing_status"]["processed_pages"]
            
            # 显示处理状态
            if is_resumed:
                logger.info(f"从断点继续处理，已处理 {len(processed_pages)}/{total_pages} 页")
            else:
                logger.info(f"开始处理PDF文件，共 {total_pages} 页")
            
            # 将PDF转换为图片
            pages_to_process = [i for i in range(total_pages) if i not in processed_pages]
            
            if not pages_to_process:
                logger.info("所有页面已处理完成，合并文本内容...")
            else:
                logger.info(f"需要处理 {len(pages_to_process)} 页...")
                
                # 转换PDF为图片
                convert_result = json.loads(pdf_to_images(
                    pdf_path=pdf_path,
                    output_dir=self.cache_dir,
                    dpi=dpi,
                    image_format="png"
                ))
                
                if not convert_result["success"]:
                    logger.error(f"PDF转图片失败: {convert_result['message']}")
                    return {"success": False, "message": convert_result["message"]}
                
                logger.info(f"PDF转图片完成: {convert_result['message']}")
                
                # 处理每一页
                for page_num in pages_to_process:
                    try:
                        # 获取图片路径
                        image_path = f"{self.cache_dir}/page_{page_num}.png"
                        
                        # 检查图片是否存在
                        if not os.path.exists(image_path):
                            logger.warning(f"图片不存在: {image_path}，跳过处理")
                            continue
                        
                        # 使用多模态Agent提取文本
                        logger.info(f"处理第 {page_num+1} 页...")
                        
                        # 构建输入
                        agent_input = f"文件分析请求: {image_path},分析/处理要求: 提取图片中的所有文本内容，保持原始格式"
                        
                        # 调用多模态Agent
                        start_time = time.time()
                        result = self.multimodal_agent(agent_input)
                        processing_time = time.time() - start_time
                        
                        # 提取文本内容
                        extracted_text = ""
                        if hasattr(result, 'content') and result.content:
                            extracted_text = result.content
                        elif isinstance(result, str):
                            extracted_text = result
                        elif hasattr(result, 'text'):
                            extracted_text = result.text
                        else:
                            # 如果result是其他格式，尝试转换为字符串
                            extracted_text = str(result)
                        
                        # 保存提取的文本
                        text_file = f"{self.cache_dir}/text_{page_num}.md"
                        with open(text_file, "w", encoding="utf-8") as f:
                            f.write(extracted_text)
                        
                        # 更新处理状态
                        self.state["processing_status"]["processed_pages"].append(page_num)
                        self.state["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        
                        # 保存状态
                        update_result = json.loads(manage_processing_state(
                            action="update",
                            pdf_path=pdf_path,
                            state_dir=self.cache_dir,
                            state_data=self.state
                        ))
                        
                        if not update_result["success"]:
                            logger.warning(f"状态更新失败: {update_result['message']}")
                        
                        logger.info(f"第 {page_num+1} 页处理完成 (用时: {processing_time:.2f}秒)")
                        
                    except Exception as e:
                        logger.error(f"处理第 {page_num+1} 页时出错: {str(e)}")
                        # 记录失败的页面
                        if page_num not in self.state["processing_status"]["failed_pages"]:
                            self.state["processing_status"]["failed_pages"].append(page_num)
                            
                        # 保存状态
                        manage_processing_state(
                            action="update",
                            pdf_path=pdf_path,
                            state_dir=self.cache_dir,
                            state_data=self.state
                        )
            
            # 合并所有文本文件
            text_files = []
            for page_num in range(total_pages):
                text_file = f"{self.cache_dir}/text_{page_num}.md"
                if os.path.exists(text_file):
                    text_files.append(text_file)
            
            if text_files:
                merge_result = json.loads(merge_text_content(
                    input_files=text_files,
                    output_file=output_file,
                    include_page_numbers=True,
                    handle_missing_files=True
                ))
                
                if not merge_result["success"]:
                    logger.error(f"合并文本失败: {merge_result['message']}")
                    return {"success": False, "message": merge_result["message"]}
                
                logger.info(f"文本合并完成: {merge_result['message']}")
                
                # 更新处理状态为完成
                self.state["processing_status"]["completed"] = True
                self.state["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
                
                manage_processing_state(
                    action="update",
                    pdf_path=pdf_path,
                    state_dir=self.cache_dir,
                    state_data=self.state
                )
                
                # 清理临时文件
                if cleanup:
                    cleanup_result = json.loads(cleanup_extraction_files(
                        pdf_path=pdf_path,
                        cache_dir=self.cache_dir,
                        keep_state_file=True,
                        keep_output_file=True
                    ))
                    
                    if cleanup_result["success"]:
                        logger.info(f"清理完成: {cleanup_result['message']}")
                    else:
                        logger.warning(f"清理失败: {cleanup_result['message']}")
                
                return {
                    "success": True,
                    "message": f"PDF文本提取完成，输出文件: {output_file}",
                    "output_file": output_file,
                    "total_pages": total_pages,
                    "processed_pages": len(self.state["processing_status"]["processed_pages"]),
                    "failed_pages": self.state["processing_status"]["failed_pages"]
                }
            else:
                return {
                    "success": False,
                    "message": "没有可合并的文本文件",
                    "output_file": None
                }
                
        except Exception as e:
            logger.error(f"PDF处理过程中发生错误: {str(e)}")
            return {"success": False, "message": f"处理错误: {str(e)}"}
    
    def get_processing_status(self, pdf_path: str) -> Dict[str, Any]:
        """
        获取PDF处理状态
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            处理状态字典
        """
        try:
            state_result = json.loads(manage_processing_state(
                action="read",
                pdf_path=pdf_path,
                state_dir=self.cache_dir
            ))
            
            if not state_result["success"]:
                return {"success": False, "message": state_result["message"]}
            
            state_data = state_result["state_data"]
            total_pages = state_data["processing_status"]["total_pages"]
            processed_pages = state_data["processing_status"]["processed_pages"]
            failed_pages = state_data["processing_status"]["failed_pages"]
            completed = state_data["processing_status"]["completed"]
            
            return {
                "success": True,
                "pdf_path": pdf_path,
                "total_pages": total_pages,
                "processed_pages": len(processed_pages),
                "failed_pages": len(failed_pages),
                "completion_percentage": round(len(processed_pages) / total_pages * 100, 2) if total_pages > 0 else 0,
                "completed": completed,
                "output_file": state_data.get("output_file", None),
                "last_updated": state_data.get("last_updated", None)
            }
            
        except Exception as e:
            return {"success": False, "message": f"获取状态错误: {str(e)}"}


# 创建 BedrockAgentCoreApp 实例
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import json as _json
app = BedrockAgentCoreApp()


# ==================== AgentCore 入口点（必须包含）====================
from typing import Dict, Any as TypingAny

@app.entrypoint
def handler(payload: Dict[str, TypingAny]) -> str:
    """
    AgentCore 标准入口点

    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息
            - pdf_path: PDF文件路径
            - output_path: 输出文件路径

    Returns:
        str: 响应文本
    """
    print(f"📥 Received payload: {_json.dumps(payload, ensure_ascii=False)}")

    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")
    pdf_path = payload.get("pdf_path") or payload.get("file_path")
    output_path = payload.get("output_path")

    if not prompt and not pdf_path:
        return "Error: Missing 'prompt' or 'pdf_path' in request"

    print(f"🔄 Processing: prompt={prompt}, pdf_path={pdf_path}")

    try:
        extractor = PDFExtractorAgent()
        if pdf_path:
            result = extractor.process_pdf(pdf_path, output_file=output_path)
            if result.get("success"):
                response_text = f"PDF处理完成: {result.get('message', '')}"
                if result.get("output_file"):
                    response_text += f"\n输出文件: {result['output_file']}"
                return response_text
            else:
                return f"Error: {result.get('message', 'Unknown error')}"
        else:
            return "Error: Please provide pdf_path parameter"
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return f"Error: {str(e)}"


# ==================== 本地运行入口 ====================
def main():
    """主函数，处理命令行参数并执行PDF提取"""
    parser = argparse.ArgumentParser(description='PDF内容提取工具')
    parser.add_argument('pdf_path', help='PDF文件路径')
    parser.add_argument('-o', '--output', help='输出文本文件路径')
    parser.add_argument('-c', '--cache', default='.cache', help='缓存目录路径')
    parser.add_argument('-d', '--dpi', type=int, default=300, help='图像分辨率')
    parser.add_argument('-f', '--force', action='store_true', help='强制重新开始处理')
    parser.add_argument('-s', '--status', action='store_true', help='只显示处理状态')
    parser.add_argument('--no-cleanup', action='store_true', help='不清理临时文件')
    parser.add_argument('-e', '--env', type=str, default='production', help='指定Agent运行环境 (默认: production)')
    parser.add_argument('-v', '--version', type=str, default='latest', help='指定Agent版本 (默认: latest)')
    
    args = parser.parse_args()
    
    # 创建PDF提取Agent
    extractor = PDFExtractorAgent(cache_dir=args.cache, env=args.env, version=args.version)
    
    if args.status:
        # 只显示处理状态
        status = extractor.get_processing_status(args.pdf_path)
        if status["success"]:
            print(f"PDF文件: {args.pdf_path}")
            print(f"总页数: {status['total_pages']}")
            print(f"已处理页数: {status['processed_pages']}")
            print(f"失败页数: {status['failed_pages']}")
            print(f"完成百分比: {status['completion_percentage']}%")
            print(f"处理状态: {'已完成' if status['completed'] else '未完成'}")
            if status["output_file"]:
                print(f"输出文件: {status['output_file']}")
            if status["last_updated"]:
                print(f"最后更新时间: {status['last_updated']}")
        else:
            print(f"获取状态失败: {status['message']}")
    else:
        # 处理PDF文件
        print(f"开始处理PDF文件: {args.pdf_path}")
        result = extractor.process_pdf(
            pdf_path=args.pdf_path,
            output_file=args.output,
            force_restart=args.force,
            dpi=args.dpi,
            cleanup=not args.no_cleanup
        )
        
        if result["success"]:
            print(f"处理成功: {result['message']}")
            print(f"输出文件: {result['output_file']}")
            print(f"总页数: {result['total_pages']}")
            print(f"已处理页数: {result['processed_pages']}")
            if result["failed_pages"]:
                print(f"失败页数: {len(result['failed_pages'])}")
                print(f"失败页面: {result['failed_pages']}")
        else:
            print(f"处理失败: {result['message']}")


if __name__ == "__main__":
    # 检查是否在 Docker 容器中运行（AgentCore 部署）
    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"

    if is_docker:
        # AgentCore 部署模式：启动 HTTP 服务器
        print("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        app.run()
    else:
        main()