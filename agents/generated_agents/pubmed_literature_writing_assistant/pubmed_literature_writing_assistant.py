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
            "model_id": self.model_id,
            "enable_logging": True
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
    
    def _load_marked_literature_ids(self, research_id: str) -> List[str]:
        """从manifest.json加载被标记的文献ID列表"""
        try:
            manifest_path = Path(".cache/pmc_literature") / research_id / "manifest.json"
            
            if not manifest_path.exists():
                logger.error(f"manifest.json不存在: {manifest_path}")
                return []
            
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            
            pmc_ids = []
            
            if isinstance(manifest_data, dict):
                if "marked_literature" in manifest_data:
                    marked_lit = manifest_data["marked_literature"]
                    if isinstance(marked_lit, dict) and "by_year" in marked_lit:
                        for year_data in marked_lit["by_year"].values():
                            if isinstance(year_data, dict) and "literature" in year_data:
                                for lit in year_data["literature"]:
                                    lit_id = lit.get("pmcid") or lit.get("id") or lit.get("pmid")
                                    if lit_id:
                                        pmc_ids.append(lit_id)
                    elif isinstance(marked_lit, dict) and "literature" in marked_lit:
                        for lit in marked_lit["literature"]:
                            lit_id = lit.get("pmcid") or lit.get("id") or lit.get("pmid")
                            if lit_id:
                                pmc_ids.append(lit_id)
                    elif isinstance(marked_lit, list):
                        for lit in marked_lit:
                            lit_id = lit.get("pmcid") or lit.get("id") or lit.get("pmid")
                            if lit_id:
                                pmc_ids.append(lit_id)
            
            return pmc_ids
            
        except Exception as e:
            logger.error(f"加载标记文献ID失败: {str(e)}")
            return []
    
    def _load_analysis_results(self, research_id: str, pmc_ids: List[str] = None) -> List[Dict]:
        """从analysis_results加载完整的文献分析结果"""
        try:
            analysis_dir = Path(".cache/pmc_literature") / research_id / "analysis_results"
            
            if not analysis_dir.exists():
                logger.warning(f"analysis_results目录不存在: {analysis_dir}")
                return []
            
            if pmc_ids is None:
                # 加载所有analysis_result文件
                analysis_files = list(analysis_dir.glob("*.json"))
            else:
                # 只加载指定的pmcid
                analysis_files = [analysis_dir / f"{pmcid}.json" for pmcid in pmc_ids]
            
            results = []
            
            for analysis_file in analysis_files:
                if not analysis_file.exists():
                    logger.warning(f"分析结果文件不存在: {analysis_file}")
                    continue
                
                try:
                    with open(analysis_file, 'r', encoding='utf-8') as f:
                        analysis_data = json.load(f)
                    results.append(analysis_data)
                except Exception as e:
                    logger.error(f"读取分析结果失败 {analysis_file}: {str(e)}")
                    continue
            
            logger.info(f"成功加载 {len(results)} 个分析结果")
            return results
            
        except Exception as e:
            logger.error(f"加载分析结果失败: {str(e)}")
            return []
    
    def _load_literature_metadata(self, research_id: str) -> List[Dict]:
        """加载文献元数据（保持向后兼容）"""
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
        """获取待处理的一篇文献（按影响因子从高到低排序，只返回analysis_results中的元数据，不提供全文）"""
        try:
            # 获取所有被标记的文献ID
            all_pmc_ids = self._load_marked_literature_ids(research_id)
            
            if not all_pmc_ids:
                return None
            
            status = self._get_processing_status(research_id)
            if not status:
                return None
            
            processed_ids = status.get("processed_literature", [])
            
            # 获取所有未处理文献的分析结果
            pending_literatures = []
            
            for lit_id in all_pmc_ids:
                if lit_id not in processed_ids:
                    # 从analysis_results加载完整的分析结果
                    analysis_results = self._load_analysis_results(research_id, [lit_id])
                    
                    if analysis_results and len(analysis_results) > 0:
                        analysis_data = analysis_results[0]
                        
                        # 提取影响因子，默认值为0
                        impact_factor = 0
                        try:
                            impact_factor_raw = analysis_data.get("impact_factor", 0)
                            if isinstance(impact_factor_raw, str):
                                impact_factor = float(impact_factor_raw)
                            else:
                                impact_factor = float(impact_factor_raw) if impact_factor_raw else 0
                        except (ValueError, TypeError):
                            impact_factor = 0
                        
                        pending_literatures.append({
                            "pmcid": lit_id,
                            "metadata": analysis_data,
                            "impact_factor": impact_factor,
                            "has_fulltext": False
                        })
            
            if not pending_literatures:
                return None
            
            # 按影响因子从高到低排序
            pending_literatures.sort(key=lambda x: x["impact_factor"], reverse=True)
            
            # 返回影响因子最高的未处理文献
            top_literature = pending_literatures[0]
            logger.info(f"选择待处理文献: {top_literature['pmcid']} (影响因子: {top_literature['impact_factor']})")
            
            return {
                "pmcid": top_literature["pmcid"],
                "metadata": top_literature["metadata"],
                "has_fulltext": top_literature["has_fulltext"]
            }
            
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
    
    def _mark_selected_papers_processed(self, research_id: str, pmc_ids: List[str]) -> None:
        """标记选中的文献为已处理"""
        try:
            cache_dir = Path(".cache/pmc_literature")
            research_dir = cache_dir / research_id
            status_file = research_dir / "step4.status"
            
            if status_file.exists():
                with open(status_file, 'r', encoding='utf-8') as f:
                    status = json.load(f)
            else:
                status = self._get_processing_status(research_id)
            
            # 将选中的文献ID添加到已处理列表
            for pmc_id in pmc_ids:
                if pmc_id and pmc_id not in status.get("processed_literature", []):
                    status["processed_literature"].append(pmc_id)
            
            status["updated_at"] = datetime.now().isoformat()
            
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功标记 {len(pmc_ids)} 篇文献为已处理")
            
        except Exception as e:
            logger.error(f"标记选中文献为已处理失败: {str(e)}")
    
    def _retry_agent_call(self, agent_input: str, max_retries: int = 5, retry_delay: int = 150):
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
                logger.info("="*100)
                print("="*100)
                print(f"Total tokens: {agent_response.metrics.accumulated_usage}")
                print(f"agent_response: {agent_response}")
                logger.info(f"agent_response: {agent_response}")
                logger.info(f"Total tokens: {agent_response.metrics.accumulated_usage}")
                logger.info(f"Execution time: {sum(agent_response.metrics.cycle_durations):.2f} seconds")
                logger.info(f"Tools used: {list(agent_response.metrics.tool_metrics.keys())}")
                print("="*100)
                logger.info("="*100)
                logger.info(f"✅ Agent 调用成功（尝试 {attempt}）")
                return agent_response
                    
            except Exception as e:
                logger.warning(f"⚠️ Agent 调用失败（尝试 {attempt}/{max_retries}）: {str(e)}")
                
                if attempt < max_retries:
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    # 只有在agent_response存在时才打印metrics
                    if agent_response and hasattr(agent_response, 'metrics'):
                        logger.info("="*100)
                        print(f"Total tokens: {agent_response.metrics.accumulated_usage}")
                        logger.info(f"Total tokens: {agent_response.metrics.accumulated_usage}")
                        logger.info(f"Execution time: {sum(agent_response.metrics.cycle_durations):.2f} seconds")
                        logger.info(f"Tools used: {list(agent_response.metrics.tool_metrics.keys())}")
                    sleep(retry_delay)
                else:
                    logger.error(f"❌ Agent 调用失败，已达最大重试次数: {str(e)}")
                    raise
        
        # 如果所有重试都失败
        raise Exception(f"Agent 调用失败，已重试 {max_retries} 次")
    
    def _extract_key_fields(self, metadata: Dict) -> Dict:
        """提取文献元数据的关键字段
        
        Args:
            metadata: 完整的文献元数据字典
            
        Returns:
            只包含关键字段的字典
        """
        key_fields = [
            "pmcid", "title", "abstract", "methods", "results", 
            "conclusions", "publication_date", "reasoning", "key_findings"
        ]
        
        extracted = {}
        for field in key_fields:
            if field in metadata:
                value = metadata[field]
                # key_findings如果是列表，需要特殊处理
                if field == "key_findings" and isinstance(value, list):
                    extracted[field] = value
                else:
                    extracted[field] = value
        
        return extracted
    
    def _format_metadata_for_agent(self, metadata_list: List[Dict]) -> str:
        """将元数据列表格式化为紧凑的文本格式以减少token
        
        使用紧凑格式：每篇文献用分隔符分隔，字段用简短标签
        格式说明：[序号]ID:xxx|T:标题|A:摘要|M:方法|R:结果|C:结论|Date:日期|Reason:理由|Findings:发现
        注意：不限制文本长度，保留完整内容
        
        Args:
            metadata_list: 文献元数据列表
            
        Returns:
            格式化后的紧凑文本字符串
        """
        if not metadata_list:
            return ""
        
        formatted_items = []
        for i, meta in enumerate(metadata_list, 1):
            # 提取关键字段
            key_meta = self._extract_key_fields(meta)
            
            # 构建紧凑格式
            parts = [f"[{i}]"]
            
            if "pmcid" in key_meta:
                parts.append(f"ID:{key_meta['pmcid']}")
            
            if "title" in key_meta:
                parts.append(f"T:{key_meta['title']}")
            
            if "abstract" in key_meta:
                parts.append(f"A:{key_meta['abstract']}")
            
            if "methods" in key_meta:
                parts.append(f"M:{key_meta['methods']}")
            
            if "results" in key_meta:
                parts.append(f"R:{key_meta['results']}")
            
            if "conclusions" in key_meta:
                parts.append(f"C:{key_meta['conclusions']}")
            
            if "publication_date" in key_meta:
                parts.append(f"Date:{key_meta['publication_date']}")
            
            if "reasoning" in key_meta:
                parts.append(f"Reason:{key_meta['reasoning']}")
            
            if "key_findings" in key_meta and isinstance(key_meta['key_findings'], list):
                findings = "|".join(key_meta['key_findings'])
                parts.append(f"Findings:{findings}")
            
            formatted_items.append("|".join(parts))
        
        return "\n".join(formatted_items)
    
    def _parse_agent_json_response(self, agent_response: Any) -> Optional[Dict]:
        """从agent_response中提取并解析JSON结果"""
        try:
            # 提取文本内容
            text_content = None
            if hasattr(agent_response, 'message'):
                message = agent_response.message
                if isinstance(message, str):
                    text_content = message
                elif isinstance(message, dict) and 'content' in message:
                    content_list = message['content']
                    if content_list and isinstance(content_list, list):
                        text_content = content_list[0].get('text', '') if isinstance(content_list[0], dict) else str(content_list[0])
            elif isinstance(agent_response, str):
                text_content = agent_response
            elif isinstance(agent_response, dict):
                return agent_response
            
            if not text_content:
                return None
            
            # 方法1: 尝试直接解析JSON
            try:
                return json.loads(text_content.strip())
            except json.JSONDecodeError:
                pass
            
            # 方法2: 查找```json代码块
            json_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', text_content)
            if json_block_match:
                json_str = json_block_match.group(1).strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            # 方法3: 从后往前查找最后一个完整的JSON对象
            json_end = -1
            json_start = -1
            brace_count = 0
            
            for i in range(len(text_content) - 1, -1, -1):
                if text_content[i] == '}':
                    json_end = i + 1
                    brace_count = 1
                    for j in range(i - 1, -1, -1):
                        char = text_content[j]
                        if char == '}':
                            brace_count += 1
                        elif char == '{':
                            brace_count -= 1
                            if brace_count == 0:
                                json_start = j
                                json_str = text_content[json_start:json_end].strip()
                                try:
                                    return json.loads(json_str)
                                except json.JSONDecodeError:
                                    pass
                                break
                    if json_start >= 0:
                        break
            
        except (AttributeError, KeyError, IndexError, TypeError) as e:
            logger.error(f"解析Agent响应失败: {str(e)}")
        return None
    
    def generate_literature_review(self, research_id: str, requirement: str = None, 
                                  language: str = "english", max_paper_to_init: int = 50) -> str:
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
                    
                    # 从manifest.json获取被标记的文献ID列表
                    pmc_ids = self._load_marked_literature_ids(research_id)
                    if not pmc_ids:
                        return "无法加载被标记的文献ID列表"
                    
                    # 从analysis_results加载完整的分析结果
                    all_analysis_results = self._load_analysis_results(research_id, pmc_ids)
                    if not all_analysis_results:
                        return "无法加载文献分析结果"
                    
                    # 按相关性分数和影响因子排序并取前max_paper_to_init篇
                    total_papers = len(all_analysis_results)
                    if total_papers > max_paper_to_init:
                        # 提取相关性分数和影响因子用于排序
                        for item in all_analysis_results:
                            # 提取相关性分数
                            relevance_score = 0
                            try:
                                relevance_score_raw = item.get("relevance_score", 0)
                                if isinstance(relevance_score_raw, str):
                                    relevance_score = float(relevance_score_raw)
                                else:
                                    relevance_score = float(relevance_score_raw) if relevance_score_raw else 0
                            except (ValueError, TypeError):
                                relevance_score = 0
                            item["_relevance_score_for_sort"] = relevance_score
                            
                            # 提取影响因子
                            impact_factor = 0
                            try:
                                impact_factor_raw = item.get("impact_factor", 0)
                                if isinstance(impact_factor_raw, str):
                                    impact_factor = float(impact_factor_raw)
                                else:
                                    impact_factor = float(impact_factor_raw) if impact_factor_raw else 0
                            except (ValueError, TypeError):
                                impact_factor = 0
                            item["_impact_factor_for_sort"] = impact_factor
                        
                        # 先按相关性分数从高到低排序，取前max_paper_to_init篇
                        papers_by_relevance = all_analysis_results.copy()
                        papers_by_relevance.sort(key=lambda x: x.get("_relevance_score_for_sort", 0), reverse=True)
                        top_by_relevance = papers_by_relevance[:max_paper_to_init]
                        
                        # 再按影响因子从高到低排序，取前max_paper_to_init篇
                        papers_by_impact = all_analysis_results.copy()
                        papers_by_impact.sort(key=lambda x: x.get("_impact_factor_for_sort", 0), reverse=True)
                        top_by_impact = papers_by_impact[:max_paper_to_init]
                        
                        # 合并两个结果并去重（使用pmcid作为唯一标识）
                        selected_pmc_ids_set = set()
                        selected_results = []
                        
                        # 先添加按相关性排序的结果
                        for item in top_by_relevance:
                            pmcid = item.get("pmcid")
                            if pmcid and pmcid not in selected_pmc_ids_set:
                                selected_pmc_ids_set.add(pmcid)
                                selected_results.append(item)
                        
                        # 再添加按影响因子排序的结果（避免重复）
                        for item in top_by_impact:
                            pmcid = item.get("pmcid")
                            if pmcid and pmcid not in selected_pmc_ids_set:
                                selected_pmc_ids_set.add(pmcid)
                                selected_results.append(item)
                        
                        # 记录使用的文献ID，以便后续标记为已处理
                        selected_pmc_ids = list(selected_pmc_ids_set)
                        
                        logger.info(f"从 {total_papers} 个文献中：按相关性选择了 {len(top_by_relevance)} 篇，按影响因子选择了 {len(top_by_impact)} 篇，合并去重后共 {len(selected_results)} 篇用于生成初始版本")
                        all_analysis_results = selected_results
                    else:
                        # 如果文献数量不超过限制，记录所有文献ID
                        selected_pmc_ids = [item.get("pmcid") for item in all_analysis_results if item.get("pmcid")]
                    
                    logger.info(f"加载了 {len(all_analysis_results)} 个分析结果用于初始版本")
                    
                    agent_input = f"""
====================项目基础信息====================
研究ID: {research_id}
输出语言: {language}
文献数量: {len(all_analysis_results)}
============================================================
用户研究需求:
{requirement if requirement else "无特殊需求"}
============================================================
文献完整分析结果（格式说明：每行一篇文献，格式为[序号]ID:xxx|T:标题|A:摘要|M:方法|R:结果|C:结论|Date:日期|Reason:理由|Findings:发现）:
{self._format_metadata_for_agent(all_analysis_results)}
============================================================
### 任务:请基于这些文献的完整分析结果生成初始版本的文献综述，并在完成后以JSON格式返回结果：

你的任务：
1. 仔细阅读用户需求，以及所有提供的文章分析结果
2. 生成初始版本的文献综述，要求有逻辑性，内容详细
3. 使用`file_write`工具将综述内容保存到文件
4. **必须**以JSON格式返回结果,不要返回其他内容：
```json
{{
    "status": "success",
    "research_id": "{research_id}",
    "version": "initial",
    "file_path": "保存的文件路径",
    "message": "成功生成初始版本"
}}
```
============================================================
"""
                    
                    logger.info("调用Agent生成初始版本")
                    agent_response = self._retry_agent_call(agent_input)
                    result = self._parse_agent_json_response(agent_response)
                    
                    if result and isinstance(result, dict) and result.get("status") == "success":
                        file_path = result.get("file_path", "")
                        
                        # 标记初始版本使用的文献为已处理
                        # self._mark_selected_papers_processed(research_id, selected_pmc_ids)
                        
                        if file_path:
                            logger.info(f"初始版本保存成功: {file_path}")
                            all_results.append(f"✅ 初始版本生成成功\n文件路径: {file_path}\n使用了 {len(selected_pmc_ids)} 篇文献\n")
                            
                            self._update_processing_status(research_id, 
                                                          "initial_marker", "initial", 
                                                          file_path)
                        else:
                            all_results.append(f"⚠️ 初始版本生成成功，但未获取到文件路径")
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
                    
                    # 获取新文献的完整分析结果元数据
                    new_literature_metadata = pending_literature.get('metadata', {})
                    
                    agent_input = f"""
====================项目基础信息====================
研究ID: {research_id}
现有版本文献地址: {status.get('version_file_path', 'N/A')}
新文献ID: {lit_id}
新文献分析结果路径: .cache/pmc_literature/{research_id}/analysis_results/{lit_id}.json
输出语言: {language}
====================现有文献综述内容====================
{latest_review}
====================新文献完整分析结果====================
文献ID: {lit_id}

**完整分析结果（格式说明：[序号]ID:xxx|T:标题|A:摘要|M:方法|R:结果|C:结论|Date:日期|Reason:理由|Findings:发现）:**
{self._format_metadata_for_agent([new_literature_metadata])}

============================================================

### 任务：请基于现有文献综述，判断整合新文献的内容是否必要，若必要则整合新文献的内容（基于上面提供的完整分析结果），并在完成后以JSON格式返回结果
注意：
- 新文献提供的是元数据及之前的分析信息，请使用工具extract_literature_content获取详细内容，并合理的将结果内容整合到现有综述中，详细补充和更新相关内容
- 原始版本综述基于所有文献元数据分析得到,更新综述时会提供其中一篇文献全文,统计数量时不应作为新文献数量

你的任务：
1. 结合文献元数据及之前的分析结果，以及当前版本文献内容，分析判断是否需要引用或已被引用
2. 针对疑问或不明确的内容，使用工具获取更加详细的内容、表格、结论等
3. 如需引用或该文献已被引用，至少使用一次工具获取详细内容，并合理的将结果内容整合到现有综述中，详细补充和更新相关内容
4. 使用`file_write`工具将更新后的综述内容保存到文件
5. 保存完成文件后，请总结输出一下主要更新内容
6. **必须**以JSON格式返回结果，不要返回其他内容：
```json
{{
    "status": "success",
    "research_id": "{research_id}",
    "processed_literature_id": "{lit_id}",
    "version": "{next_version}",
    "file_path": "保存的文件路径",
    "message": "成功更新综述"
}}
```

## 重要说明
- **当你觉得提供的文献全文没有引用价值时，可以直接返回JSON结果，结果中message值为：文献全文没有引用价值，processed_literature_id为该文献ID，其他值保持不变**
- **必须先保存文件**：使用工具file_write保存综述内容到文件后，再返回JSON结果
- **JSON返回格式**：所有任务完成后必须返回指定格式的JSON
- **file_path字段**：在JSON返回中包含保存的文件路径
- **版本标识**：initial用于初始版本，数字1、2、3...用于更新版本，final用于最终版本
============================================================
"""
                    # print(f"agent_input: {agent_input}")
                    logger.info(f"调用Agent处理文献 {lit_id}")
                    agent_response = self._retry_agent_call(agent_input)
                    result = self._parse_agent_json_response(agent_response)
                    
                    logger.info(f"result: {result}")
                    if result and isinstance(result, dict):
                        logger.info(f"✅ 成功解析Agent JSON结果: status={result.get('status')}")
                        logger.info(f"   文件路径: {result.get('file_path')}")
                        logger.info(f"   版本: {result.get('version')}")
                    else:
                        logger.error(f"❌ 无法解析Agent JSON结果")
                        logger.error(f"原始响应前1000字符: {str(agent_response)[:1000]}")
                    
                    if result and isinstance(result, dict) and result.get("status") == "success":
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
    parser.add_argument('-n', '--max_paper_to_init', type=int, default=50,
                       help='初始版本使用的最大文献数量，默认50')
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
            language=args.language,
            max_paper_to_init=args.max_paper_to_init
        )
        
    elif args.mode == 'status':
        print(f"📊 查询处理状态: 研究ID={args.research_id}")
        result = agent.get_review_status(
            research_id=args.research_id
        )
    
    print(f"📋 处理结果:\n{str(result)}")
