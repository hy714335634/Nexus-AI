import boto3
import json

# 初始化客户端
client = boto3.client('bedrock-agentcore', region_name='us-west-2')

# Agent ARN
agent_arn = 'arn:aws:bedrock-agentcore:us-west-2:034362076319:runtime/fitness_advisor_agent-bUADlV3mEM'

# 测试输入
test_input = {"query": "我想制定一个减肥计划，目标是3个月减重10公斤"}

print(f"🧪 测试 Fitness Advisor Agent")
print(f"📝 输入: {test_input['query']}\n")

# 调用 Agent
response = client.invoke_agent_runtime(
    agentRuntimeArn=agent_arn,
    payload=json.dumps(test_input)
)

# 解析响应
print("📤 Agent 响应:")
if 'payload' in response:
    result = json.loads(response['payload'].read())
    print(json.dumps(result, indent=2, ensure_ascii=False))
else:
    print(json.dumps(response, indent=2, default=str))
