#!/usr/bin/env python3
"""
工作流编排器 Agent - 使用 agent_factory 创建并编排其他 agents
"""

import os
import time
import uuid
import json
import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)
from nexus_utils.agent_factory import create_agent_from_prompt_template
from nexus_utils.structured_output_model.project_intent_recognition import IntentRecognitionResult
from strands.session.file_session_manager import FileSessionManager
from tools.system_tools.agent_build_workflow.stage_tracker import (
    initialize_project_record,
    mark_stage_running,
    mark_stage_completed,
    mark_stage_failed,
)
from strands.telemetry import StrandsTelemetry
from nexus_utils.workflow_rule_extract import (
    get_base_rules,
    get_build_workflow_rules,
)
from nexus_utils.config_loader import ConfigLoader
config = ConfigLoader()
# 设置环境变量
os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")
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


def _parse_stage_output(content: str) -> Optional[Dict[str, Any]]:
    """
    解析阶段输出内容，尝试提取 JSON 数据
    
    Args:
        content: 阶段输出的原始内容
        
    Returns:
        解析后的字典，如果无法解析则返回 None
    """
    if not content:
        return None
    
    try:
        # 尝试直接解析 JSON
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # 尝试从 markdown 代码块中提取 JSON
    json_patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            try:
                # 清理可能的前后空白
                cleaned = match.strip()
                if cleaned.startswith('{') or cleaned.startswith('['):
                    parsed = json.loads(cleaned)
                    # 验证解析结果是有效的结构化数据
                    if isinstance(parsed, dict) and len(parsed) > 0:
                        return parsed
            except json.JSONDecodeError:
                continue
    
    # 尝试查找最大的 JSON 对象（从 { 开始到匹配的 } 结束）
    json_objects = _extract_json_objects(content)
    if json_objects:
        # 返回最大的有效 JSON 对象
        largest_obj = max(json_objects, key=lambda x: len(json.dumps(x, ensure_ascii=False)))
        return largest_obj
    
    # 如果无法解析为 JSON，返回包含原始内容的字典
    return {"raw_content": content[:10000]}  # 限制大小


def _extract_json_objects(content: str) -> List[Dict[str, Any]]:
    """
    从文本中提取所有有效的 JSON 对象
    
    Args:
        content: 包含 JSON 的文本内容
        
    Returns:
        提取到的 JSON 对象列表
    """
    json_objects = []
    
    # 查找所有可能的 JSON 起始位置
    i = 0
    while i < len(content):
        if content[i] == '{':
            # 尝试找到匹配的结束括号
            depth = 0
            start = i
            in_string = False
            escape_next = False
            
            for j in range(i, len(content)):
                char = content[j]
                
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\' and in_string:
                    escape_next = True
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if in_string:
                    continue
                
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        # 找到完整的 JSON 对象
                        json_str = content[start:j+1]
                        try:
                            obj = json.loads(json_str)
                            if isinstance(obj, dict) and len(obj) > 0:
                                # 检查是否包含有意义的键（不只是 raw_content）
                                meaningful_keys = [k for k in obj.keys() if k not in ['raw_content']]
                                if meaningful_keys:
                                    json_objects.append(obj)
                        except json.JSONDecodeError:
                            pass
                        break
            
            i = j + 1 if depth == 0 else i + 1
        else:
            i += 1
    
    return json_objects


def _get_project_id():
    """获取当前项目ID（从环境变量或生成新的）"""
    return os.environ.get("NEXUS_STAGE_TRACKER_PROJECT_ID") or str(uuid.uuid4())


def _is_remote_mode():
    """
    检查是否为远程模式（通过 worker 调用）
    
    如果设置了 NEXUS_STAGE_TRACKER_PROJECT_ID 环境变量，
    说明是通过 worker 调用的，使用 v2 API 更新状态。
    """
    return os.environ.get("NEXUS_STAGE_TRACKER_PROJECT_ID") is not None


def _get_resume_from_stage():
    """
    获取恢复起始阶段（从环境变量）
    
    返回:
        str: 恢复起始阶段名称，如果不需要恢复则返回 None
    """
    return os.environ.get("NEXUS_RESUME_FROM_STAGE")


