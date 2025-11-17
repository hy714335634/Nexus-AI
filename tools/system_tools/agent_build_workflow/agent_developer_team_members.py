from strands import tool
import os
from nexus_utils.agent_factory import create_agent_from_prompt_template
from nexus_utils.config_loader import ConfigLoader
loader = ConfigLoader()

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": loader.get_nested("nexus_ai", "workflow_default_version", "agent_build")
}


@tool
def agent_code_developer(query: str) -> str:
    """
    invoke code developer agent to develop agent code, need to provide the agent name, agent design specification, prompt template and tool path
    Args:
        query: A agent code development question

    Returns:
        A detailed agent code development answer
    """
    try:
        agent_code_developer = create_agent_from_prompt_template(
            agent_name="system_agents_prompts/agent_build_workflow/agent_code_developer", 
            **agent_params
        )

        response = agent_code_developer(query)
        return str(response)
    except Exception as e:
        return f"Error in research assistant: {str(e)}"


@tool
def agent_tool_developer(query: str) -> str:
    """
    invoke tool developer agent to develop tool code, need to provide the tool name, tool design specification

    Args:
        query: A tool code development question or design specification

    Returns:
        A detailed tool code development answer
    """
    try:
        agent_tool_developer = create_agent_from_prompt_template(
            agent_name="system_agents_prompts/agent_build_workflow/tool_developer", 
            **agent_params
        )

        response = agent_tool_developer(query)
        return str(response)
    except Exception as e:
        return f"Error in tool code developer: {str(e)}"

@tool
def agent_prompt_engineer(query: str) -> str:
    """
    invoke prompt engineer agent to develop prompt template, need to provide the agent name, prompt template design specification, tool path

    Args:
        query: A prompt template development question or design specification

    Returns:
        str: A detailed prompt template development answer
    """
    try:
        agent_prompt_engineer = create_agent_from_prompt_template(
            agent_name="system_agents_prompts/agent_build_workflow/prompt_engineer", 
            **agent_params
        )

        response = agent_prompt_engineer(query)
        return str(response)
    except Exception as e:
        return f"Error in prompt engineer: {str(e)}"



@tool
def agent_template_searcher(query: str) -> str:
    """
    智能模版搜索专家，通过自然语言需求分析和智能匹配算法，为agent提供精准的tools、agent、prompt模版推荐服务。
    
    该工具能够：
    1. 智能分析用户需求，提取核心功能、技术约束、业务场景等关键特征
    2. 根据用户明确指定（如"工具模版"、"Agent模版"、"提示词模版"）或需求特点智能判断需要搜索的模版类型
    3. 使用多种搜索策略进行模版匹配，包括语义相似度、功能匹配度、技术栈兼容性等多重指标
    4. 为每个推荐模版提供详细的匹配理由、0-100分的匹配度评分、优缺点分析和使用建议
    5. 提供替代方案和定制化说明，帮助用户做出最佳选择
    
    Args:
        query: 用户的自然语言需求描述，可以明确指定模版类型（如"工具模版"、"Agent模版"、"提示词模版"）

    Returns:
        结构化的模版推荐结果，包含：
        - 需求分析结果（核心功能、技术约束、业务场景等）
        - 判断的模版类型
        - 推荐模版列表（包含评分、匹配理由、优势、限制、使用建议、定制说明）
        - 替代方案
        - 搜索总结
    """
    try:
        agent_template_searcher_agent = create_agent_from_prompt_template(
            agent_name="system_agents_prompts/agent_build_workflow/agent_template_searcher", 
            **agent_params
        )

        response = agent_template_searcher_agent(query)
        return str(response)
    except Exception as e:
        return f"Error in agent template searcher: {str(e)}"

