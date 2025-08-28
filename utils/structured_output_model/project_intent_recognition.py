from typing import Optional, Literal
from pydantic import BaseModel, Field


class ProjectInfo(BaseModel):
    """项目基本信息"""
    project_name: str = Field(description="项目名称")
    description: str = Field(description="项目描述")
    agent_count: int = Field(description="项目中的Agent数量")


class IntentRecognitionResult(BaseModel):
    """
    意图识别结果 - 判断用户是新项目还是已存在的项目
    """
    
    # 用户原始输入
    user_input: str = Field(description="用户原始输入内容")
    
    # 核心意图识别
    intent_type: Literal["new_project", "existing_project", "unclear"] = Field(
        description="意图类型：new_project(新项目), existing_project(已存在项目), unclear(不明确)"
    )
    
    # 项目相关信息
    mentioned_project_name: Optional[str] = Field(
        default=None,
        description="用户提到的项目名称，如果有明确提及的话"
    )
    
    project_exists: bool = Field(
        default=False,
        description="项目是否存在，基于list_all_projects的结果判断"
    )
    
    existing_project_info: Optional[ProjectInfo] = Field(
        default=None,
        description="如果项目存在，提供项目的详细信息"
    )
    
    # 给orchestrator的指导
    orchestrator_guidance: str = Field(
        description="给orchestrator的处理建议"
    )


# 使用示例
"""
使用示例：

# 新项目场景
result = IntentRecognitionResult(
    user_input="我想创建一个智能客服系统，支持多轮对话",
    intent_type="new_project",
    mentioned_project_name=None,
    project_exists=False,
    existing_project_info=None,
    orchestrator_guidance="启动新项目创建流程，进行需求分析"
)

# 已存在项目场景  
result = IntentRecognitionResult(
    user_input="帮我优化customer_service_bot项目的对话流程",
    intent_type="existing_project", 
    mentioned_project_name="customer_service_bot",
    project_exists=True,
    existing_project_info=ProjectInfo(
        project_name="customer_service_bot",
        description="智能客服机器人项目",
        agent_count=3
    ),
    orchestrator_guidance="加载现有项目，基于当前状态进行增量开发"
)

# 不明确场景
result = IntentRecognitionResult(
    user_input="帮我处理some_project",
    intent_type="unclear",
    mentioned_project_name="some_project", 
    project_exists=False,
    existing_project_info=None,
    orchestrator_guidance="与用户交互澄清具体需求和意图"
)
"""