def _should_skip_stage(stage_name: str, resume_from_stage: Optional[str], stage_order: List[str]) -> bool:
    """
    判断是否应该跳过指定阶段
    
    参数:
        stage_name: 当前阶段名称
        resume_from_stage: 恢复起始阶段名称
        stage_order: 阶段执行顺序列表
        
    返回:
        bool: 是否应该跳过该阶段
    """
    if not resume_from_stage:
        return False
    
    try:
        current_index = stage_order.index(stage_name)
        resume_index = stage_order.index(resume_from_stage)
        return current_index < resume_index
    except ValueError:
        # 如果阶段名称不在列表中，不跳过
        return False


def _load_build_rules() -> str:
    """读取Base与Build工作流规则。"""
    base_rules = get_base_rules()
    build_rules = get_build_workflow_rules()
    return base_rules + "\n" + build_rules + "\n=====规则声明结束，请遵守以上规则=====\n"


def analyze_user_intent(user_input: str):
    """分析用户意图 - 通过JSON输出方式"""
    print(f"\n{'='*80}")
    print(f"🔍 [INTENT] 开始分析用户意图")
    print(f"{'='*80}")
    
    try:
        # 创建意图分析 agent（不使用session manager）
        intent_analyzer = create_agent_from_prompt_template(
            agent_name="system_agents_prompts/agent_build_workflow/agent_intent_analyzer",
            nocallback=True,
            **agent_params
        )
        
        # 构建包含JSON结构说明的提示
        intent_result_schema = IntentRecognitionResult.model_json_schema()
        intent_result_example = {
            "user_input": "用户原始输入内容",
            "intent_type": "new_project",  # 或 "existing_project" 或 "unclear"
            "mentioned_project_name": "项目名称（如果有）",
            "project_exists": False,
            "existing_project_info": None,  # 或 ExistingProjectInfo 对象
            "new_project_info": None,  # 或 NewProjectInfo 对象
            "orchestrator_guidance": "给orchestrator的处理建议"
        }
        
        intent_prompt = f"""用户输入：{user_input}

请分析用户意图，并输出JSON格式的结果。

JSON结构说明：
{json.dumps(intent_result_schema, ensure_ascii=False, indent=2)}

示例JSON：
{json.dumps(intent_result_example, ensure_ascii=False, indent=2)}

请直接输出JSON，不要包含其他文字说明。确保JSON格式正确，可以直接被解析。"""
        
        # 调用agent获取响应
        response = intent_analyzer(intent_prompt)
        
        # 从响应中提取JSON
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # 尝试提取JSON（可能包含在代码块中）
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response_text
        
        # 解析JSON为IntentRecognitionResult对象
        intent_data = json.loads(json_str)
        intent_structured_result = IntentRecognitionResult(**intent_data)
        
        print(f"\n{'='*80}")
        print(f"📊 意图类型:\t{intent_structured_result.intent_type}")
        print(f"📊 提到的项目:\t{intent_structured_result.mentioned_project_name}")
        print(f"📊 项目存在:\t{intent_structured_result.project_exists}")
        print(f"📊 处理建议:\t{intent_structured_result.orchestrator_guidance}")
        print(f"{'='*80}\n")

        return intent_structured_result
        
    except Exception as e:
        print(f"❌ 意图分析失败: {e}")
        import traceback
        traceback.print_exc()
        # 返回默认结果
        return IntentRecognitionResult(
            user_input=user_input,
            intent_type="unclear",
            mentioned_project_name=None,
            project_exists=False,
            existing_project_info=None,
            orchestrator_guidance="需要进一步分析用户需求"
        )


