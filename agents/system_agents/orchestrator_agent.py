import os
from strands import Agent, tool
from strands_tools import calculator, file_read, shell, file_write, current_time
from agents.system_agents.requirements_analyzer_agent import requirements_analyzer
from agents.system_agents.system_architect_agent import system_architect
from agents.system_agents.agent_designer import agent_designer
from agents.system_agents.prompt_engineer import prompt_engineer
from agents.system_agents.tool_developer import tool_developer
from agents.system_agents.agent_code_developer import agent_code_developer
from agents.system_agents.agent_developer_manager import agent_developer_manager
from utils import prompts_manager
from utils.agent_logging import LoggingHook
from utils.config_loader import get_config
from strands import Agent
from strands.multiagent import GraphBuilder, Swarm
from strands.models import BedrockModel
from tools.system_tools.project_manager import project_init,generate_content,get_project_config,get_project_readme,get_project_status,update_project_config,update_project_readme,update_project_status,update_project_stage_content,get_project_stage_content
from strands.telemetry import StrandsTelemetry
from botocore.config import Config as BotocoreConfig
import boto3

os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()      # Send traces to OTLP endpoint



config = get_config()

boto_config = BotocoreConfig(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=10,
    read_timeout=120
)

# Create a custom boto3 session
session = boto3.Session(
    region_name=config.get_aws_config().get("bedrock_region_name")
)

# Create a Bedrock model with the custom session
bedrock_model = BedrockModel(
    model_id=config.get_bedrock_config().get("model_id"),
    max_tokens=prompts_manager.get_agent("orchestrator").get_environment_config("production").max_tokens,
    boto_session=session,
    boto_client_config=boto_config
)

# Create a orchestrator agent node
orchestrator = Agent(
        name="orchestrator",
        model=bedrock_model,
        system_prompt=prompts_manager.get_agent("orchestrator").get_version("latest").system_prompt,
        tools=[
            shell,
            file_read,
            current_time,
            project_init,
            update_project_config,
            update_project_readme,
            update_project_status,
            get_project_status,
            get_project_config,
            get_project_readme,
            get_project_stage_content
        ]
    )

# Create a graph with the swarm as a node
builder = GraphBuilder()
builder.add_node(orchestrator, "orchestrator")
builder.add_node(requirements_analyzer, "requirements_analyzer")
builder.add_node(system_architect, "system_architect")
builder.add_node(agent_designer, "agent_designer")
builder.add_node(prompt_engineer, "prompt_engineer")
builder.add_node(tool_developer, "tool_developer")
builder.add_node(agent_code_developer, "agent_code_developer")
builder.add_node(agent_developer_manager, "agent_developer_manager")

builder.add_edge("orchestrator", "requirements_analyzer")
builder.add_edge("requirements_analyzer", "system_architect")
builder.add_edge("system_architect", "agent_designer")
builder.add_edge("agent_designer", "prompt_engineer")
builder.add_edge("prompt_engineer", "tool_developer")
builder.add_edge("tool_developer", "agent_code_developer")
builder.add_edge("agent_code_developer", "agent_developer_manager")


graph = builder.build()

result = graph("我会提供客户在其他云平台的账单或者本地IDC的配置清单，请给我按照AWS产品进行报价")

# Access the results
print(f"\n{result}")
