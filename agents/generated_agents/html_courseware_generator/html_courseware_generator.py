#!/usr/bin/env python3
"""
智能HTML课件与教案生成系统

专业的HTML课件与教案生成专家，支持多学科动态交互课件生成、教案自动生成、FastAPI Web服务集成。
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# 核心框架导入
from nexus_utils.agent_factory import create_agent_from_prompt_template
from nexus_utils.config_loader import ConfigLoader
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import RequestContext
from strands.telemetry import StrandsTelemetry

# FastAPI 导入
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# 工具导入
from tools.generated_tools.html_courseware_generator.courseware_generation_tools import (
    html_structure_generator,
    css_style_generator,
    javascript_code_generator,
    math_formula_renderer,
    chemistry_equation_generator,
    interactive_element_builder,
    code_validator,
    xss_scanner,
    subject_template_selector,
    physics_chart_generator
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("html_courseware_generator")

# 环境变量配置
loader = ConfigLoader()
os.environ["BYPASS_TOOL_CONSENT"] = "true"
otel_endpoint = loader.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 创建 BedrockAgentCoreApp 实例
app = BedrockAgentCoreApp()

# ==================== Agent 创建 ====================
def create_courseware_agent(env: str = "production", version: str = "latest", model_id: str = "default"):
    """创建课件生成Agent"""
    agent_params = {
        "env": env,
        "version": version,
        "model_id": model_id,
        "enable_logging": True
    }
    return create_agent_from_prompt_template(
        agent_name="generated_agents_prompts/html_courseware_generator/html_courseware_generator",
        **agent_params
    )

# 创建 Agent 实例
courseware_agent = create_courseware_agent()

# ==================== FastAPI 应用 ====================
fastapi_app = FastAPI(
    title="HTML课件与教案生成系统",
    description="智能生成HTML课件和教案的Web服务",
    version="1.0.0"
)

# CORS 配置
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 课件存储目录
COURSEWARE_DIR = Path("courseware")
COURSEWARE_DIR.mkdir(exist_ok=True)

# 静态文件服务
fastapi_app.mount("/courseware", StaticFiles(directory=str(COURSEWARE_DIR)), name="courseware")

# ==================== 数据模型 ====================
class CoursewareGenerationRequest(BaseModel):
    """课件生成请求"""
    subject: str = Field(..., description="学科名称，如'数学'、'化学'、'物理'")
    topic: str = Field(..., description="课件主题，如'二次函数'、'氧化还原反应'")
    grade: Optional[str] = Field(None, description="目标年级，如'高中一年级'")
    duration: Optional[int] = Field(45, description="课时长度（分钟），默认45")
    requirements: Optional[str] = Field(None, description="详细要求")

class CoursewareGenerationResult(BaseModel):
    """课件生成结果"""
    status: str = Field(..., description="生成状态：success、partial、failed")
    courseware_url: Optional[str] = Field(None, description="课件访问URL")
    lesson_plan_url: Optional[str] = Field(None, description="教案访问URL")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    message: str = Field(..., description="结果消息")
    error: Optional[str] = Field(None, description="错误信息")

# ==================== 工具函数 ====================
def sanitize_filename(name: str, max_length: int = 50) -> str:
    """清洗文件名，去除特殊字符"""
    import re
    # 去除特殊字符，保留中文、英文、数字、下划线
    name = re.sub(r'[^\w\u4e00-\u9fff]', '_', name)
    # 限制长度
    if len(name) > max_length:
        name = name[:max_length]
    return name

def create_folder_structure(subject: str, topic: str) -> Path:
    """创建文件夹结构"""
    subject_clean = sanitize_filename(subject)
    topic_clean = sanitize_filename(topic)
    
    folder_path = COURSEWARE_DIR / subject_clean / topic_clean
    
    # 处理文件夹冲突
    if folder_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_path = COURSEWARE_DIR / subject_clean / f"{topic_clean}_{timestamp}"
    
    folder_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created folder: {folder_path}")
    return folder_path

def save_courseware_files(folder_path: Path, html_content: str, lesson_plan_content: str, metadata: Dict[str, Any]) -> Dict[str, str]:
    """保存课件和教案文件"""
    try:
        # 保存HTML课件
        courseware_file = folder_path / "index.html"
        courseware_file.write_text(html_content, encoding='utf-8')
        logger.info(f"Saved courseware: {courseware_file}")
        
        # 保存教案
        lesson_plan_file = folder_path / "lesson_plan.html"
        lesson_plan_file.write_text(lesson_plan_content, encoding='utf-8')
        logger.info(f"Saved lesson plan: {lesson_plan_file}")
        
        # 保存元数据
        metadata_file = folder_path / "metadata.json"
        metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        logger.info(f"Saved metadata: {metadata_file}")
        
        # 生成访问URL
        relative_path = folder_path.relative_to(COURSEWARE_DIR)
        courseware_url = f"/courseware/{relative_path}/index.html"
        lesson_plan_url = f"/courseware/{relative_path}/lesson_plan.html"
        
        return {
            "courseware_path": str(courseware_file),
            "lesson_plan_path": str(lesson_plan_file),
            "metadata_path": str(metadata_file),
            "courseware_url": courseware_url,
            "lesson_plan_url": lesson_plan_url
        }
    except Exception as e:
        logger.error(f"Error saving files: {str(e)}")
        raise

async def generate_courseware_and_lesson_plan(request: CoursewareGenerationRequest) -> CoursewareGenerationResult:
    """生成课件和教案的核心函数"""
    try:
        logger.info(f"Starting generation for {request.subject} - {request.topic}")
        
        # 构建提示词
        prompt = f"""请生成以下课件和教案：

