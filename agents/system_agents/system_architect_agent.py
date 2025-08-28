#!/usr/bin/env python3

import sys
import os
from typing import Dict, Any, Optional
from strands import Agent, tool
from strands_tools import calculator,file_read,file_write,current_time,shell
from utils.config_loader import get_config
from utils import prompts_manager
from tools.system_tools.agent_template_provider import get_all_templates,get_template_content
from tools.system_tools.project_manager import get_project_config,get_project_readme,get_project_status,update_project_config,update_project_readme,update_project_status,update_project_stage_content,get_project_stage_content
import boto3
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig
os.environ["BYPASS_TOOL_CONSENT"] = "true"

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
    max_tokens=prompts_manager.get_agent("system_architect").get_environment_config("production").max_tokens,
    boto_session=session,
    boto_client_config=boto_config
)

# 创建Agent实例
system_architect = Agent(
    name="system_architect",
    model=bedrock_model,
    tools=[
        file_read,
        get_all_templates,
        get_template_content,
        current_time,
        get_project_status,
        get_project_config,
        get_project_readme,
        get_project_stage_content,
        update_project_config,
        update_project_readme,
        update_project_status,
        update_project_stage_content
    ],
    system_prompt=prompts_manager.get_agent("system_architect").get_version("latest").system_prompt,
)
