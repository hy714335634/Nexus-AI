import boto3
import json
import base64

client = boto3.client('bedrock-agentcore', region_name='us-west-2')

# Read file and encode to base64
with open("README.md", "rb") as f:
    file_data = base64.b64encode(f.read()).decode('utf-8')

# Prepare payload with file content
payload = json.dumps({
    "prompt": "Please summarize this file in short format",
    "media": {
        "type": "document",
        "format": "markdown", 
        "data": file_data
    }
}).encode()

response = client.invoke_agent_runtime(
    agentRuntimeArn='arn:aws:bedrock-agentcore:us-west-2:034362076319:runtime/file_summarizer-20694WEZRC',
    runtimeSessionId='dfmeoagmreaklgmrkleafremoigrmtesogmtrskhmtkrlshmt',
    payload=payload,
    qualifier="DEFAULT"
)

# Handle streaming response
if "text/event-stream" in response.get("contentType", ""):
    content = []
    for line in response["response"].iter_lines(chunk_size=10):
        if line:
            line = line.decode("utf-8")
            if line.startswith("data: "):
                line = line[6:]
                print(line)
                content.append(line)
    print("\nComplete response:", "\n".join(content))
else:
    response_body = response['response'].read()
    response_data = json.loads(response_body)
    print("Agent Response:", json.dumps(response_data, indent=2))
