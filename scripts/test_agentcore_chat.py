#!/usr/bin/env python3
"""
测试 AgentCore 对话功能

直接调用 AgentCore API 测试流式响应
"""
import os
import sys
import json
import boto3
from botocore.config import Config

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_agentcore_invoke(
    runtime_arn: str,
    session_id: str,
    message: str,
    region: str = "us-west-2"
):
    """测试 AgentCore 调用"""
    print(f"\n{'='*60}")
    print("🧪 测试 AgentCore 调用")
    print(f"{'='*60}")
    print(f"📍 Runtime ARN: {runtime_arn}")
    print(f"📍 Session ID: {session_id} (长度: {len(session_id)})")
    print(f"📍 Region: {region}")
    print(f"📍 Message: {message}")
    print(f"{'='*60}\n")
    
    # 构建 payload
    payload = {"prompt": message}
    payload_str = json.dumps(payload)
    print(f"📦 Payload: {payload_str}")
    
    # 配置 boto3 客户端
    config = Config(
        read_timeout=300,
        connect_timeout=30,
        retries={'max_attempts': 0}
    )
    
    try:
        client = boto3.client(
            "bedrock-agentcore",
            region_name=region,
            config=config
        )
        print("✅ boto3 客户端创建成功")
        
        print("\n🚀 调用 invoke_agent_runtime...")
        response = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            contentType="application/json",
            accept="text/event-stream",
            payload=payload_str
        )
        
        print(f"✅ 调用成功!")
        print(f"📋 Response keys: {list(response.keys())}")
        print(f"📋 Content-Type: {response.get('contentType', 'N/A')}")
        print(f"📋 Status Code: {response.get('ResponseMetadata', {}).get('HTTPStatusCode', 'N/A')}")
        
        # 读取响应流
        response_stream = response.get('response')
        content_type = response.get('contentType', '')
        
        print(f"\n📥 读取响应流...")
        print(f"📋 Stream type: {type(response_stream)}")
        print(f"📋 Has iter_lines: {hasattr(response_stream, 'iter_lines')}")
        print(f"📋 Has read: {hasattr(response_stream, 'read')}")
        
        if 'text/event-stream' in content_type and response_stream:
            print("\n📜 流式响应内容:")
            print("-" * 40)
            
            if hasattr(response_stream, 'iter_lines'):
                line_count = 0
                for line in response_stream.iter_lines(chunk_size=1):
                    if line:
                        line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                        line_count += 1
                        print(f"[{line_count}] {line_str[:200]}{'...' if len(line_str) > 200 else ''}")
                print(f"\n总共 {line_count} 行")
            else:
                raw = response_stream.read()
                content = raw.decode('utf-8') if isinstance(raw, bytes) else raw
                print(content[:1000])
        
        elif response_stream:
            print("\n📜 非流式响应内容:")
            print("-" * 40)
            if hasattr(response_stream, 'read'):
                raw = response_stream.read()
                content = raw.decode('utf-8') if isinstance(raw, bytes) else raw
            else:
                content = str(response_stream)
            print(content[:1000])
        
        print(f"\n{'='*60}")
        print("✅ 测试完成")
        print(f"{'='*60}")
        return True
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='测试 AgentCore 对话')
    parser.add_argument('--arn', type=str, required=True, help='AgentCore Runtime ARN')
    parser.add_argument('--session', type=str, default=None, help='Session ID (默认生成新的)')
    parser.add_argument('--message', type=str, default='Hello, how are you?', help='测试消息')
    parser.add_argument('--region', type=str, default='us-west-2', help='AWS Region')
    
    args = parser.parse_args()
    
    # 生成 session ID（如果未提供）
    if not args.session:
        import uuid
        args.session = f"sess-{uuid.uuid4()}"
        print(f"📝 生成 Session ID: {args.session}")
    
    test_agentcore_invoke(
        runtime_arn=args.arn,
        session_id=args.session,
        message=args.message,
        region=args.region
    )


if __name__ == "__main__":
    main()
