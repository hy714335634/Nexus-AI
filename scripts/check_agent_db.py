#!/usr/bin/env python3
"""
检查数据库中的 Agent 记录

用于调试 Agent 配置问题
"""
import os
import sys
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def check_agent_in_db(agent_id: str):
    """检查数据库中的 Agent 记录"""
    print(f"\n{'='*60}")
    print(f"🔍 检查 Agent: {agent_id}")
    print(f"{'='*60}")
    
    try:
        from api.v2.database import db_client
        
        # 直接从数据库获取
        agent = db_client.get_agent(agent_id)
        
        if agent:
            print(f"\n✅ 在数据库中找到 Agent")
            print(f"\n📋 Agent 详情:")
            for key, value in agent.items():
                if value is not None:
                    print(f"   {key}: {value}")
            
            # 检查关键字段
            print(f"\n🔑 关键配置:")
            print(f"   agentcore_runtime_arn: {agent.get('agentcore_runtime_arn', 'N/A')}")
            print(f"   agentcore_runtime_alias: {agent.get('agentcore_runtime_alias', 'N/A')}")
            print(f"   agentcore_region: {agent.get('agentcore_region', 'N/A')}")
            print(f"   deployment_type: {agent.get('deployment_type', 'N/A')}")
            print(f"   status: {agent.get('status', 'N/A')}")
        else:
            print(f"\n❌ 数据库中未找到 Agent: {agent_id}")
            
    except Exception as e:
        print(f"\n❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()


def list_all_agents():
    """列出数据库中所有 Agent"""
    print(f"\n{'='*60}")
    print(f"📋 数据库中的所有 Agent")
    print(f"{'='*60}")
    
    try:
        from api.v2.database import db_client
        
        result = db_client.list_agents(limit=100)
        agents = result.get('items', [])
        
        if agents:
            print(f"\n找到 {len(agents)} 个 Agent:\n")
            for agent in agents:
                agent_id = agent.get('agent_id', 'N/A')
                agent_name = agent.get('agent_name', 'N/A')
                status = agent.get('status', 'N/A')
                deployment_type = agent.get('deployment_type', 'N/A')
                arn = agent.get('agentcore_runtime_arn', 'N/A')
                
                print(f"   📦 {agent_id}")
                print(f"      名称: {agent_name}")
                print(f"      状态: {status}")
                print(f"      部署类型: {deployment_type}")
                print(f"      ARN: {arn[:50]}..." if arn and len(str(arn)) > 50 else f"      ARN: {arn}")
                print()
        else:
            print("\n数据库中没有 Agent 记录")
            
    except Exception as e:
        print(f"\n❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()


def check_agent_service(agent_id: str):
    """通过 AgentService 检查 Agent"""
    print(f"\n{'='*60}")
    print(f"🔍 通过 AgentService 检查 Agent: {agent_id}")
    print(f"{'='*60}")
    
    try:
        from api.v2.services.agent_service import agent_service
        
        agent = agent_service.get_agent(agent_id)
        
        if agent:
            print(f"\n✅ 找到 Agent")
            print(f"\n📋 Agent 详情:")
            for key, value in agent.items():
                if value is not None and key not in ['agentcore_config']:
                    print(f"   {key}: {value}")
            
            # 检查 agentcore_config
            agentcore_config = agent.get('agentcore_config')
            if agentcore_config:
                print(f"\n🔧 AgentCore 配置:")
                for key, value in agentcore_config.items():
                    print(f"   {key}: {value}")
            else:
                print(f"\n⚠️ 没有 agentcore_config")
            
            # 检查关键字段
            print(f"\n🔑 关键配置:")
            print(f"   agentcore_runtime_arn: {agent.get('agentcore_runtime_arn', 'N/A')}")
            print(f"   agentcore_arn: {agent.get('agentcore_arn', 'N/A')}")
            print(f"   agent_path: {agent.get('agent_path', 'N/A')}")
            print(f"   source: {agent.get('source', 'N/A')}")
        else:
            print(f"\n❌ 未找到 Agent: {agent_id}")
            
    except Exception as e:
        print(f"\n❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='检查数据库中的 Agent 记录')
    parser.add_argument('--agent-id', type=str, help='要检查的 Agent ID')
    parser.add_argument('--list', action='store_true', help='列出所有 Agent')
    parser.add_argument('--service', action='store_true', help='通过 AgentService 检查')
    
    args = parser.parse_args()
    
    if args.list:
        list_all_agents()
    elif args.agent_id:
        if args.service:
            check_agent_service(args.agent_id)
        else:
            check_agent_in_db(args.agent_id)
    else:
        # 默认检查 business_english_teacher_agent
        agent_ids = [
            "business_english_teacher_agent:business_english_teacher_agent",
            "local_business_english_teacher_agent",
        ]
        
        list_all_agents()
        
        for agent_id in agent_ids:
            check_agent_service(agent_id)


if __name__ == "__main__":
    main()
