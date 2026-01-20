#!/usr/bin/env python3
"""
测试流式对话 API

直接调用后端 API 测试流式响应
"""
import os
import sys
import json
import requests

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_stream_api(session_id: str, message: str, api_base: str = "http://localhost:8000"):
    """测试流式对话 API"""
    print(f"\n{'='*60}")
    print("🧪 测试流式对话 API")
    print(f"{'='*60}")
    print(f"📍 API Base: {api_base}")
    print(f"📍 Session ID: {session_id}")
    print(f"📍 Message: {message}")
    print(f"{'='*60}\n")
    
    url = f"{api_base}/api/v2/sessions/{session_id}/stream"
    payload = {"content": message, "role": "user"}
    
    print(f"📤 POST {url}")
    print(f"📦 Payload: {json.dumps(payload)}")
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=60
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        print(f"📥 Response Headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            print(f"\n❌ 错误响应: {response.text}")
            return False
        
        print(f"\n📜 流式响应内容:")
        print("-" * 40)
        
        event_count = 0
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                event_count += 1
                print(f"[{event_count}] {line_str}")
        
        print("-" * 40)
        print(f"\n总共 {event_count} 个事件")
        
        return True
        
    except requests.exceptions.Timeout:
        print(f"\n❌ 请求超时")
        return False
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_or_create_session(agent_id: str, api_base: str = "http://localhost:8000") -> str:
    """获取或创建会话"""
    print(f"\n🔍 获取或创建会话...")
    
    # 先尝试获取现有会话
    url = f"{api_base}/api/v2/agents/{agent_id}/sessions"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        sessions = data.get('data', [])
        if sessions:
            session_id = sessions[0].get('session_id')
            print(f"✅ 使用现有会话: {session_id}")
            return session_id
    
    # 创建新会话
    print(f"📝 创建新会话...")
    response = requests.post(
        url,
        json={"display_name": "测试会话"},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        session_id = data.get('data', {}).get('session_id')
        print(f"✅ 创建会话成功: {session_id}")
        return session_id
    else:
        print(f"❌ 创建会话失败: {response.text}")
        return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='测试流式对话 API')
    parser.add_argument('--session', type=str, help='Session ID')
    parser.add_argument('--agent', type=str, default='business_english_teacher_agent:business_english_teacher_agent', help='Agent ID')
    parser.add_argument('--message', type=str, default='Hello, how are you?', help='测试消息')
    parser.add_argument('--api-base', type=str, default='http://localhost:8000', help='API Base URL')
    
    args = parser.parse_args()
    
    # 获取或创建会话
    session_id = args.session
    if not session_id:
        session_id = get_or_create_session(args.agent, args.api_base)
        if not session_id:
            print("❌ 无法获取会话 ID")
            return
    
    # 测试流式 API
    test_stream_api(session_id, args.message, args.api_base)


if __name__ == "__main__":
    main()
