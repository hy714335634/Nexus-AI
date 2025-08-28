from strands import Agent, tool
from strands_tools import calculator
import json
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands.models import BedrockModel

app = BedrockAgentCoreApp()

# 自定义工具定义
@tool
def custom_tool():
    """自定义工具示例"""
    return "这是自定义工具的输出"

# 模型配置
model_id = "us.anthropic.claude-sonnet-4-20250514-v1:0"
model = BedrockModel(
    model_id=model_id,
)

# Agent配置
agent = Agent(
    model=model,
    tools=[calculator, custom_tool],
    system_prompt="你是一个有用的助手。你可以进行简单的数学计算，并使用自定义工具。"
)

@app.entrypoint
def strands_agent_bedrock(payload):
    """
    使用payload调用agent
    
    Args:
        payload (dict): 包含用户输入的payload
        
    Returns:
        str: agent的响应文本
    """
    user_input = payload.get("prompt")
    print("用户输入:", user_input)
    response = agent(user_input)
    return response.message['content'][0]['text']

if __name__ == "__main__":
    app.run() 