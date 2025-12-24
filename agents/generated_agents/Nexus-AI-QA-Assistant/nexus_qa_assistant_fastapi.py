#!/usr/bin/env python3
"""
Nexus-AI 专属问答助手（FastAPI 版本）

特性：
1. 预加载核心项目文件内容，减少运行期重复工具调用。
2. 提供 HTTP API（FastAPI），支持通过 REST 接口发起问答请求。
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# =============================================================================
# 环境变量与常量配置
# =============================================================================

os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKSHOP_HTML_PATH = PROJECT_ROOT / "agents/generated_agents/Nexus-AI-QA-Assistant/workshop.html"
WORKSHOP_STATIC_DIR = WORKSHOP_HTML_PATH.parent
CORE_FILE_SOURCES = [
    (
        "README",
        PROJECT_ROOT / "README.md",
        "项目概述、核心架构与使用指南"
    ),
    (
        "default_config",
        PROJECT_ROOT / "config/default_config.yaml",
        "Nexus-AI 项目配置文件"
    ),
    (
        "template_agents",
        PROJECT_ROOT / "agents/template_agents/agent_templates_config.yaml",
        "agent库示例配置文件"
    ),
    (
        "template_prompts",
        PROJECT_ROOT / "prompts/system_agents_prompts/agent_build_workflow/requirements_analyzer.yaml",
        "示例Agent提示词模版"
    ),
    (
        "template_project",
        PROJECT_ROOT / "projects/company_info_search_agent/README.md",
        "示例项目README文件"
    ),
    (
        "WorkflowSummary",
        PROJECT_ROOT / "projects/Nexus-AI-QA-Assistant/workflow_summary_report.md",
        "示例项目Agent 构建与执行工作流总结"
    ),
    # system_workflow 文档
    (
        "magician_agent_readme",
        PROJECT_ROOT / "docs/system_workflow/magician_agent/README.md",
        "Magician Agent 概述文档"
    ),
    (
        "magician_agent_design",
        PROJECT_ROOT / "docs/system_workflow/magician_agent/magician_agent_design.md",
        "Magician Agent 设计文档"
    ),
    (
        "magician_agent_quick_ref",
        PROJECT_ROOT / "docs/system_workflow/magician_agent/quick_reference.md",
        "Magician Agent 快速参考"
    ),
    (
        "agent_build_readme",
        PROJECT_ROOT / "docs/system_workflow/agent_build/README.md",
        "Agent 构建工作流概述"
    ),
    (
        "agent_build_design",
        PROJECT_ROOT / "docs/system_workflow/agent_build/agent_build_workflow_design.md",
        "Agent 构建工作流设计文档"
    ),
    (
        "agent_build_quick_ref",
        PROJECT_ROOT / "docs/system_workflow/agent_build/quick_reference.md",
        "Agent 构建工作流快速参考"
    ),
    (
        "agent_update_readme",
        PROJECT_ROOT / "docs/system_workflow/agent_update/README.md",
        "Agent 更新工作流概述"
    ),
    (
        "agent_update_design",
        PROJECT_ROOT / "docs/system_workflow/agent_update/agent_update_workflow_design.md",
        "Agent 更新工作流设计文档"
    ),
    (
        "agent_update_quick_ref",
        PROJECT_ROOT / "docs/system_workflow/agent_update/quick_reference.md",
        "Agent 更新工作流快速参考"
    ),
    (
        "tool_build_readme",
        PROJECT_ROOT / "docs/system_workflow/tool_build/README.md",
        "Tool 构建工作流概述"
    ),
    (
        "tool_build_design",
        PROJECT_ROOT / "docs/system_workflow/tool_build/tool_build_workflow_design.md",
        "Tool 构建工作流设计文档"
    ),
    (
        "tool_build_quick_ref",
        PROJECT_ROOT / "docs/system_workflow/tool_build/quick_reference.md",
        "Tool 构建工作流快速参考"
    ),
]

DEFAULT_MAX_SECTION_CHARS = int(os.getenv("NEXUS_QA_MAX_SECTION_CHARS", "6000"))

# =============================================================================
# 遥测初始化
# =============================================================================

strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# =============================================================================
# Agent 初始化
# =============================================================================

AGENT_PARAMS = {
    "env": os.getenv("NEXUS_QA_AGENT_ENV", "production"),
    "version": os.getenv("NEXUS_QA_AGENT_VERSION", "latest"),
    "model_id": os.getenv("NEXUS_QA_AGENT_MODEL_ID", "default"),
    "nocallback": True,  # FastAPI 接口默认不使用回调以降低额外工具调用
}

NEXUS_QA_AGENT = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/Nexus-AI-QA-Assistant/nexus_qa_assistant",
    **AGENT_PARAMS,
)

if NEXUS_QA_AGENT is None:
    raise RuntimeError("无法创建 Nexus QA Agent，请检查配置和依赖。")

# =============================================================================
# 核心文件预加载
# =============================================================================


def _read_file_content(path: Path, max_chars: int) -> str:
    try:
        content = path.read_text(encoding="utf-8")
        if len(content) > max_chars:
            return content[:max_chars] + "\n...[内容已截断]"
        return content
    except FileNotFoundError:
        return f"[未找到文件: {path}]"
    except Exception as exc:
        return f"[读取失败: {path} -> {exc}]"


def _load_core_sections(max_chars: int) -> Dict[str, Dict[str, str]]:
    sections: Dict[str, Dict[str, str]] = {}
    for section_id, file_path, description in CORE_FILE_SOURCES:
        sections[section_id] = {
            "description": description,
            "path": str(file_path),
            "content": _read_file_content(file_path, max_chars),
        }
    return sections


CORE_SECTIONS = _load_core_sections(DEFAULT_MAX_SECTION_CHARS)
try:
    WORKSHOP_HTML_CONTENT = WORKSHOP_HTML_PATH.read_text(encoding="utf-8")
except Exception as exc:
    WORKSHOP_HTML_CONTENT = (
        f"<!DOCTYPE html><html><body><h1>加载失败</h1><p>{exc}</p></body></html>"
    )

# =============================================================================
# FastAPI 应用定义
# =============================================================================

app = FastAPI(
    title="Nexus-AI QA Assistant API",
    description="提供基于 Nexus-AI 项目知识库的智能问答服务（FastAPI 封装版）。",
    version="1.0.0",
)

app.mount("/assets", StaticFiles(directory=WORKSHOP_STATIC_DIR), name="assets")

# 允许前端通过代理访问本地服务，避免 CORS 限制
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("NEXUS_QA_API_CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., description="用户提问内容")
    context: Optional[str] = Field(None, description="额外上下文或文件路径提示")
    mode: str = Field(
        "general",
        description="问题类型：architecture/workflow/code/operation/general",
        pattern="^(architecture|workflow|code|operation|general)$",
    )
    include_sections: Optional[List[str]] = Field(
        None, description="指定需要附带的核心资料段落 ID，默认为全部"
    )
    extra_snippets: Optional[List[str]] = Field(
        None, description="额外补充的文本片段，将附加在预加载资料之后"
    )


class AskResponse(BaseModel):
    answer: str
    used_sections: List[str]
    prompt_tokens_hint: int


def _build_augmented_prompt(payload: AskRequest, sections: Dict[str, Dict[str, str]]) -> str:
    section_blocks: List[str] = []
    for section_id, data in sections.items():
        section_blocks.append(
            f"【{section_id} - {data['description']}】\n来源: {data['path']}\n{data['content']}\n"
        )

    extra_block = ""
    if payload.extra_snippets:
        extra_block = "\n".join(payload.extra_snippets)

    context_block = f"\n上下文信息: {payload.context}" if payload.context else ""
    mode_block = "" if payload.mode == "general" else f"\n问题类型: {payload.mode}"

    augmented_prompt = (
        "以下为已预加载的 Nexus-AI 核心资料，请基于这些内容优先作答，避免重复调用工具或文件读取。\n"
        "当资料不足以回答时，可以使用工具进行查询。\n\n"
        + "\n".join(section_blocks)
        + ("\n【额外补充】\n" + extra_block if extra_block else "")
        + "\n【用户提问】\n"
        + f"问题: {payload.question}{context_block}{mode_block}\n"
        "请提供清晰的结构化回答，并引用上述资料来源标注出处。"
    )

    return augmented_prompt


def _select_sections(include_ids: Optional[List[str]]) -> Dict[str, Dict[str, str]]:
    if not include_ids:
        return CORE_SECTIONS

    filtered = {}
    for section_id in include_ids:
        if section_id in CORE_SECTIONS:
            filtered[section_id] = CORE_SECTIONS[section_id]
    if not filtered:
        raise HTTPException(status_code=400, detail="include_sections 无有效匹配，请检查传入的段落 ID。")
    return filtered


@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/core-sections")
async def list_core_sections() -> Dict[str, Dict[str, str]]:
    return {
        section_id: {
            "description": data["description"],
            "path": data["path"],
            "chars": len(data["content"]),
        }
        for section_id, data in CORE_SECTIONS.items()
    }


@app.get("/", response_class=HTMLResponse)
async def serve_workshop() -> HTMLResponse:
    return HTMLResponse(content=WORKSHOP_HTML_CONTENT)


@app.post("/ask", response_model=AskResponse)
async def ask_question(payload: AskRequest) -> AskResponse:
    if not payload.question.strip():
        raise HTTPException(status_code=422, detail="question 不能为空。")

    selected_sections = _select_sections(payload.include_sections)
    augmented_prompt = _build_augmented_prompt(payload, selected_sections)

    try:
        NEXUS_QA_AGENT = create_agent_from_prompt_template(
            agent_name="generated_agents_prompts/Nexus-AI-QA-Assistant/nexus_qa_assistant",
            **AGENT_PARAMS,
        )
        raw_answer = NEXUS_QA_AGENT(augmented_prompt)
        if isinstance(raw_answer, str):
            answer_text = raw_answer
        elif hasattr(raw_answer, "output"):
            answer_text = getattr(raw_answer, "output")
        elif hasattr(raw_answer, "output_text"):
            answer_text = getattr(raw_answer, "output_text")
        elif hasattr(raw_answer, "response"):
            answer_text = getattr(raw_answer, "response")
        else:
            answer_text = str(raw_answer)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent 调用失败: {exc}") from exc

    token_hint = raw_answer.metrics.accumulated_usage['outputTokens']

    return AskResponse(
        answer=answer_text,
        used_sections=list(selected_sections.keys()),
        prompt_tokens_hint=token_hint,
    )


if __name__ == "__main__":
    import uvicorn
    # uvicorn agents.generated_agents.Nexus-AI-QA-Assistant.nexus_qa_assistant_fastapi:app --host 0.0.0.0 --port 8000 --workers 7 --reload
    host = os.getenv("NEXUS_QA_API_HOST", "0.0.0.0")
    port = int(os.getenv("NEXUS_QA_API_PORT", "8888"))
    uvicorn.run("agents.generated_agents.Nexus-AI-QA-Assistant.nexus_qa_assistant_fastapi:app", host=host, port=port, reload=True)

