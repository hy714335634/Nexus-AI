import boto3
import json

client = boto3.client('bedrock-agentcore', region_name='us-west-2')
agent_arn = 'arn:aws:bedrock-agentcore:us-west-2:034362076319:runtime/fitness_advisor_agent-bUADlV3mEM'

test_input = {"query": "我想制定一个增肌计划，目标是6个月增重5公斤"}

print(f"🧪 测试 Fitness Advisor Agent")
print(f"📝 输入: {test_input['query']}\n")

try:
    response = client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        payload=json.dumps(test_input)
    )
    
    print("✅ Agent 调用成功")
    print(f"📊 响应状态码: {response['ResponseMetadata']['HTTPStatusCode']}")
    
    # 读取流式响应
    if 'payload' in response:
        payload_stream = response['payload']
        result = payload_stream.read().decode('utf-8')
        print(f"\n📤 Agent 响应:\n{result}")
    else:
        print(f"\n📤 完整响应:\n{json.dumps(response, indent=2, default=str)}")
        
except Exception as e:
    print(f"❌ 错误: {e}")
    print("\n💡 提示: Agent 可能已经成功运行，请查看 CloudWatch 日志:")
    print("aws logs tail /aws/bedrock-agentcore/runtimes/fitness_advisor_agent-bUADlV3mEM-DEFAULT --since 5m --region us-west-2")
