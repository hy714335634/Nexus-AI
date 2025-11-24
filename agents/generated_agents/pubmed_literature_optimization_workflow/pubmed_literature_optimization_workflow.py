#!/usr/bin/env python3
"""
PubMed Literature Optimization Workflow

手动编排editor、writing、review三个agent，实现文献优化工作流。
工作流：
1. review_assistant审核 → 通过后 → editor_assistant审核 → 通过后 → 结束
2. review_assistant不通过 → writing_assistant修正 → 重复1
3. editor_assistant不通过 → writing_assistant修正 → 重复3
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

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置遥测
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()


class PubmedLiteratureOptimizationWorkflow:
    """PubMed文献优化工作流类"""
    
    def __init__(self, research_id: str, env: str = "production", version: str = "latest", model_id: str = "default"):
        """
        初始化PubMed文献优化工作流
        
        Args:
            research_id (str): 研究ID
            session_manager: 会话管理器实例
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
            "model_id": self.model_id
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
    
    def _save_iteration_result(self, iteration: int, stage: str, content: str) -> Path:
        """保存迭代结果到文件"""
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        filename = f"iteration_{iteration}_{stage}_{timestamp}.md"
        file_path = self.output_dir / filename
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"保存迭代结果: {file_path}")
        return file_path
    
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
                logger.info(f"调用Agent（尝试 {attempt}/{max_retries}）")
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
        1. 加载最新版本文献全文和元数据
        2. 调用review_assistant审核，解析JSON结果
        3. 若review通过，调用editor_assistant审核，解析JSON结果
        4. 若editor通过，结束工作流
        5. 若review不通过，调用writing_assistant修正，然后重复2
        6. 若editor不通过，调用writing_assistant修正，然后重复3
        
        Args:
            max_iterations (int): 最大迭代次数，默认10次
            
        Returns:
            Dict: 工作流执行结果
        """
        try:
            logger.info(f"开始执行优化工作流，research_id: {self.research_id}")
            
            # 1. 加载step4.status
            logger.info("加载step4.status文件...")
            step4_status = self._load_step4_status()
            
            # 2. 获取当前版本号
            current_version = self._get_current_version()
            
            # 3. 加载version_file_path指定的文件内容
            version_file_path = step4_status.get("version_file_path")
            if not version_file_path:
                raise ValueError("step4.status中未找到version_file_path字段")
            
            logger.info(f"加载文件内容: {version_file_path}")
            current_content = self._load_version_file(version_file_path)
            
            # 初始化工作流状态
            iteration = 0
            review_passed = False
            editor_passed = False
            current_stage = "review"  # review -> editor
            
            workflow_status = {
                "research_id": self.research_id,
                "started_at": datetime.now().isoformat(),
                "iterations": [],
                "review_passed": False,
                "editor_passed": False,
                "final_status": "running"
            }
            
            review_report_path = None
            editor_report_path = None
            
            logger.info("="*80)
            logger.info("开始优化工作流循环")
            logger.info("="*80)
            
            # 主循环
            while iteration < max_iterations:
                iteration += 1
                logger.info(f"\n{'='*80}")
                logger.info(f"迭代 {iteration}/{max_iterations} - 当前阶段: {current_stage}")
                logger.info(f"Review状态: {'已通过' if review_passed else '未通过'}")
                logger.info(f"Editor状态: {'已通过' if editor_passed else '未通过'}")
                logger.info(f"{'='*80}\n")
                
                iteration_record = {
                    "iteration": iteration,
                    "stage": current_stage,
                    "timestamp": datetime.now().isoformat(),
                    "status": "running"
                }
                
                try:
                    if current_stage == "review" and not review_passed:
                        # 步骤2：调用review_assistant
                        logger.info("调用Review Assistant进行审核...")
                        
                        review_prompt = f"""
请对以下文献内容进行全面审核：

研究ID: {self.research_id}
当前版本: {current_version}
文件路径: {version_file_path}
语言: 基于提供的文献内容，判断文献语言，输出与文献语言一致的文本

**重要说明**：
- 请使用research_id={self.research_id}和version={current_version}参数
- 所有输出文件应保存在: .cache/pmc_literature/{self.research_id}/feedback/reviewer/{current_version}/

