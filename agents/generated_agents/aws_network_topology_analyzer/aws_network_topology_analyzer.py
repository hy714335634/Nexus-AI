#!/usr/bin/env python3
"""
AWS Network Topology Analyzer Agent

这个智能体专门用于分析AWS账号中的网络拓扑结构，将资源关系存储在Neo4j图数据库中，
并通过自然语言交互帮助用户理解网络结构、诊断问题和进行安全分析。

主要功能：
1. 扫描AWS账号中的网络资源
2. 构建网络拓扑关系图到Neo4j图数据库
3. 支持自然语言交互回答网络拓扑问题
4. 辅助用户进行网络和安全分析

作者: Agent Build Workflow
版本: 1.0.0
日期: 2025-11-11
"""

import os
import json
import logging
import argparse
from typing import Dict, List, Optional, Any, Union
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 设置遥测
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 默认Neo4j连接参数
DEFAULT_NEO4J_URI = "neo4j://localhost:7687"
DEFAULT_NEO4J_USER = "neo4j"
DEFAULT_NEO4J_PASSWORD = "neo4jneo4j"
DEFAULT_NEO4J_DATABASE = "neo4j"

class AWSNetworkTopologyAnalyzer:
    """
    AWS网络拓扑分析器类，提供便捷的方法来使用Agent功能
    """
    
    def __init__(self, 
                 env: str = "production",
                 model_id: str = "default",
                 version: str = "latest"):
        """
        初始化AWS网络拓扑分析器
        
        Args:
            env: 环境配置，可选值: production, development, testing
            model_id: 使用的模型ID
            version: Agent版本
        """
        self.agent_params = {
            "env": env,
            "version": version,
            "model_id": model_id,
            "enable_logging": True
        }
        
        self.agent_name = "generated_agents_prompts/aws_network_topology_analyzer/aws_network_topology_analyzer"
        self.agent = self._create_agent()
        logger.info(f"AWS Network Topology Analyzer Agent initialized with {env} environment")
        
    def _create_agent(self):
        """创建Agent实例"""
        try:
            agent = create_agent_from_prompt_template(
                agent_name=self.agent_name,
                **self.agent_params
            )
            return agent
        except Exception as e:
            logger.error(f"Failed to create agent: {str(e)}")
            raise
    
    def scan_resources(self, 
                       profile_name: str, 
                       region: str, 
                       resource_types: Optional[List[str]] = None,
                       neo4j_uri: str = DEFAULT_NEO4J_URI,
                       neo4j_user: str = DEFAULT_NEO4J_USER,
                       neo4j_password: str = DEFAULT_NEO4J_PASSWORD) -> str:
        """
        扫描AWS资源并存储到Neo4j数据库
        
        Args:
            profile_name: AWS配置文件名称
            region: AWS区域
            resource_types: 要扫描的资源类型列表，如果为None则扫描所有网络资源
            neo4j_uri: Neo4j数据库URI
            neo4j_user: Neo4j用户名
            neo4j_password: Neo4j密码
            
        Returns:
            str: Agent的响应
        """
        if resource_types is None:
            resource_types = ["all_network"]
            
        prompt = f"""
        请扫描AWS账号中的网络资源并存储到Neo4j数据库中。

        AWS配置:
        - Profile: {profile_name}
        - Region: {region}
        - 资源类型: {', '.join(resource_types)}

        Neo4j配置:
        - URI: {neo4j_uri}
        - 用户名: {neo4j_user}
        - 密码: {neo4j_password}

        请执行以下操作:
        1. 验证AWS Profile是否有效
        2. 连接Neo4j数据库
        3. 扫描指定的AWS资源
        4. 将资源存储到Neo4j数据库中
        5. 构建资源间的关系
        6. 提供扫描结果摘要
        """
        
        try:
            response = self.agent(prompt)
            return response
        except Exception as e:
            logger.error(f"Error during resource scanning: {str(e)}")
            raise
    
    def query_topology(self, 
                      query: str,
                      profile_name: Optional[str] = None,
                      neo4j_uri: str = DEFAULT_NEO4J_URI,
                      neo4j_user: str = DEFAULT_NEO4J_USER,
                      neo4j_password: str = DEFAULT_NEO4J_PASSWORD) -> str:
        """
        通过自然语言查询网络拓扑
        
        Args:
            query: 自然语言查询
            profile_name: AWS配置文件名称（可选）
            neo4j_uri: Neo4j数据库URI
            neo4j_user: Neo4j用户名
            neo4j_password: Neo4j密码
            
        Returns:
            str: Agent的响应
        """
        prompt = f"""
        请回答以下关于AWS网络拓扑的问题:

        问题: {query}

        Neo4j配置:
        - URI: {neo4j_uri}
        - 用户名: {neo4j_user}
        - 密码: {neo4j_password}
        """
        
        if profile_name:
            prompt += f"\nAWS Profile: {profile_name}"
            
        try:
            response = self.agent(prompt)
            return response
        except Exception as e:
            logger.error(f"Error during topology query: {str(e)}")
            raise
    
    def analyze_path(self,
                    source: str,
                    destination: str,
                    profile_name: Optional[str] = None,
                    neo4j_uri: str = DEFAULT_NEO4J_URI,
                    neo4j_user: str = DEFAULT_NEO4J_USER,
                    neo4j_password: str = DEFAULT_NEO4J_PASSWORD) -> str:
        """
        分析两个资源之间的网络路径
        
        Args:
            source: 源资源ID或名称
            destination: 目标资源ID或名称
            profile_name: AWS配置文件名称（可选）
            neo4j_uri: Neo4j数据库URI
            neo4j_user: Neo4j用户名
            neo4j_password: Neo4j密码
            
        Returns:
            str: Agent的响应
        """
        prompt = f"""
        请分析从源资源到目标资源的网络路径:

        源资源: {source}
        目标资源: {destination}

        Neo4j配置:
        - URI: {neo4j_uri}
        - 用户名: {neo4j_user}
        - 密码: {neo4j_password}
        
        请提供:
        1. 完整的网络路径
        2. 经过的网络组件
        3. 潜在的网络限制或安全规则
        4. 路径可达性分析
        """
        
        if profile_name:
            prompt += f"\nAWS Profile: {profile_name}"
            
        try:
            response = self.agent(prompt)
            return response
        except Exception as e:
            logger.error(f"Error during path analysis: {str(e)}")
            raise
    
    def visualize_topology(self,
                          scope: str = "all",
                          resource_type: Optional[str] = None,
                          resource_id: Optional[str] = None,
                          profile_name: Optional[str] = None,
                          neo4j_uri: str = DEFAULT_NEO4J_URI,
                          neo4j_user: str = DEFAULT_NEO4J_USER,
                          neo4j_password: str = DEFAULT_NEO4J_PASSWORD) -> str:
        """
        可视化网络拓扑
        
        Args:
            scope: 可视化范围，可选值: all, vpc, subnet
            resource_type: 资源类型过滤器（可选）
            resource_id: 资源ID过滤器（可选）
            profile_name: AWS配置文件名称（可选）
            neo4j_uri: Neo4j数据库URI
            neo4j_user: Neo4j用户名
            neo4j_password: Neo4j密码
            
        Returns:
            str: Agent的响应
        """
        prompt = f"""
        请可视化AWS网络拓扑:

        可视化范围: {scope}
        """
        
        if resource_type:
            prompt += f"\n资源类型: {resource_type}"
            
        if resource_id:
            prompt += f"\n资源ID: {resource_id}"
            
        prompt += f"""
        
        Neo4j配置:
        - URI: {neo4j_uri}
        - 用户名: {neo4j_user}
        - 密码: {neo4j_password}
        
        请提供:
        1. 网络拓扑的可视化描述
        2. 资源间的关系
        3. 关键网络组件的说明
        """
        
        if profile_name:
            prompt += f"\nAWS Profile: {profile_name}"
            
        try:
            response = self.agent(prompt)
            return response
        except Exception as e:
            logger.error(f"Error during topology visualization: {str(e)}")
            raise
    
    def analyze_security(self,
                        resource_id: Optional[str] = None,
                        vpc_id: Optional[str] = None,
                        profile_name: Optional[str] = None,
                        neo4j_uri: str = DEFAULT_NEO4J_URI,
                        neo4j_user: str = DEFAULT_NEO4J_USER,
                        neo4j_password: str = DEFAULT_NEO4J_PASSWORD) -> str:
        """
        分析网络安全配置
        
        Args:
            resource_id: 资源ID（可选）
            vpc_id: VPC ID（可选）
            profile_name: AWS配置文件名称（可选）
            neo4j_uri: Neo4j数据库URI
            neo4j_user: Neo4j用户名
            neo4j_password: Neo4j密码
            
        Returns:
            str: Agent的响应
        """
        prompt = f"""
        请分析AWS网络的安全配置:
        """
        
        if resource_id:
            prompt += f"\n资源ID: {resource_id}"
            
        if vpc_id:
            prompt += f"\nVPC ID: {vpc_id}"
            
        prompt += f"""
        
        Neo4j配置:
        - URI: {neo4j_uri}
        - 用户名: {neo4j_user}
        - 密码: {neo4j_password}
        
        请提供:
        1. 安全组规则分析
        2. 网络ACL配置评估
        3. 公共可访问资源识别
        4. 潜在的安全风险
        5. 安全最佳实践建议
        """
        
        if profile_name:
            prompt += f"\nAWS Profile: {profile_name}"
            
        try:
            response = self.agent(prompt)
            return response
        except Exception as e:
            logger.error(f"Error during security analysis: {str(e)}")
            raise
    
    def run_custom_query(self, 
                        query: str,
                        neo4j_uri: str = DEFAULT_NEO4J_URI,
                        neo4j_user: str = DEFAULT_NEO4J_USER,
                        neo4j_password: str = DEFAULT_NEO4J_PASSWORD) -> str:
        """
        执行自定义查询
        
        Args:
            query: 自然语言查询或Cypher查询
            neo4j_uri: Neo4j数据库URI
            neo4j_user: Neo4j用户名
            neo4j_password: Neo4j密码
            
        Returns:
            str: Agent的响应
        """
        prompt = f"""
        请执行以下查询:

        查询: {query}

        Neo4j配置:
        - URI: {neo4j_uri}
        - 用户名: {neo4j_user}
        - 密码: {neo4j_password}
        
        如果这是一个自然语言查询，请先将其转换为Cypher查询，然后执行。
        如果这已经是一个Cypher查询，请直接执行。
        
        请提供:
        1. 执行的查询（如果进行了转换）
        2. 查询结果
        3. 结果的解释和分析
        """
        
        try:
            response = self.agent(prompt)
            return response
        except Exception as e:
            logger.error(f"Error during custom query: {str(e)}")
            raise

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"
}

