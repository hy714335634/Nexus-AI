#!/usr/bin/env python3
"""
PubMed Literature Writing Assistant

专门负责科研文献编写工作，能够根据用户提供的材料和思路进行文献综述的编写工作。
支持处理大量PubMed文献并生成高质量文献综述，实现断点续传和多语言输出功能。

功能特点:
- 读取研究ID对应的文献元数据
- 基于元数据生成初始文献综述
- 逐篇处理文献内容并更新综述
- 支持断点续传功能
- 多语言输出支持
- 会话数据缓存
"""

import os
import json
import logging
import re
from time import sleep
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry
from tools.system_tools.qcli_integration import call_q_cli

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置遥测
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()


class PubmedLiteratureWritingAssistant:
    """PubMed文献编写智能体类"""
    
    def __init__(self, env: str = "production", version: str = "latest", model_id: str = "default"):
        """
        初始化PubMed文献编写智能体
        
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
        self.agent_config_path = "generated_agents_prompts/pubmed_literature_writing_assistant/pubmed_literature_writing_assistant"
    
    def _create_agent(self):
        """创建新的智能体实例"""
        return create_agent_from_prompt_template(
            agent_name=self.agent_config_path,
            **self.agent_params
        )
    
    def _get_processing_status(self, research_id: str) -> Dict:
        """获取处理状态"""
        try:
            cache_dir = Path(".cache/pmc_literature")
            research_dir = cache_dir / research_id
            status_file = research_dir / "step4.status"
            
            if not status_file.exists():
                total_literature = 0
                try:
                    manifest_path = research_dir / "manifest.json"
                    if manifest_path.exists():
                        with open(manifest_path, 'r', encoding='utf-8') as f:
                            manifest_data = json.load(f)
                        
                        if isinstance(manifest_data, dict):
                            if "marked_literature" in manifest_data:
                                marked_lit = manifest_data["marked_literature"]
                                all_literature = []
                                if isinstance(marked_lit, dict) and "by_year" in marked_lit:
                                    for year_data in marked_lit["by_year"].values():
                                        if isinstance(year_data, dict) and "literature" in year_data:
                                            all_literature.extend(year_data["literature"])
                                elif isinstance(marked_lit, dict) and "literature" in marked_lit:
                                    all_literature = marked_lit["literature"]
                                elif isinstance(marked_lit, list):
                                    all_literature = marked_lit
                                total_literature = len(all_literature)
                            elif "literature" in manifest_data:
                                total_literature = len(manifest_data["literature"]) if isinstance(manifest_data["literature"], list) else 1
                        elif isinstance(manifest_data, list):
                            total_literature = len(manifest_data)
                except Exception as e:
                    logger.warning(f"读取manifest.json失败: {str(e)}")
                
                initial_status = {
                    "research_id": research_id,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "processed_literature": [],
                    "current_version": None,
                    "version_file_path": None,
                    "total_literature": total_literature,
                    "completed": False
                }
                
                with open(status_file, 'w', encoding='utf-8') as f:
                    json.dump(initial_status, f, ensure_ascii=False, indent=2)
                
                return initial_status
            
            with open(status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)
            
            return status
            
        except Exception as e:
            logger.error(f"获取处理状态失败: {str(e)}")
            return None
    
    def _load_literature_metadata(self, research_id: str) -> List[Dict]:
        """加载文献元数据"""
        try:
            manifest_path = Path(".cache/pmc_literature") / research_id / "manifest.json"
            
            if not manifest_path.exists():
                logger.error(f"manifest.json不存在: {manifest_path}")
                return []
            
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            
            if isinstance(manifest_data, dict):
                if "marked_literature" in manifest_data:
                    marked_lit = manifest_data["marked_literature"]
                    all_literature = []
                    if isinstance(marked_lit, dict) and "by_year" in marked_lit:
                        for year_data in marked_lit["by_year"].values():
                            if isinstance(year_data, dict) and "literature" in year_data:
                                all_literature.extend(year_data["literature"])
                    elif isinstance(marked_lit, dict) and "literature" in marked_lit:
                        all_literature = marked_lit["literature"]
                    elif isinstance(marked_lit, list):
                        all_literature = marked_lit
                    return all_literature
                elif "literature" in manifest_data:
                    return manifest_data["literature"]
            elif isinstance(manifest_data, list):
                return manifest_data
            
            return []
            
        except Exception as e:
            logger.error(f"加载文献元数据失败: {str(e)}")
            return []
    
    def _get_pending_literature(self, research_id: str) -> Optional[Dict]:
        """获取待处理的一篇文献"""
        try:
            all_metadata = self._load_literature_metadata(research_id)
            
            if not all_metadata:
                return None
            
            status = self._get_processing_status(research_id)
            if not status:
                return None
            
            processed_ids = status.get("processed_literature", [])
            research_dir = Path(".cache/pmc_literature") / research_id
            paper_dir = research_dir / "paper"
            
            for meta in all_metadata:
                lit_id = meta.get("pmcid") or meta.get("id") or meta.get("pmid")
                
                if lit_id and lit_id not in processed_ids:
                    paper_path = paper_dir / f"{lit_id}.txt"
                    fulltext = ""
                    
                    if paper_path.exists():
                        try:
                            with open(paper_path, 'r', encoding='utf-8') as f:
                                fulltext = f.read()
                        except Exception:
                            pass
                    
                    return {
                        "pmcid": lit_id,
                        "metadata": meta,
                        "fulltext": fulltext,
                        "has_fulltext": len(fulltext) > 0
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"获取待处理文献失败: {str(e)}")
            return None
    
    def _get_latest_review(self, research_id: str) -> Optional[str]:
        """获取最新生成的综述内容"""
        try:
            # 方法1：优先从status文件读取当前版本路径
            status = self._get_processing_status(research_id)
            if status and status.get("version_file_path"):
                version_path = status["version_file_path"]
                # 处理相对路径和绝对路径
                if not os.path.isabs(version_path):
                    file_path = Path(version_path)
                else:
                    file_path = Path(version_path)
                
                if file_path.exists():
                    logger.info(f"从status读取版本文件: {version_path}")
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return content
            
            # 方法2：解析文件名中的版本号，按版本排序
            reviews_dir = Path(".cache/pmc_literature") / research_id / "reviews"
            
            if not reviews_dir.exists():
                return None
            
            # 解析所有文件，提取版本号
            def extract_version(filename: str) -> tuple:
                """提取版本号和优先级
                返回: (priority, version_number, timestamp_str)
                initial=0, 数字版本直接比较"""
                name = filename.name
                if name.startswith("review_initial_"):
                    timestamp = name.replace("review_initial_", "").replace(".md", "")
                    return (0, 0, timestamp)
                elif name.startswith("review_v"):
                    # review_v{version}_{timestamp}.md
                    parts = name.replace("review_v", "").replace(".md", "").split("_")
                    if parts:
                        try:
                            version_num = int(parts[0])
                            timestamp = "_".join(parts[1:]) if len(parts) > 1 else ""
                            return (1, version_num, timestamp)
                        except:
                            return (2, 0, name)  # 无法解析，放到最后
                elif name.startswith("review_final_"):
                    timestamp = name.replace("review_final_", "").replace(".md", "")
                    return (3, 999999, timestamp)  # final 放到最后但优先级最高
                return (4, -1, name)  # 未知格式
            
            review_files = list(reviews_dir.glob("review_*.md"))
            if not review_files:
                return None
            
            # 按版本号排序
            sorted_files = sorted(review_files, key=extract_version)
            
            latest_file = sorted_files[-1]  # 获取版本号最大的
            logger.info(f"获取最新版本文件: {latest_file.name}")
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return content
            
        except Exception as e:
            logger.error(f"获取最新综述失败: {str(e)}")
            return None
    
    def _save_review_version(self, research_id: str, content: str, version: Union[str, int]) -> Dict:
        """保存文献综述版本"""
        try:
            reviews_dir = Path(".cache/pmc_literature") / research_id / "reviews"
            os.makedirs(reviews_dir, exist_ok=True)
            
            version_str = str(version).lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if version_str in ["initial", "final"]:
                filename = f"review_{version_str}_{timestamp}.md"
            else:
                filename = f"review_v{version_str}_{timestamp}.md"
            
            file_path = reviews_dir / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "status": "success",
                "research_id": research_id,
                "version": version_str,
                "file_path": str(file_path),
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"保存综述版本失败: {str(e)}")
            return {
                "status": "error",
                "message": f"保存失败: {str(e)}"
            }
    
    def _update_processing_status(self, research_id: str, 
                                 processed_literature_id: str, version: Union[str, int],
                                 version_file_path: str = None) -> Dict:
        """更新处理状态"""
        try:
            cache_dir = Path(".cache/pmc_literature")
            research_dir = cache_dir / research_id
            status_file = research_dir / "step4.status"
            
            if status_file.exists():
                with open(status_file, 'r', encoding='utf-8') as f:
                    status = json.load(f)
            else:
                status = self._get_processing_status(research_id)
            
            if processed_literature_id and processed_literature_id.lower() not in ["initial_marker"]:
                if processed_literature_id not in status["processed_literature"]:
                    status["processed_literature"].append(processed_literature_id)
            
            status["current_version"] = str(version)
            status["updated_at"] = datetime.now().isoformat()
            
            if version_file_path:
                status["version_file_path"] = version_file_path
            
            total = status.get("total_literature", 0)
            processed = len(status["processed_literature"])
            
            if total > 0 and processed >= total:
                status["completed"] = True
            
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
            
            return {
                "status": "success",
                "processed": processed,
                "total": total,
                "completed": status["completed"]
            }
            
        except Exception as e:
            logger.error(f"更新处理状态失败: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _mark_all_metadata_processed(self, research_id: str) -> Dict:
        """标记所有文献元数据已处理"""
        return self._update_processing_status(research_id, "initial_marker", "initial")
    
    def _retry_agent_call(self, agent_input: str, max_retries: int = 3, retry_delay: int = 60):
        """
        带重试机制的 Agent 调用
        
        Args:
            agent_input: 输入给 Agent 的内容
            max_retries: 最大重试次数，默认3次
            retry_delay: 重试间隔（秒），默认5秒
            
        Returns:
            AgentResult 对象
        """
        for attempt in range(1, max_retries + 1):
            agent_response = None
            try:
                logger.info(f"调用 Agent（尝试 {attempt}/{max_retries}）")
                # 每次调用前创建新的agent实例
                agent = self._create_agent()
                agent_response = agent(agent_input)
                
                # 验证响应
                if hasattr(agent_response, 'message') and agent_response.message:
                    logger.info(f"✅ Agent 调用成功（尝试 {attempt}）")
                    return agent_response
                elif hasattr(agent_response, 'content') and agent_response.content:
                    logger.info(f"✅ Agent 调用成功（尝试 {attempt}）")
                    return agent_response
                else:
                    raise ValueError("Agent 响应无效")
                    
            except Exception as e:
                logger.warning(f"⚠️ Agent 调用失败（尝试 {attempt}/{max_retries}）: {str(e)}")
                
                if attempt < max_retries:
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    # 只有在agent_response存在时才打印metrics
                    if agent_response and hasattr(agent_response, 'metrics'):
                        print("="*100)
                        print(f"Total tokens: {agent_response.metrics.accumulated_usage}")
                        print(f"Execution time: {sum(agent_response.metrics.cycle_durations):.2f} seconds")
                        print(f"Tools used: {list(agent_response.metrics.tool_metrics.keys())}")
                    sleep(retry_delay)
                else:
                    logger.error(f"❌ Agent 调用失败，已达最大重试次数: {str(e)}")
                    raise
        
        # 如果所有重试都失败
        raise Exception(f"Agent 调用失败，已重试 {max_retries} 次")
    
    def _extract_agent_text(self, agent_response: Any) -> str:
        """从 Agent 响应中提取文本内容"""
        # 首先检查是否是字典格式（Strands框架的标准消息格式）
        if isinstance(agent_response, dict):
            if 'content' in agent_response:
                # 格式：{'role': 'assistant', 'content': [{'text': '...'}]}
                content_list = agent_response['content']
                if isinstance(content_list, list):
                    texts = []
                    for item in content_list:
                        if isinstance(item, dict) and 'text' in item:
                            texts.append(item['text'])
                        elif isinstance(item, str):
                            texts.append(item)
                    return '\n'.join(texts)
                elif isinstance(content_list, str):
                    return content_list
            elif 'message' in agent_response:
                return str(agent_response['message'])
            else:
                return str(agent_response)
        elif hasattr(agent_response, 'message'):
            message = agent_response.message
            # 如果message是字典格式（Strands框架的标准消息格式）
            if isinstance(message, dict):
                if 'content' in message:
                    content_list = message['content']
                    if isinstance(content_list, list):
                        texts = []
                        for item in content_list:
                            if isinstance(item, dict) and 'text' in item:
                                texts.append(item['text'])
                            elif isinstance(item, str):
                                texts.append(item)
                        return '\n'.join(texts)
                    elif isinstance(content_list, str):
                        return content_list
            return str(message)
        elif hasattr(agent_response, 'content'):
            content = agent_response.content
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                texts = []
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        texts.append(item['text'])
                return '\n'.join(texts)
            elif isinstance(content, dict):
                # content 本身是一个字典 {'role': 'assistant', 'content': [...]}
                content_list = content.get('content', [])
                if isinstance(content_list, list):
                    texts = []
                    for item in content_list:
                        if isinstance(item, dict) and 'text' in item:
                            texts.append(item['text'])
                        elif isinstance(item, str):
                            texts.append(item)
                    return '\n'.join(texts)
                elif isinstance(content_list, str):
                    return content_list
            else:
                return str(content)
        else:
            # 尝试从字符串表示中提取内容
            str_repr = str(agent_response)
            # 如果看起来是字典的字符串表示，尝试提取其中的文本
            if str_repr.startswith("{'") and 'content' in str_repr:
                # 尝试解析这个字典的字符串表示
                try:
                    import ast
                    parsed = ast.literal_eval(str_repr)
                    if isinstance(parsed, dict) and 'content' in parsed:
                        content_list = parsed['content']
                        if isinstance(content_list, list):
                            texts = []
                            for item in content_list:
                                if isinstance(item, dict) and 'text' in item:
                                    texts.append(item['text'])
                            if texts:
                                return '\n'.join(texts)
                except:
                    pass
            return str_repr
    
    def _parse_agent_json_result(self, agent_response: str) -> Optional[Dict]:
        """解析Agent返回的JSON结果"""
        try:
            # 打印Agent响应用于调试
            logger.info(f"Agent响应前500字符: {agent_response[:500]}")
            
            # 方法1: 查找```json和```之间的所有内容（更健壮的方法）
            json_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', agent_response)
            if json_block_match:
                json_str = json_block_match.group(1).strip()
                logger.info("从```json代码块中提取JSON")
                try:
                    result = json.loads(json_str)
                    logger.info(f"成功解析JSON: status={result.get('status')}")
                    return result
                except Exception as e:
                    logger.error(f"解析代码块中的JSON失败: {str(e)}")
            
            # 方法2: 从后往前查找，找到最后一个完整的JSON对象
            # Agent通常会在最后返回JSON结果，这样可以避免匹配到中间思考过程的JSON片段
            logger.info("尝试从后往前查找JSON对象")
            json_end = -1
            json_start = -1
            brace_count = 0
            
            # 从后往前找最后一个}
            for i in range(len(agent_response) - 1, -1, -1):
                if agent_response[i] == '}':
                    json_end = i + 1
                    brace_count = 1
                    # 现在从i-1开始往前找匹配的{
                    for j in range(i - 1, -1, -1):
                        char = agent_response[j]
                        if char == '}':
                            brace_count += 1
                        elif char == '{':
                            brace_count -= 1
                            if brace_count == 0:
                                json_start = j
                                # 找到了一个完整的JSON对象
                                json_str = agent_response[json_start:json_end]
                                json_str = json_str.strip()
                                logger.info(f"从后往前找到JSON对象（前200字符）: {json_str[:200]}...")
                                try:
                                    result = json.loads(json_str)
                                    logger.info(f"成功解析JSON: status={result.get('status')}")
                                    # 验证是否包含预期的字段
                                    if 'status' in result:
                                        return result
                                except Exception as e:
                                    logger.warning(f"解析JSON对象失败: {str(e)}")
                                break
                    # 如果找到了一个完整的JSON，退出外层循环
                    if json_start >= 0:
                        break
            
            # 方法3: 向前兼容，从前往后查找第一个JSON对象
            json_start = agent_response.find('{')
            if json_start >= 0:
                brace_count = 0
                json_end = -1
                for i in range(json_start, len(agent_response)):
                    char = agent_response[i]
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                if json_end > json_start:
                    json_str = agent_response[json_start:json_end]
                    logger.info(f"从响应中找到JSON对象（前200字符）: {json_str[:200]}...")
                    try:
                        result = json.loads(json_str)
                        logger.info(f"成功解析JSON: status={result.get('status')}")
                        return result
                    except Exception as e:
                        logger.error(f"解析JSON对象失败: {str(e)}")
                        logger.error(f"完整JSON内容: {json_str}")
            
            # 方法3: 尝试直接解析整个响应
            try:
                result = json.loads(agent_response)
                logger.info("直接解析响应成功")
                return result
            except Exception as e:
                logger.warning(f"直接解析失败: {str(e)}")
            
            logger.error("无法从Agent响应中解析JSON")
            logger.error(f"完整响应内容: {agent_response}")
            return None
            
        except Exception as e:
            logger.error(f"解析Agent JSON结果时发生异常: {str(e)}")
            logger.error(f"响应内容: {agent_response}")
            return None
    
    def generate_literature_review(self, research_id: str, requirement: str = None, 
                                  language: str = "english") -> str:
        """生成文献综述（主控制循环）"""
        try:
            all_results = []
            
            while True:
                status = self._get_processing_status(research_id)
                if not status:
                    return "获取处理状态失败"
                
                processed_count = len(status.get("processed_literature", []))
                total_count = status.get("total_literature", 0)
                pending_count = total_count - processed_count
                
                logger.info(f"当前进度: {processed_count}/{total_count}, 待处理: {pending_count}")
                
                if processed_count == 0 and not status.get("current_version"):
                    # 情况A：生成初始版本
                    logger.info("所有文献未处理，生成初始版本")
                    
                    metadata = self._load_literature_metadata(research_id)
                    if not metadata:
                        return "无法加载文献元数据"
                    
                    agent_input = f"""
