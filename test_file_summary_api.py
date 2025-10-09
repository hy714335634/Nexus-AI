import boto3
import json

client = boto3.client('bedrock-agentcore', region_name='us-west-2')

# Test with a prompt that uses the agent's expected format
payload = json.dumps({
    "input": {
        "prompt": """Please summarize the following file:

File path: README.md
Summary length: short
Output format: plain
Extract keywords: No

Please use the file_summarizer_tool to read and summarize the file content."""
    }
})

response = client.invoke_agent_runtime(
    agentRuntimeArn='arn:aws:bedrock-agentcore:us-west-2:034362076319:runtime/file_summarizer-20694WEZRC',
    runtimeSessionId='dfmeoagmreaklgmrkleafremoigrmtesogmtrskhmtkrlshmt',
    payload=payload,
    qualifier="DEFAULT"
)

response_body = response['response'].read()
response_data = json.loads(response_body)
print("Agent Response:", json.dumps(response_data, indent=2))
