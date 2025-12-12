#!/usr/bin/env python3
"""
PubMed Literature Optimization Workflow

手动编排review、editor、writing三个agent，实现文献优化工作流。
工作流：
1. 自动找到当前最新版本文献
2. 调用review agent对文章进行分析，给出评审意见（只返回JSON结果，无需生成图表）
3. 如果review未通过，将review审核结果+文献全文给到writing agent进行修正，然后回到步骤2
4. 如果review通过，调用editor agent对文章进行分析，给出评审意见（只返回JSON结果，无需生成图表）
5. 如果editor未通过，将editor审核结果+文献全文给到writing agent进行修正，然后回到步骤2
6. 如果review和editor都通过，则结束流程
7. 重复步骤2-6，直到都通过或达到最大迭代次数
"""

import os
import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry
from nexus_utils.config_loader import ConfigLoader
config = ConfigLoader()
# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置遥测
os.environ["BYPASS_TOOL_CONSENT"] = "true"
otel_endpoint = config.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default",
    "enable_logging": True
}


class PubmedLiteratureOptimizationWorkflow:
    """PubMed文献优化工作流类"""
    
    def __init__(self, research_id: str, env: str = "production", version: str = "latest", model_id: str = "default"):
        """
        初始化PubMed文献优化工作流
        
        Args:
            research_id (str): 研究ID
            env (str): 环境配置 (development, production, testing)
            version (str): 智能体版本
            model_id (str): 使用的模型ID
        """
        self.research_id = research_id
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
        
        logger.info("Agent实例将在需要时创建")
        
        # 设置输出目录
        self.base_cache_dir = Path(".cache/pmc_literature")
        self.output_dir = self.base_cache_dir / research_id / "optimization"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_step4_status(self) -> Dict[str, Any]:
        """加载step4.status文件"""
        status_path = self.base_cache_dir / self.research_id / "step4.status"
        if not status_path.exists():
            raise FileNotFoundError(f"找不到step4.status文件: {status_path}")
        
        with open(status_path, "r", encoding="utf-8") as f:
            status = json.load(f)
        
        return status
    
    def _get_current_version(self) -> str:
        """从step4.status获取当前版本号"""
        step4_status = self._load_step4_status()
        current_version = step4_status.get("current_version", "1")
        logger.info(f"获取到当前版本号: {current_version}")
        return str(current_version)
    
    def _load_version_file(self, version_file_path: str) -> str:
        """加载version_file_path指定的文件内容"""
        # 处理相对路径和绝对路径
        if not os.path.isabs(version_file_path):
            file_path = Path(version_file_path)
        else:
            file_path = Path(version_file_path)
        
        # 如果路径不是绝对路径，尝试从当前目录或缓存目录查找
        if not file_path.is_absolute():
            # 尝试从缓存目录查找
            cache_path = self.base_cache_dir / self.research_id / file_path
            if cache_path.exists():
                file_path = cache_path
            else:
                # 尝试从当前目录查找
                current_path = Path(file_path)
                if current_path.exists():
                    file_path = current_path
                else:
                    raise FileNotFoundError(f"找不到文件: {version_file_path}")
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        logger.info(f"成功加载文件内容: {file_path}, 长度: {len(content)} 字符")
        return content
    
    def _save_status(self, status: Dict[str, Any]) -> None:
        """保存工作流状态"""
        status_file = self.output_dir / "workflow_status.json"
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
    
    def _call_agent(self, agent_name: str, input_text: str, max_retries: int = 3, retry_delay: int = 5):
        """
        调用agent并返回结果，带重试机制
        每次重试都会创建新的agent实例，确保上下文隔离
        
        Args:
            agent_name: agent配置名称
            input_text: 输入文本
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        
        Returns:
            AgentResult对象
        """
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"调用Agent {agent_name}（尝试 {attempt}/{max_retries}）")
                # 每次重试创建新实例，确保上下文隔离
                agent = create_agent_from_prompt_template(
                    agent_name=agent_name,
                    **self.agent_params
                )
                agent_response = agent(input_text)
                
                logger.info("="*100)
                logger.info(f"Total tokens: {agent_response.metrics.accumulated_usage}")
                logger.info(f"Execution time: {sum(agent_response.metrics.cycle_durations):.2f} seconds")
                logger.info(f"Tools used: {list(agent_response.metrics.tool_metrics.keys())}")
                logger.info("="*100)
                
                logger.info(f"✅ Agent调用成功（尝试 {attempt}）")
                return agent_response
                
            except Exception as e:
                logger.warning(f"⚠️ Agent调用失败（尝试 {attempt}/{max_retries}）: {str(e)}")
                if attempt < max_retries:
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"❌ Agent调用失败，已达最大重试次数: {str(e)}")
                    raise
        
        raise Exception(f"Agent调用失败，已重试 {max_retries} 次")
    
    def _extract_agent_content(self, agent_response: Any) -> str:
        """从agent_response中提取文本内容"""
        try:
            if hasattr(agent_response, 'content'):
                return str(agent_response.content)
            elif hasattr(agent_response, 'message'):
                message = agent_response.message
                if isinstance(message, str):
                    return message
                elif isinstance(message, dict) and 'content' in message:
                    content_list = message['content']
                    if content_list and isinstance(content_list, list):
                        if isinstance(content_list[0], dict):
                            return content_list[0].get('text', '')
                        else:
                            return str(content_list[0])
            elif isinstance(agent_response, str):
                return agent_response
            else:
                return str(agent_response)
        except Exception as e:
            logger.error(f"提取Agent响应内容失败: {str(e)}")
            return str(agent_response)
    
    def _parse_agent_json_response(self, agent_response: Any) -> Optional[Dict]:
        """从agent_response中提取并解析JSON结果"""
        try:
            # 提取文本内容
            text_content = self._extract_agent_content(agent_response)
            
            if not text_content:
                logger.warning("无法提取文本内容")
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
    
    def run_optimization(self, max_iterations: int = 10) -> Dict[str, Any]:
        """
        执行优化工作流
        
        工作流逻辑：
        1. 自动找到当前最新版本文献
        2. 调用review agent对文章进行分析，给出评审意见（只返回JSON结果）
        3. 如果review未通过，将review审核结果+文献全文给到writing agent进行修正，然后回到步骤2
        4. 如果review通过，调用editor agent对文章进行分析，给出评审意见（只返回JSON结果）
        5. 如果editor未通过，将editor审核结果+文献全文给到writing agent进行修正，然后回到步骤2
        6. 如果review和editor都通过，则结束流程
        7. 重复步骤2-6，直到都通过或达到最大迭代次数
        
        Args:
            max_iterations (int): 最大迭代次数，默认10次
        
        Returns:
            Dict: 工作流执行结果
        """
        try:
            logger.info(f"开始执行优化工作流，research_id: {self.research_id}, 最大迭代次数: {max_iterations}")
            
            # 初始化工作流状态
            workflow_status = {
                "research_id": self.research_id,
                "started_at": datetime.now().isoformat(),
                "max_iterations": max_iterations,
                "iterations": [],
                "final_status": "running"
            }
            
            # 步骤1: 加载最新版本文献
            logger.info("="*80)
            logger.info("步骤1: 加载最新版本文献")
            logger.info("="*80)
            
            step4_status = self._load_step4_status()
            current_version = self._get_current_version()
            version_file_path = step4_status.get("version_file_path")
            
            if not version_file_path:
                raise ValueError("step4.status中未找到version_file_path字段")
            
            logger.info(f"加载文件内容: {version_file_path}")
            current_content = self._load_version_file(version_file_path)
            
            workflow_status["initial_version"] = current_version
            workflow_status["initial_file_path"] = version_file_path
            
            # 主迭代循环
            iteration = 0
            review_passed = False
            editor_passed = False
            
            logger.info("="*80)
            logger.info("开始优化工作流迭代循环")
            logger.info("="*80)
            
            while iteration < max_iterations:
                iteration += 1
                logger.info(f"\n{'='*80}")
                logger.info(f"迭代 {iteration}/{max_iterations}")
                logger.info(f"当前版本: {current_version}")
                logger.info(f"Review状态: {'已通过' if review_passed else '未通过'}")
                logger.info(f"Editor状态: {'已通过' if editor_passed else '未通过'}")
                logger.info(f"{'='*80}\n")
                
                iteration_record = {
                    "iteration": iteration,
                    "version": current_version,
                    "timestamp": datetime.now().isoformat(),
                    "status": "running"
                }
                
                try:
                    # 步骤2: 调用review agent
                    logger.info(f"[迭代 {iteration}] 调用Review Assistant进行审核")
                    
                    review_prompt = f"""
请对以下文献内容进行全面审核：

研究ID: {self.research_id}
当前版本: {current_version}
文件路径: {version_file_path}

**重要说明**：
- 请使用research_id={self.research_id}和version={current_version}参数
- **无需生成图表，只返回JSON结果**
- 所有输出文件应保存在: .cache/pmc_literature/{self.research_id}/feedback/reviewer/{current_version}/

**任务要求**：
1. 对文献进行全面的多维度评估
2. **必须以JSON格式返回结果**，包含以下字段：
   - approved: True/False (是否通过审核)
   - report_path: 评估报告文件路径（可选）
   - feedback: 审核意见和建议（详细内容）

**JSON返回格式**：
```json
{{
    "approved": true/false,
    "report_path": "保存的报告文件路径（可选）",
    "feedback": "审核意见和建议（详细内容）"
}}
```

**注意**：请直接返回JSON格式，不要包含其他文字说明，不要生成图表。

文献内容：
{current_content}
"""
                    
                    review_response = self._call_agent(
                        "generated_agents_prompts/pubmed_literature_review_assistant/pubmed_literature_review_assistant",
                        review_prompt
                    )
                    review_result = self._parse_agent_json_response(review_response)
                    
                    if not review_result or not isinstance(review_result, dict):
                        raise ValueError("Review Assistant返回结果解析失败，无法获取JSON结果")
                    
                    review_feedback = review_result.get("feedback", "")
                    review_report_path = review_result.get("report_path", "")
                    review_approved = review_result.get("approved", False)
                    
                    logger.info(f"Review Assistant审核完成: {'通过' if review_approved else '不通过'}")
                    logger.info(f"反馈长度: {len(review_feedback)} 字符")
                    
                    iteration_record["review_result"] = review_result
                    iteration_record["review_approved"] = review_approved
                    
                    # 如果review未通过，立即调用writing agent修正
                    if not review_approved:
                        logger.info(f"[迭代 {iteration}] Review未通过，调用Writing Assistant进行修正")
                        
                        # 计算下一个版本号
                        if current_version == "initial":
                            next_version = 1
                        else:
                            try:
                                next_version = int(current_version) + 1
                            except:
                                next_version = 1
                        
                        writing_prompt = f"""
请根据Review Assistant的审核意见对文献进行修正：

研究ID: {self.research_id}
当前版本: {current_version}
目标版本: {next_version}

**Review反馈**：
{review_feedback}

**Review报告路径**：{review_report_path}

**重要说明**：
- 请根据Review反馈意见修改文献内容
- 使用file_write保存修正后的文献
- 所有输出文件应保存在: .cache/pmc_literature/{self.research_id}/reviews/
- **必须以JSON格式返回结果**

**JSON返回格式**：
```json
{{
    "status": "success",
    "research_id": "{self.research_id}",
    "version": "{next_version}",
    "file_path": "保存的文件路径",
    "message": "成功更新综述"
}}
```

当前文献内容：
{current_content}
"""
                        
                        writing_response = self._call_agent(
                            "generated_agents_prompts/pubmed_literature_writing_assistant/pubmed_literature_writing_assistant",
                            writing_prompt
                        )
                        writing_result = self._parse_agent_json_response(writing_response)
                        
                        if not writing_result or not isinstance(writing_result, dict):
                            raise ValueError("Writing Assistant返回结果解析失败，无法获取JSON结果")
                        
                        new_file_path = writing_result.get("file_path")
                        if not new_file_path or not Path(new_file_path).exists():
                            raise ValueError(f"Writing Assistant未返回有效文件路径: {new_file_path}")
                        
                        # 更新当前内容和版本
                        current_content = Path(new_file_path).read_text(encoding="utf-8")
                        current_version = str(next_version)
                        version_file_path = new_file_path
                        
                        logger.info(f"Writing Assistant修正完成")
                        logger.info(f"新文件路径: {new_file_path}")
                        logger.info(f"新版本: {current_version}")
                        
                        iteration_record["writing_result"] = writing_result
                        iteration_record["new_version"] = current_version
                        iteration_record["new_file_path"] = new_file_path
                        iteration_record["status"] = "completed"
                        iteration_record["correction_reason"] = "review_not_passed"
                        workflow_status["iterations"].append(iteration_record)
                        
                        # 重置审核状态，准备下一轮迭代
                        review_passed = False
                        editor_passed = False
                        
                        # 防止无限循环
                        time.sleep(2)
                        continue  # 重新开始迭代，跳过editor审核
                    
                    # Review通过，继续调用editor agent
                    review_passed = True
                    logger.info(f"[迭代 {iteration}] Review通过，继续调用Editor Assistant进行审核")
                    
                    # 步骤3: 调用editor agent
                    editor_prompt = f"""
请对以下文献内容进行主编级别的审核：

研究ID: {self.research_id}
当前版本: {current_version}
文件路径: {version_file_path}

**重要说明**：
- 请使用research_id={self.research_id}和version={current_version}参数
- **无需生成图表，只返回JSON结果**
- 所有输出文件应保存在: .cache/pmc_literature/{self.research_id}/feedback/editor/{current_version}/

**任务要求**：
1. 从主编视角进行全面的期刊评审
2. **必须以JSON格式返回结果**，包含以下字段：
   - approved: True/False (是否通过审核)
   - report_path: 评审报告文件路径（可选）
   - feedback: 评审意见和建议（详细内容）

**JSON返回格式**：
```json
{{
    "approved": true/false,
    "report_path": "保存的报告文件路径（可选）",
    "feedback": "评审意见和建议（详细内容）"
}}
```

**注意**：请直接返回JSON格式，不要包含其他文字说明，不要生成图表。

文献内容：
{current_content}
"""
                    
                    editor_response = self._call_agent(
                        "generated_agents_prompts/pubmed_literature_editor_assistant/pubmed_literature_editor_assistant",
                        editor_prompt
                    )
                    editor_result = self._parse_agent_json_response(editor_response)
                    
                    if not editor_result or not isinstance(editor_result, dict):
                        raise ValueError("Editor Assistant返回结果解析失败，无法获取JSON结果")
                    
                    editor_feedback = editor_result.get("feedback", "")
                    editor_report_path = editor_result.get("report_path", "")
                    editor_approved = editor_result.get("approved", False)
                    
                    logger.info(f"Editor Assistant审核完成: {'通过' if editor_approved else '不通过'}")
                    logger.info(f"反馈长度: {len(editor_feedback)} 字符")
                    
                    iteration_record["editor_result"] = editor_result
                    iteration_record["editor_approved"] = editor_approved
                    
                    # 更新状态
                    editor_passed = editor_approved
                    
                    # 检查是否都通过
                    if review_passed and editor_passed:
                        logger.info("="*80)
                        logger.info("🎉 Review和Editor都通过，工作流完成！")
                        logger.info("="*80)
                        iteration_record["status"] = "completed"
                        iteration_record["all_passed"] = True
                        workflow_status["iterations"].append(iteration_record)
                        workflow_status["review_passed"] = True
                        workflow_status["editor_passed"] = True
                        workflow_status["final_status"] = "completed"
                        workflow_status["final_version"] = current_version
                        workflow_status["final_file_path"] = version_file_path
                        break
                    
                    # Editor未通过，调用writing agent修正
                    if not editor_approved:
                        logger.info(f"[迭代 {iteration}] Editor未通过，调用Writing Assistant进行修正")
                        
                        # 计算下一个版本号
                        if current_version == "initial":
                            next_version = 1
                        else:
                            try:
                                next_version = int(current_version) + 1
                            except:
                                next_version = 1
                        
                        writing_prompt = f"""
请根据Editor Assistant的评审意见对文献进行修正：

研究ID: {self.research_id}
当前版本: {current_version}
目标版本: {next_version}

**Editor反馈**：
{editor_feedback}

**Editor报告路径**：{editor_report_path}

**重要说明**：
- 请根据Editor反馈意见修改文献内容
- 使用file_write保存修正后的文献
- 所有输出文件应保存在: .cache/pmc_literature/{self.research_id}/reviews/
- **必须以JSON格式返回结果**

**JSON返回格式**：
```json
{{
    "status": "success",
    "research_id": "{self.research_id}",
    "version": "{next_version}",
    "file_path": "保存的文件路径",
    "message": "成功更新综述"
}}
```

当前文献内容：
{current_content}
"""
                        
                        writing_response = self._call_agent(
                            "generated_agents_prompts/pubmed_literature_writing_assistant/pubmed_literature_writing_assistant",
                            writing_prompt
                        )
                        writing_result = self._parse_agent_json_response(writing_response)
                        
                        if not writing_result or not isinstance(writing_result, dict):
                            raise ValueError("Writing Assistant返回结果解析失败，无法获取JSON结果")
                        
                        new_file_path = writing_result.get("file_path")
                        if not new_file_path or not Path(new_file_path).exists():
                            raise ValueError(f"Writing Assistant未返回有效文件路径: {new_file_path}")
                        
                        # 更新当前内容和版本
                        current_content = Path(new_file_path).read_text(encoding="utf-8")
                        current_version = str(next_version)
                        version_file_path = new_file_path
                        
                        logger.info(f"Writing Assistant修正完成")
                        logger.info(f"新文件路径: {new_file_path}")
                        logger.info(f"新版本: {current_version}")
                        
                        iteration_record["writing_result"] = writing_result
                        iteration_record["new_version"] = current_version
                        iteration_record["new_file_path"] = new_file_path
                        iteration_record["status"] = "completed"
                        iteration_record["correction_reason"] = "editor_not_passed"
                        workflow_status["iterations"].append(iteration_record)
                        
                        # 重置审核状态，准备下一轮迭代
                        review_passed = False
                        editor_passed = False
                        
                        # 防止无限循环
                        time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"迭代 {iteration} 出错: {str(e)}")
                    iteration_record["status"] = "error"
                    iteration_record["error"] = str(e)
                    workflow_status["iterations"].append(iteration_record)
                    break
            
            # 保存最终结果
            workflow_status["ended_at"] = datetime.now().isoformat()
            workflow_status["total_iterations"] = iteration
            workflow_status["review_passed"] = review_passed
            workflow_status["editor_passed"] = editor_passed
            
            if iteration >= max_iterations and not (review_passed and editor_passed):
                workflow_status["final_status"] = "max_iterations_reached"
                logger.warning(f"达到最大迭代次数 {max_iterations}，工作流终止")
            elif not (review_passed and editor_passed):
                workflow_status["final_status"] = "failed"
            else:
                workflow_status["final_status"] = "completed"
            
            if not workflow_status.get("final_version"):
                workflow_status["final_version"] = current_version
                workflow_status["final_file_path"] = version_file_path
            
            self._save_status(workflow_status)
            
            logger.info("="*80)
            logger.info("优化工作流完成")
            logger.info("="*80)
            logger.info(f"最终状态: {workflow_status['final_status']}")
            logger.info(f"总迭代次数: {iteration}")
            logger.info(f"Review通过: {review_passed}")
            logger.info(f"Editor通过: {editor_passed}")
            logger.info(f"最终版本: {workflow_status.get('final_version', 'N/A')}")
            logger.info("="*80)
            
            return workflow_status
            
        except Exception as e:
            logger.error(f"优化工作流执行失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
            workflow_status["ended_at"] = datetime.now().isoformat()
            workflow_status["final_status"] = "failed"
            workflow_status["error"] = str(e)
            self._save_status(workflow_status)
            
            raise


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PubMed文献优化工作流')
    parser.add_argument('-r', '--research_id', type=str, required=True,
                       help='研究ID，对应.cache/pmc_literature下的目录名')
    parser.add_argument('-m', '--max_iterations', type=int, default=10,
                       help='最大迭代次数，默认10次')
    parser.add_argument('--env', type=str, default='production',
                       help='环境配置 (development, production, testing)')
    parser.add_argument('--version', type=str, default='latest',
                       help='智能体版本')
    parser.add_argument('--model_id', type=str, default='default',
                       help='使用的模型ID')
    
    args = parser.parse_args()
    
    # 创建工作流实例
    workflow = PubmedLiteratureOptimizationWorkflow(
        research_id=args.research_id,
        env=args.env,
        version=args.version,
        model_id=args.model_id
    )
    
    print(f"✅ PubMed文献优化工作流创建成功")
    print(f"📋 研究ID: {args.research_id}")
    print(f"🔄 最大迭代次数: {args.max_iterations}")
    print(f"📁 输出目录: {workflow.output_dir}")
    print(f"{'='*80}\n")
    
    # 执行优化工作流
    try:
        result = workflow.run_optimization(max_iterations=args.max_iterations)
        
        print(f"\n{'='*80}")
        print(f"🎉 优化工作流执行完成")
        print(f"📊 最终状态: {result['final_status']}")
        print(f"🔄 总迭代次数: {result.get('total_iterations', 0)}")
        print(f"✅ Review通过: {result.get('review_passed', False)}")
        print(f"✅ Editor通过: {result.get('editor_passed', False)}")
        print(f"📄 最终版本: {result.get('final_version', 'N/A')}")
        print(f"📄 最终文件: {result.get('final_file_path', 'N/A')}")
        if result.get('iterations'):
            last_iteration = result['iterations'][-1]
            print(f"📄 Review报告: {last_iteration.get('review_result', {}).get('report_path', 'N/A')}")
            print(f"📄 Editor报告: {last_iteration.get('editor_result', {}).get('report_path', 'N/A')}")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"\n❌ 优化工作流执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