请根据以下文献元数据生成初始版本的文献综述：

研究ID: {research_id}
输出语言: {language}
文献数量: {len(metadata)}

用户研究需求:
{requirement if requirement else "无特殊需求"}

文献元数据:
{json.dumps(metadata, ensure_ascii=False, indent=2)}

请生成初始版本的文献综述，并在完成后以JSON格式返回结果：
{{
    "status": "success",
    "research_id": "{research_id}",
    "version": "initial",
    "file_path": "保存的文件路径",
    "message": "成功生成初始版本"
}}
"""
                    
                    logger.info("调用Agent生成初始版本")
                    agent_response = self._retry_agent_call(agent_input)

                    print("="*100)
                    # Access metrics through the AgentResult
                    print(f"Total tokens: {agent_response.metrics.accumulated_usage}")
                    print(f"Execution time: {sum(agent_response.metrics.cycle_durations):.2f} seconds")
                    print(f"Tools used: {list(agent_response.metrics.tool_metrics.keys())}")
                    
                    agent_text = self._extract_agent_text(agent_response)
                    result = self._parse_agent_json_result(agent_text)
                    print("="*100)
                    print(f"解析结果: {result}")
                    
                    
                    if result and result.get("status") == "success":
                        file_path = result.get("file_path", "")
                        
                        if file_path:
                            logger.info(f"初始版本保存成功: {file_path}")
                            all_results.append(f"✅ 初始版本生成成功\n文件路径: {file_path}\n")
                            
                            self._mark_all_metadata_processed(research_id)
                            self._update_processing_status(research_id, 
                                                          "initial_marker", "initial", 
                                                          file_path)
                        else:
                            all_results.append(f"⚠️ 初始版本生成成功，但未获取到文件路径")
                            self._mark_all_metadata_processed(research_id)
                            self._update_processing_status(research_id, 
                                                          "initial_marker", "initial", 
                                                          None)
                    else:
                        all_results.append(f"❌ Agent生成初始版本失败")
                        break
                
                elif pending_count > 0:
                    # 情况B：继续处理未处理文献
                    logger.info(f"继续处理，还有 {pending_count} 篇文献待处理")
                    
                    pending_literature = self._get_pending_literature(research_id)
                    
                    if not pending_literature:
                        logger.info("没有待处理的文献")
                        break
                    
                    lit_id = pending_literature["pmcid"]
                    logger.info(f"处理文献: {lit_id}")
                    
                    latest_review = self._get_latest_review(research_id)
                    
                    if not latest_review:
                        all_results.append("❌ 无法获取最新综述")
                        break
                    
                    current_version = status.get("current_version", "initial")
                    if current_version == "initial":
                        next_version = 1
                    else:
                        try:
                            next_version = int(current_version) + 1
                        except:
                            next_version = 1                    
                    lit_metadata = pending_literature.get('metadata', {})
                    processed_fulltext = self._remove_reference_from_literature(pending_literature['fulltext'])
                    
                    agent_input = f"""
