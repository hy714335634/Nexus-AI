#!/usr/bin/env python3
"""
工作流执行脚本 V2 - 使用新的 WorkflowEngine

这个脚本使用重构后的 WorkflowEngine 类来执行 Agent 构建工作流，
支持从任意阶段开始、暂停/恢复、状态持久化等功能。

用法:
    # 交互式模式（默认）
    python scripts/run_workflow_v2.py
    
    # 批处理模式 - 直接提供需求
    python scripts/run_workflow_v2.py -i "创建一个AWS定价Agent"
    
    # 从文件读取需求
    python scripts/run_workflow_v2.py -f requirements.txt
    
    # 继续已有项目
    python scripts/run_workflow_v2.py --project-id <uuid>
    
    # 从指定阶段开始
    python scripts/run_workflow_v2.py --project-id <uuid> --from-stage agent_designer
    
    # 查看项目状态
    python scripts/run_workflow_v2.py --project-id <uuid> --status
"""

import os
import sys
import uuid
import json
import time
import argparse
import logging
from datetime import datetime
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus_utils.config_loader import ConfigLoader
from nexus_utils.workflow_rule_extract import get_base_rules, get_build_workflow_rules

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载配置
config = ConfigLoader()

# 设置环境变量
os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")
otel_endpoint = config.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)


def print_banner():
    """打印启动横幅"""
    print(f"\n{'='*60}")
    print("🚀 Nexus-AI Agent Build Workflow V2")
    print("   使用 WorkflowEngine 的新版本工作流执行器")
    print(f"{'='*60}\n")


def print_status(status: dict):
    """打印工作流状态"""
    print(f"\n{'='*60}")
    print("📊 工作流状态")
    print(f"{'='*60}")
    print(f"  项目ID: {status.get('project_id', 'N/A')}")
    print(f"  状态: {status.get('status', 'N/A')}")
    print(f"  控制状态: {status.get('control_status', 'N/A')}")
    print(f"  当前阶段: {status.get('current_stage', 'N/A')}")
    print(f"  已完成阶段: {', '.join(status.get('completed_stages', []))}")
    print(f"  待执行阶段: {', '.join(status.get('pending_stages', []))}")
    
    metrics = status.get('aggregated_metrics', {})
    if metrics:
        print(f"\n📈 指标:")
        print(f"  总耗时: {metrics.get('total_duration_seconds', 0):.2f}秒")
        print(f"  输入Tokens: {metrics.get('total_input_tokens', 0)}")
        print(f"  输出Tokens: {metrics.get('total_output_tokens', 0)}")
        print(f"  工具调用: {metrics.get('total_tool_calls', 0)}")
    print(f"{'='*60}\n")


def run_interactive_collection() -> str:
    """
    运行交互式需求收集会话
    
    Returns:
        收集完成的需求描述文本
    """
    from nexus_utils.agent_factory import create_agent_from_prompt_template
    
    print(f"\n{'='*60}")
    print("🎯 Nexus-AI 交互式需求收集")
    print(f"{'='*60}")
    print("💡 提示：")
    print("   - 输入 /done 或 /finish 完成需求收集")
    print("   - 输入 /quit 或 /exit 退出（不保存）")
    print("   - 按 Ctrl+C 强制退出")
    print(f"{'='*60}\n")
    
    # 创建交互式需求收集Agent
    collection_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/interface_agent/information_collection",
        env="production",
        version="latest",
        model_id="default",
        enable_logging=False
    )
    
    if not collection_agent:
        print("❌ 无法创建需求收集Agent")
        return ""
    
    # 发送开场消息
    opening_prompt = "用户刚刚进入交互式需求收集界面，请友好地问候并开始引导用户描述他们想要构建的AI Agent。"
    
    try:
        response = collection_agent(opening_prompt)
        print("=================================")
        print("🤖 Nexus-AI: ")
        response_text = str(response.content) if hasattr(response, 'content') else str(response)
        print(response_text)
        print("=================================\n")
    except Exception as e:
        print(f"❌ Agent响应失败: {e}")
        return ""
    
    # 交互循环
    while True:
        try:
            user_input = input("👤 您: ").strip()
            
            # 检查退出命令
            if user_input.lower() in ['/quit', '/exit', 'quit', 'exit']:
                print("\n👋 已退出，需求未保存。")
                return ""
            
            # 检查完成命令
            if user_input.lower() in ['/done', '/finish', '/完成', '完成', 'done', 'finish']:
                print("\n📋 正在整理需求...")
                break
            
            if not user_input:
                continue
            
            # 获取Agent响应
            print("🤖 Nexus-AI: ", end="", flush=True)
            response = collection_agent(user_input)
            response_text = str(response.content) if hasattr(response, 'content') else str(response)
            print(response_text)
            print()
            
        except KeyboardInterrupt:
            print("\n\n⚠️ 检测到中断信号...")
            confirm = input("是否保存当前收集的需求？(y/n): ").strip().lower()
            if confirm == 'y':
                break
            else:
                print("👋 已退出，需求未保存。")
                return ""
        except EOFError:
            print("\n\n⚠️ 输入流结束，正在整理需求...")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            continue
    
    # 生成最终需求摘要
    print(f"\n{'='*60}")
    print("📝 正在生成最终需求描述...")
    print(f"{'='*60}\n")
    
    summary_prompt = """基于之前的对话内容，请生成一份完整的Agent开发需求描述。
请按以下格式输出最终需求（纯文本，不要markdown代码块）：

项目名称：[建议的英文snake_case名称]

功能概述：[一段话描述Agent的核心功能]

目标用户：[使用这个Agent的人群]

核心功能需求：
1. [功能1]
2. [功能2]
...

输入规格：
- 类型：[输入类型]
- 来源：[数据来源]

输出规格：
- 类型：[输出类型]
- 格式：[输出格式]

外部集成需求：
- [需要集成的API或服务]

约束条件：
- [技术或业务约束]

附加说明：
- [其他重要信息]
"""
    
    try:
        summary_response = collection_agent(summary_prompt)
        final_requirements = str(summary_response.content) if hasattr(summary_response, 'content') else str(summary_response)
        
        print("📋 最终需求描述：")
        print(f"{'─'*60}")
        print(final_requirements)
        print(f"{'─'*60}\n")
        
        # 确认
        confirm = input("✅ 确认使用此需求开始构建？(y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ 已取消，请重新运行交互式收集。")
            return ""
        
        return final_requirements
        
    except Exception as e:
        print(f"❌ 生成需求摘要失败: {e}")
        return ""