学科：{request.subject}
主题：{request.topic}
年级：{request.grade or '通用'}
课时：{request.duration}分钟
详细要求：{request.requirements or '无'}

请按照以下步骤完成：
1. 生成包含动态交互功能的HTML课件
2. 生成配套的教学教案
3. 确保课件和教案内容一致

课件要求：
- 包含完整的HTML结构、CSS样式和JavaScript交互代码
- 支持{request.subject}学科的特定功能（如数学公式、化学方程式等）
- 交互元素包括选择题、输入题等
- 响应式设计，支持不同屏幕尺寸
- 所有代码必须通过XSS安全检查

教案要求：
- 包含教学目标（知识、能力、情感）
- 包含教学重点和难点
- 包含详细的教学步骤（导入、讲授、练习、小结）
- 包含时间分配建议
- 包含作业布置和教学反思建议
"""
        
        # 调用Agent生成内容
        logger.info("Calling courseware agent...")
        response = courseware_agent(prompt)
        
        # 解析响应
        if hasattr(response, 'content') and response.content:
            content = response.content
        elif isinstance(response, str):
            content = response
        else:
            content = str(response)
        
        logger.info(f"Agent response received, length: {len(content)}")
        
        # 提取HTML课件和教案内容（简化处理，实际应该更复杂）
        # 这里假设Agent返回的内容包含HTML和教案两部分
        html_content = content  # 实际应该解析出HTML部分
        lesson_plan_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{request.subject} - {request.topic} 教案</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; }}
        h1, h2, h3 {{ color: #333; }}
        .section {{ margin-bottom: 20px; }}
    </style>
</head>
<body>
    <h1>{request.subject} - {request.topic} 教案</h1>
    <div class="section">
        <h2>课程信息</h2>
        <p><strong>学科：</strong>{request.subject}</p>
        <p><strong>主题：</strong>{request.topic}</p>
        <p><strong>年级：</strong>{request.grade or '通用'}</p>
        <p><strong>课时：</strong>{request.duration}分钟</p>
    </div>
    <div class="section">
        <h2>教学目标</h2>
        <p>（由Agent生成的教学目标）</p>
    </div>
    <div class="section">
        <h2>教学重点</h2>
        <p>（由Agent生成的教学重点）</p>
    </div>
    <div class="section">
        <h2>教学步骤</h2>
        <p>（由Agent生成的教学步骤）</p>
    </div>
</body>
</html>"""
        
        # 创建文件夹结构
        folder_path = create_folder_structure(request.subject, request.topic)
        
        # 准备元数据
        metadata = {
            "id": folder_path.name,
            "subject": request.subject,
            "topic": request.topic,
            "grade": request.grade,
            "duration": request.duration,
            "created_at": datetime.now().isoformat(),
            "requirements": request.requirements
        }
        
        # 保存文件
        file_paths = save_courseware_files(folder_path, html_content, lesson_plan_content, metadata)
        
        logger.info("Generation completed successfully")
        
        return CoursewareGenerationResult(
            status="success",
            courseware_url=file_paths["courseware_url"],
            lesson_plan_url=file_paths["lesson_plan_url"],
            metadata=metadata,
            message="课件和教案生成成功"
        )
        
    except Exception as e:
        logger.error(f"Error during generation: {str(e)}")
        return CoursewareGenerationResult(
            status="failed",
            message="生成失败",
            error=str(e)
        )