====================项目基础信息====================
研究ID: {research_id}
现有版本文献地址: {status.get('version_file_path', 'N/A')}
新文献地址: .cache/pmc_literature/{research_id}/paper/{lit_id}.txt
输出语言: {language}
====================现有文献综述内容====================
**现有文献综述内容:**
{latest_review}
====================新文献元数据及全文内容====================
**新文献元数据:**
- PMCID: {lit_id}
- metadata: {json.dumps(lit_metadata, ensure_ascii=False, indent=2)}
====================输出要求====================
{{
    "status": "success",
    "research_id": "{research_id}",
    "processed_literature_id": "{lit_id}",
    "version": "{next_version}",
    "file_path": "保存的文件路径",
    "message": "成功更新综述"
}}
============================================================
请基于现有文献综述，判断整合新文献的内容是否必要，若必要则整合新文献的内容，并在完成后以JSON格式返回结果
如需要更详细内容，请使用工具extract_literature_content获取
"""
                    print(f"agent_input: {agent_input}")
                    logger.info(f"调用Agent处理文献 {lit_id}")
                    agent_response = self._retry_agent_call(agent_input)
                    
                    # 从 AgentResult 对象中提取文本内容
                    agent_text = self._extract_agent_text(agent_response)
                    result = self._parse_agent_json_result(agent_text)
                    print("="*100)
                    print(f"agent_text: {agent_text[:500]}")

                    print("="*100)
                    print(f"Total tokens: {agent_response.metrics.accumulated_usage}")
                    print(f"Execution time: {sum(agent_response.metrics.cycle_durations):.2f} seconds")
                    print(f"Tools used: {list(agent_response.metrics.tool_metrics.keys())}")
                    print(result)
                    print("="*100)
                    if result:
                        logger.info(f"✅ 成功解析Agent JSON结果: status={result.get('status')}")
                        logger.info(f"   文件路径: {result.get('file_path')}")
                        logger.info(f"   版本: {result.get('version')}")
                    else:
                        logger.error(f"❌ 无法解析Agent JSON结果")
                        logger.error(f"原始响应前1000字符: {str(agent_response)[:1000]}")
                    
                    if result and result.get("status") == "success":
                        logger.info(f"✅ JSON解析成功，开始更新状态")
                        file_path = result.get("file_path", "")
                        processed_id = result.get("processed_literature_id", lit_id)
                        
                        if file_path:
                            logger.info(f"版本 {next_version} 保存成功: {file_path}")
                            all_results.append(f"✅ 处理文献 {lit_id} 成功\n版本: {next_version}\n文件路径: {file_path}\n")
                            
                            self._update_processing_status(research_id, 
                                                          processed_id, next_version,
                                                          file_path)
                        else:
                            all_results.append(f"⚠️ 处理文献 {lit_id} 成功，但未获取到文件路径")
                            self._update_processing_status(research_id, 
                                                          processed_id, next_version,
                                                          None)
                    else:
                        all_results.append(f"❌ 处理文献 {lit_id} 失败")
                        print("="*100)
                        print(f"Total tokens: {agent_response.metrics.accumulated_usage}")
                        print(f"Execution time: {sum(agent_response.metrics.cycle_durations):.2f} seconds")
                        print(f"Tools used: {list(agent_response.metrics.tool_metrics.keys())}")
                        print("="*100)
                        break
                
                elif pending_count == 0:
                    # 所有文献已处理完成
                    logger.info("所有文献已处理完成")
                    
                    # Agent已经保存了每个版本的文件，只需要更新状态为完成
                    status["completed"] = True
                    
                    # 获取最新的文件路径
                    reviews_dir = Path(".cache/pmc_literature") / research_id / "reviews"
                    if reviews_dir.exists():
                        review_files = sorted(reviews_dir.glob("review_*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
                        if review_files:
                            latest_file = review_files[0]
                            file_path = str(latest_file)
                            status["version_file_path"] = file_path
                            all_results.append(f"✅ 所有文献处理完成最终版本: {file_path}")
                    
                    status_file = Path(".cache/pmc_literature") / research_id / "step4.status"
                    
                    with open(status_file, 'w', encoding='utf-8') as f:
                        json.dump(status, f, ensure_ascii=False, indent=2)
                    
                    break
                
                else:
                    logger.warning("未知状态，停止处理")
                    break
                sleep(60)
            
            
            return "\n" + "="*80 + "\n" + "\n".join(all_results)
            
        except Exception as e:
            logger.error(f"文献综述生成失败: {str(e)}")
            return f"文献综述生成过程中发生错误: {str(e)}"

    def _remove_reference_from_literature(self, literature: str) -> str:
        """移除文献中的参考文献"""
        # 按==== Refs分割，删除==== Refs之后的所有内容
        refs = literature.split('==== Refs')

        # 保留==== Body到==== Refs之间的内容
        body = refs[0].split('==== Body')[1].strip()
        return body

    def get_review_status(self, research_id: str) -> str:
        """获取文献综述处理状态"""
        try:
            status = self._get_processing_status(research_id)
            
            if not status:
                return "无法获取处理状态"
            
            processed_count = len(status.get("processed_literature", []))
            total_count = status.get("total_literature", 0)
            pending_count = total_count - processed_count
            
            result = f"""