def on_stage_start(stage_name: str):
    """阶段开始回调"""
    print(f"\n{'='*60}")
    print(f"🔄 开始执行阶段: {stage_name}")
    print(f"{'='*60}")


def on_stage_complete(stage_name: str, output):
    """阶段完成回调"""
    print(f"\n✅ 阶段完成: {stage_name}")
    if hasattr(output, 'metrics') and output.metrics:
        print(f"   耗时: {output.metrics.duration_seconds:.2f}秒")
        print(f"   Tokens: {output.metrics.input_tokens} / {output.metrics.output_tokens}")


def on_stage_error(stage_name: str, error: Exception):
    """阶段错误回调"""
    print(f"\n❌ 阶段失败: {stage_name}")
    print(f"   错误: {error}")


def run_workflow_v2(
    user_input: str,
    project_id: Optional[str] = None,
    from_stage: Optional[str] = None,
) -> dict:
    """
    使用 WorkflowEngine 执行工作流
    
    Args:
        user_input: 用户需求输入
        project_id: 项目ID（可选，如果未提供则创建新项目）
        from_stage: 从指定阶段开始（可选）
        
    Returns:
        执行结果字典
    """
    from nexus_utils.workflow.engine import WorkflowEngine, ExecutionResult
    from nexus_utils.workflow.context import WorkflowContextManager
    from api.v2.database import db_client
    
    print_banner()
    
    # 生成或使用项目ID
    if project_id is None:
        project_id = str(uuid.uuid4())
        print(f"📁 创建新项目: {project_id}")
        
        # 在数据库中创建项目记录
        try:
            db_client.create_project({
                'project_id': project_id,
                'project_name': f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'requirement': user_input[:500],
                'status': 'pending',
                'control_status': 'running',
                'created_at': datetime.now().isoformat(),
            })
            print(f"✅ 项目记录已创建")
        except Exception as e:
            logger.warning(f"创建项目记录失败（可能使用本地模式）: {e}")
    else:
        print(f"📁 继续项目: {project_id}")
    
    # 创建工作流引擎
    print(f"\n🔧 初始化 WorkflowEngine...")
    engine = WorkflowEngine(project_id)
    
    # 设置回调
    engine.set_callbacks(
        on_stage_start=on_stage_start,
        on_stage_complete=on_stage_complete,
        on_stage_error=on_stage_error,
    )
    
    # 如果是新项目，设置需求
    if not engine.context.requirement:
        # 加载规则
        rules = get_base_rules() + "\n" + get_build_workflow_rules()
        
        # 构建完整的工作流输入
        full_input = (
            f"# Build Workflow Kickoff\n"
            f"## 必须严格遵守的规则:\n{rules}\n"
            f"## 用户原始输入\n{user_input}\n"
            f"请按顺序完成构建流程，遵守以上规则。"
        )
        engine.context.requirement = full_input
    
    # 打印初始状态
    print_status(engine.get_status())
    
    # 执行工作流
    start_time = time.time()
    
    print(f"\n🚀 开始执行工作流...")
    print("📋 预计执行阶段:")
    for i, stage in enumerate(engine.context.get_pending_stages(), 1):
        print(f"  {i}. {stage}")
    print()
    
    try:
        if from_stage:
            print(f"📍 从阶段 {from_stage} 开始执行")
            result = engine.execute_from_stage(from_stage, to_completion=True)
        else:
            result = engine.execute_to_completion()
        
        execution_time = time.time() - start_time
        
        # 打印结果
        print(f"\n{'='*60}")
        print("📊 工作流执行结果")
        print(f"{'='*60}")
        print(f"  状态: {'✅ 成功' if result.success else '❌ 失败'}")
        print(f"  完成阶段: {', '.join(result.completed_stages)}")
        if result.failed_stage:
            print(f"  失败阶段: {result.failed_stage}")
        if result.error_message:
            print(f"  错误信息: {result.error_message}")
        print(f"  执行时间: {execution_time:.2f}秒")
        print(f"{'='*60}\n")
        
        # 打印最终状态
        print_status(engine.get_status())
        
        return {
            'project_id': project_id,
            'success': result.success,
            'completed_stages': result.completed_stages,
            'failed_stage': result.failed_stage,
            'error_message': result.error_message,
            'execution_time': execution_time,
            'final_status': result.final_status.value,
        }
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 检测到中断信号，正在暂停工作流...")
        engine.pause()
        print("✅ 工作流已暂停，可以使用 --project-id 参数继续执行")
        return {
            'project_id': project_id,
            'success': False,
            'error_message': 'Interrupted by user',
            'final_status': 'paused',
        }
    except Exception as e:
        logger.error(f"工作流执行失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'project_id': project_id,
            'success': False,
            'error_message': str(e),
            'final_status': 'failed',
        }


