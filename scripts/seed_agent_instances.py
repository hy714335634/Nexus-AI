from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Any

from api.database.dynamodb_client import DynamoDBClient
from api.models.schemas import AgentRecord, AgentStatus

DEFAULT_AGENT = {
  "agent_id": "fitness_advisor_agent",
  "project_id": "job_fitness_advisor",
  "agent_name": "Fitness Advisor",
  "description": "增肌计划与营养顾问，提供训练安排、饮食方案和进度跟踪建议。",
  "category": "fitness",
  "entrypoint": "agents/generated_agents/fitness_advisor/fitness_advisor_agent.py",
  "prompt_path": "prompts/generated_agents_prompts/fitness_advisor/system_prompt.txt",
  "tools_path": "tools/generated_tools/fitness_advisor",
  "code_path": "agents/generated_agents/fitness_advisor",
  "supported_models": ["anthropic.claude-3-5-sonnet-20241022-v2:0"],
  "supported_inputs": ["text"],
  "tags": ["fitness", "nutrition", "coaching"],
  "agentcore_runtime_arn": "arn:aws:bedrock-agentcore:us-west-2:000000000000:runtime/sample-agent",
  "agentcore_runtime_alias": "DEFAULT",
  "agentcore_region": "us-west-2",
  "runtime_model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
  "runtime_config": {
    "temperature": 0.7,
    "max_tokens": 4096,
  },
}


def create_agent_record(
  agent_id: str = DEFAULT_AGENT["agent_id"],
  agent_name: str = DEFAULT_AGENT["agent_name"],
  project_id: str = DEFAULT_AGENT["project_id"],
  description: str | None = DEFAULT_AGENT["description"],
  category: str | None = DEFAULT_AGENT["category"],
  status: AgentStatus = AgentStatus.RUNNING,
  entrypoint: str | None = DEFAULT_AGENT["entrypoint"],
  code_path: str | None = DEFAULT_AGENT["code_path"],
  prompt_path: str | None = DEFAULT_AGENT["prompt_path"],
  tools_path: str | None = DEFAULT_AGENT["tools_path"],
  supported_models: list[str] | None = None,
  supported_inputs: list[str] | None = None,
  tags: list[str] | None = None,
  agentcore_runtime_arn: str | None = DEFAULT_AGENT["agentcore_runtime_arn"],
  agentcore_runtime_alias: str | None = DEFAULT_AGENT["agentcore_runtime_alias"],
  agentcore_region: str | None = DEFAULT_AGENT["agentcore_region"],
  runtime_model_id: str | None = DEFAULT_AGENT["runtime_model_id"],
  runtime_config: dict[str, Any] | None = DEFAULT_AGENT["runtime_config"],
) -> AgentRecord:
  return AgentRecord(
    agent_id=agent_id,
    project_id=project_id,
    agent_name=agent_name,
    description=description,
    category=category,
    status=status,
    entrypoint=entrypoint,
    code_path=code_path,
    prompt_path=prompt_path,
    tools_path=tools_path,
    created_at=datetime.now(timezone.utc),
    supported_models=supported_models or DEFAULT_AGENT["supported_models"],
    supported_inputs=supported_inputs or DEFAULT_AGENT["supported_inputs"],
    tags=tags or DEFAULT_AGENT["tags"],
    deployment_type="local",
    deployment_status="pending",
    agentcore_runtime_arn=agentcore_runtime_arn,
    agentcore_runtime_alias=agentcore_runtime_alias,
    agentcore_region=agentcore_region,
    runtime_model_id=runtime_model_id,
    runtime_config=runtime_config or DEFAULT_AGENT["runtime_config"],
  )


def main() -> None:
  parser = argparse.ArgumentParser(description="Seed AgentInstances with a sample agent record.")
  parser.add_argument("--agent-id", default=DEFAULT_AGENT["agent_id"])
  parser.add_argument("--project-id", default=DEFAULT_AGENT["project_id"])
  parser.add_argument("--agent-name", default=DEFAULT_AGENT["agent_name"])
  parser.add_argument("--description", default=DEFAULT_AGENT["description"])
  parser.add_argument("--category", default=DEFAULT_AGENT["category"])
  parser.add_argument("--runtime-arn", default=DEFAULT_AGENT["agentcore_runtime_arn"])
  parser.add_argument("--runtime-alias", default=DEFAULT_AGENT["agentcore_runtime_alias"])
  parser.add_argument("--runtime-region", default=DEFAULT_AGENT["agentcore_region"])
  parser.add_argument("--model-id", default=DEFAULT_AGENT["runtime_model_id"])
  args = parser.parse_args()

  record = create_agent_record(
    agent_id=args.agent_id,
    project_id=args.project_id,
    agent_name=args.agent_name,
    description=args.description,
    category=args.category,
    agentcore_runtime_arn=args.runtime_arn,
    agentcore_runtime_alias=args.runtime_alias,
    agentcore_region=args.runtime_region,
    runtime_model_id=args.model_id,
  )

  db = DynamoDBClient()
  db.create_agent_record(record)
  print(f"✅ Seeded AgentInstances with agent_id={record.agent_id}")


if __name__ == "__main__":
  main()