def _create_agents_with_session(session_manager: Optional[FileSessionManager] = None):
    """创建带session管理的agents"""
    agent_kwargs = {**agent_params}
    if session_manager:
        agent_kwargs["session_manager"] = session_manager
    
    # 创建各个agent
    orchestrator_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/orchestrator",
        **agent_kwargs
    )
    
    requirements_analyzer_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/requirements_analyzer",
        **agent_kwargs
    )
    
    system_architect_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/system_architect",
        **agent_kwargs
    )
    
    agent_designer_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/agent_designer",
        **agent_kwargs
    )
    
    # 创建开发团队的agents
    tool_developer_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/tool_developer",
        **agent_kwargs
    )
    
    prompt_engineer_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/prompt_engineer",
        **agent_kwargs
    )
    
    agent_code_developer_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/agent_code_developer",
        **agent_kwargs
    )

    agent_developer_manager_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/agent_developer_manager",
        **agent_kwargs
    )
    
    agent_deployer_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/agent_deployer",
        **agent_kwargs
    )
    
    return {
        "orchestrator": orchestrator_agent,
        "requirements_analyzer": requirements_analyzer_agent,
        "system_architect": system_architect_agent,
        "agent_designer": agent_designer_agent,
        "tool_developer": tool_developer_agent,
        "prompt_engineer": prompt_engineer_agent,
        "agent_code_developer": agent_code_developer_agent,
        "agent_developer_manager": agent_developer_manager_agent,
        "agent_deployer": agent_deployer_agent,
    }