# 使用 agent_factory 创建 agent
aws_network_topology_analyzer = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/aws_network_topology_analyzer/aws_network_topology_analyzer", 
    **agent_params
)

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='AWS Network Topology Analyzer')
    
    # 基本配置
    parser.add_argument('--profile', type=str, help='AWS配置文件名称')
    parser.add_argument('--region', type=str, help='AWS区域')
    parser.add_argument('--neo4j-uri', type=str, default=DEFAULT_NEO4J_URI, help='Neo4j数据库URI')
    parser.add_argument('--neo4j-user', type=str, default=DEFAULT_NEO4J_USER, help='Neo4j用户名')
    parser.add_argument('--neo4j-password', type=str, default=DEFAULT_NEO4J_PASSWORD, help='Neo4j密码')
    parser.add_argument('--neo4j-database', type=str, default=DEFAULT_NEO4J_DATABASE, help='Neo4j数据库名称')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 扫描资源子命令
    scan_parser = subparsers.add_parser('scan', help='扫描AWS资源')
    scan_parser.add_argument('--resource-types', type=str, nargs='+', 
                           default=['all_network', 'all_compute'], 
                           help='要扫描的资源类型列表，例如vpc subnet route_table')
    
    # 查询拓扑子命令
    query_parser = subparsers.add_parser('query', help='查询网络拓扑')
    query_parser.add_argument('--question', type=str, required=True, help='自然语言查询问题')
    
    # 分析路径子命令
    path_parser = subparsers.add_parser('path', help='分析网络路径')
    path_parser.add_argument('--source', type=str, required=True, help='源资源ID或名称')
    path_parser.add_argument('--destination', type=str, required=True, help='目标资源ID或名称')
    
    # 可视化拓扑子命令
    viz_parser = subparsers.add_parser('visualize', help='可视化网络拓扑')
    viz_parser.add_argument('--scope', type=str, default='all', choices=['all', 'vpc', 'subnet'], help='可视化范围')
    viz_parser.add_argument('--resource-type', type=str, help='资源类型过滤器')
    viz_parser.add_argument('--resource-id', type=str, help='资源ID过滤器')
    
    # 安全分析子命令
    security_parser = subparsers.add_parser('security', help='分析网络安全配置')
    security_parser.add_argument('--resource-id', type=str, help='资源ID')
    security_parser.add_argument('--vpc-id', type=str, help='VPC ID')
    
    # 自定义查询子命令
    custom_parser = subparsers.add_parser('custom', help='执行自定义查询')
    custom_parser.add_argument('--query', type=str, required=True, help='自然语言查询或Cypher查询')
    
    # 交互模式子命令
    subparsers.add_parser('interactive', help='进入交互模式')
    
    # 解析参数
    args = parser.parse_args()
    
    # 创建分析器实例
    analyzer = AWSNetworkTopologyAnalyzer()
    
    # 处理子命令
    if args.command == 'scan':
        if not args.profile or not args.region:
            parser.error("scan命令需要--profile和--region参数")
        
        print(f"正在扫描AWS资源...\nProfile: {args.profile}\nRegion: {args.region}\n资源类型: {args.resource_types}")
        response = analyzer.scan_resources(
            profile_name=args.profile,
            region=args.region,
            resource_types=args.resource_types,
            neo4j_uri=args.neo4j_uri,
            neo4j_user=args.neo4j_user,
            neo4j_password=args.neo4j_password
        )
        print("\n扫描结果:")
        print(response)
        
    elif args.command == 'query':
        print(f"正在查询: {args.question}")
        response = analyzer.query_topology(
            query=args.question,
            profile_name=args.profile,
            neo4j_uri=args.neo4j_uri,
            neo4j_user=args.neo4j_user,
            neo4j_password=args.neo4j_password
        )
        print("\n查询结果:")
        print(response)
        
    elif args.command == 'path':
        print(f"正在分析从 {args.source} 到 {args.destination} 的路径...")
        response = analyzer.analyze_path(
            source=args.source,
            destination=args.destination,
            profile_name=args.profile,
            neo4j_uri=args.neo4j_uri,
            neo4j_user=args.neo4j_user,
            neo4j_password=args.neo4j_password
        )
        print("\n路径分析结果:")
        print(response)
        
    elif args.command == 'visualize':
        scope_desc = "所有资源" if args.scope == 'all' else f"{args.scope}资源"
        print(f"正在可视化{scope_desc}的网络拓扑...")
        response = analyzer.visualize_topology(
            scope=args.scope,
            resource_type=args.resource_type,
            resource_id=args.resource_id,
            profile_name=args.profile,
            neo4j_uri=args.neo4j_uri,
            neo4j_user=args.neo4j_user,
            neo4j_password=args.neo4j_password
        )
        print("\n可视化结果:")
        print(response)
        
    elif args.command == 'security':
        print("正在分析网络安全配置...")
        response = analyzer.analyze_security(
            resource_id=args.resource_id,
            vpc_id=args.vpc_id,
            profile_name=args.profile,
            neo4j_uri=args.neo4j_uri,
            neo4j_user=args.neo4j_user,
            neo4j_password=args.neo4j_password
        )
        print("\n安全分析结果:")
        print(response)
        
    elif args.command == 'custom':
        print(f"正在执行自定义查询: {args.query}")
        response = analyzer.run_custom_query(
            query=args.query,
            neo4j_uri=args.neo4j_uri,
            neo4j_user=args.neo4j_user,
            neo4j_password=args.neo4j_password
        )
        print("\n查询结果:")
        print(response)
        
    elif args.command == 'interactive':
        print("进入交互模式. 输入 'exit' 或 'quit' 退出.")
        print("示例命令:")
        print("  scan --profile default --region us-east-1")
        print("  query \"列出所有VPC和它们的子网\"")
        print("  path --source vpc-123 --destination subnet-456")
        print("  visualize --scope vpc --resource-id vpc-123")
        print("  security --vpc-id vpc-123")
        print("  custom \"MATCH (n:VPC) RETURN n.resource_id, n.cidr_block\"")
        print("  exit")
        
        while True:
            try:
                user_input = input("\n> ")
                if user_input.lower() in ['exit', 'quit']:
                    break
                
                # 简单的命令解析
                if user_input.startswith('scan '):
                    # 提取参数
                    cmd_args = user_input.split(' ')
                    profile_idx = cmd_args.index('--profile') if '--profile' in cmd_args else -1
                    region_idx = cmd_args.index('--region') if '--region' in cmd_args else -1
                    
                    if profile_idx == -1 or region_idx == -1:
                        print("错误: scan命令需要--profile和--region参数")
                        continue
                    
                    profile = cmd_args[profile_idx + 1]
                    region = cmd_args[region_idx + 1]
                    
                    # 提取资源类型
                    resource_types = ['all_network']
                    if '--resource-types' in cmd_args:
                        rt_idx = cmd_args.index('--resource-types')
                        rt_end = next((i for i, arg in enumerate(cmd_args[rt_idx+1:], rt_idx+1) if arg.startswith('--')), len(cmd_args))
                        resource_types = cmd_args[rt_idx+1:rt_end]
                    
                    print(f"正在扫描AWS资源...\nProfile: {profile}\nRegion: {region}\n资源类型: {resource_types}")
                    response = analyzer.scan_resources(
                        profile_name=profile,
                        region=region,
                        resource_types=resource_types,
                        neo4j_uri=args.neo4j_uri,
                        neo4j_user=args.neo4j_user,
                        neo4j_password=args.neo4j_password
                    )
                    print("\n扫描结果:")
                    print(response)
                    
                elif user_input.startswith('query '):
                    question = user_input[6:].strip()
                    if question.startswith('"') and question.endswith('"'):
                        question = question[1:-1]
                    
                    print(f"正在查询: {question}")
                    response = analyzer.query_topology(
                        query=question,
                        profile_name=args.profile,
                        neo4j_uri=args.neo4j_uri,
                        neo4j_user=args.neo4j_user,
                        neo4j_password=args.neo4j_password
                    )
                    print("\n查询结果:")
                    print(response)
                    
                elif user_input.startswith('path '):
                    # 提取参数
                    cmd_args = user_input.split(' ')
                    source_idx = cmd_args.index('--source') if '--source' in cmd_args else -1
                    dest_idx = cmd_args.index('--destination') if '--destination' in cmd_args else -1
                    
                    if source_idx == -1 or dest_idx == -1:
                        print("错误: path命令需要--source和--destination参数")
                        continue
                    
                    source = cmd_args[source_idx + 1]
                    destination = cmd_args[dest_idx + 1]
                    
                    print(f"正在分析从 {source} 到 {destination} 的路径...")
                    response = analyzer.analyze_path(
                        source=source,
                        destination=destination,
                        profile_name=args.profile,
                        neo4j_uri=args.neo4j_uri,
                        neo4j_user=args.neo4j_user,
                        neo4j_password=args.neo4j_password
                    )
                    print("\n路径分析结果:")
                    print(response)
                    
                elif user_input.startswith('visualize'):
                    # 提取参数
                    cmd_args = user_input.split(' ')
                    scope = 'all'
                    resource_type = None
                    resource_id = None
                    
                    if '--scope' in cmd_args:
                        scope_idx = cmd_args.index('--scope')
                        scope = cmd_args[scope_idx + 1]
                    
                    if '--resource-type' in cmd_args:
                        rt_idx = cmd_args.index('--resource-type')
                        resource_type = cmd_args[rt_idx + 1]
                    
                    if '--resource-id' in cmd_args:
                        rid_idx = cmd_args.index('--resource-id')
                        resource_id = cmd_args[rid_idx + 1]
                    
                    scope_desc = "所有资源" if scope == 'all' else f"{scope}资源"
                    print(f"正在可视化{scope_desc}的网络拓扑...")
                    response = analyzer.visualize_topology(
                        scope=scope,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        profile_name=args.profile,
                        neo4j_uri=args.neo4j_uri,
                        neo4j_user=args.neo4j_user,
                        neo4j_password=args.neo4j_password
                    )
                    print("\n可视化结果:")
                    print(response)
                    
                elif user_input.startswith('security'):
                    # 提取参数
                    cmd_args = user_input.split(' ')
                    resource_id = None
                    vpc_id = None
                    
                    if '--resource-id' in cmd_args:
                        rid_idx = cmd_args.index('--resource-id')
                        resource_id = cmd_args[rid_idx + 1]
                    
                    if '--vpc-id' in cmd_args:
                        vid_idx = cmd_args.index('--vpc-id')
                        vpc_id = cmd_args[vid_idx + 1]
                    
                    print("正在分析网络安全配置...")
                    response = analyzer.analyze_security(
                        resource_id=resource_id,
                        vpc_id=vpc_id,
                        profile_name=args.profile,
                        neo4j_uri=args.neo4j_uri,
                        neo4j_user=args.neo4j_user,
                        neo4j_password=args.neo4j_password
                    )
                    print("\n安全分析结果:")
                    print(response)
                    
                elif user_input.startswith('custom '):
                    query = user_input[7:].strip()
                    if query.startswith('"') and query.endswith('"'):
                        query = query[1:-1]
                    
                    print(f"正在执行自定义查询: {query}")
                    response = analyzer.run_custom_query(
                        query=query,
                        neo4j_uri=args.neo4j_uri,
                        neo4j_user=args.neo4j_user,
                        neo4j_password=args.neo4j_password
                    )
                    print("\n查询结果:")
                    print(response)
                    
                else:
                    print("未知命令。可用命令: scan, query, path, visualize, security, custom, exit")
                    
            except Exception as e:
                print(f"错误: {str(e)}")
        
        print("退出交互模式")
        
    else:
        # 如果没有提供子命令，显示帮助信息
        parser.print_help()