处理状态信息:
- 研究ID: {research_id}
- 总文献数: {total_count}
- 已处理: {processed_count}
- 待处理: {pending_count}
- 当前版本: {status.get('current_version', 'N/A')}
- 版本文件: {status.get('version_file_path', 'N/A')}
- 是否完成: {status.get('completed', False)}
"""
            
            return result
            
        except Exception as e:
            logger.error(f"获取处理状态失败: {str(e)}")
            return f"获取处理状态过程中发生错误: {str(e)}"


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='PubMed文献编写智能体')
    parser.add_argument('-r', '--research_id', type=str, required=True,
                       help='研究ID，对应.cache/pmc_literature下的目录名')
    parser.add_argument('-q', '--requirement', type=str, default=None,
                       help='用户额外研究需求')
    parser.add_argument('-l', '--language', type=str, default='english',
                       help='输出语言')
    parser.add_argument('-m', '--mode', type=str,
                       choices=['generate', 'status'],
                       default='generate',
                       help='操作模式')
    args = parser.parse_args()
    
    agent = PubmedLiteratureWritingAssistant()
    print(f"✅ PubMed文献编写智能体创建成功")
    
    if args.mode == 'generate':
        print(f"📝 开始生成文献综述: 研究ID={args.research_id}")
        
        result = agent.generate_literature_review(
            research_id=args.research_id,
            requirement=args.requirement,
            language=args.language
        )
        
    elif args.mode == 'status':
        print(f"📊 查询处理状态: 研究ID={args.research_id}")
        result = agent.get_review_status(
            research_id=args.research_id
        )
    
    print(f"📋 处理结果:\n{result}")
