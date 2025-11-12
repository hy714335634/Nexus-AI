#!/usr/bin/env python3
"""
AWS Network Topology Visualizer

专业的AWS网络拓扑分析和可视化智能体，能够收集AWS网络资源信息，分析网络连接关系，
生成可视化的网络拓扑图，并高亮显示网络边界，以满足审计要求。

主要功能:
1. 收集AWS网络资源信息（VPC、子网、路由表、安全组等）
2. 识别各种VPC连接类型（TGW、VPC Peering、PrivateLink等）
3. 识别跨区域和跨账户连接
4. 识别通过CGW、DXGW的连接
5. 识别通过Network Firewall隔离的网络
6. 分析网络连接关系和网络边界
7. 生成可视化的网络拓扑图
8. 高亮显示网络边界
9. 导出网络拓扑图（PNG、JPG、SVG格式）
"""

import os
import json
import argparse
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("aws_network_topology_visualizer")

# 设置遥测
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

class NetworkTopologyVisualizer:
    """AWS网络拓扑可视化工具类，封装主要功能"""
    
    def __init__(self, profile_name: Optional[str] = None, 
                 regions: Optional[List[str]] = None,
                 accounts: Optional[List[Dict[str, str]]] = None,
                 output_dir: str = "./output"):
        """
        初始化网络拓扑可视化工具
        
        Args:
            profile_name: AWS配置文件名称
            regions: 要分析的AWS区域列表
            accounts: 要分析的AWS账户列表，每个账户为包含account_id和role_name的字典
            output_dir: 输出目录路径
        """
        self.profile_name = profile_name
        self.regions = regions or ["us-east-1"]
        self.accounts = accounts or []
        self.output_dir = output_dir
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建智能体
        self.agent = self._create_agent()
        logger.info(f"AWS Network Topology Visualizer initialized with regions: {self.regions}")
    
    def _create_agent(self):
        """创建AWS网络拓扑可视化智能体"""
        agent_params = {
            "env": "production",
            "version": "latest",
            "model_id": "default"
        }
        
        return create_agent_from_prompt_template(
            agent_name="generated_agents_prompts/aws_network_topology_audit/aws_network_topology_visualizer",
            **agent_params
        )
    
    def collect_resources(self, resource_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        收集AWS网络资源信息
        
        Args:
            resource_types: 要收集的资源类型列表，如果为None则收集所有类型
            
        Returns:
            包含收集到的资源信息的字典
        """
        resource_types_str = ", ".join(resource_types) if resource_types else "所有网络资源"
        prompt = f"""
        请收集以下AWS网络资源信息:
        - 区域: {', '.join(self.regions)}
        - 资源类型: {resource_types_str}
        - AWS配置文件: {self.profile_name or '默认'}
        
        {f'- 跨账户收集: {json.dumps(self.accounts)}' if self.accounts else ''}
        
        请返回JSON格式的资源收集结果。
        """
        
        logger.info(f"Collecting AWS resources: {resource_types_str}")
        result = self.agent(prompt)
        return result
    
    def analyze_connections(self, resources: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析网络连接关系
        
        Args:
            resources: 收集到的资源信息
            
        Returns:
            包含连接分析结果的字典
        """
        prompt = f"""
        请分析以下AWS网络资源的连接关系:
        ```
        {json.dumps(resources, indent=2)}
        ```
        
        分析要点:
        1. 识别各种VPC连接类型（TGW、VPC Peering、PrivateLink等）
        2. 识别跨区域连接
        3. 识别跨账户连接
        4. 识别通过CGW、DXGW的连接
        5. 识别通过Network Firewall隔离的网络
        6. 识别网络边界
        
        请返回JSON格式的连接分析结果。
        """
        
        logger.info("Analyzing network connections")
        result = self.agent(prompt)
        return result
    
    def generate_topology_graph(self, connections: Dict[str, Any], 
                               output_format: str = "png",
                               highlight_boundaries: bool = True) -> str:
        """
        生成网络拓扑图
        
        Args:
            connections: 连接分析结果
            output_format: 输出格式（png, jpg, svg）
            highlight_boundaries: 是否高亮显示网络边界
            
        Returns:
            生成的拓扑图文件路径
        """
        prompt = f"""
        请根据以下网络连接分析结果生成网络拓扑图:
        ```
        {json.dumps(connections, indent=2)}
        ```
        
        要求:
        1. 输出格式: {output_format}
        2. {'高亮显示网络边界' if highlight_boundaries else '不需要高亮显示网络边界'}
        3. 使用清晰的图例说明各种连接类型和资源类型
        4. 按区域和账户分组排列资源
        5. 优化节点位置减少线条交叉
        
        请生成拓扑图并返回文件保存路径。
        """
        
        logger.info(f"Generating network topology graph in {output_format} format")
        result = self.agent(prompt)
        return result
    
    def run_full_analysis(self, resource_types: Optional[List[str]] = None,
                         output_format: str = "png",
                         highlight_boundaries: bool = True) -> Dict[str, Any]:
        """
        运行完整的网络拓扑分析流程
        
        Args:
            resource_types: 要收集的资源类型列表
            output_format: 输出格式
            highlight_boundaries: 是否高亮显示网络边界
            
        Returns:
            包含分析结果和拓扑图路径的字典
        """
        prompt = f"""
        请执行AWS网络拓扑的完整分析流程:
        
        1. 收集AWS网络资源信息:
           - 区域: {', '.join(self.regions)}
           - 资源类型: {', '.join(resource_types) if resource_types else '所有网络资源'}
           - AWS配置文件: {self.profile_name or '默认'}
           {f'- 跨账户收集: {json.dumps(self.accounts)}' if self.accounts else ''}
        
        2. 分析网络连接关系:
           - 识别各种VPC连接类型（TGW、VPC Peering、PrivateLink等）
           - 识别跨区域和跨账户连接
           - 识别通过CGW、DXGW的连接
           - 识别通过Network Firewall隔离的网络
           - 识别网络边界
        
        3. 生成网络拓扑图:
           - 输出格式: {output_format}
           - {'高亮显示网络边界' if highlight_boundaries else '不需要高亮显示网络边界'}
           - 使用清晰的图例说明各种连接类型和资源类型
           - 按区域和账户分组排列资源
           - 优化节点位置减少线条交叉
        
        请返回完整的分析结果，包括资源收集摘要、连接分析报告和拓扑图文件路径。
        """
        
        logger.info("Running full network topology analysis")
        result = self.agent(prompt)
        return result


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='AWS Network Topology Visualizer')
    
    parser.add_argument('--profile', type=str, default=None,
                        help='AWS配置文件名称')
    
    parser.add_argument('--regions', type=str, default='us-east-1',
                        help='要分析的AWS区域，多个区域用逗号分隔')
    
    parser.add_argument('--accounts', type=str, default=None,
                        help='要分析的AWS账户，格式为JSON字符串，例如：[{"account_id": "123456789012", "role_name": "CrossAccountRole"}]')
    
    parser.add_argument('--resource-types', type=str, default=None,
                        help='要收集的资源类型，多个类型用逗号分隔，例如：vpc,subnet,security-group')
    
    parser.add_argument('--output-format', type=str, choices=['png', 'jpg', 'svg'], default='png',
                        help='拓扑图输出格式')
    
    parser.add_argument('--output-dir', type=str, default='./output',
                        help='输出目录路径')
    
    parser.add_argument('--no-highlight-boundaries', action='store_true',
                        help='不高亮显示网络边界')
    
    parser.add_argument('--mode', type=str, choices=['full', 'collect', 'analyze', 'visualize'], default='full',
                        help='运行模式')
    
    parser.add_argument('--input-file', type=str, default=None,
                        help='输入文件路径，用于analyze和visualize模式')
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()
    
    # 解析参数
    regions = [region.strip() for region in args.regions.split(',')]
    
    accounts = None
    if args.accounts:
        try:
            accounts = json.loads(args.accounts)
        except json.JSONDecodeError:
            logger.error("Invalid JSON format for accounts parameter")
            return
    
    resource_types = None
    if args.resource_types:
        resource_types = [rt.strip() for rt in args.resource_types.split(',')]
    
    # 创建可视化工具
    visualizer = NetworkTopologyVisualizer(
        profile_name=args.profile,
        regions=regions,
        accounts=accounts,
        output_dir=args.output_dir
    )
    
    # 根据运行模式执行操作
    if args.mode == 'full':
        result = visualizer.run_full_analysis(
            resource_types=resource_types,
            output_format=args.output_format,
            highlight_boundaries=not args.no_highlight_boundaries
        )
        print(json.dumps(result, indent=2))
    
    elif args.mode == 'collect':
        resources = visualizer.collect_resources(resource_types=resource_types)
        
        # 保存收集结果到文件
        output_file = os.path.join(args.output_dir, 'resources.json')
        with open(output_file, 'w') as f:
            json.dump(resources, f, indent=2)
        
        print(f"Resources collected and saved to {output_file}")
    
    elif args.mode == 'analyze':
        if not args.input_file:
            logger.error("Input file is required for analyze mode")
            return
        
        # 从文件加载资源信息
        with open(args.input_file, 'r') as f:
            resources = json.load(f)
        
        connections = visualizer.analyze_connections(resources)
        
        # 保存分析结果到文件
        output_file = os.path.join(args.output_dir, 'connections.json')
        with open(output_file, 'w') as f:
            json.dump(connections, f, indent=2)
        
        print(f"Connection analysis completed and saved to {output_file}")
    
    elif args.mode == 'visualize':
        if not args.input_file:
            logger.error("Input file is required for visualize mode")
            return
        
        # 从文件加载连接分析结果
        with open(args.input_file, 'r') as f:
            connections = json.load(f)
        
        graph_path = visualizer.generate_topology_graph(
            connections=connections,
            output_format=args.output_format,
            highlight_boundaries=not args.no_highlight_boundaries
        )
        
        print(f"Topology graph generated: {graph_path}")


if __name__ == "__main__":
    # 创建 agent 的通用参数
    agent_params = {
        "env": "production",
        "version": "latest", 
        "model_id": "default"
    }

    # 使用 agent_factory 创建 agent
    aws_network_topology_visualizer = create_agent_from_prompt_template(
        agent_name="generated_agents_prompts/aws_network_topology_audit/aws_network_topology_visualizer", 
        **agent_params
    )
    
    print(f"✅ AWS Network Topology Visualizer Agent 创建成功")
    
    # 运行主程序或处理简单的交互式查询
    if len(os.sys.argv) > 1:
        main()
    else:
        print("请输入您的AWS网络拓扑分析请求，输入'exit'退出:")
        while True:
            user_input = input("> ")
            if user_input.lower() == 'exit':
                break
            
            try:
                result = aws_network_topology_visualizer(user_input)
                print(f"📋 Agent 响应:\n{result}")
            except Exception as e:
                print(f"❌ 错误: {e}")