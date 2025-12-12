#!/usr/bin/env python3
"""
PubMed Literature Reviewer Agent

专业的科研文献/报告审核Agent，能够根据用户提供的完整文献，结合在线检索PMC文献的工具，
进行犀利的评价与反馈，指出信息不全、幻觉等问题，并提供修正建议。

功能特点:
- 多维度评估科研文献质量
- 验证文献中的关键声明和数据
- 识别信息不全、幻觉等问题
- 提供结构化的JSON格式评估结果
- 支持research_id参数指定缓存目录
- 提供具体的修正建议
"""

import os
import json
import logging
import uuid
import time
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry
from strands.session.file_session_manager import FileSessionManager
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

class PubmedLiteratureReviewer:
    """PubMed文献审核专家智能体类"""
    
    def __init__(self, session_manager=None, env: str = "production", version: str = "latest", model_id: str = "default"):
        """
        初始化PubMed文献审核专家智能体
        
        Args:
            session_manager: 会话管理器实例
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
        
        # 创建智能体实例
        self.agent = create_agent_from_prompt_template(
            agent_name="generated_agents_prompts/pubmed_literature_review_assistant/pubmed_literature_review_assistant",
            session_manager=self.session_manager,
            **self.agent_params
        )
        
        logger.info(f"PubMed文献审核专家智能体初始化完成: {self.agent.name}")
        
        # 创建缓存目录
        self.base_cache_dir = Path(".cache/pmc_literature")
        self.base_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 统一输出子路径
        self.feedback_subpath = Path("feedback") / "reviewer"

    # ----------------------
    # 内部工具方法：统一输出与版本控制
    # ----------------------
    def _ensure_research_id(self, research_id: Optional[str]) -> str:
        """确保存在research_id；若未提供，则生成一个新的uuid并返回。"""
        if not research_id:
            generated = str(uuid.uuid4())
            logger.info(f"未提供research_id，已自动生成: {generated}")
            return generated
        return research_id

    def _get_output_dir(self, research_id: str, version: Optional[int] = None) -> Path:
        """获取标准输出目录 .cache/pmc_literature/<research_id>/feedback/reviewer[/<version>] 并确保存在。"""
        out_dir = self.base_cache_dir / research_id / self.feedback_subpath
        if version is not None:
            out_dir = out_dir / str(version)
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    def _now_ts(self) -> str:
        """返回时间戳：YYYYMMDDThhmmss"""
        return time.strftime("%Y%m%dT%H%M%S", time.localtime())

    def _load_status(self, research_id: str) -> Dict[str, Any]:
        """读取 .cache/pmc_literature/<research_id>/step5.status（若不存在则返回默认结构）。"""
        status_path = self.base_cache_dir / research_id / "step5.status"
        if status_path.exists():
            try:
                with open(status_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"读取step5.status失败，将重建。错误: {e}")
        return {
            "research_id": research_id,
            "latest_version": 0,
            "versions": {}
        }

    def _get_or_create_run_version(self, research_id: str) -> int:
        """在一次agent运行中固定版本号：
        - 优先读取 .current_run_version 
        - 若不存在则依据status/目录计算下一个版本，并写入 .current_run_version
        """
        base_dir = self.base_cache_dir / research_id
        marker = base_dir / ".current_run_version"
        try:
            if marker.exists():
                with open(marker, "r", encoding="utf-8") as f:
                    v = int(f.read().strip())
                    return v
        except Exception:
            pass

        # 计算新版本
        reviewer_root = base_dir / self.feedback_subpath
        reviewer_root.mkdir(parents=True, exist_ok=True)
        status = self._load_status(research_id)
        version = self._detect_next_version(research_id, reviewer_root, status)
        try:
            with open(marker, "w", encoding="utf-8") as f:
                f.write(str(version))
        except Exception as e:
            logger.warning(f"写入.current_run_version失败: {e}")
        return version

    def _write_status(self, research_id: str, status: Dict[str, Any]) -> None:
        """写回 step5.status。"""
        status_path = self.base_cache_dir / research_id / "step5.status"
        try:
            with open(status_path, "w", encoding="utf-8") as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"写入step5.status失败: {e}")

    def _detect_next_version(self, research_id: str, output_dir: Path, status: Dict[str, Any]) -> int:
        """基于现有status和目录内文件检测下一个版本号。优先使用status.latest_version。
        兼容扫描feedback/reviewer根目录与其下的数字子目录。"""
        latest_version = int(status.get("latest_version", 0))
        if latest_version > 0:
            return latest_version + 1
        # 兜底：从目录扫描匹配 review_<version>_*.json 推断最大版本（兼容旧结构与新结构）
        max_found = 0
        # 旧结构：reviewer/ 下直接文件
        for p in output_dir.glob("review_*_*.json"):
            name = p.stem  # review_<v>_<ts>
            parts = name.split("_")
            if len(parts) >= 3 and parts[0] == "review":
                try:
                    v = int(parts[1])
                    if v > max_found:
                        max_found = v
                except Exception:
                    continue
        # 新结构：reviewer/<version>/ 子目录
        for sub in (self.base_cache_dir / research_id / self.feedback_subpath).glob("*"):
            if sub.is_dir():
                try:
                    v = int(sub.name)
                    if v > max_found:
                        max_found = v
                except Exception:
                    continue
        return max_found + 1

    def _save_outputs(self, research_id: str, mode: str, content_text: str, agent_result: str, forced_version: Optional[int] = None) -> Dict[str, Any]:
        """
        将本次运行产物按照规范命名写入：
        - 目录：.cache/pmc_literature/<research_id>/feedback/reviewer/
        - 基名：review_<version>_<timestamp>
        - 扩展：.json（结构化），.md（原始输出），.txt（原始输出纯文本）
        返回：{"version": int, "timestamp": str, "files": {ext: path}}
        """
        research_id = self._ensure_research_id(research_id)
        base_output_dir = self._get_output_dir(research_id)
        status = self._load_status(research_id)
        version = forced_version if forced_version is not None else self._detect_next_version(research_id, base_output_dir, status)
        ts = self._now_ts()

        # 使用版本子目录
        version_dir = self._get_output_dir(research_id, version)
        verification_dir = version_dir / "verification"
        verification_dir.mkdir(parents=True, exist_ok=True)
        base_name = f"review_{version}_{ts}"
        json_path = verification_dir / f"{base_name}.json"
        md_path = verification_dir / f"{base_name}.md"
        txt_path = verification_dir / f"{base_name}.txt"

        # 解析agent输出为JSON；若失败则以包装结构存储
        json_payload: Dict[str, Any]
        try:
            json_payload = json.loads(agent_result)
        except Exception as e:
            json_payload = {
                "error": "agent_output_not_valid_json",
                "message": str(e),
                "raw_output": agent_result
            }

        # 附加元信息，便于溯源
        json_payload = {
            "_meta": {
                "mode": mode,
                "research_id": research_id,
                "version": version,
                "timestamp": ts
            },
            "data": json_payload
        }

        # 写文件
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"写入JSON失败: {e}")

        try:
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(agent_result)
        except Exception as e:
            logger.error(f"写入Markdown失败: {e}")

        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(agent_result)
        except Exception as e:
            logger.error(f"写入TXT失败: {e}")

        # 汇总到status（按版本归档）
        status["latest_version"] = version
        versions = status.setdefault("versions", {})
        versions[str(version)] = {
            "generated_at": ts,
            "mode": mode,
            "files": {
                "json": [str(json_path.resolve())],
                "md": [str(md_path.resolve())],
                "txt": [str(txt_path.resolve())],
                "others": []
            }
        }

        self._write_status(research_id, status)

        return {
            "version": version,
            "timestamp": ts,
            "files": {
                "json": str(json_path.resolve()),
                "md": str(md_path.resolve()),
                "txt": str(txt_path.resolve())
            }
        }
    
    def review_literature(self, content: str, research_id: Optional[str] = None) -> str:
        """
        评审科研文献并提供反馈
        
        Args:
            content (str): 文献内容
            research_id (str, optional): 研究ID，用于指定缓存和上下文工作目录
            
        Returns:
            str: 智能体响应，包含评审结果和修正建议
        """
        try:
            start_time = time.time()
            logger.info(f"开始评审文献，{'使用research_id: ' + research_id if research_id else '未指定research_id'}")
            
            # 准备输入，添加research_id信息
            input_text = content
            if research_id:
                # 确保research_id目录存在
                research_dir = self.base_cache_dir / research_id
                research_dir.mkdir(parents=True, exist_ok=True)
                
                # 在输入中添加research_id信息
                input_text += f"\n\nresearch_id: {research_id}"
            
            # 固定本次运行版本
            rid = self._ensure_research_id(research_id)
            run_version = self._get_or_create_run_version(rid)

            # 调用智能体处理文献评审
            result = self.agent(input_text)

            # 落盘与状态更新（统一输出规范）
            self._save_outputs(rid, mode="review", content_text=content, agent_result=result, forced_version=run_version)
            
            elapsed_time = time.time() - start_time
            logger.info(f"文献评审完成，耗时: {elapsed_time:.2f}秒")
            
            return result
        except Exception as e:
            logger.error(f"文献评审失败: {str(e)}")
            return f"文献评审过程中发生错误: {str(e)}"
    
    def verify_specific_claims(self, content: str, claims: List[str], 
                              research_id: Optional[str] = None) -> str:
        """
        验证文献中的特定声明
        
        Args:
            content (str): 文献内容
            claims (List[str]): 需要验证的声明列表
            research_id (str, optional): 研究ID，用于指定缓存和上下文工作目录
            
        Returns:
            str: 智能体响应，包含声明验证结果
        """
        try:
            logger.info(f"开始验证特定声明，共{len(claims)}条")
            
            # 准备输入，格式化声明列表和research_id信息
            claims_text = "\n".join([f"- {claim}" for claim in claims])
            input_text = f"""请验证以下文献中的特定声明:

{content}

需要验证的声明:
{claims_text}

请针对每条声明进行验证，并提供支持或反对的证据。
"""
            
            if research_id:
                input_text += f"\n\nresearch_id: {research_id}"
            
            # 固定本次运行版本
            rid = self._ensure_research_id(research_id)
            run_version = self._get_or_create_run_version(rid)

            # 调用智能体处理声明验证
            result = self.agent(input_text)

            # 落盘与状态更新
            self._save_outputs(rid, mode="verify", content_text=content, agent_result=result, forced_version=run_version)
            
            logger.info("声明验证完成")
            return result
        except Exception as e:
            logger.error(f"声明验证失败: {str(e)}")
            return f"声明验证过程中发生错误: {str(e)}"
    
    def compare_literature(self, content1: str, content2: str, 
                          research_id: Optional[str] = None) -> str:
        """
        比较两篇文献的内容和质量
        
        Args:
            content1 (str): 第一篇文献内容
            content2 (str): 第二篇文献内容
            research_id (str, optional): 研究ID，用于指定缓存和上下文工作目录
            
        Returns:
            str: 智能体响应，包含文献比较结果
        """
        try:
            logger.info("开始比较两篇文献")
            
            # 准备输入，格式化两篇文献内容和research_id信息
            input_text = f"""请比较以下两篇文献的内容和质量:

文献1:
{content1}

文献2:
{content2}

请从科学准确性、方法论合理性、结论有效性、创新性、完整性等维度进行比较分析，并指出各自的优缺点。
"""
            
            if research_id:
                input_text += f"\n\nresearch_id: {research_id}"
            
            # 固定本次运行版本
            rid = self._ensure_research_id(research_id)
            run_version = self._get_or_create_run_version(rid)

            # 调用智能体处理文献比较
            result = self.agent(input_text)

            # 落盘与状态更新
            self._save_outputs(rid, mode="compare", content_text=f"[DOC1]\n{content1}\n\n[DOC2]\n{content2}", agent_result=result, forced_version=run_version)
            
            logger.info("文献比较完成")
            return result
        except Exception as e:
            logger.error(f"文献比较失败: {str(e)}")
            return f"文献比较过程中发生错误: {str(e)}"
    
    def get_assessment_history(self, research_id: str) -> str:
        """
        获取指定research_id的评估历史
        
        Args:
            research_id (str): 研究ID
            
        Returns:
            str: 评估历史信息
        """
        try:
            logger.info(f"获取research_id: {research_id}的评估历史")
            
            # 检查research_id目录是否存在
            research_dir = self.base_cache_dir / research_id
            if not research_dir.exists():
                return f"未找到research_id: {research_id}的评估历史"
            
            # 查找所有assessment文件
            assessment_files = list(research_dir.glob("assessment_*.json"))
            if not assessment_files:
                return f"research_id: {research_id}没有评估记录"
            
            # 读取评估文件内容
            assessments = []
            for file_path in sorted(assessment_files):
                try:
                    with open(file_path, 'r') as f:
                        assessment = json.load(f)
                    
                    # 提取关键信息
                    metadata = assessment.get("metadata", {})
                    overall = assessment.get("overall_assessment", {})
                    
                    assessments.append({
                        "assessment_id": metadata.get("assessment_id", ""),
                        "assessment_date": metadata.get("assessment_date", ""),
                        "document_title": metadata.get("document_title", ""),
                        "overall_score": overall.get("score", 0),
                        "overall_grade": overall.get("grade", ""),
                        "file_path": str(file_path)
                    })
                except Exception as e:
                    logger.warning(f"读取评估文件{file_path}时出错: {str(e)}")
            
            # 格式化输出
            if assessments:
                result = f"research_id: {research_id}的评估历史 (共{len(assessments)}条):\n\n"
                for i, assessment in enumerate(assessments, 1):
                    result += f"{i}. {assessment['assessment_date']}: {assessment['document_title']}\n"
                    result += f"   评分: {assessment['overall_score']}/100 ({assessment['overall_grade']}级)\n"
                    result += f"   ID: {assessment['assessment_id']}\n\n"
            else:
                result = f"research_id: {research_id}没有有效的评估记录"
            
            return result
        except Exception as e:
            logger.error(f"获取评估历史失败: {str(e)}")
            return f"获取评估历史过程中发生错误: {str(e)}"

def get_pubmed_literature_reviewer(env: str = "production", version: str = "latest", model_id: str = "default") -> PubmedLiteratureReviewer:
    """
    获取PubMed文献审核专家智能体实例
    
    Args:
        env (str): 环境配置 (development, production, testing)
        version (str): 智能体版本
        model_id (str): 使用的模型ID
        
    Returns:
        PubmedLiteratureReviewer: 智能体实例
    """
    return PubmedLiteratureReviewer(env=env, version=version, model_id=model_id)

# 直接使用agent_factory创建智能体的便捷方法
def create_pubmed_literature_reviewer(env: str = "production", version: str = "latest", model_id: str = "default"):
    """
    创建PubMed文献审核专家智能体
    
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
        agent_name="generated_agents_prompts/pubmed_literature_review_agent/pubmed_literature_reviewer",
        **agent_params
    )

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='PubMed文献审核专家智能体')
    parser.add_argument('-f', '--file', type=str, 
                       help='文献文件路径')
    parser.add_argument('-c', '--claims', type=str, 
                       help='需要验证的声明，多个声明用逗号分隔')
    parser.add_argument('-r', '--research_id', type=str, 
                       default=None,
                       help='研究ID，用于指定缓存和上下文工作目录')
    parser.add_argument('-m', '--mode', type=str,
                       choices=['review', 'verify', 'history', 'compare'],
                       default='review',
                       help='操作模式: review(评审文献), verify(验证声明), history(查看评估历史), compare(比较文献)')
    parser.add_argument('-c1', '--compare1', type=str, 
                       help='比较模式下的第一篇文献文件路径')
    parser.add_argument('-c2', '--compare2', type=str, 
                       help='比较模式下的第二篇文献文件路径')
    parser.add_argument('--session_id', type=str,
                       default=None,
                       help='可选：指定session_id')
    args = parser.parse_args()
    
    # 设置会话管理器
    session_id = args.session_id if args.session_id else str(uuid.uuid4())
    session_manager = FileSessionManager(
        session_id=session_id,
        storage_dir="./.cache/session_cache"
    )
    
    # 创建智能体
    agent_params = {
        "env": "production",
        "version": "latest",
        "model_id": "default"
    }
    
    reviewer = PubmedLiteratureReviewer(session_manager=session_manager, **agent_params)
    print(f"✅ PubMed文献审核专家智能体创建成功: {reviewer.agent.name}")
    
    # 根据模式执行不同操作
    if args.mode == 'review':
        if args.file:
            try:
                with open(args.file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                print(f"📄 正在评审文献: {args.file}")
                result = reviewer.review_literature(content, args.research_id)
            except Exception as e:
                print(f"❌ 读取文件失败: {str(e)}")
                exit(1)
        else:
            print("请输入文献内容 (输入完成后按Ctrl+D结束):")
            try:
                content = ""
                while True:
                    line = input()
                    content += line + "\n"
            except EOFError:
                print("\n📄 正在评审文献...")
                result = reviewer.review_literature(content, args.research_id)
    
    elif args.mode == 'verify':
        if not args.claims:
            print("❌ 需要提供要验证的声明 (使用 --claims 参数)")
            exit(1)
            
        claims = [claim.strip() for claim in args.claims.split(',')]
        
        if args.file:
            try:
                with open(args.file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                print(f"🔍 正在验证文献中的{len(claims)}条声明")
                result = reviewer.verify_specific_claims(content, claims, args.research_id)
            except Exception as e:
                print(f"❌ 读取文件失败: {str(e)}")
                exit(1)
        else:
            print("请输入文献内容 (输入完成后按Ctrl+D结束):")
            try:
                content = ""
                while True:
                    line = input()
                    content += line + "\n"
            except EOFError:
                print(f"\n🔍 正在验证文献中的{len(claims)}条声明")
                result = reviewer.verify_specific_claims(content, claims, args.research_id)
    
    elif args.mode == 'compare':
        if not args.compare1 or not args.compare2:
            print("❌ 比较模式需要提供两个文献文件路径 (使用 --compare1 和 --compare2 参数)")
            exit(1)
            
        try:
            with open(args.compare1, 'r', encoding='utf-8') as f:
                content1 = f.read()
                
            with open(args.compare2, 'r', encoding='utf-8') as f:
                content2 = f.read()
            
            print(f"🔍 正在比较两篇文献: {args.compare1} 和 {args.compare2}")
            result = reviewer.compare_literature(content1, content2, args.research_id)
        except Exception as e:
            print(f"❌ 读取文件失败: {str(e)}")
            exit(1)
    
    elif args.mode == 'history':
        if not args.research_id:
            print("❌ 需要提供research_id (使用 --research_id 参数)")
            exit(1)
            
        print(f"📋 获取research_id: {args.research_id}的评估历史")
        result = reviewer.get_assessment_history(args.research_id)
    
    # 输出结果
    print(f"\n📋 智能体响应:\n{result}")