#!/usr/bin/env python3
"""
PubMed Literature Optimization Workflow

使用Swarm编排editor、writing、review三个agent，实现文献优化工作流。
工作流：review给出意见 → writing修正 → review通过后 → editor给出意见 → writing修正 → 直到最终通过
"""

import os
import json
import logging
import uuid
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.multiagent import Swarm
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
        
        # 创建三个agent实例
        logger.info("正在创建agent实例...")
        self.editor_agent = create_agent_from_prompt_template(
            agent_name="generated_agents_prompts/pubmed_literature_editor_assistant/pubmed_literature_editor_assistant",
            **self.agent_params
        )
        
        self.writing_agent = create_agent_from_prompt_template(
            agent_name="generated_agents_prompts/pubmed_literature_writing_assistant/pubmed_literature_writing_assistant",
            **self.agent_params
        )
        
        self.review_agent = create_agent_from_prompt_template(
            agent_name="generated_agents_prompts/pubmed_literature_review_assistant/pubmed_literature_review_assistant",
            **self.agent_params
        )
        
        logger.info(f"Editor agent创建完成: {self.editor_agent.name}")
        logger.info(f"Writing agent创建完成: {self.writing_agent.name}")
        logger.info(f"Review agent创建完成: {self.review_agent.name}")
        
        # 创建Swarm，设置editor为入口agent
        # 注意：虽然entry_point是editor，但实际工作流由我们控制agent的调用顺序
        self.swarm = Swarm(
            [self.editor_agent, self.writing_agent, self.review_agent],
            entry_point=self.review_agent,
            max_handoffs=20,
            max_iterations=20,
            execution_timeout=6000.0,  # 15 minutes
            node_timeout=3000.0,       # 5 minutes per agent
            repetitive_handoff_detection_window=8,  # There must be >= 3 unique agents in the last 8 handoffs
            repetitive_handoff_min_unique_agents=3
            
        )
        logger.info("Swarm创建完成，entry_point为review（但工作流由代码控制）")
        
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
    
    def _parse_approval_status(self, response: str) -> bool:
        """
        从agent响应中解析是否通过
        简单判断：如果响应中包含明确的通过标识，返回True
        """
        response_lower = response.lower()
        # 查找通过标识
        approval_keywords = [
            "通过", "approved", "accept", "可以", "满意", 
            "good", "excellent", "no further changes needed",
            "无需修改", "不需要修改"
        ]
        
        rejection_keywords = [
            "不通过", "reject", "拒绝", "需要修改", "还需要",
            "needs revision", "requires changes", "修改", "improve"
        ]
        
        # 统计关键词出现次数
        approval_count = sum(1 for keyword in approval_keywords if keyword in response_lower)
        rejection_count = sum(1 for keyword in rejection_keywords if keyword in response_lower)
        
        # 如果明确有通过标识且拒绝标识较少，认为通过
        if approval_count > 0 and approval_count > rejection_count:
            return True
        
        # 如果有明确的拒绝标识，认为不通过
        if rejection_count > approval_count:
            return False
        
        # 默认需要继续修改（不通过）
        return False
    
    def run_optimization(self, max_iterations: int = 10) -> Dict[str, Any]:
        """
        执行优化工作流
        
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
            initial_content = self._load_version_file(version_file_path)
            
            # 4. 构建初始提示词
            initial_prompt = f"""
请对以下文献内容进行优化工作流：

研究ID: {self.research_id}
当前版本: {current_version}
原始文件路径: {version_file_path}
**请通过file_read工具读取文献/文件内容**

**重要版本管理说明**：
- 所有reviewer输出的临时文件应保存在: .cache/pmc_literature/{self.research_id}/feedback/reviewer/{current_version}/
- 所有editor输出的临时文件应保存在: .cache/pmc_literature/{self.research_id}/feedback/editor/{current_version}/
- 请使用research_id={self.research_id}和version={current_version}参数，除非writing更新了version id
- file_write请遵循临时文件存储要求，无论输出格式是md还是png等其他格式，都应保存在.cache/pmc_literature/{self.research_id}/feedback/reviewer/{current_version}/或.cache/pmc_literature/{self.research_id}/feedback/editor/{current_version}/目录下

工作流说明：
1. reviewer agent首先审核文献并给出意见
2. writing agent根据review的意见进行修正，并返回JSON输出
3. 重复步骤1，如果通过，则editor agent给出意见
4. writing agent根据editor的意见进行修正
5. 循环此过程直到editor和review都通过

**注意事项**
- reviewer审核通过应handoff给editor agent，editor审核通过应返回结论并结束工作流
- reviewer和editor审核未通过时均handoff给writing agent
- writing agent完成任务后应返回JSON输出，并handoff给未通过的agent

**必须**以JSON格式返回结果，不要返回其他内容：
```json
{{
    "status": "success",
    "research_id": "{self.research_id}",
    "version": "new_version_number",
    "file_path": "保存的文件路径",
    "message": "成功更新综述"
}}
```
"""
            
            # 初始化状态
            current_content = initial_content
            iteration = 1
            workflow_status = {
                "research_id": self.research_id,
                "started_at": datetime.now().isoformat(),
                "iterations": [],
                "final_status": "running"
            }
            
            review_passed = False
            editor_passed = False
            stage = "review"  # 当前阶段：review 或 editor
            
            logger.info("开始迭代优化...")
            
            while iteration <= max_iterations:
                logger.info(f"\n{'='*80}")
                logger.info(f"迭代 {iteration}/{max_iterations} - 阶段: {stage}")
                logger.info(f"{'='*80}")
                
                iteration_result = {
                    "iteration": iteration,
                    "stage": stage,
                    "timestamp": datetime.now().isoformat(),
                    "status": "running"
                }
                result = self.swarm(initial_prompt)
                logger.info(f"Status: {result.status}")
                logger.info(f"Node history: {[node.node_id for node in result.node_history]}")
                
                
            # 保存最终结果
            if iteration > max_iterations:
                workflow_status["final_status"] = "max_iterations_reached"
            
            workflow_status["ended_at"] = datetime.now().isoformat()
            workflow_status["final_content"] = current_content
            
            # 保存最终内容
            final_file = self.output_dir / "final_content.md"
            with open(final_file, "w", encoding="utf-8") as f:
                f.write(current_content)
            workflow_status["final_file"] = str(final_file)
            
            self._save_status(workflow_status)
            
            logger.info(f"\n{'='*80}")
            logger.info(f"优化工作流完成")
            logger.info(f"最终状态: {workflow_status['final_status']}")
            logger.info(f"总迭代次数: {len(workflow_status['iterations'])}")
            logger.info(f"最终文件: {final_file}")
            logger.info(f"{'='*80}")
            
            return workflow_status
            
        except Exception as e:
            logger.error(f"优化工作流执行失败: {str(e)}")
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
        print(f"🔄 总迭代次数: {len(result['iterations'])}")
        print(f"📄 最终文件: {result.get('final_file', 'N/A')}")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"\n❌ 优化工作流执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()

