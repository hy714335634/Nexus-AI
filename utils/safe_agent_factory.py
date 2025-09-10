#!/usr/bin/env python3
"""
安全的Agent工厂

提供带验证的Agent创建功能，确保所有依赖都存在
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from utils.agent_factory import create_agent_from_prompt_template
from utils.agent_validation import validate_agent_dependencies, fix_agent_dependencies
from strands import Agent

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_validated_agent(
    agent_name: str,
    env: str = "production",
    version: str = "latest",
    model_id: str = "default",
    enable_logging: bool = False,
    state: Optional[Dict[str, Any]] = None,
    session_manager: Optional[Any] = None,
    auto_fix_dependencies: bool = True,
    **agent_params
) -> Dict[str, Any]:
    """
    创建经过验证的Agent
    
    Args:
        agent_name: Agent名称或相对路径
        env: 环境配置
        version: 版本号
        model_id: 模型ID
        enable_logging: 是否启用日志
        state: 状态数据
        session_manager: 会话管理器
        auto_fix_dependencies: 是否自动修复依赖
        **agent_params: 额外的Agent参数
        
    Returns:
        Dict[str, Any]: 创建结果，包含Agent实例或错误信息
    """
    try:
        logger.info(f"开始创建Agent: {agent_name}")
        
        # 第一步：验证依赖
        logger.info("验证Agent依赖...")
        validation_result = validate_agent_dependencies(agent_name, version)
        
        if not validation_result["valid"]:
            logger.warning(f"Agent依赖验证失败: {agent_name}")
            
            if auto_fix_dependencies:
                logger.info("尝试自动修复依赖...")
                fix_result = fix_agent_dependencies(agent_name, version, auto_fix=True)
                
                if fix_result["success"]:
                    logger.info("依赖修复成功，重新验证...")
                    validation_result = validate_agent_dependencies(agent_name, version)
                    
                    if not validation_result["valid"]:
                        return {
                            "success": False,
                            "error": "依赖修复后仍然验证失败",
                            "validation_result": validation_result,
                            "fix_result": fix_result
                        }
                else:
                    return {
                        "success": False,
                        "error": "依赖修复失败",
                        "validation_result": validation_result,
                        "fix_result": fix_result
                    }
            else:
                return {
                    "success": False,
                    "error": "Agent依赖验证失败，且未启用自动修复",
                    "validation_result": validation_result
                }
        
        # 第二步：创建Agent
        logger.info("依赖验证通过，创建Agent...")
        agent = create_agent_from_prompt_template(
            agent_name=agent_name,
            env=env,
            version=version,
            model_id=model_id,
            enable_logging=enable_logging,
            state=state,
            session_manager=session_manager,
            **agent_params
        )
        
        if agent is None:
            return {
                "success": False,
                "error": "Agent创建失败，create_agent_from_prompt_template返回None"
            }
        
        # 第三步：验证Agent功能
        logger.info("验证Agent基本功能...")
        try:
            # 简单的功能测试
            test_result = agent("Hello, this is a test message.")
            logger.info("Agent功能测试通过")
        except Exception as e:
            logger.warning(f"Agent功能测试失败: {str(e)}")
            # 不阻止Agent创建，只记录警告
        
        logger.info(f"Agent创建成功: {agent.name}")
        
        return {
            "success": True,
            "agent": agent,
            "validation_result": validation_result,
            "message": f"Agent '{agent_name}' 创建成功"
        }
        
    except Exception as e:
        logger.error(f"创建Agent时出现错误: {str(e)}")
        return {
            "success": False,
            "error": f"创建Agent时出现错误: {str(e)}"
        }


def create_agent_with_fallback(
    agent_name: str,
    fallback_agent_name: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    创建Agent，如果失败则使用备用Agent
    
    Args:
        agent_name: 主要Agent名称
        fallback_agent_name: 备用Agent名称
        **kwargs: 其他参数
        
    Returns:
        Dict[str, Any]: 创建结果
    """
    try:
        # 尝试创建主要Agent
        result = create_validated_agent(agent_name, **kwargs)
        
        if result["success"]:
            return result
        
        # 如果主要Agent创建失败且提供了备用Agent
        if fallback_agent_name:
            logger.warning(f"主要Agent '{agent_name}' 创建失败，尝试备用Agent '{fallback_agent_name}'")
            
            fallback_result = create_validated_agent(fallback_agent_name, **kwargs)
            
            if fallback_result["success"]:
                fallback_result["message"] = f"主要Agent创建失败，使用备用Agent '{fallback_agent_name}'"
                fallback_result["primary_agent_error"] = result["error"]
                return fallback_result
        
        # 如果都失败了
        return result
        
    except Exception as e:
        logger.error(f"创建Agent时出现错误: {str(e)}")
        return {
            "success": False,
            "error": f"创建Agent时出现错误: {str(e)}"
        }


