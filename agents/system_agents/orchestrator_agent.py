from strands import Agent
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from system_agents.requirements_analyzer_agent import requirements_analyzer
from system_agents.code_generator_agent import code_generator
from strands import Agent, tool
from strands_tools import calculator, file_read, shell,file_write
from utils import prompts_manager
from utils.agent_logging import LoggingHook
os.environ["BYPASS_TOOL_CONSENT"] = "true"

def main():
    """主函数，用于测试需求分析Agent"""
    MAIN_SYSTEM_PROMPT = prompts_manager.get_agent("orchestrator").get_version("latest").system_prompt
    
    print("=== Agent测试 ===")
    orchestrator = Agent(
        name="orchestrator",
        system_prompt=MAIN_SYSTEM_PROMPT,
        callback_handler=None,
        hooks=[LoggingHook()],
        tools=[file_read,file_write,requirements_analyzer, code_generator]
    )
    # 测试基础需求分析
    result = orchestrator("我需要一个agent，我会提供关于IT产品的描述和价格，它需要帮我根据aws服务和产品对照，生成完整的报价表单，并输出markdown格式。")
    print(result)

if __name__ == "__main__":
    main()