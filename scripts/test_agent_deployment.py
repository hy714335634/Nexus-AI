#!/usr/bin/env python3
"""
测试 Agent 部署功能的脚本

此脚本模拟 AgentCore 容器环境中的 agent 创建过程，
用于验证日志权限等问题是否已修复。

使用方法:
    # 基础测试（不需要 AWS 凭证）
    python scripts/test_agent_deployment.py --skip-factory
    
    # 完整测试（需要 AWS 凭证）
    python scripts/test_agent_deployment.py --agent business_english_teacher_agent
    
    # 测试 AgentCore 部署（dry-run 模式）
    python scripts/test_agent_deployment.py --test-deploy --project business_english_teacher_agent
    
    # 实际部署到 AgentCore
    python scripts/test_agent_deployment.py --test-deploy --project business_english_teacher_agent --no-dry-run
"""

import os
import sys
import argparse
import tempfile
import logging

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_logging_permission():
    """测试日志文件权限"""
    print("\n" + "=" * 60)
    print("🔍 测试 1: 日志文件权限")
    print("=" * 60)
    
    # 测试默认日志路径
    log_paths = [
        "logs/nexus_ai.log",
        "logs/enhanced_workflow.log",
    ]
    
    for log_path in log_paths:
        full_path = os.path.join(project_root, log_path)
        log_dir = os.path.dirname(full_path)
        
        print(f"\n📁 测试路径: {full_path}")
        
        # 检查目录是否存在
        if os.path.exists(log_dir):
            print(f"   ✅ 目录存在: {log_dir}")
        else:
            print(f"   ⚠️ 目录不存在，尝试创建...")
            try:
                os.makedirs(log_dir, exist_ok=True)
                print(f"   ✅ 目录创建成功")
            except PermissionError as e:
                print(f"   ❌ 目录创建失败: {e}")
                continue
        
        # 测试文件写入
        try:
            with open(full_path, 'a', encoding='utf-8') as f:
                f.write(f"# Test write at {__import__('datetime').datetime.now()}\n")
            print(f"   ✅ 文件写入成功")
        except PermissionError as e:
            print(f"   ❌ 文件写入失败: {e}")


def test_config_loader():
    """测试配置加载器"""
    print("\n" + "=" * 60)
    print("🔍 测试 2: 配置加载器")
    print("=" * 60)
    
    try:
        from nexus_utils.config_loader import ConfigLoader
        config = ConfigLoader()
        print("   ✅ ConfigLoader 初始化成功")
        
        # 测试获取配置
        enhanced_logging = config.get("enhanced_logging", default={})
        print(f"   📋 enhanced_logging 配置: {type(enhanced_logging)}")
        
        log_file = enhanced_logging.get("log_file", "logs/nexus_ai.log") if isinstance(enhanced_logging, dict) else "logs/nexus_ai.log"
        print(f"   📋 日志文件路径: {log_file}")
        
    except Exception as e:
        print(f"   ❌ ConfigLoader 初始化失败: {e}")
        import traceback
        traceback.print_exc()


def test_agent_logging_hook():
    """测试 Agent 日志钩子"""
    print("\n" + "=" * 60)
    print("🔍 测试 3: Agent 日志钩子")
    print("=" * 60)
    
    try:
        from nexus_utils.strands_agent_logging_hook import AgentLoggingHook, create_agent_logging_hook
        
        # 测试创建日志钩子
        hook = create_agent_logging_hook("test_agent")
        if hook:
            print("   ✅ AgentLoggingHook 创建成功")
            print(f"   📋 Agent 名称: {hook.agent_name}")
        else:
            print("   ⚠️ AgentLoggingHook 返回 None（可能是配置禁用了）")
            
    except PermissionError as e:
        print(f"   ❌ 权限错误: {e}")
    except Exception as e:
        print(f"   ❌ 创建失败: {e}")
        import traceback
        traceback.print_exc()