def batch_create_agents(
    agent_configs: List[Dict[str, Any]],
    continue_on_error: bool = True
) -> Dict[str, Any]:
    """
    批量创建Agent
    
    Args:
        agent_configs: Agent配置列表，每个配置包含agent_name和其他参数
        continue_on_error: 是否在遇到错误时继续创建其他Agent
        
    Returns:
        Dict[str, Any]: 批量创建结果
    """
    try:
        results = {
            "total_agents": len(agent_configs),
            "successful_agents": 0,
            "failed_agents": 0,
            "agent_results": {},
            "created_agents": {}
        }
        
        for config in agent_configs:
            agent_name = config.get("agent_name")
            if not agent_name:
                logger.error("Agent配置缺少agent_name")
                continue
            
            logger.info(f"创建Agent: {agent_name}")
            
            # 提取agent_name，其余作为参数
            agent_params = {k: v for k, v in config.items() if k != "agent_name"}
            
            result = create_validated_agent(agent_name, **agent_params)
            
            results["agent_results"][agent_name] = result
            
            if result["success"]:
                results["successful_agents"] += 1
                results["created_agents"][agent_name] = result["agent"]
                logger.info(f"Agent '{agent_name}' 创建成功")
            else:
                results["failed_agents"] += 1
                logger.error(f"Agent '{agent_name}' 创建失败: {result['error']}")
                
                if not continue_on_error:
                    logger.error("遇到错误，停止批量创建")
                    break
        
        return results
        
    except Exception as e:
        logger.error(f"批量创建Agent时出现错误: {str(e)}")
        return {
            "success": False,
            "error": f"批量创建Agent时出现错误: {str(e)}"
        }


def get_agent_health_status(agent: Agent) -> Dict[str, Any]:
    """
    获取Agent的健康状态
    
    Args:
        agent: Agent实例
        
    Returns:
        Dict[str, Any]: 健康状态信息
    """
    try:
        health_status = {
            "agent_name": agent.name,
            "model_info": {
                "model_id": getattr(agent.model, 'model_id', 'Unknown'),
                "max_tokens": getattr(agent.model, 'max_tokens', 'Unknown'),
                "temperature": getattr(agent.model, 'temperature', 'Unknown')
            },
            "tools_count": len(agent.tools) if hasattr(agent, 'tools') else 0,
            "system_prompt_length": len(agent.system_prompt) if hasattr(agent, 'system_prompt') else 0,
            "status": "healthy"
        }
        
        # 简单的功能测试
        try:
            test_response = agent("Health check test")
            health_status["last_test_success"] = True
            health_status["last_test_response_length"] = len(str(test_response))
        except Exception as e:
            health_status["last_test_success"] = False
            health_status["last_test_error"] = str(e)
            health_status["status"] = "unhealthy"
        
        return health_status
        
    except Exception as e:
        return {
            "agent_name": getattr(agent, 'name', 'Unknown'),
            "status": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='安全Agent工厂测试')
    parser.add_argument('-a', '--agent', type=str, required=True, help='要创建的Agent名称')
    parser.add_argument('-e', '--env', type=str, default='production', help='环境配置')
    parser.add_argument('-v', '--version', type=str, default='latest', help='版本号')
    parser.add_argument('--no-auto-fix', action='store_true', help='禁用自动修复依赖')
    parser.add_argument('--test', type=str, help='测试输入')
    
    args = parser.parse_args()
    
    print(f"创建Agent: {args.agent}")
    
    result = create_validated_agent(
        agent_name=args.agent,
        env=args.env,
        version=args.version,
        auto_fix_dependencies=not args.no_auto_fix
    )
    
    if result["success"]:
        print(f"✅ Agent创建成功: {result['agent'].name}")
        
        if args.test:
            print(f"🧪 测试Agent功能...")
            try:
                response = result["agent"](args.test)
                print(f"📋 Agent响应:\n{response}")
            except Exception as e:
                print(f"❌ 测试失败: {e}")
        
        # 显示健康状态
        health = get_agent_health_status(result["agent"])
        print(f"🏥 Agent健康状态: {json.dumps(health, ensure_ascii=False, indent=2)}")
    
    else:
        print(f"❌ Agent创建失败: {result['error']}")
        if "validation_result" in result:
            print(f"📋 验证结果: {json.dumps(result['validation_result'], ensure_ascii=False, indent=2)}")