#!/usr/bin/env python3
"""
注册本地Agent到DynamoDB并部署到AgentCore

用于将本地已存在但DDB无记录的Agent注册并部署

使用方法:
    # 仅注册到DDB（不部署）
    python scripts/register_local_agent.py --project mindmap_generator --register-only
    
    # 注册并部署到AgentCore
    python scripts/register_local_agent.py --project mindmap_generator --deploy
    
    # Dry-run模式（测试）
    python scripts/register_local_agent.py --project mindmap_generator --deploy --dry-run
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def load_project_config(project_name: str) -> dict:
    """加载项目配置"""
    config_path = project_root / "projects" / project_name / "project_config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"项目配置不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def register_agent_to_ddb(project_name: str, config: dict) -> str:
    """注册Agent到DynamoDB"""
    from api.v2.database import db_client
    from api.v2.models.schemas import AgentStatus
    
    # 提取Agent信息
    prompt_files = config.get('prompt_files', [])
    prompt_info = prompt_files[0] if prompt_files else {}
    agent_info = prompt_info.get('agent_info', {})
    metadata = prompt_info.get('metadata', {})
    
    agent_scripts = config.get('agent_scripts', [])
    script_info = agent_scripts[0] if agent_scripts else {}
    
    agent_name = agent_info.get('name', project_name)
    description = agent_info.get('description', '')
    category = agent_info.get('category', 'general')
    
    # 生成agent_id
    project_id = config.get('project_id', project_name)
    agent_id = f"{project_id}:{agent_name}"
    
    # 检查是否已存在
    existing = db_client.get_agent(agent_id)
    if existing:
        print(f"⚠️  Agent已存在: {agent_id}")
        return agent_id
    
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    agent_data = {
        'agent_id': agent_id,
        'project_id': project_id,
        'agent_name': agent_name,
        'description': description,
        'category': category,
        'version': '1.0.0',
        'status': AgentStatus.OFFLINE.value,
        'deployment_type': 'local',
        'deployment_status': 'pending',
        'code_path': script_info.get('script_path'),
        'prompt_path': prompt_info.get('prompt_path'),
        'dependencies': script_info.get('dependencies', []),
        'supported_models': metadata.get('supported_models', []),
        'tags': metadata.get('tags', []),
        'tools_dependencies': metadata.get('tools_dependencies', []),
        'total_invocations': 0,
        'successful_invocations': 0,
        'failed_invocations': 0,
        'avg_duration_ms': 0,
        'created_at': now,
        'updated_at': now,
    }
    
    db_client.create_agent(agent_data)
    print(f"✅ Agent已注册到DynamoDB: {agent_id}")
    
    return agent_id


def deploy_to_agentcore(project_name: str, dry_run: bool = False) -> dict:
    """部署Agent到AgentCore"""
    from api.v2.services.agent_deployment_service import AgentDeploymentService
    
    # 设置dry-run环境变量
    if dry_run:
        os.environ["AGENTCORE_DEPLOY_DRY_RUN"] = "true"
    else:
        os.environ.pop("AGENTCORE_DEPLOY_DRY_RUN", None)
    
    service = AgentDeploymentService()
    result = service.deploy_to_agentcore(project_name=project_name)
    
    return result.to_dict()


def update_project_config_with_agentcore(project_name: str, deployment_result: dict):
    """更新project_config.json添加agentcore配置"""
    config_path = project_root / "projects" / project_name / "project_config.json"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 添加agentcore配置
    config['agentcore'] = {
        'agent_arn': deployment_result.get('agent_runtime_arn'),
        'agent_alias_id': deployment_result.get('agent_alias_id'),
        'agent_alias_arn': deployment_result.get('agent_alias_arn'),
        'region': deployment_result.get('region'),
        'deployed_at': datetime.now(timezone.utc).isoformat(),
    }
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已更新project_config.json的agentcore配置")


def main():
    parser = argparse.ArgumentParser(description='注册本地Agent到DynamoDB并部署到AgentCore')
    parser.add_argument('--project', '-p', type=str, required=True,
                        help='项目名称（projects目录下的文件夹名）')
    parser.add_argument('--register-only', action='store_true',
                        help='仅注册到DDB，不部署')
    parser.add_argument('--deploy', action='store_true',
                        help='注册并部署到AgentCore')
    parser.add_argument('--dry-run', action='store_true',
                        help='Dry-run模式（不实际部署）')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 本地Agent注册与部署工具")
    print("=" * 60)
    print(f"📁 项目: {args.project}")
    print(f"📋 模式: {'仅注册' if args.register_only else '注册并部署'}")
    if args.deploy and args.dry_run:
        print(f"⚠️  Dry-run模式: 启用")
    print("=" * 60)
    
    try:
        # 1. 加载项目配置
        print("\n📖 加载项目配置...")
        config = load_project_config(args.project)
        print(f"   项目名: {config.get('project_name')}")
        print(f"   Agent脚本数: {len(config.get('agent_scripts', []))}")
        print(f"   工具数: {config.get('total_tools', 0)}")
        
        # 2. 注册到DDB
        print("\n📝 注册Agent到DynamoDB...")
        agent_id = register_agent_to_ddb(args.project, config)
        
        # 3. 部署到AgentCore（如果需要）
        if args.deploy:
            print("\n🚀 部署到AgentCore...")
            result = deploy_to_agentcore(args.project, dry_run=args.dry_run)
            
            print(f"\n📋 部署结果:")
            print(f"   Agent ID: {result.get('agent_id')}")
            print(f"   部署状态: {result.get('deployment_status')}")
            print(f"   部署类型: {result.get('deployment_type')}")
            
            if result.get('agent_runtime_arn'):
                print(f"   Runtime ARN: {result.get('agent_runtime_arn')}")
                
                # 更新project_config.json
                if not args.dry_run:
                    update_project_config_with_agentcore(args.project, result)
        
        print("\n" + "=" * 60)
        print("✅ 完成!")
        print("=" * 60)
        
    except FileNotFoundError as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
