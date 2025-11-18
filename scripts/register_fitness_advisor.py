#!/usr/bin/env python3
"""注册 Fitness Advisor Agent 到 DynamoDB"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timezone
from decimal import Decimal
from api.database.dynamodb_client import DynamoDBClient
from api.models.schemas import AgentRecord, AgentStatus

def main():
    db = DynamoDBClient()
    
    agent_record = AgentRecord(
        agent_id="fitness_advisor_agent",
        project_id="job_fitness_advisor",
        agent_name="Fitness Advisor",
        description="增肌计划与营养顾问，提供训练安排、饮食方案和进度跟踪建议",
        category="fitness",
        version="v1.0.0",
        status=AgentStatus.RUNNING,
        entrypoint="agents/generated_agents/fitness_advisor/fitness_advisor_agent.py",
        code_path="agents/generated_agents/fitness_advisor",
        prompt_path="prompts/generated_agents_prompts/fitness_advisor/system_prompt.txt",
        tools_path="tools/generated_tools/fitness_advisor",
        deployment_type="agentcore",
        deployment_status="deployed",
        supported_models=["anthropic.claude-3-5-sonnet-20241022-v2:0"],
        supported_inputs=["text"],
        tags=["fitness", "nutrition", "coaching"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        # AgentCore Runtime 信息
        agentcore_runtime_arn="arn:aws:bedrock-agentcore:us-west-2:034362076319:runtime/fitness_advisor_agent-bUADlV3mEM",
        agentcore_runtime_alias="DEFAULT",
        agentcore_region="us-west-2",
        deployment_stage="deployed",
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        runtime_config={
            "temperature": Decimal('0.7'),
            "max_tokens": 4096
        },
        last_deployed_at=datetime.now(timezone.utc)
    )
    
    db.create_agent_record(agent_record)
    print(f"✅ 已注册 Agent: {agent_record.agent_id}")
    print(f"📍 Runtime ARN: {agent_record.agentcore_runtime_arn}")
    print(f"🔗 可通过 API 访问: http://localhost:8000/api/v1/agents?limit=200")

if __name__ == "__main__":
    main()
