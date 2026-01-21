"""
AgentCore API Router

AgentCore 直接调用相关的 API 端点
支持前端直接与 AgentCore Runtime 交互
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
import logging
import json

from api.v2.services.agent_runtime_service import invoke_agentcore_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agentcore", tags=["AgentCore"])


class AgentCoreStreamRequest(BaseModel):
    """AgentCore 流式调用请求"""
    runtime_arn: str = Field(..., description="AgentCore Runtime ARN")
    session_id: str = Field(..., description="会话 ID")
    content: str = Field(..., description="用户消息内容")
    runtime_alias: str = Field(default="DEFAULT", description="Runtime Alias")
    region: Optional[str] = Field(default=None, description="AWS Region")


@router.post("/stream")
async def stream_agentcore(request: AgentCoreStreamRequest):
    """
    直接调用 AgentCore Runtime 流式对话
    
    前端可以通过此端点直接与 AgentCore Runtime 交互，
    无需通过 session 管理层
    """
    logger.info(f"AgentCore stream request: arn={request.runtime_arn}, session={request.session_id}")
    
    def _format_sse(data: dict) -> str:
        """格式化 SSE 数据"""
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    
    async def generate():
        """生成流式响应"""
        try:
            async for event in invoke_agentcore_stream(
                runtime_arn=request.runtime_arn,
                session_id=request.session_id,
                message=request.content,
                runtime_alias=request.runtime_alias,
                runtime_region=request.region,
            ):
                yield _format_sse(event)
                
        except Exception as e:
            logger.error(f"AgentCore stream error: {e}", exc_info=True)
            yield _format_sse({
                "event": "error",
                "error": str(e)
            })
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
        }
    )