**任务要求**：
1. 通过file_read工具读取文献内容
2. 对文献进行全面的多维度评估
3. 将评估结果保存为JSON文件
4. **必须以JSON格式返回结果**，包含以下字段：
   - approved: True/False (是否通过审核)
   - report_path: 评估报告文件路径
   - feedback: 审核意见和建议

**JSON返回格式**：
```json
{{
    "approved": true/false,
    "report_path": "保存的报告文件路径",
    "feedback": "审核意见和建议"
}}
```

文献内容：
{current_content}
"""
                        review_response = self._call_agent(
                            "generated_agents_prompts/pubmed_literature_review_assistant/pubmed_literature_review_assistant",
                            review_prompt
                        )
                        review_result = self._parse_agent_json_response(review_response)
                        
                        if review_result and isinstance(review_result, dict):
                            review_passed = review_result.get("approved", False)
                            review_report_path = review_result.get("report_path")
                            review_feedback = review_result.get("feedback", "")
                            
                            logger.info(f"Review Assistant审核结果: {'通过' if review_passed else '不通过'}")
                            logger.info(f"报告路径: {review_report_path}")
                            
                            iteration_record.update({
                                "agent": "review",
                                "approved": review_passed,
                                "report_path": review_report_path,
                                "feedback": review_feedback
                            })
                            
                            if review_passed:
                                # 通过后切换到editor阶段
                                current_stage = "editor"
                                logger.info("Review通过，进入Editor阶段")
                            else:
                                # 不通过，调用writing_assistant修正
                                logger.info("Review不通过，调用Writing Assistant进行修正...")
                                
                                # 更新版本号
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
- 请根据反馈意见修改文献内容
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
<<<<<<< HEAD
                                    "generated_agents_prompts/pubmed_literature_writing_assistant/pubmed_literature_optimization_assistant",
=======
                                    "generated_agents_prompts/pubmed_literature_writing_assistant/pubmed_literature_writing_assistant",
>>>>>>> origin/main
                                    writing_prompt
                                )
                                writing_result = self._parse_agent_json_response(writing_response)
                                
                                if writing_result and isinstance(writing_result, dict):
                                    new_file_path = writing_result.get("file_path")
                                    if new_file_path and Path(new_file_path).exists():
                                        current_content = Path(new_file_path).read_text(encoding="utf-8")
                                        current_version = str(next_version)
                                        logger.info(f"Writing完成，已更新到版本 {current_version}")
                                        logger.info(f"新文件路径: {new_file_path}")
                                        
                                        iteration_record.update({
                                            "writing": True,
                                            "new_version": current_version,
                                            "new_file_path": new_file_path
                                        })
                                    else:
                                        logger.error("Writing未返回有效文件路径")
                                        iteration_record["status"] = "error"
                                else:
                                    logger.error("Writing返回结果解析失败")
                                    iteration_record["status"] = "error"
                        
                        else:
                            logger.error("Review返回结果解析失败")
                            iteration_record["status"] = "error"
                            review_passed = False
                    
                    elif current_stage == "editor" and not editor_passed and review_passed:
                        # 步骤3：调用editor_assistant
                        logger.info("调用Editor Assistant进行审核...")
                        
                        editor_prompt = f"""
请对以下文献内容进行主编级别的审核：

研究ID: {self.research_id}
当前版本: {current_version}
文件路径: {version_file_path}

**重要信息**：
- 本文献已通过Review Assistant审核
- Review报告路径: {review_report_path}
- 请使用research_id={self.research_id}和version={current_version}参数
- 所有输出文件应保存在: .cache/pmc_literature/{self.research_id}/feedback/editor/{current_version}/

**任务要求**：
1. 通过file_read工具读取文献内容
2. 从主编视角进行全面的期刊评审
3. 将评审结果保存为JSON文件
4. **必须以JSON格式返回结果**，包含以下字段：
   - approved: True/False (是否通过审核)
   - report_path: 评审报告文件路径
   - feedback: 评审意见和建议

**JSON返回格式**：
```json
{{
    "approved": true/false,
    "report_path": "保存的报告文件路径",
    "feedback": "评审意见和建议"
}}
```

