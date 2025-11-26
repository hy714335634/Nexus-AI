#!/usr/bin/env python3
"""
部署 kids_chat_companion 到 Amazon Bedrock AgentCore
"""

import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.services.agent_deployment_service import AgentDeploymentService, AgentDeploymentError


def main():
    project_name = "kids_chat_companion"

    print(f"{'='*60}")
    print(f"🚀 开始部署项目: {project_name}")
    print(f"{'='*60}")

    try:
        service = AgentDeploymentService()

        result = service.deploy_to_agentcore(
            project_name=project_name,
            # 可选参数：
            # agent_name="kids_chat_agent",  # 如果有多个 agent，可以指定
            # region="us-west-2",  # 覆盖默认 region
        )

        print(f"\n{'='*60}")
        print(f"✅ 部署成功!")
        print(f"{'='*60}")
        print(f"📋 部署详情:")

        result_dict = result.to_dict()
        for key, value in result_dict.items():
            print(f"  {key}: {value}")

        print(f"{'='*60}")

    except AgentDeploymentError as e:
        print(f"\n❌ 部署失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 未知错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
