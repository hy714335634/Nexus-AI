#!/usr/bin/env python3
"""
调试 AgentCore 流式响应格式

用于分析 AgentCore 返回的实际数据格式
"""
import os
import sys
import json
import boto3
from botocore.config import Config

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def debug_agentcore_stream(
    runtime_arn: str,
    session_id: str,
    message: str,
    region: str = "us-west-2"
):
    """调试 AgentCore 流式响应"""
    print(f"\n{'='*60}")
    print("🔍 调试 AgentCore 流式响应")
    print(f"{'='*60}")
    print(f"📍 Runtime ARN: {runtime_arn}")
    print(f"📍 Session ID: {session_id}")
    print(f"📍 Region: {region}")
    print(f"📍 Message: {message}")
    print(f"{'='*60}\n")
    
    # 构建 payload
    payload = {"prompt": message}
    payload_str = json.dumps(payload)
    
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
        
        print("🚀 调用 invoke_agent_runtime...")
        response = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            contentType="application/json",
            accept="text/event-stream",
            payload=payload_str
        )
        
        print(f"✅ 调用成功!")
        print(f"📋 Content-Type: {response.get('contentType', 'N/A')}")
        
        response_stream = response.get('response')
        content_type = response.get('contentType', '')
        
        print(f"\n📥 响应流信息:")
        print(f"   - 类型: {type(response_stream)}")
        print(f"   - 类名: {type(response_stream).__name__}")
        print(f"   - 方法: {[m for m in dir(response_stream) if not m.startswith('_')]}")
        
        if 'text/event-stream' in content_type and response_stream:
            print(f"\n📜 流式响应内容 (逐行):")
            print("-" * 60)
            
            line_count = 0
            text_chunks = []
            
            # 使用 iter_lines 逐行读取
            for line in response_stream.iter_lines():
                if line:
                    line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                    line_count += 1
                    
                    # 打印原始行
                    print(f"\n[行 {line_count}] 原始数据:")
                    print(f"   长度: {len(line_str)}")
                    print(f"   内容: {line_str[:200]}{'...' if len(line_str) > 200 else ''}")
                    
                    # 尝试解析
                    if line_str.startswith('data: '):
                        data_content = line_str[6:]
                        print(f"   [SSE data] {data_content[:150]}...")
                        
                        try:
                            parsed = json.loads(data_content)
                            print(f"   [JSON 解析成功] keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'not dict'}")
                            
                            # 提取文本内容
                            if isinstance(parsed, dict):
                                if 'event' in parsed:
                                    event_data = parsed['event']
                                    print(f"   [event] keys: {list(event_data.keys()) if isinstance(event_data, dict) else event_data}")
                                    
                                    if 'contentBlockDelta' in event_data:
                                        delta = event_data['contentBlockDelta'].get('delta', {})
                                        text = delta.get('text', '')
                                        if text:
                                            text_chunks.append(text)
                                            print(f"   [文本] {text[:50]}...")
                                            
                        except json.JSONDecodeError as e:
                            print(f"   [JSON 解析失败] {e}")
                    elif line_str.startswith('data:'):
                        data_content = line_str[5:]
                        print(f"   [SSE data (无空格)] {data_content[:150]}...")
                    else:
                        print(f"   [非 SSE 格式]")
            
            print(f"\n{'='*60}")
            print(f"📊 统计:")
            print(f"   - 总行数: {line_count}")
            print(f"   - 文本块数: {len(text_chunks)}")
            if text_chunks:
                full_text = ''.join(text_chunks)
                print(f"   - 完整文本长度: {len(full_text)}")
                print(f"\n📝 完整响应文本:")
                print("-" * 60)
                print(full_text)
        
        else:
            print(f"\n⚠️ 非流式响应")
            if response_stream and hasattr(response_stream, 'read'):
                raw = response_stream.read()
                content = raw.decode('utf-8') if isinstance(raw, bytes) else raw
                print(f"内容: {content[:500]}")
        
        print(f"\n{'='*60}")
        print("✅ 调试完成")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


def main():
    import argparse
    import uuid
    
    parser = argparse.ArgumentParser(description='调试 AgentCore 流式响应')
    parser.add_argument('--arn', type=str, required=True, help='AgentCore Runtime ARN')
    parser.add_argument('--session', type=str, default=None, help='Session ID')
    parser.add_argument('--message', type=str, default='你好，请简单介绍一下你自己', help='测试消息')
    parser.add_argument('--region', type=str, default='us-west-2', help='AWS Region')
    
    args = parser.parse_args()
    
    if not args.session:
        args.session = f"debug-sess-{uuid.uuid4()}"
        print(f"📝 生成 Session ID: {args.session}")
    
    debug_agentcore_stream(
        runtime_arn=args.arn,
        session_id=args.session,
        message=args.message,
        region=args.region
    )


if __name__ == "__main__":
    main()