文献内容：
{current_content}
"""
                        editor_response = self._call_agent(
                            "generated_agents_prompts/pubmed_literature_editor_assistant/pubmed_literature_editor_assistant",
                            editor_prompt
                        )
                        editor_result = self._parse_agent_json_response(editor_response)
                        
                        if editor_result and isinstance(editor_result, dict):
                            editor_passed = editor_result.get("approved", False)
                            editor_report_path = editor_result.get("report_path")
                            editor_feedback = editor_result.get("feedback", "")
                            
                            logger.info(f"Editor Assistant审核结果: {'通过' if editor_passed else '不通过'}")
                            logger.info(f"报告路径: {editor_report_path}")
                            
                            iteration_record.update({
                                "agent": "editor",
                                "approved": editor_passed,
                                "report_path": editor_report_path,
                                "feedback": editor_feedback
                            })
                            
                            if not editor_passed:
                                # 不通过，调用writing_assistant修正
                                logger.info("Editor不通过，调用Writing Assistant进行修正...")
                                
                                # 更新版本号
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
- 请根据主编级别的反馈意见修改文献内容
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
                                
                                if writing_result and isinstance(writing_result, dict):
                                    new_file_path = writing_result.get("file_path")
                                    if new_file_path and Path(new_file_path).exists():
                                        current_content = Path(new_file_path).read_text(encoding="utf-8")
                                        current_version = str(next_version)
                                        logger.info(f"Writing完成，已更新到版本 {current_version}")
                                        logger.info(f"新文件路径: {new_file_path}")
                                        
                                        # 重置review状态，因为editor修改后需要重新review
                                        review_passed = False
                                        current_stage = "review"
                                        iteration_record.update({
                                            "writing": True,
                                            "new_version": current_version,
                                            "new_file_path": new_file_path,
                                            "restart_review": True
                                        })
                                    else:
                                        logger.error("Writing未返回有效文件路径")
                                        iteration_record["status"] = "error"
                                else:
                                    logger.error("Writing返回结果解析失败")
                                    iteration_record["status"] = "error"
                        
                        else:
                            logger.error("Editor返回结果解析失败")
                            iteration_record["status"] = "error"
                            editor_passed = False
                    
                    # 检查是否都通过了
                    if review_passed and editor_passed:
                        logger.info("="*80)
                        logger.info("🎉 所有审核通过，工作流完成！")
                        logger.info("="*80)
                        iteration_record["status"] = "completed"
                        workflow_status["review_passed"] = True
                        workflow_status["editor_passed"] = True
                        workflow_status["final_status"] = "completed"
                        break
                    
                    iteration_record["status"] = "completed"
                    workflow_status["iterations"].append(iteration_record)
                    
                except Exception as e:
                    logger.error(f"迭代 {iteration} 出错: {str(e)}")
                    iteration_record["status"] = "error"
                    iteration_record["error"] = str(e)
                    workflow_status["iterations"].append(iteration_record)
                    break
                
                # 防止无限循环
                time.sleep(2)
                
            # 保存最终结果
            workflow_status["ended_at"] = datetime.now().isoformat()
            workflow_status["review_report_path"] = review_report_path
            workflow_status["editor_report_path"] = editor_report_path
            workflow_status["final_version"] = current_version
            workflow_status["review_passed"] = review_passed
            workflow_status["editor_passed"] = editor_passed
            
            if iteration >= max_iterations and not (review_passed and editor_passed):
                workflow_status["final_status"] = "max_iterations_reached"
                logger.warning(f"达到最大迭代次数 {max_iterations}，工作流终止")
            
            self._save_status(workflow_status)
            
            logger.info(f"\n{'='*80}")
            logger.info(f"优化工作流完成")
            logger.info(f"最终状态: {workflow_status['final_status']}")
            logger.info(f"总迭代次数: {iteration}")
            logger.info(f"Review通过: {review_passed}")
            logger.info(f"Editor通过: {editor_passed}")
            logger.info(f"最终版本: {current_version}")
            logger.info(f"{'='*80}")
            
            return workflow_status
            
        except Exception as e:
            logger.error(f"优化工作流执行失败: {str(e)}")
            import traceback
            traceback.print_exc()
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
        print(f"🔄 总迭代次数: {len(result.get('iterations', []))}")
        print(f"✅ Review通过: {result.get('review_passed', False)}")
        print(f"✅ Editor通过: {result.get('editor_passed', False)}")
        print(f"📄 Review报告: {result.get('review_report_path', 'N/A')}")
        print(f"📄 Editor报告: {result.get('editor_report_path', 'N/A')}")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"\n❌ 优化工作流执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()