def run_workflow(user_input: str, session_id: Optional[str] = None, project_name: Optional[str] = None):
    """
    执行构建工作流
    
    Args:
        user_input: 用户输入内容
        session_id: 可选的session_id，如果未提供则自动生成
        project_name: 可选的项目名称，如果提供则约束Agent使用此名称
    """
    print(f"\n{'='*80}", flush=True)
    print(f"🎯 [WORKFLOW] 开始工作流执行", flush=True)
    print(f"{'='*80}", flush=True)

    # 第一步：分析用户意图（不使用session）
    print(f"🔍 [STEP 1] 分析用户意图...", flush=True)
    intent_structured_result = analyze_user_intent(user_input)

    # 第二步：生成或使用session_id，创建session manager
    if session_id is None:
        session_id = str(uuid.uuid4())
        print(f"🔑 [STEP 2] 生成新的session_id: {session_id}", flush=True)
    else:
        print(f"🔑 [STEP 2] 使用指定的session_id: {session_id}", flush=True)
    
    # 创建session manager
    session_manager = FileSessionManager(
        session_id=session_id,
        storage_dir="./.cache/session_cache"
    )
    
    # 第三步：创建带session的agents
    print(f"\n🏗️ [STEP 3] 创建构建工作流agents（带session管理）...", flush=True)
    agents = _create_agents_with_session(session_manager)
    
    # 第四步：执行工作流
    print(f"\n{'='*80}", flush=True)
    print(f"⚡ [STEP 4] 执行工作流", flush=True)
    print(f"📝 输入内容: {user_input[:100]}...", flush=True)
    print(f"🔑 Session ID: {session_id}", flush=True)
    print(f"{'='*80}", flush=True)
    
    try:
        print("🚀 开始执行工作流...", flush=True)
        print("📋 预计执行阶段:", flush=True)
        print("  1️⃣ orchestrator - 工作流编排", flush=True)
        print("  2️⃣ requirements_analyzer - 需求分析", flush=True)
        print("  3️⃣ system_architect - 系统架构设计", flush=True)
        print("  4️⃣ agent_designer - Agent设计", flush=True)
        print("  5️⃣ tool_developer - 工具开发", flush=True)
        print("  6️⃣ prompt_engineer - 提示词开发", flush=True)
        print("  7️⃣ agent_code_developer - Agent脚本开发", flush=True)
        print("  8️⃣ agent_developer_manager - 开发管理", flush=True)
        print("  9️⃣ agent_deployer - Agent部署", flush=True)
        print(f"{'='*60}", flush=True)

        # 执行工作流并监控进度
        start_time = time.time()

        # 加载规则作为上下文
        rules = _load_build_rules()
        
        # 构建工作流输入，包含规则、意图识别结果和用户输入
        # 如果指定了项目名称，添加约束
        project_name_constraint = ""
        if project_name:
            project_name_constraint = (
                f"## 项目名称约束\n"
                f"**重要**: 用户已指定项目名称为 `{project_name}`，在调用 project_init 工具时必须使用此名称作为 project_name 参数。\n"
                f"不要自行生成或修改项目名称。\n\n"
            )
        
        workflow_input = (
            f"# Build Workflow Kickoff\n"
            f"## 必须严格遵守的规则:\n{rules}\n"
            f"{project_name_constraint}"
            f"## 意图识别结果\n{json.dumps(intent_structured_result.model_dump(), ensure_ascii=False, indent=2)}\n"
            f"## 用户原始输入\n{user_input}\n"
            f"请按顺序完成构建流程，遵守以上规则。"
        )

        # 顺序调用各个agent
        base_context = workflow_input
        current_context = workflow_input
        execution_results = {}  # 存储AgentResult对象
        execution_order = []
        project_id = _get_project_id()
        
        # 检查是否为远程模式（通过 worker 调用，使用 v2 API）
        mode = "remote" if _is_remote_mode() else "local"
        logger.info(f"工作流模式: {mode}, project_id: {project_id}")
        print(f"ℹ️ 工作流模式: {mode}, project_id: {project_id}", flush=True)
        
        # 检查是否需要从断点恢复
        resume_from_stage = _get_resume_from_stage()
        if resume_from_stage:
            logger.info(f"从断点恢复: {resume_from_stage}")
            print(f"🔄 从断点恢复: {resume_from_stage}", flush=True)
        
        # 定义阶段执行顺序（使用 v2 API 的阶段名称）
        stage_order = [
            'orchestrator',
            'requirements_analysis',
            'system_architecture',
            'agent_design',
            'tools_developer',
            'prompt_engineer',
            'agent_code_developer',
            'agent_developer_manager',
            'agent_deployer',
        ]
        
        # 1. Orchestrator
        print(f"\n{'='*60}")
        print(f"🔄 [1/9] 执行 orchestrator...")
        print(f"{'='*60}")
        if _should_skip_stage('orchestrator', resume_from_stage, stage_order):
            print(f"⏭️ 跳过已完成阶段: orchestrator", flush=True)
        else:
            try:
                mark_stage_running(project_id, 'orchestrator') if mode == "remote" else None
                orchestrator_result = agents["orchestrator"](current_context)
                execution_results["orchestrator"] = orchestrator_result
                execution_order.append("orchestrator")
                orchestrator_content = str(orchestrator_result.content) if hasattr(orchestrator_result, 'content') else str(orchestrator_result)
                current_context = base_context + "\n===\nOrchestrator Agent: " + orchestrator_content + "\n===\n"
                mark_stage_completed(project_id, 'orchestrator', _parse_stage_output(orchestrator_content)) if mode == "remote" else None
            except Exception as e:
                mark_stage_failed(project_id, 'orchestrator', str(e)) if mode == "remote" else None
                raise

        # 2. Requirements Analyzer
        print(f"\n{'='*60}")
        print(f"🔄 [2/9] 执行 requirements_analyzer...")
        print(f"{'='*60}")
        if _should_skip_stage('requirements_analysis', resume_from_stage, stage_order):
            print(f"⏭️ 跳过已完成阶段: requirements_analysis", flush=True)
        else:
            try:
                mark_stage_running(project_id, 'requirements_analysis') if mode == "remote" else None
                requirements_result = agents["requirements_analyzer"](current_context)
                execution_results["requirements_analyzer"] = requirements_result
                execution_order.append("requirements_analyzer")
                requirements_content = str(requirements_result.content) if hasattr(requirements_result, 'content') else str(requirements_result)
                current_context = base_context + "\n===\nRequirements Analyzer Agent: " + requirements_content + "\n===\n"
                mark_stage_completed(project_id, 'requirements_analysis', _parse_stage_output(requirements_content)) if mode == "remote" else None
            except Exception as e:
                mark_stage_failed(project_id, 'requirements_analysis', str(e)) if mode == "remote" else None
                raise
        
        # 3. System Architect
        print(f"\n{'='*60}")
        print(f"🔄 [3/9] 执行 system_architect...")
        print(f"{'='*60}")
        if _should_skip_stage('system_architecture', resume_from_stage, stage_order):
            print(f"⏭️ 跳过已完成阶段: system_architecture", flush=True)
        else:
            try:
                mark_stage_running(project_id, 'system_architecture') if mode == "remote" else None
                architect_result = agents["system_architect"](current_context)
                execution_results["system_architect"] = architect_result
                execution_order.append("system_architect")
                architect_content = str(architect_result.content) if hasattr(architect_result, 'content') else str(architect_result)
                current_context = base_context + "\n===\nSystem Architect Agent: " + architect_content + "\n===\n"
                mark_stage_completed(project_id, 'system_architecture', _parse_stage_output(architect_content)) if mode == "remote" else None
            except Exception as e:
                mark_stage_failed(project_id, 'system_architecture', str(e)) if mode == "remote" else None
                raise
        
        # 4. Agent Designer
        print(f"\n{'='*60}")
        print(f"🔄 [4/9] 执行 agent_designer...")
        print(f"{'='*60}")
        if _should_skip_stage('agent_design', resume_from_stage, stage_order):
            print(f"⏭️ 跳过已完成阶段: agent_design", flush=True)
        else:
            try:
                mark_stage_running(project_id, 'agent_design') if mode == "remote" else None
                designer_result = agents["agent_designer"](current_context)
                execution_results["agent_designer"] = designer_result
                execution_order.append("agent_designer")
                designer_content = str(designer_result.content) if hasattr(designer_result, 'content') else str(designer_result)
                current_context = base_context + "\n===\nAgent Designer Agent: " + designer_content + "\n===\n"
                mark_stage_completed(project_id, 'agent_design', _parse_stage_output(designer_content)) if mode == "remote" else None
            except Exception as e:
                mark_stage_failed(project_id, 'agent_design', str(e)) if mode == "remote" else None
                raise
        
        # 5. Tool Developer
        print(f"\n{'='*60}")
        print(f"🔄 [5/9] 执行 tool_developer...")
        print(f"{'='*60}")
        if _should_skip_stage('tools_developer', resume_from_stage, stage_order):
            print(f"⏭️ 跳过已完成阶段: tools_developer", flush=True)
        else:
            try:
                mark_stage_running(project_id, 'tools_developer') if mode == "remote" else None
                tool_developer_result = agents["tool_developer"](current_context)
                execution_results["tool_developer"] = tool_developer_result
                execution_order.append("tool_developer")
                tool_developer_content = str(tool_developer_result.content) if hasattr(tool_developer_result, 'content') else str(tool_developer_result)
                current_context = current_context + "\n===\nTool Developer Agent: " + tool_developer_content + "\n===\n"
                mark_stage_completed(project_id, 'tools_developer', _parse_stage_output(tool_developer_content)) if mode == "remote" else None
            except Exception as e:
                mark_stage_failed(project_id, 'tools_developer', str(e)) if mode == "remote" else None
                raise
        
        # 6. Prompt Engineer
        print(f"\n{'='*60}")
        print(f"🔄 [6/9] 执行 prompt_engineer...")
        print(f"{'='*60}")
        if _should_skip_stage('prompt_engineer', resume_from_stage, stage_order):
            print(f"⏭️ 跳过已完成阶段: prompt_engineer", flush=True)
        else:
            try:
                mark_stage_running(project_id, 'prompt_engineer') if mode == "remote" else None
                prompt_engineer_result = agents["prompt_engineer"](current_context)
                execution_results["prompt_engineer"] = prompt_engineer_result
                execution_order.append("prompt_engineer")
                prompt_engineer_content = str(prompt_engineer_result.content) if hasattr(prompt_engineer_result, 'content') else str(prompt_engineer_result)
                current_context = current_context + "\n===\nPrompt Engineer Agent: " + prompt_engineer_content + "\n===\n"
                mark_stage_completed(project_id, 'prompt_engineer', _parse_stage_output(prompt_engineer_content)) if mode == "remote" else None
            except Exception as e:
                mark_stage_failed(project_id, 'prompt_engineer', str(e)) if mode == "remote" else None
                raise
        
        # 7. Agent Code Developer
        print(f"\n{'='*60}")
        print(f"🔄 [7/9] 执行 agent_code_developer...")
        print(f"{'='*60}")
        if _should_skip_stage('agent_code_developer', resume_from_stage, stage_order):
            print(f"⏭️ 跳过已完成阶段: agent_code_developer", flush=True)
        else:
            try:
                mark_stage_running(project_id, 'agent_code_developer') if mode == "remote" else None
                agent_code_developer_result = agents["agent_code_developer"](current_context)
                execution_results["agent_code_developer"] = agent_code_developer_result
                execution_order.append("agent_code_developer")
                agent_code_developer_content = str(agent_code_developer_result.content) if hasattr(agent_code_developer_result, 'content') else str(agent_code_developer_result)
                current_context = current_context + "\n===\nAgent Code Developer Agent: " + agent_code_developer_content + "\n===\n"
                mark_stage_completed(project_id, 'agent_code_developer', _parse_stage_output(agent_code_developer_content)) if mode == "remote" else None
            except Exception as e:
                mark_stage_failed(project_id, 'agent_code_developer', str(e)) if mode == "remote" else None
                raise
        
        # 8. Agent Developer Manager
        print(f"\n{'='*60}")
        print(f"🔄 [8/9] 执行 agent_developer_manager...")
        print(f"{'='*60}")
        if _should_skip_stage('agent_developer_manager', resume_from_stage, stage_order):
            print(f"⏭️ 跳过已完成阶段: agent_developer_manager", flush=True)
        else:
            try:
                mark_stage_running(project_id, 'agent_developer_manager') if mode == "remote" else None
                developer_manager_result = agents["agent_developer_manager"](current_context)
                execution_results["agent_developer_manager"] = developer_manager_result
                execution_order.append("agent_developer_manager")
                developer_manager_content = str(developer_manager_result.content) if hasattr(developer_manager_result, 'content') else str(developer_manager_result)
                current_context = base_context + "\n===\nAgent Developer Manager Agent: " + developer_manager_content + "\n===\n"
                mark_stage_completed(project_id, 'agent_developer_manager', _parse_stage_output(developer_manager_content)) if mode == "remote" else None
            except Exception as e:
                mark_stage_failed(project_id, 'agent_developer_manager', str(e)) if mode == "remote" else None
                raise
        
        # 9. Agent Deployer
        print(f"\n{'='*60}")
        print(f"🔄 [9/9] 执行 agent_deployer...")
        print(f"{'='*60}")
        if _should_skip_stage('agent_deployer', resume_from_stage, stage_order):
            print(f"⏭️ 跳过已完成阶段: agent_deployer", flush=True)
        elif mode == "remote":
            try:
                mark_stage_running(project_id, 'agent_deployer')
                deployer_result = agents["agent_deployer"](current_context)
                execution_results["agent_deployer"] = deployer_result
                execution_order.append("agent_deployer")
                deployer_content = str(deployer_result.content) if hasattr(deployer_result, 'content') else str(deployer_result)
                mark_stage_completed(project_id, 'agent_deployer', _parse_stage_output(deployer_content))
            except Exception as e:
                mark_stage_failed(project_id, 'agent_deployer', str(e))
                raise
        else:
            print(f"ℹ️ [LOCAL模式] 跳过agent_deployer执行", flush=True)

        end_time = time.time()
        execution_duration = end_time - start_time
        print(f"\n⏱️ 实际执行时间: {execution_duration:.2f}秒")

        print("✅ 工作流执行完成")

        # 更新项目状态为 COMPLETED（由 build_handler 处理，这里不需要重复更新）
        # 项目状态更新已在 build_handler._update_project_status 中完成
        if mode == "remote":
            print(f"✅ 项目状态将由 worker 更新为 COMPLETED")

        # 生成工作流总结报告
        print(f"\n{'='*80}")
        print(f"📊 [RESULTS] 工作流执行结果")
        print(f"{'='*80}")

        print(f"📈 状态: COMPLETED")
        print(f"📊 总节点数: {len(execution_order)}")
        print(f"✅ 完成节点数: {len(execution_order)}")
        print(f"❌ 失败节点数: 0")
        print(f"⏱️ 执行时间: {execution_duration:.2f}秒")

        # 显示执行顺序
        for i, node_name in enumerate(execution_order, 1):
            print(f"  {i}. {node_name}")

        print(f"{'='*80}")

        # 生成工作流总结报告
        from nexus_utils.workflow_report_generator import generate_sequential_workflow_report
        report_path = generate_sequential_workflow_report(
            execution_results=execution_results,
            execution_order=execution_order,
            execution_time=execution_duration,
            intent_analysis=intent_structured_result,
            default_project_root_path='./projects'
        )
        if report_path:
            print(f"📄 报告路径: {report_path}")
        
        # 采集项目信息并同步到 DynamoDB
        if mode == "remote":
            try:
                from nexus_utils.project_info_collector import collect_project_info_after_workflow
                from nexus_utils.workflow_report_generator import extract_project_name_from_agent_results
                
                # 提取项目名称
                local_project_name = extract_project_name_from_agent_results(execution_results)
                
                print(f"📊 [INFO] 开始采集项目信息并同步到 DynamoDB...")
                collect_result = collect_project_info_after_workflow(
                    project_name=local_project_name,
                    project_id=project_id,
                    project_root_path='./projects'
                )
                
                if collect_result.get("success"):
                    print(f"✅ [INFO] 项目信息已同步到 DynamoDB")
                    if collect_result.get("sync_status", {}).get("stages_updated", 0) > 0:
                        print(f"   - 更新了 {collect_result['sync_status']['stages_updated']} 个阶段的指标数据")
                else:
                    errors = collect_result.get("errors", [])
                    print(f"⚠️ [WARN] 项目信息同步部分失败: {errors}")
            except Exception as e:
                print(f"⚠️ [WARN] 采集项目信息失败: {e}")
                import traceback
                traceback.print_exc()
        
        # 同步Agent文件到S3（如果启用）
        # 优先级：环境变量 > 配置文件
        auto_sync_to_s3 = os.environ.get("NEXUS_AUTO_SYNC_TO_S3", "").lower() == "true"
        if not auto_sync_to_s3:
            # 从配置文件读取
            auto_sync_to_s3 = config.get_nested('nexus_ai', 'auto_sync_to_s3', default=False)
        
        if auto_sync_to_s3:
            try:
                from nexus_utils.workflow_report_generator import extract_project_name_from_agent_results
                from nexus_utils.artifact_sync import sync_agent_to_s3
                
                # 提取项目名称
                agent_name = extract_project_name_from_agent_results(execution_results)
                
                if agent_name:
                    print(f"\n📤 [S3] 开始同步Agent文件到S3...")
                    print(f"   Agent名称: {agent_name}")
                    
                    sync_result = sync_agent_to_s3(
                        agent_name=agent_name,
                        version_tag=f"build-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        notes=f"Auto-sync after agent build workflow completion",
                        base_path="."
                    )
                    
                    if sync_result.success:
                        print(f"✅ [S3] Agent文件同步成功!")
                        print(f"   - 版本UUID: {sync_result.version_uuid}")
                        print(f"   - 文件数: {sync_result.files_synced}")
                        print(f"   - 总大小: {sync_result.total_size} 字节")
                        print(f"   - 耗时: {sync_result.duration_seconds:.2f}秒")
                    else:
                        print(f"⚠️ [S3] Agent文件同步失败: {sync_result.error}")
                else:
                    print(f"⚠️ [S3] 无法提取Agent名称，跳过S3同步")
            except Exception as e:
                print(f"⚠️ [S3] S3同步失败: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"{'='*80}")

        return {
            "session_id": session_id,
            "intent_analysis": intent_structured_result,
            "execution_results": execution_results,
            "execution_order": execution_order,
            "execution_time": execution_duration,
            "status": "COMPLETED",
            "report_path": report_path
        }
    except Exception as e:
        print(f"❌ 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()
        raise


def run_interactive_collection() -> str:
    """
    运行交互式需求收集会话
    
    Returns:
        收集完成的需求描述文本
    """
    print(f"\n{'='*60}")
    print(f"🎯 Nexus-AI 交互式需求收集")
    print(f"{'='*60}")
    print(f"💡 提示：")
    print(f"   - 输入 /done 或 /finish 完成需求收集")
    print(f"   - 输入 /quit 或 /exit 退出（不保存）")
    print(f"   - 按 Ctrl+C 强制退出")
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
    
    collected_requirements = []
    
    # 发送开场消息
    opening_prompt = "用户刚刚进入交互式需求收集界面，请友好地问候并开始引导用户描述他们想要构建的AI Agent。"
    
    try:
        response = collection_agent(opening_prompt)
        print("=================================\n🤖 Nexus-AI: ")
        response_text = str(response.content) if hasattr(response, 'content') else str(response)
        print("=================================\n")
    except Exception as e:
        print(f"❌ Agent响应失败: {e}")
        return ""
    
    # 交互循环
    while True:
        try:
            print("=================================\n")
            user_input = input("👤 您: ").strip()
            
            # 检查退出命令
            if user_input.lower() in ['/quit', '/exit', 'quit', 'exit']:
                print("=================================\n")
                print("\n👋 已退出，需求未保存。")
                return ""
            
            # 检查完成命令
            if user_input.lower() in ['/done', '/finish', '/完成', '完成', 'done', 'finish']:
                print("=================================\n")
                print("\n📋 正在整理需求...")
                break
            
            if not user_input:
                continue
            
            # 获取Agent响应
            print("=================================\n")
            print("🤖 Nexus-AI: ", end="", flush=True)
            response = collection_agent(user_input)
            print("\n=================================\n")
            
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
    
    summary_prompt = f"""基于之前的对话内容，请生成一份完整的Agent开发需求描述。
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


if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Agent Build Workflow - AI Agent 构建工作流')
    parser.add_argument('-i', '--input', type=str, 
                       help='直接指定需求输入内容')
    parser.add_argument('-it', '--interactive', action='store_true',
                       help='启动交互式需求收集模式')
    parser.add_argument('-f', '--file', type=str, 
                       help='从文件中读取需求内容')
    parser.add_argument('-s', '--session_id', type=str,
                       default=None,
                       help='可选的session_id，用于恢复之前的会话')
    parser.add_argument('--sync-to-s3', action='store_true',
                       help='构建完成后自动同步Agent文件到S3')
    args = parser.parse_args()
    
    # 设置S3同步环境变量
    if args.sync_to_s3:
        os.environ["NEXUS_AUTO_SYNC_TO_S3"] = "true"
    
    test_input = None
    
    # 交互式模式
    if args.interactive:
        print(f"🎯 [SYSTEM] 启动交互式需求收集模式...", flush=True)
        test_input = run_interactive_collection()
        if not test_input:
            print("❌ [SYSTEM] 未收集到有效需求，退出。")
            exit(0)
    # 从文件读取
    elif args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                test_input = f.read()
            print(f"📁 [SYSTEM] 已从文件 {args.file} 读取需求内容")
        except FileNotFoundError:
            print(f"❌ [SYSTEM] 文件 {args.file} 不存在")
            exit(1)
        except Exception as e:
            print(f"❌ [SYSTEM] 读取文件 {args.file} 失败: {e}")
            exit(1)
    # 直接输入
    elif args.input:
        test_input = args.input
    # 无参数时默认进入交互模式
    else:
        print(f"🎯 [SYSTEM] 未指定输入，启动交互式需求收集模式...", flush=True)
        test_input = run_interactive_collection()
        if not test_input:
            print("❌ [SYSTEM] 未收集到有效需求，退出。")
            exit(0)
    
    print(f"\n{'='*80}")
    print(f"🎯 [SYSTEM] 开始执行Agent构建工作流...")
    print(f"{'='*80}")
    print(f"📝 [SYSTEM] 需求输入: {test_input[:200]}...")
    if args.session_id:
        print(f"🔑 [SYSTEM] 使用指定的session_id: {args.session_id}")
    
    try:
        result = run_workflow(test_input, session_id=args.session_id)
        print(f"\n{'='*80}")
        print(f"🎉 [SYSTEM] 工作流执行完成")
        print(f"🔑 Session ID: {result['session_id']}")
        print(f"📊 执行状态: {result['status']}")
        print(f"⏱️ 执行时间: {result['execution_time']:.2f}秒")
        print(f"{'='*80}")
    except Exception as e:
        print(f"❌ [SYSTEM] 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()