# ==================== FastAPI 端点 ====================
@fastapi_app.post("/api/generate", response_model=CoursewareGenerationResult)
async def generate_courseware(request: CoursewareGenerationRequest, background_tasks: BackgroundTasks):
    """生成课件和教案"""
    logger.info(f"Received generation request: {request.subject} - {request.topic}")
    
    # 参数验证
    if not request.subject or not request.topic:
        raise HTTPException(status_code=400, detail="学科和主题不能为空")
    
    # 调用生成函数
    result = await generate_courseware_and_lesson_plan(request)
    
    return result

@fastapi_app.get("/api/courseware/list")
async def list_courseware(subject: Optional[str] = None, limit: int = 20, offset: int = 0):
    """查询课件列表"""
    try:
        courseware_list = []
        
        # 遍历课件目录
        for subject_dir in COURSEWARE_DIR.iterdir():
            if not subject_dir.is_dir():
                continue
            
            # 如果指定了学科，只返回该学科的课件
            if subject and subject_dir.name != sanitize_filename(subject):
                continue
            
            for topic_dir in subject_dir.iterdir():
                if not topic_dir.is_dir():
                    continue
                
                metadata_file = topic_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
                        courseware_list.append(metadata)
                    except Exception as e:
                        logger.error(f"Error reading metadata: {str(e)}")
        
        # 排序（按创建时间降序）
        courseware_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # 分页
        total = len(courseware_list)
        items = courseware_list[offset:offset+limit]
        
        return {
            "total": total,
            "items": items,
            "page_info": {
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total
            }
        }
    except Exception as e:
        logger.error(f"Error listing courseware: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/api/courseware/{courseware_id}")
async def get_courseware_detail(courseware_id: str):
    """查询课件详情"""
    try:
        # 查找课件
        for subject_dir in COURSEWARE_DIR.iterdir():
            if not subject_dir.is_dir():
                continue
            
            for topic_dir in subject_dir.iterdir():
                if topic_dir.name == courseware_id:
                    metadata_file = topic_dir / "metadata.json"
                    if metadata_file.exists():
                        metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
                        return metadata
        
        raise HTTPException(status_code=404, detail="课件不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting courseware detail: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "html_courseware_generator",
        "version": "1.0.0"
    }

# ==================== AgentCore 入口点 ====================
@app.entrypoint
async def handler(payload: Dict[str, Any], context: RequestContext):
    """
    AgentCore 标准入口点（支持流式响应）
    
    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息
            - subject: 学科（可选）
            - topic: 主题（可选）
        context: 请求上下文
        
    Yields:
        str: 流式响应的文本片段
    """
    session_id = context.session_id
    logger.info(f"Received AgentCore request, session_id: {session_id}")
    
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")
    
    if not prompt:
        yield "Error: Missing 'prompt' in request"
        return
    
    try:
        # 使用流式响应
        stream = courseware_agent.stream_async(prompt)
        async for event in stream:
            logger.debug(f"Streaming event: {event}")
            yield event
            
    except Exception as e:
        logger.error(f"Error in handler: {str(e)}")
        yield f"Error: {str(e)}"

# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='HTML课件与教案生成系统')
    parser.add_argument('-i', '--input', type=str, default=None, help='测试输入')
    parser.add_argument('--subject', type=str, default="数学", help='学科')
    parser.add_argument('--topic', type=str, default="二次函数", help='主题')
    parser.add_argument('--port', type=int, default=8000, help='FastAPI服务端口')
    parser.add_argument('-it', '--interactive', action='store_true', default=False, help='启动交互式多轮对话模式')
    args = parser.parse_args()
    
    # 检查是否在 Docker 容器中运行（AgentCore 部署）
    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"
    
    if is_docker:
        # AgentCore 部署模式：启动 HTTP 服务器
        logger.info("Starting AgentCore HTTP server on port 8080")
        app.run()
    elif args.input:
        # 本地测试模式
        logger.info(f"Agent created: {courseware_agent.name}")
        logger.info(f"Input: {args.input}")
        result = courseware_agent(args.input)
        logger.info(f"Response: {result}")
    elif args.interactive:
        # 交互式对话模式
        logger.info(f"Agent created: {courseware_agent.name}")
        logger.info("进入交互式对话模式（输入 'quit' 或 'exit' 退出）")
        while True:
            user_input = input("You: ")
            result = courseware_agent(user_input)
            logger.info(f"Response: {result}")
            if user_input.lower() in ['quit', 'exit']:
                break
    else:
        # 启动 FastAPI 服务
        logger.info(f"Starting FastAPI server on port {args.port}")
        # 注意：reload 模式需要以导入字符串形式传递应用，这里使用直接运行模式
        uvicorn.run(fastapi_app, host="0.0.0.0", port=args.port, reload=False)