def test_agent_factory(agent_name: str = None):
    """测试 Agent 工厂"""
    print("\n" + "=" * 60)
    print("🔍 测试 4: Agent 工厂")
    print("=" * 60)
    
    if not agent_name:
        agent_name = "business_english_teacher_agent"
    
    prompt_path = f"generated_agents_prompts/{agent_name}/{agent_name}_prompt"
    
    print(f"   📋 测试 Agent: {agent_name}")
    print(f"   📋 Prompt 路径: {prompt_path}")
    
    try:
        from nexus_utils.agent_factory import create_agent_from_prompt_template
        
        # 尝试创建 agent（不实际调用，只测试初始化）
        agent = create_agent_from_prompt_template(
            agent_name=prompt_path,
            env="production",
            version="latest",
            model_id="default",
            enable_logging=True,
            nocallback=True  # 不注册回调，避免实际调用
        )
        
        if agent:
            print(f"   ✅ Agent 创建成功")
            print(f"   📋 Agent 类型: {type(agent)}")
            if hasattr(agent, 'name'):
                print(f"   📋 Agent 名称: {agent.name}")
        else:
            print("   ❌ Agent 创建返回 None")
            
    except PermissionError as e:
        print(f"   ❌ 权限错误: {e}")
    except Exception as e:
        print(f"   ❌ 创建失败: {e}")
        import traceback
        traceback.print_exc()


def test_with_temp_logs():
    """使用临时目录测试（模拟容器环境）"""
    print("\n" + "=" * 60)
    print("🔍 测试 5: 模拟容器环境（临时目录）")
    print("=" * 60)
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"   📁 临时目录: {temp_dir}")
        
        # 设置环境变量模拟容器环境
        old_cwd = os.getcwd()
        
        try:
            # 创建日志目录
            logs_dir = os.path.join(temp_dir, "logs")
            os.makedirs(logs_dir, exist_ok=True)
            os.chmod(logs_dir, 0o777)
            print(f"   ✅ 创建日志目录: {logs_dir}")
            
            # 测试写入
            test_log = os.path.join(logs_dir, "test.log")
            with open(test_log, 'w') as f:
                f.write("test")
            print(f"   ✅ 日志写入测试成功")
            
        finally:
            os.chdir(old_cwd)