def get_project_status(project_id: str) -> dict:
    """获取项目状态"""
    from nexus_utils.workflow.engine import WorkflowEngine
    
    engine = WorkflowEngine(project_id)
    return engine.get_status()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Nexus-AI Agent Build Workflow V2 - 使用 WorkflowEngine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 交互式模式
  python scripts/run_workflow_v2.py
  
  # 批处理模式
  python scripts/run_workflow_v2.py -i "创建一个AWS定价Agent"
  
  # 从文件读取需求
  python scripts/run_workflow_v2.py -f requirements.txt
  
  # 继续已有项目
  python scripts/run_workflow_v2.py --project-id <uuid>
  
  # 从指定阶段开始
  python scripts/run_workflow_v2.py --project-id <uuid> --from-stage agent_designer
  
  # 查看项目状态
  python scripts/run_workflow_v2.py --project-id <uuid> --status
        """
    )
    
    parser.add_argument('-i', '--input', type=str,
                       help='直接指定需求输入内容')
    parser.add_argument('-f', '--file', type=str,
                       help='从文件中读取需求内容')
    parser.add_argument('--project-id', type=str,
                       help='项目ID（用于继续已有项目）')
    parser.add_argument('--from-stage', type=str,
                       help='从指定阶段开始执行')
    parser.add_argument('--status', action='store_true',
                       help='查看项目状态（需要 --project-id）')
    parser.add_argument('--sync-to-s3', action='store_true',
                       help='构建完成后自动同步Agent文件到S3')
    
    args = parser.parse_args()
    
    # 设置S3同步环境变量
    if args.sync_to_s3:
        os.environ["NEXUS_AUTO_SYNC_TO_S3"] = "true"
    
    # 查看状态模式
    if args.status:
        if not args.project_id:
            print("❌ 查看状态需要指定 --project-id")
            sys.exit(1)
        
        try:
            status = get_project_status(args.project_id)
            print_status(status)
        except Exception as e:
            print(f"❌ 获取状态失败: {e}")
            sys.exit(1)
        return
    
    # 获取用户输入
    user_input = None
    
    if args.file:
        # 从文件读取
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                user_input = f.read()
            print(f"📁 已从文件 {args.file} 读取需求内容")
        except FileNotFoundError:
            print(f"❌ 文件 {args.file} 不存在")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            sys.exit(1)
    elif args.input:
        # 直接输入
        user_input = args.input
    elif args.project_id:
        # 继续已有项目，不需要新输入
        user_input = ""
    else:
        # 交互式模式
        user_input = run_interactive_collection()
        if not user_input:
            print("❌ 未收集到有效需求，退出。")
            sys.exit(0)
    
    # 执行工作流
    try:
        result = run_workflow_v2(
            user_input=user_input,
            project_id=args.project_id,
            from_stage=args.from_stage,
        )
        
        if result['success']:
            print(f"\n🎉 工作流执行成功！")
            print(f"   项目ID: {result['project_id']}")
        else:
            print(f"\n⚠️ 工作流执行未完成")
            print(f"   项目ID: {result['project_id']}")
            print(f"   状态: {result['final_status']}")
            if result.get('error_message'):
                print(f"   错误: {result['error_message']}")
            
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
