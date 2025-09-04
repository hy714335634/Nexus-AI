from strands import tool
import os
from utils.agent_factory import create_agent_from_prompt_template

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"
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
        A detailed prompt template development answer
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