def test_deployment_service(project_name: str, dry_run: bool = True):
    """测试 AgentCore 部署服务"""
    print("\n" + "=" * 60)
    print("🔍 测试 6: AgentCore 部署服务")
    print("=" * 60)
    
    print(f"   📋 项目名称: {project_name}")
    print(f"   📋 Dry-run 模式: {dry_run}")
    
    # 检查项目目录是否存在
    project_dir = os.path.join(project_root, "projects", project_name)
    if not os.path.exists(project_dir):
        print(f"   ❌ 项目目录不存在: {project_dir}")
        return False
    
    print(f"   ✅ 项目目录存在: {project_dir}")
    
    # 检查 project_config.json
    config_path = os.path.join(project_dir, "project_config.json")
    if os.path.exists(config_path):
        print(f"   ✅ project_config.json 存在")
        try:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"   📋 项目ID: {config.get('project_id', 'N/A')}")
            print(f"   📋 Agent脚本数: {len(config.get('agent_scripts', []))}")
            print(f"   📋 工具数: {config.get('total_tools', 0)}")
        except Exception as e:
            print(f"   ⚠️ 读取 project_config.json 失败: {e}")
    else:
        print(f"   ⚠️ project_config.json 不存在")
    
    # 设置环境变量
    if dry_run:
        os.environ["AGENTCORE_DEPLOY_DRY_RUN"] = "true"
    else:
        os.environ.pop("AGENTCORE_DEPLOY_DRY_RUN", None)
    
    try:
        from api.v2.services.agent_deployment_service import AgentDeploymentService
        
        print("\n   🚀 初始化部署服务...")
        service = AgentDeploymentService()
        print(f"   ✅ 部署服务初始化成功")
        print(f"   📋 Repo Root: {service.repo_root}")
        
        print("\n   🚀 开始部署...")
        result = service.deploy_to_agentcore(
            project_name=project_name,
        )
        
        print(f"\n   ✅ 部署完成!")
        print(f"   📋 Agent ID: {result.agent_id}")
        print(f"   📋 Project ID: {result.project_id}")
        print(f"   📋 部署类型: {result.deployment_type}")
        print(f"   📋 部署状态: {result.deployment_status}")
        
        if result.details:
            print(f"   📋 详细信息:")
            for key, value in result.details.items():
                if value is not None:
                    print(f"      - {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 部署失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_deployment_artifacts(project_name: str):
    """测试部署产物生成"""
    print("\n" + "=" * 60)
    print("🔍 测试 7: 部署产物检查")
    print("=" * 60)
    
    print(f"   📋 项目名称: {project_name}")
    
    project_dir = os.path.join(project_root, "projects", project_name)
    if not os.path.exists(project_dir):
        print(f"   ❌ 项目目录不存在: {project_dir}")
        return
    
    # 检查关键文件
    files_to_check = [
        "config.yaml",
        "status.yaml",
        "project_config.json",
        "requirements.txt",
    ]
    
    for filename in files_to_check:
        filepath = os.path.join(project_dir, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"   ✅ {filename} ({size} bytes)")
        else:
            print(f"   ⚠️ {filename} 不存在")
    
    # 检查 agents 目录
    agents_dir = os.path.join(project_dir, "agents")
    if os.path.exists(agents_dir):
        agent_folders = [d for d in os.listdir(agents_dir) if os.path.isdir(os.path.join(agents_dir, d))]
        print(f"   ✅ agents/ 目录存在，包含 {len(agent_folders)} 个 agent")
        for folder in agent_folders[:3]:  # 只显示前3个
            print(f"      - {folder}")
    else:
        print(f"   ⚠️ agents/ 目录不存在")
    
    # 检查 Dockerfile
    dockerfile_path = os.path.join(project_root, "api", "Dockerfile")
    if os.path.exists(dockerfile_path):
        with open(dockerfile_path, 'r') as f:
            content = f.read()
        
        # 检查关键配置
        checks = [
            ("mkdir -p /app/logs", "日志目录创建"),
            ("chmod 777 /app/logs", "日志目录权限"),
            ("USER app", "非 root 用户"),
            ("PYTHONPATH", "Python 路径"),
        ]
        
        print(f"\n   📋 Dockerfile 检查:")
        for pattern, desc in checks:
            if pattern in content:
                print(f"      ✅ {desc}: 已配置")
            else:
                print(f"      ⚠️ {desc}: 未找到")


def main():
    parser = argparse.ArgumentParser(description='测试 Agent 部署功能')
    parser.add_argument('--agent', type=str, default=None, help='要测试的 Agent 名称')
    parser.add_argument('--project', type=str, default=None, help='要部署的项目名称')
    parser.add_argument('--skip-factory', action='store_true', help='跳过 Agent 工厂测试（需要 AWS 凭证）')
    parser.add_argument('--test-deploy', action='store_true', help='测试 AgentCore 部署')
    parser.add_argument('--no-dry-run', action='store_true', help='实际执行部署（默认为 dry-run）')
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("🚀 Agent 部署功能测试")
    print("=" * 60)
    print(f"📁 项目根目录: {project_root}")
    print(f"🐍 Python 版本: {sys.version}")
    
    # 运行基础测试
    test_logging_permission()
    test_config_loader()
    test_agent_logging_hook()
    
    if not args.skip_factory:
        test_agent_factory(args.agent)
    else:
        print("\n⏭️ 跳过 Agent 工厂测试")
    
    test_with_temp_logs()
    
    # 部署测试
    if args.test_deploy:
        project_name = args.project or args.agent or "business_english_teacher_agent"
        test_deployment_artifacts(project_name)
        test_deployment_service(project_name, dry_run=not args.no_dry_run)
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
