"""
AWS Sales Proposal Generator - Professional Sales Proposal Generation Module

This module provides functionality for generating professional sales proposals
based on AWS pricing and configuration recommendations.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from strands import tool

# Import pricing and recommendation tools
from tools.generated_tools.aws_pricing_assistant.aws_pricing_api import calculate_aws_cost
from tools.generated_tools.aws_pricing_assistant.aws_recommendation import generate_aws_solution

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AWS Region display names
AWS_REGION_NAMES = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "ap-east-1": "Asia Pacific (Hong Kong)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "ap-northeast-2": "Asia Pacific (Seoul)",
    "ap-northeast-3": "Asia Pacific (Osaka)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "ap-southeast-3": "Asia Pacific (Jakarta)",
    "eu-central-1": "Europe (Frankfurt)",
    "eu-west-1": "Europe (Ireland)",
    "eu-west-2": "Europe (London)",
    "eu-west-3": "Europe (Paris)",
    "eu-north-1": "Europe (Stockholm)",
    "eu-south-1": "Europe (Milan)",
    "sa-east-1": "South America (São Paulo)",
    "ca-central-1": "Canada (Central)",
    "me-south-1": "Middle East (Bahrain)",
    "af-south-1": "Africa (Cape Town)",
    "cn-north-1": "China (Beijing)",
    "cn-northwest-1": "China (Ningxia)"
}

@tool
def generate_sales_proposal(
    customer_name: str,
    requirements: str,
    region: str = "us-east-1",
    is_production: bool = True,
    proposal_type: str = "standard",
    contact_info: Optional[Dict[str, str]] = None
) -> str:
    """
    Generate a professional AWS sales proposal based on customer requirements.
    
    Args:
        customer_name: Name of the customer or company
        requirements: Description of customer requirements in natural language
        region: AWS region code (default: us-east-1)
        is_production: Whether this is for a production environment (default: True)
        proposal_type: Type of proposal (standard, detailed, executive) (default: standard)
        contact_info: Optional contact information dictionary
    
    Returns:
        JSON string with a structured sales proposal
    """
    try:
        # Generate AWS solution based on requirements
        solution_json = generate_aws_solution(requirements, region, is_production)
        solution = json.loads(solution_json)
        
        # Check for errors in solution generation
        if "error" in solution:
            return json.dumps({
                "error": solution["error"],
                "proposal_status": "failed"
            })
        
        # Create proposal structure
        proposal = {
            "proposal_info": {
                "title": f"AWS 云服务解决方案报价 - {customer_name}",
                "customer_name": customer_name,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "region": region,
                "region_display_name": AWS_REGION_NAMES.get(region, region),
                "environment_type": "生产环境" if is_production else "开发/测试环境",
                "proposal_type": proposal_type
            },
            "executive_summary": _generate_executive_summary(customer_name, requirements, solution),
            "solution_overview": _generate_solution_overview(solution),
            "technical_specifications": _generate_technical_specifications(solution),
            "pricing_details": _generate_pricing_details(solution),
            "implementation_timeline": _generate_implementation_timeline(solution),
            "terms_and_conditions": _generate_terms_and_conditions(),
            "next_steps": _generate_next_steps()
        }
        
        # Add contact information if provided
        if contact_info:
            proposal["proposal_info"]["contact_info"] = contact_info
        
        return json.dumps(proposal, ensure_ascii=False, indent=2)
    
    except Exception as e:
        logger.error(f"Error generating sales proposal: {str(e)}")
        return json.dumps({
            "error": f"Error generating sales proposal: {str(e)}",
            "proposal_status": "failed"
        })

def _generate_executive_summary(customer_name: str, requirements: str, solution: Dict[str, Any]) -> Dict[str, Any]:
    """Generate executive summary section of the proposal."""
    # Extract key components from solution
    components = []
    for component_type, component_info in solution.get("components", {}).items():
        if component_info.get("selected"):
            components.append(component_type.upper())
    
    components_text = "、".join(components) if components else "AWS 云服务"
    
    # Get total monthly cost
    total_cost = solution.get("cost_summary", {}).get("total_monthly_cost", 0)
    cost_text = f"预估每月成本约为 {total_cost:.2f} 美元" if total_cost else "详细价格请参见报价明细"
    
    return {
        "summary": f"本方案为 {customer_name} 提供基于 {components_text} 的全面云解决方案，满足您的业务需求。{cost_text}。AWS 提供高可用性、可扩展性和安全性，帮助您降低总体拥有成本，提高业务灵活性。",
        "key_benefits": [
            "高可用性：AWS 全球基础设施提供 99.99% 的服务可用性",
            "可扩展性：根据业务需求自动扩展资源",
            "安全性：符合行业标准的安全措施和合规认证",
            "成本优化：按使用量付费，无需前期投资",
            "全球覆盖：利用 AWS 全球数据中心网络"
        ],
        "customer_challenges": _extract_customer_challenges(requirements),
        "proposed_solution_highlights": _extract_solution_highlights(solution)
    }

def _extract_customer_challenges(requirements: str) -> List[str]:
    """Extract customer challenges from requirements."""
    challenges = []
    
    # Look for common challenge indicators in requirements
    if any(term in requirements.lower() for term in ["scale", "scaling", "growth", "expand", "扩展", "增长"]):
        challenges.append("需要可扩展的基础设施以支持业务增长")
    
    if any(term in requirements.lower() for term in ["cost", "budget", "expensive", "save", "saving", "成本", "预算", "节省"]):
        challenges.append("需要优化 IT 成本并提高投资回报率")
    
    if any(term in requirements.lower() for term in ["performance", "slow", "latency", "speed", "性能", "延迟", "速度"]):
        challenges.append("现有系统性能不足，无法满足业务需求")
    
    if any(term in requirements.lower() for term in ["security", "compliance", "protect", "安全", "合规", "保护"]):
        challenges.append("需要提高系统安全性和合规性")
    
    if any(term in requirements.lower() for term in ["availability", "downtime", "reliable", "可用性", "宕机", "可靠"]):
        challenges.append("需要提高系统可用性，减少宕机时间")
    
    if any(term in requirements.lower() for term in ["manage", "maintenance", "operate", "管理", "维护", "运营"]):
        challenges.append("IT 运维负担重，需要简化管理")
    
    # Add default challenge if none detected
    if not challenges:
        challenges = [
            "需要可靠、安全且具有成本效益的云基础设施",
            "寻求能够支持业务增长的可扩展解决方案",
            "需要简化 IT 运维并提高资源利用率"
        ]
    
    return challenges

def _extract_solution_highlights(solution: Dict[str, Any]) -> List[str]:
    """Extract solution highlights based on recommended components."""
    highlights = []
    components = solution.get("components", {})
    
    if "ec2" in components:
        highlights.append("高性能计算资源，满足应用处理需求")
    
    if "rds" in components:
        highlights.append("全托管数据库服务，减少管理负担")
    
    if "elasticache" in components:
        highlights.append("内存缓存服务，提高应用响应速度")
    
    if "s3" in components:
        highlights.append("可靠的对象存储，满足数据存储需求")
    
    if "loadbalancer" in components:
        highlights.append("负载均衡服务，确保应用高可用性")
    
    if "opensearch" in components:
        highlights.append("搜索和分析服务，提供实时数据洞察")
    
    # Add architecture recommendations
    for recommendation in solution.get("architecture_recommendations", [])[:2]:
        highlights.append(recommendation)
    
    # Add default highlights if none detected
    if not highlights:
        highlights = [
            "基于 AWS 的全面云解决方案",
            "高可用性和可扩展性架构设计",
            "符合行业最佳实践的安全配置"
        ]
    
    return highlights

def _generate_solution_overview(solution: Dict[str, Any]) -> Dict[str, Any]:
    """Generate solution overview section of the proposal."""
    # Extract architecture diagram description
    architecture_description = "该解决方案基于 AWS 云平台构建，"
    components = solution.get("components", {})
    
    if "ec2" in components and "loadbalancer" in components:
        architecture_description += "采用负载均衡器将流量分发到多个 EC2 实例，"
    elif "ec2" in components:
        architecture_description += "使用 EC2 实例作为计算资源，"
    
    if "rds" in components:
        architecture_description += "使用 RDS 托管数据库服务存储关键数据，"
    
    if "elasticache" in components:
        architecture_description += "通过 ElastiCache 提供高性能缓存层，"
    
    if "s3" in components:
        architecture_description += "利用 S3 对象存储服务存储静态资源，"
    
    if "opensearch" in components:
        architecture_description += "集成 OpenSearch 服务实现高效搜索和日志分析，"
    
    architecture_description += "构成一个高可用、可扩展且安全的云架构。"
    
    # Generate component descriptions
    component_descriptions = []
    for component_type, component_info in components.items():
        if component_info.get("selected"):
            selected = component_info["selected"]
            
            if component_type == "ec2":
                component_descriptions.append({
                    "name": "Amazon EC2",
                    "type": "计算服务",
                    "description": f"使用 {selected.get('instance_type')} 实例类型，提供可靠的计算资源。" + 
                                  f"该实例类型具有 {selected.get('vcpu')} 个 vCPU 和 {selected.get('memory_gib')} GB 内存，" +
                                  f"适合{selected.get('use_case')}。"
                })
            
            elif component_type == "ebs":
                component_descriptions.append({
                    "name": "Amazon EBS",
                    "type": "块存储服务",
                    "description": f"使用 {selected.get('volume_type')} 卷类型，提供 {selected.get('size_gb')} GB 的持久存储。" +
                                  f"该卷类型适合{selected.get('use_case')}。"
                })
            
            elif component_type == "s3":
                component_descriptions.append({
                    "name": "Amazon S3",
                    "type": "对象存储服务",
                    "description": f"使用 {selected.get('storage_class')} 存储类别，提供高耐久性的对象存储。" +
                                  f"该存储类别适合{selected.get('use_case')}。"
                })
            
            elif component_type == "rds":
                component_descriptions.append({
                    "name": "Amazon RDS",
                    "type": "关系数据库服务",
                    "description": f"使用 {selected.get('instance_type')} 实例类型，运行 {selected.get('engine')} 数据库引擎，" +
                                  f"配置为{selected.get('deployment_option')}部署模式，" +
                                  f"提供 {selected.get('storage_gb')} GB 存储空间。"
                })
            
            elif component_type == "elasticache":
                component_descriptions.append({
                    "name": "Amazon ElastiCache",
                    "type": "内存缓存服务",
                    "description": f"使用 {selected.get('node_type')} 节点类型，运行 {selected.get('engine')} 缓存引擎，" +
                                  f"提供高性能内存缓存服务。"
                })
            
            elif component_type == "opensearch":
                component_descriptions.append({
                    "name": "Amazon OpenSearch Service",
                    "type": "搜索和分析服务",
                    "description": f"使用 {selected.get('instance_type')} 实例类型，" +
                                  f"配置 {selected.get('node_count')} 个节点，" +
                                  f"每个节点提供 {selected.get('storage_gb')} GB 存储空间，" +
                                  f"支持高效的搜索和日志分析。"
                })
            
            elif component_type == "loadbalancer":
                component_descriptions.append({
                    "name": f"Elastic Load Balancing ({selected.get('name', '').split(' ')[0]})",
                    "type": "负载均衡服务",
                    "description": f"使用 {selected.get('name')}，" +
                                  f"为应用提供高可用性和自动扩展能力。"
                })
    
    # Generate business benefits
    business_benefits = [
        {
            "benefit": "提高可靠性",
            "description": "AWS 提供 99.99% 的服务可用性承诺，显著减少系统宕机风险。"
        },
        {
            "benefit": "增强安全性",
            "description": "利用 AWS 安全最佳实践和合规认证，保护您的数据和应用。"
        },
        {
            "benefit": "优化成本",
            "description": "按使用量付费模式，无需前期硬件投资，优化资源利用率。"
        },
        {
            "benefit": "提升敏捷性",
            "description": "快速部署和扩展资源，缩短上市时间，提高业务响应速度。"
        }
    ]
    
    # Add specific benefits based on components
    if "rds" in components:
        business_benefits.append({
            "benefit": "减少管理负担",
            "description": "全托管数据库服务自动处理备份、补丁和维护，让您专注于应用开发。"
        })
    
    if "elasticache" in components:
        business_benefits.append({
            "benefit": "提高应用性能",
            "description": "内存缓存层显著提升应用响应速度，改善用户体验。"
        })
    
    return {
        "architecture_overview": architecture_description,
        "components": component_descriptions,
        "business_benefits": business_benefits
    }

def _generate_technical_specifications(solution: Dict[str, Any]) -> Dict[str, Any]:
    """Generate technical specifications section of the proposal."""
    # Extract components and their specifications
    components = solution.get("components", {})
    specifications = []
    
    # EC2 specifications
    if "ec2" in components and components["ec2"].get("selected"):
        selected = components["ec2"]["selected"]
        specifications.append({
            "component": "Amazon EC2",
            "specifications": [
                {"name": "实例类型", "value": selected.get("instance_type")},
                {"name": "vCPU 数量", "value": selected.get("vcpu")},
                {"name": "内存", "value": f"{selected.get('memory_gib')} GB"},
                {"name": "操作系统", "value": "Amazon Linux 2"},
                {"name": "部署模式", "value": "多可用区" if solution.get("requirements", {}).get("is_production") else "单可用区"}
            ]
        })
    
    # EBS specifications
    if "ebs" in components and components["ebs"].get("selected"):
        selected = components["ebs"]["selected"]
        specifications.append({
            "component": "Amazon EBS",
            "specifications": [
                {"name": "卷类型", "value": selected.get("volume_type")},
                {"name": "存储容量", "value": f"{selected.get('size_gb')} GB"},
                {"name": "IOPS", "value": EBS_IOPS_MAP.get(selected.get("volume_type"), "根据卷大小自动分配")},
                {"name": "吞吐量", "value": EBS_THROUGHPUT_MAP.get(selected.get("volume_type"), "根据卷大小自动分配")}
            ]
        })
    
    # S3 specifications
    if "s3" in components and components["s3"].get("selected"):
        selected = components["s3"]["selected"]
        requirements = components["s3"].get("requirements", {})
        specifications.append({
            "component": "Amazon S3",
            "specifications": [
                {"name": "存储类别", "value": selected.get("storage_class")},
                {"name": "存储容量", "value": f"{requirements.get('storage_size_gb', 100)} GB"},
                {"name": "数据传输量", "value": f"{requirements.get('data_transfer_gb', 50)} GB/月"},
                {"name": "可用性", "value": selected.get("availability", "99.99%")},
                {"name": "耐久性", "value": "99.999999999%"}
            ]
        })
    
    # RDS specifications
    if "rds" in components and components["rds"].get("selected"):
        selected = components["rds"]["selected"]
        specifications.append({
            "component": "Amazon RDS",
            "specifications": [
                {"name": "实例类型", "value": selected.get("instance_type")},
                {"name": "数据库引擎", "value": selected.get("engine")},
                {"name": "vCPU 数量", "value": selected.get("vcpu")},
                {"name": "内存", "value": f"{selected.get('memory_gb')} GB"},
                {"name": "存储容量", "value": f"{selected.get('storage_gb')} GB"},
                {"name": "部署模式", "value": selected.get("deployment_option")}
            ]
        })
    
    # ElastiCache specifications
    if "elasticache" in components and components["elasticache"].get("selected"):
        selected = components["elasticache"]["selected"]
        specifications.append({
            "component": "Amazon ElastiCache",
            "specifications": [
                {"name": "节点类型", "value": selected.get("node_type")},
                {"name": "缓存引擎", "value": selected.get("engine")},
                {"name": "vCPU 数量", "value": selected.get("vcpu")},
                {"name": "内存", "value": f"{selected.get('memory_gb')} GB"},
                {"name": "节点数量", "value": "2" if solution.get("requirements", {}).get("is_production") else "1"}
            ]
        })
    
    # OpenSearch specifications
    if "opensearch" in components and components["opensearch"].get("selected"):
        selected = components["opensearch"]["selected"]
        specifications.append({
            "component": "Amazon OpenSearch Service",
            "specifications": [
                {"name": "实例类型", "value": selected.get("instance_type")},
                {"name": "节点数量", "value": selected.get("node_count")},
                {"name": "存储容量/节点", "value": f"{selected.get('storage_gb')} GB"},
                {"name": "vCPU/节点", "value": selected.get("vcpu_per_node")},
                {"name": "内存/节点", "value": f"{selected.get('memory_gb_per_node')} GB"}
            ]
        })
    
    # Load Balancer specifications
    if "loadbalancer" in components and components["loadbalancer"].get("selected"):
        selected = components["loadbalancer"]["selected"]
        requirements = components["loadbalancer"].get("requirements", {})
        specifications.append({
            "component": selected.get("name", "Elastic Load Balancing"),
            "specifications": [
                {"name": "负载均衡器类型", "value": selected.get("name")},
                {"name": "数据处理量", "value": f"{requirements.get('data_processed_gb', 500)} GB/月"},
                {"name": "连接类型", "value": "第7层 (HTTP/HTTPS)" if selected.get("lb_type") == "alb" else "第4层 (TCP/UDP)"}
            ]
        })
    
    # Generate security features
    security_features = [
        {
            "feature": "网络安全",
            "description": "使用安全组和网络 ACL 控制流量，实现多层防御"
        },
        {
            "feature": "数据加密",
            "description": "传输中和静态数据加密，保护敏感信息"
        },
        {
            "feature": "身份认证",
            "description": "使用 AWS IAM 实现细粒度的访问控制和权限管理"
        },
        {
            "feature": "安全监控",
            "description": "使用 AWS CloudTrail 和 AWS Config 进行安全审计和合规监控"
        }
    ]
    
    # Generate scalability features
    scalability_features = [
        {
            "feature": "自动扩展",
            "description": "根据负载自动调整资源容量，满足业务需求"
        },
        {
            "feature": "负载均衡",
            "description": "自动分配流量，确保高可用性和性能"
        },
        {
            "feature": "多可用区部署",
            "description": "跨多个可用区部署资源，提高系统弹性"
        }
    ]
    
    return {
        "component_specifications": specifications,
        "security_features": security_features,
        "scalability_features": scalability_features,
        "compliance_standards": [
            "ISO 27001", "SOC 1/2/3", "PCI DSS", "GDPR"
        ]
    }

# Helper maps for EBS volume specifications
EBS_IOPS_MAP = {
    "gp3": "3,000 IOPS (基准)",
    "gp2": "3 IOPS/GB (最低 100 IOPS)",
    "io1": "最高 64,000 IOPS",
    "io2": "最高 64,000 IOPS",
    "st1": "最高 500 IOPS",
    "sc1": "最高 250 IOPS",
    "standard": "40-200 IOPS"
}

EBS_THROUGHPUT_MAP = {
    "gp3": "125 MB/s (基准)",
    "gp2": "最高 250 MB/s",
    "io1": "最高 1,000 MB/s",
    "io2": "最高 1,000 MB/s",
    "st1": "最高 500 MB/s",
    "sc1": "最高 250 MB/s",
    "standard": "40-90 MB/s"
}

def _generate_pricing_details(solution: Dict[str, Any]) -> Dict[str, Any]:
    """Generate pricing details section of the proposal."""
    # Extract cost items
    cost_items = solution.get("cost_summary", {}).get("resources", [])
    total_cost = solution.get("cost_summary", {}).get("total_monthly_cost", 0)
    
    # Format cost items for display
    formatted_cost_items = []
    for item in cost_items:
        resource_type = item.get("resource_type", "").upper()
        
        if resource_type == "EC2":
            formatted_cost_items.append({
                "service": "Amazon EC2",
                "description": f"{item.get('instance_type')} 实例 x {item.get('count', 1)}",
                "unit_price": f"${item.get('price_per_hour', 0):.4f}/小时",
                "quantity": f"{item.get('count', 1)} 实例 x 730 小时/月",
                "monthly_cost": item.get("monthly_cost", 0)
            })
        
        elif resource_type == "EBS":
            formatted_cost_items.append({
                "service": "Amazon EBS",
                "description": f"{item.get('volume_type')} 卷 ({item.get('size_gb', 0)} GB)",
                "unit_price": "$--/GB-月",  # Actual unit price varies by volume type and size
                "quantity": f"{item.get('size_gb', 0)} GB",
                "monthly_cost": item.get("monthly_cost", 0)
            })
        
        elif resource_type == "S3":
            formatted_cost_items.append({
                "service": "Amazon S3",
                "description": f"{item.get('storage_class')} 存储 ({item.get('storage_gb', 0)} GB) + 数据传输 ({item.get('data_transfer_gb', 0)} GB)",
                "unit_price": "$--/GB-月",  # Actual unit price varies by storage class and region
                "quantity": f"{item.get('storage_gb', 0)} GB 存储 + {item.get('data_transfer_gb', 0)} GB 传输",
                "monthly_cost": item.get("monthly_cost", 0)
            })
        
        elif resource_type == "RDS":
            formatted_cost_items.append({
                "service": "Amazon RDS",
                "description": f"{item.get('instance_type')} {item.get('engine')} 数据库 ({item.get('deployment_option')})",
                "unit_price": f"${item.get('price_per_hour', 0):.4f}/小时",
                "quantity": f"{item.get('count', 1)} 实例 x 730 小时/月",
                "monthly_cost": item.get("monthly_cost", 0)
            })
        
        elif resource_type == "ELASTICACHE":
            formatted_cost_items.append({
                "service": "Amazon ElastiCache",
                "description": f"{item.get('node_type')} {item.get('engine')} 节点 x {item.get('count', 1)}",
                "unit_price": f"${item.get('price_per_hour', 0):.4f}/小时",
                "quantity": f"{item.get('count', 1)} 节点 x 730 小时/月",
                "monthly_cost": item.get("monthly_cost", 0)
            })
        
        elif resource_type == "OPENSEARCH":
            formatted_cost_items.append({
                "service": "Amazon OpenSearch Service",
                "description": f"{item.get('instance_type')} 实例 x {item.get('node_count', 1)} + 存储 ({item.get('storage_gb', 0)} GB/节点)",
                "unit_price": "$--/小时",  # Actual unit price varies by instance type and region
                "quantity": f"{item.get('node_count', 1)} 节点 x 730 小时/月",
                "monthly_cost": item.get("monthly_cost", 0)
            })
        
        elif resource_type == "LOADBALANCER":
            formatted_cost_items.append({
                "service": "Elastic Load Balancing",
                "description": f"{item.get('lb_type').upper()} 负载均衡器 + 数据处理 ({item.get('data_processed_gb', 0)} GB)",
                "unit_price": "$--/小时 + $--/GB",  # Actual unit price varies by LB type and region
                "quantity": f"1 负载均衡器 x 730 小时/月 + {item.get('data_processed_gb', 0)} GB 数据处理",
                "monthly_cost": item.get("monthly_cost", 0)
            })
        
        elif resource_type == "NETWORK":
            formatted_cost_items.append({
                "service": "数据传输",
                "description": f"从 {item.get('from_region')} 传出 {item.get('data_transfer_gb', 0)} GB 数据",
                "unit_price": "$--/GB",  # Actual unit price varies by region and destination
                "quantity": f"{item.get('data_transfer_gb', 0)} GB",
                "monthly_cost": item.get("monthly_cost", 0)
            })
    
    # Generate pricing notes
    pricing_notes = [
        "所有价格均以美元 (USD) 计算，实际账单可能因使用量变化而有所不同",
        "价格基于按需定价模式，可通过预留实例或 Savings Plans 进一步优化成本",
        "数据传输费用取决于数据传输的方向和数量",
        "某些服务可能产生额外费用，如快照存储、数据请求等"
    ]
    
    # Generate cost optimization recommendations
    cost_optimization = [
        {
            "recommendation": "使用预留实例或 Savings Plans",
            "description": "对于长期稳定的工作负载，可节省高达 72% 的成本",
            "estimated_savings": "20-72%"
        },
        {
            "recommendation": "实施自动扩展策略",
            "description": "根据实际需求自动调整资源，避免过度配置",
            "estimated_savings": "10-40%"
        },
        {
            "recommendation": "使用 S3 智能分层存储",
            "description": "自动将数据移至最具成本效益的存储层",
            "estimated_savings": "15-30%"
        },
        {
            "recommendation": "定期审查和调整资源配置",
            "description": "使用 AWS Cost Explorer 和 Trusted Advisor 识别优化机会",
            "estimated_savings": "10-25%"
        }
    ]
    
    return {
        "monthly_cost_breakdown": formatted_cost_items,
        "total_monthly_cost": total_cost,
        "currency": "USD",
        "pricing_notes": pricing_notes,
        "cost_optimization_recommendations": cost_optimization
    }

def _generate_implementation_timeline(solution: Dict[str, Any]) -> Dict[str, Any]:
    """Generate implementation timeline section of the proposal."""
    # Determine complexity based on number of components
    component_count = len(solution.get("components", {}))
    complexity = "低" if component_count <= 2 else "中" if component_count <= 4 else "高"
    
    # Generate phases based on complexity
    phases = [
        {
            "phase": "规划与设计",
            "duration": "1-2 周",
            "activities": [
                "需求分析与确认",
                "架构设计与审核",
                "资源规划与配置设计"
            ]
        },
        {
            "phase": "环境准备",
            "duration": "1 周",
            "activities": [
                "AWS 账户设置与配置",
                "网络设计与安全配置",
                "基础设施即代码模板开发"
            ]
        }
    ]
    
    # Add implementation phase based on components
    implementation_activities = ["基础网络和安全组配置"]
    
    if "ec2" in solution.get("components", {}):
        implementation_activities.append("EC2 实例部署与配置")
    
    if "rds" in solution.get("components", {}):
        implementation_activities.append("RDS 数据库设置与数据迁移")
    
    if "elasticache" in solution.get("components", {}):
        implementation_activities.append("ElastiCache 集群配置")
    
    if "s3" in solution.get("components", {}):
        implementation_activities.append("S3 存储桶创建与权限配置")
    
    if "loadbalancer" in solution.get("components", {}):
        implementation_activities.append("负载均衡器设置与目标组配置")
    
    if "opensearch" in solution.get("components", {}):
        implementation_activities.append("OpenSearch 域配置与索引设置")
    
    implementation_duration = "1 周" if complexity == "低" else "2-3 周" if complexity == "中" else "3-4 周"
    phases.append({
        "phase": "实施与部署",
        "duration": implementation_duration,
        "activities": implementation_activities
    })
    
    # Add testing and optimization phases
    phases.extend([
        {
            "phase": "测试与验证",
            "duration": "1-2 周",
            "activities": [
                "功能测试与验证",
                "性能测试与优化",
                "安全审核与合规检查"
            ]
        },
        {
            "phase": "上线与交付",
            "duration": "1 周",
            "activities": [
                "最终迁移与切换",
                "监控与告警设置",
                "文档交付与知识转移"
            ]
        },
        {
            "phase": "后续支持",
            "duration": "持续",
            "activities": [
                "运维支持与问题解决",
                "性能监控与优化",
                "定期审核与成本优化"
            ]
        }
    ])
    
    # Calculate total duration
    min_weeks = 4 if complexity == "低" else 6 if complexity == "中" else 8
    max_weeks = 6 if complexity == "低" else 9 if complexity == "中" else 12
    
    return {
        "project_complexity": complexity,
        "estimated_duration": f"{min_weeks}-{max_weeks} 周",
        "implementation_phases": phases,
        "key_milestones": [
            "架构设计审核完成",
            "基础环境配置完成",
            "核心服务部署完成",
            "测试与验证完成",
            "正式上线"
        ]
    }

def _generate_terms_and_conditions() -> Dict[str, Any]:
    """Generate terms and conditions section of the proposal."""
    return {
        "validity_period": "本报价自发出之日起 30 天内有效",
        "payment_terms": "按月结算，根据实际使用量计费",
        "service_level_agreement": "根据 AWS 服务级别协议 (SLA) 提供服务保障",
        "confidentiality": "本报价包含的所有信息均为保密信息，未经双方同意不得向第三方披露",
        "disclaimer": "最终价格可能因实际使用量、AWS 价格调整或其他因素而变化"
    }

def _generate_next_steps() -> List[Dict[str, str]]:
    """Generate next steps section of the proposal."""
    return [
        {
            "step": "方案讨论与确认",
            "description": "安排会议讨论本方案，确认需求和技术细节"
        },
        {
            "step": "签署协议",
            "description": "确认方案后签署服务协议"
        },
        {
            "step": "项目启动",
            "description": "组建项目团队，制定详细实施计划"
        },
        {
            "step": "实施与部署",
            "description": "按照实施计划部署 AWS 资源和服务"
        },
        {
            "step": "培训与交付",
            "description": "提供技术培训，完成解决方案交付"
        }
    ]

@tool
def generate_migration_proposal(
    customer_name: str,
    current_environment: str,
    target_requirements: str,
    region: str = "us-east-1",
    is_production: bool = True,
    contact_info: Optional[Dict[str, str]] = None
) -> str:
    """
    Generate a professional AWS migration proposal based on current environment and target requirements.
    
    Args:
        customer_name: Name of the customer or company
        current_environment: Description of current environment (on-premises or other cloud)
        target_requirements: Description of target requirements in natural language
        region: AWS region code (default: us-east-1)
        is_production: Whether this is for a production environment (default: True)
        contact_info: Optional contact information dictionary
    
    Returns:
        JSON string with a structured migration proposal
    """
    try:
        # Generate AWS solution based on target requirements
        solution_json = generate_aws_solution(target_requirements, region, is_production)
        solution = json.loads(solution_json)
        
        # Check for errors in solution generation
        if "error" in solution:
            return json.dumps({
                "error": solution["error"],
                "proposal_status": "failed"
            })
        
        # Create proposal structure
        proposal = {
            "proposal_info": {
                "title": f"AWS 云迁移解决方案 - {customer_name}",
                "customer_name": customer_name,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "region": region,
                "region_display_name": AWS_REGION_NAMES.get(region, region),
                "environment_type": "生产环境" if is_production else "开发/测试环境"
            },
            "executive_summary": _generate_migration_summary(customer_name, current_environment, target_requirements, solution),
            "current_environment": _analyze_current_environment(current_environment),
            "target_architecture": _generate_solution_overview(solution),
            "migration_strategy": _generate_migration_strategy(current_environment, solution),
            "technical_specifications": _generate_technical_specifications(solution),
            "pricing_details": _generate_pricing_details(solution),
            "migration_timeline": _generate_migration_timeline(current_environment, solution),
            "terms_and_conditions": _generate_terms_and_conditions(),
            "next_steps": _generate_migration_next_steps()
        }
        
        # Add contact information if provided
        if contact_info:
            proposal["proposal_info"]["contact_info"] = contact_info
        
        return json.dumps(proposal, ensure_ascii=False, indent=2)
    
    except Exception as e:
        logger.error(f"Error generating migration proposal: {str(e)}")
        return json.dumps({
            "error": f"Error generating migration proposal: {str(e)}",
            "proposal_status": "failed"
        })

def _generate_migration_summary(customer_name: str, current_environment: str, target_requirements: str, solution: Dict[str, Any]) -> Dict[str, Any]:
    """Generate executive summary for migration proposal."""
    # Extract key components from solution
    components = []
    for component_type, component_info in solution.get("components", {}).items():
        if component_info.get("selected"):
            components.append(component_type.upper())
    
    components_text = "、".join(components) if components else "AWS 云服务"
    
    # Get total monthly cost
    total_cost = solution.get("cost_summary", {}).get("total_monthly_cost", 0)
    cost_text = f"迁移后预估每月运营成本约为 {total_cost:.2f} 美元" if total_cost else "详细价格请参见报价明细"
    
    # Determine migration source type
    source_type = "本地数据中心"
    if any(cloud in current_environment.lower() for cloud in ["阿里云", "腾讯云", "华为云", "alicloud", "tencent", "huawei"]):
        source_type = "其他云平台"
    
    return {
        "summary": f"本方案为 {customer_name} 提供从{source_type}迁移至 AWS 的全面解决方案，基于 {components_text} 构建目标架构。{cost_text}。AWS 提供高可用性、可扩展性和安全性，帮助您降低总体拥有成本，提高业务灵活性。",
        "key_benefits": [
            "降低总拥有成本 (TCO)：优化资源使用，减少基础设施维护成本",
            "提高可扩展性：根据业务需求自动扩展资源，应对业务增长",
            "增强安全性：利用 AWS 安全最佳实践和合规认证保护数据和应用",
            "提升业务敏捷性：加速创新，缩短新功能和服务的上市时间",
            "简化运维：减少基础设施管理负担，专注于核心业务"
        ],
        "migration_challenges": _extract_migration_challenges(current_environment),
        "migration_approach": "采用分阶段迁移策略，最小化业务中断风险，确保平稳过渡至 AWS 云平台"
    }

def _extract_migration_challenges(current_environment: str) -> List[str]:
    """Extract migration challenges based on current environment."""
    challenges = []
    
    # Look for common challenge indicators in current environment
    if any(term in current_environment.lower() for term in ["legacy", "老旧", "遗留", "老系统"]):
        challenges.append("遗留系统现代化，确保兼容性和性能")
    
    if any(term in current_environment.lower() for term in ["data", "database", "数据", "数据库"]):
        challenges.append("大规模数据迁移，确保数据完整性和一致性")
    
    if any(term in current_environment.lower() for term in ["downtime", "availability", "宕机", "可用性"]):
        challenges.append("最小化迁移过程中的业务中断")
    
    if any(term in current_environment.lower() for term in ["compliance", "security", "合规", "安全"]):
        challenges.append("满足严格的安全和合规要求")
    
    if any(term in current_environment.lower() for term in ["complex", "complexity", "复杂"]):
        challenges.append("复杂应用架构的迁移和优化")
    
    # Add default challenges if none detected
    if not challenges:
        challenges = [
            "确保迁移过程中的业务连续性",
            "优化应用架构以充分利用云平台优势",
            "建立有效的云治理和成本管理机制"
        ]
    
    return challenges

def _analyze_current_environment(current_environment: str) -> Dict[str, Any]:
    """Analyze current environment description."""
    # Determine environment type
    env_type = "本地数据中心"
    if any(cloud in current_environment.lower() for cloud in ["阿里云", "alicloud"]):
        env_type = "阿里云"
    elif any(cloud in current_environment.lower() for cloud in ["腾讯云", "tencent"]):
        env_type = "腾讯云"
    elif any(cloud in current_environment.lower() for cloud in ["华为云", "huawei"]):
        env_type = "华为云"
    elif any(cloud in current_environment.lower() for cloud in ["azure", "微软云"]):
        env_type = "Microsoft Azure"
    elif any(cloud in current_environment.lower() for cloud in ["gcp", "google"]):
        env_type = "Google Cloud Platform"
    
    # Identify key components
    components = []
    
    if any(term in current_environment.lower() for term in ["vm", "virtual machine", "server", "虚拟机", "服务器"]):
        components.append({
            "component_type": "计算资源",
            "description": "虚拟机或物理服务器"
        })
    
    if any(term in current_environment.lower() for term in ["database", "mysql", "oracle", "sql", "db", "数据库"]):
        components.append({
            "component_type": "数据库",
            "description": "关系型数据库服务"
        })
    
    if any(term in current_environment.lower() for term in ["storage", "disk", "volume", "存储", "磁盘"]):
        components.append({
            "component_type": "存储",
            "description": "块存储或文件存储"
        })
    
    if any(term in current_environment.lower() for term in ["load balancer", "loadbalancer", "负载均衡"]):
        components.append({
            "component_type": "负载均衡",
            "description": "流量分发服务"
        })
    
    if any(term in current_environment.lower() for term in ["cache", "redis", "memcached", "缓存"]):
        components.append({
            "component_type": "缓存服务",
            "description": "内存缓存服务"
        })
    
    # Identify limitations
    limitations = []
    
    if any(term in current_environment.lower() for term in ["scalability", "scale", "扩展性", "扩容"]):
        limitations.append("扩展性受限，难以应对业务增长")
    
    if any(term in current_environment.lower() for term in ["cost", "expensive", "成本", "费用"]):
        limitations.append("运维成本高，资源利用率低")
    
    if any(term in current_environment.lower() for term in ["performance", "slow", "性能", "缓慢"]):
        limitations.append("性能瓶颈，影响用户体验")
    
    if any(term in current_environment.lower() for term in ["reliability", "downtime", "可靠性", "宕机"]):
        limitations.append("可靠性不足，存在单点故障风险")
    
    if any(term in current_environment.lower() for term in ["maintenance", "管理", "维护"]):
        limitations.append("运维负担重，管理复杂")
    
    # Add default limitations if none detected
    if not limitations:
        limitations = [
            "扩展性受限，难以满足业务增长需求",
            "资源利用率低，成本效益不佳",
            "运维负担重，技术资源分散"
        ]
    
    return {
        "environment_type": env_type,
        "key_components": components,
        "current_limitations": limitations,
        "migration_drivers": [
            "提高基础设施灵活性和可扩展性",
            "降低总体拥有成本 (TCO)",
            "提升系统可靠性和性能",
            "加速创新和业务转型",
            "简化 IT 运维和管理"
        ]
    }

def _generate_migration_strategy(current_environment: str, solution: Dict[str, Any]) -> Dict[str, Any]:
    """Generate migration strategy based on current environment and target solution."""
    # Determine migration pattern
    pattern = "重新托管 (Rehost)"
    
    if any(term in current_environment.lower() for term in ["modernize", "refactor", "重构", "现代化"]):
        pattern = "重构 (Refactor)"
    elif any(term in current_environment.lower() for term in ["replatform", "optimize", "优化", "重建平台"]):
        pattern = "重建平台 (Replatform)"
    
    # Generate migration phases
    phases = [
        {
            "phase": "评估与规划",
            "activities": [
                "详细评估当前环境和应用",
                "确定迁移策略和优先级",
                "制定详细的迁移计划",
                "建立迁移团队和职责分工"
            ]
        },
        {
            "phase": "准备与设置",
            "activities": [
                "设置 AWS 账户和网络环境",
                "配置安全策略和访问控制",
                "建立监控和备份机制",
                "准备迁移工具和脚本"
            ]
        },
        {
            "phase": "迁移执行",
            "activities": [
                "数据迁移与同步",
                "应用迁移与配置",
                "测试与验证",
                "切换与上线"
            ]
        },
        {
            "phase": "优化与现代化",
            "activities": [
                "性能优化与调整",
                "成本优化与资源调整",
                "实施自动化和 DevOps 实践",
                "应用现代化改造"
            ]
        }
    ]
    
    # Generate migration tools
    tools = [
        {
            "tool": "AWS Application Migration Service",
            "purpose": "自动将物理、虚拟或云服务器迁移至 AWS",
            "use_case": "适用于大规模服务器迁移"
        },
        {
            "tool": "AWS Database Migration Service (DMS)",
            "purpose": "数据库迁移和持续复制",
            "use_case": "适用于各类数据库迁移，支持异构数据库迁移"
        },
        {
            "tool": "AWS DataSync",
            "purpose": "自动化数据传输服务",
            "use_case": "适用于大规模文件数据迁移"
        },
        {
            "tool": "AWS Snow Family",
            "purpose": "物理设备用于大规模数据传输",
            "use_case": "适用于网络带宽受限的环境"
        }
    ]
    
    # Generate risk mitigation strategies
    risks = [
        {
            "risk": "业务中断",
            "mitigation": "采用分阶段迁移策略，实施并行运行期，确保切换前充分测试"
        },
        {
            "risk": "数据丢失或不一致",
            "mitigation": "实施数据备份策略，使用 AWS DMS 进行持续数据复制，确保数据完整性"
        },
        {
            "risk": "性能问题",
            "mitigation": "迁移前进行性能基准测试，迁移后进行性能优化和调整"
        },
        {
            "risk": "安全漏洞",
            "mitigation": "实施全面的安全评估，确保所有资源符合安全最佳实践"
        },
        {
            "risk": "成本超支",
            "mitigation": "实施详细的成本监控和优化策略，定期审核资源使用情况"
        }
    ]
    
    return {
        "migration_pattern": pattern,
        "migration_approach": "分阶段迁移，优先迁移非关键应用，逐步迁移核心业务系统",
        "migration_phases": phases,
        "migration_tools": tools,
        "risk_mitigation": risks
    }

def _generate_migration_timeline(current_environment: str, solution: Dict[str, Any]) -> Dict[str, Any]:
    """Generate migration timeline based on current environment and target solution."""
    # Determine complexity based on environment and number of components
    component_count = len(solution.get("components", {}))
    complexity_factors = 0
    
    if component_count > 4:
        complexity_factors += 1
    
    if any(term in current_environment.lower() for term in ["complex", "large", "复杂", "大规模"]):
        complexity_factors += 1
    
    if any(term in current_environment.lower() for term in ["legacy", "custom", "遗留", "定制"]):
        complexity_factors += 1
    
    complexity = "低" if complexity_factors == 0 else "中" if complexity_factors == 1 else "高"
    
    # Generate timeline based on complexity
    if complexity == "低":
        duration = "8-12 周"
        phases = [
            {"phase": "评估与规划", "duration": "2-3 周"},
            {"phase": "准备与设置", "duration": "1-2 周"},
            {"phase": "迁移执行", "duration": "3-4 周"},
            {"phase": "优化与验证", "duration": "2-3 周"}
        ]
    elif complexity == "中":
        duration = "12-16 周"
        phases = [
            {"phase": "评估与规划", "duration": "3-4 周"},
            {"phase": "准备与设置", "duration": "2-3 周"},
            {"phase": "迁移执行", "duration": "4-6 周"},
            {"phase": "优化与验证", "duration": "3-4 周"}
        ]
    else:  # 高复杂度
        duration = "16-24 周"
        phases = [
            {"phase": "评估与规划", "duration": "4-6 周"},
            {"phase": "准备与设置", "duration": "3-4 周"},
            {"phase": "迁移执行", "duration": "6-8 周"},
            {"phase": "优化与验证", "duration": "4-6 周"}
        ]
    
    return {
        "project_complexity": complexity,
        "estimated_duration": duration,
        "timeline_phases": phases,
        "key_milestones": [
            "迁移计划审核完成",
            "AWS 环境设置完成",
            "首批非关键应用迁移完成",
            "数据迁移完成",
            "核心应用迁移完成",
            "切换上线完成",
            "项目验收完成"
        ],
        "dependencies_and_prerequisites": [
            "完整的应用和基础设施清单",
            "明确的业务优先级和迁移顺序",
            "业务部门的支持和参与",
            "充分的测试环境和资源",
            "明确的回滚计划"
        ]
    }

def _generate_migration_next_steps() -> List[Dict[str, str]]:
    """Generate next steps for migration proposal."""
    return [
        {
            "step": "迁移评估研讨会",
            "description": "组织研讨会，深入评估当前环境和迁移需求"
        },
        {
            "step": "迁移计划制定",
            "description": "基于评估结果，制定详细的迁移计划和时间表"
        },
        {
            "step": "概念验证 (PoC)",
            "description": "选择代表性应用进行迁移概念验证，验证迁移方法"
        },
        {
            "step": "迁移团队组建",
            "description": "组建包括业务和技术人员的迁移团队，明确职责分工"
        },
        {
            "step": "迁移执行",
            "description": "按照计划执行迁移，包括数据迁移、应用迁移和测试"
        },
        {
            "step": "上线与优化",
            "description": "完成切换上线，持续优化云环境"
        }
    ]

@tool
def generate_comparative_proposal(
    customer_name: str,
    competitor_info: str,
    requirements: str,
    region: str = "us-east-1",
    is_production: bool = True,
    contact_info: Optional[Dict[str, str]] = None
) -> str:
    """
    Generate a comparative AWS sales proposal highlighting advantages over competitor offerings.
    
    Args:
        customer_name: Name of the customer or company
        competitor_info: Information about competitor offering (e.g., Alibaba Cloud, Tencent Cloud)
        requirements: Description of customer requirements in natural language
        region: AWS region code (default: us-east-1)
        is_production: Whether this is for a production environment (default: True)
        contact_info: Optional contact information dictionary
    
    Returns:
        JSON string with a structured comparative sales proposal
    """
    try:
        # Generate AWS solution based on requirements
        solution_json = generate_aws_solution(requirements, region, is_production)
        solution = json.loads(solution_json)
        
        # Check for errors in solution generation
        if "error" in solution:
            return json.dumps({
                "error": solution["error"],
                "proposal_status": "failed"
            })
        
        # Identify competitor
        competitor = _identify_competitor(competitor_info)
        
        # Create proposal structure
        proposal = {
            "proposal_info": {
                "title": f"AWS 云服务对比方案 - {customer_name}",
                "customer_name": customer_name,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "region": region,
                "region_display_name": AWS_REGION_NAMES.get(region, region),
                "environment_type": "生产环境" if is_production else "开发/测试环境"
            },
            "executive_summary": _generate_comparative_summary(customer_name, competitor, requirements, solution),
            "solution_overview": _generate_solution_overview(solution),
            "competitive_analysis": _generate_competitive_analysis(competitor, solution),
            "technical_specifications": _generate_technical_specifications(solution),
            "pricing_details": _generate_pricing_details(solution),
            "implementation_timeline": _generate_implementation_timeline(solution),
            "terms_and_conditions": _generate_terms_and_conditions(),
            "next_steps": _generate_next_steps()
        }
        
        # Add contact information if provided
        if contact_info:
            proposal["proposal_info"]["contact_info"] = contact_info
        
        return json.dumps(proposal, ensure_ascii=False, indent=2)
    
    except Exception as e:
        logger.error(f"Error generating comparative proposal: {str(e)}")
        return json.dumps({
            "error": f"Error generating comparative proposal: {str(e)}",
            "proposal_status": "failed"
        })

def _identify_competitor(competitor_info: str) -> Dict[str, Any]:
    """Identify competitor from competitor info."""
    competitor = {
        "name": "其他云服务提供商",
        "type": "public_cloud"
    }
    
    # Identify specific competitor
    if any(term in competitor_info.lower() for term in ["阿里", "ali", "alibaba", "aliyun"]):
        competitor["name"] = "阿里云"
        competitor["type"] = "public_cloud"
    elif any(term in competitor_info.lower() for term in ["腾讯", "tencent"]):
        competitor["name"] = "腾讯云"
        competitor["type"] = "public_cloud"
    elif any(term in competitor_info.lower() for term in ["华为", "huawei"]):
        competitor["name"] = "华为云"
        competitor["type"] = "public_cloud"
    elif any(term in competitor_info.lower() for term in ["azure", "微软"]):
        competitor["name"] = "Microsoft Azure"
        competitor["type"] = "public_cloud"
    elif any(term in competitor_info.lower() for term in ["gcp", "google"]):
        competitor["name"] = "Google Cloud Platform"
        competitor["type"] = "public_cloud"
    elif any(term in competitor_info.lower() for term in ["idc", "自建", "on-premise", "on-prem", "数据中心"]):
        competitor["name"] = "自建数据中心"
        competitor["type"] = "on_premise"
    
    return competitor

def _generate_comparative_summary(customer_name: str, competitor: Dict[str, Any], requirements: str, solution: Dict[str, Any]) -> Dict[str, Any]:
    """Generate executive summary for comparative proposal."""
    # Extract key components from solution
    components = []
    for component_type, component_info in solution.get("components", {}).items():
        if component_info.get("selected"):
            components.append(component_type.upper())
    
    components_text = "、".join(components) if components else "AWS 云服务"
    
    # Get total monthly cost
    total_cost = solution.get("cost_summary", {}).get("total_monthly_cost", 0)
    cost_text = f"预估每月成本约为 {total_cost:.2f} 美元" if total_cost else "详细价格请参见报价明细"
    
    return {
        "summary": f"本方案为 {customer_name} 提供基于 {components_text} 的全面云解决方案，相比 {competitor['name']} 具有显著优势。{cost_text}。AWS 提供全球领先的云服务，具备更高的可靠性、更广泛的服务覆盖以及更成熟的生态系统，帮助您实现业务目标并降低总体拥有成本。",
        "key_advantages": [
            "全球基础设施：AWS 在全球 25+ 区域、80+ 可用区提供服务，覆盖范围更广",
            "服务丰富度：提供 200+ 全功能云服务，满足各类业务需求",
            "成熟度与可靠性：15+ 年云服务经验，为全球数百万客户提供服务",
            "安全与合规：最全面的安全控制和合规认证",
            "生态系统：庞大的合作伙伴网络和市场领先的集成能力"
        ],
        "customer_challenges": _extract_customer_challenges(requirements),
        "proposed_solution_highlights": _extract_solution_highlights(solution)
    }

def _generate_competitive_analysis(competitor: Dict[str, Any], solution: Dict[str, Any]) -> Dict[str, Any]:
    """Generate competitive analysis section."""
    # Generate comparison points based on competitor
    comparison_points = []
    
    # Global infrastructure comparison
    if competitor["name"] in ["阿里云", "腾讯云", "华为云"]:
        comparison_points.append({
            "category": "全球基础设施",
            "aws_advantage": "AWS 在全球 25+ 区域、80+ 可用区提供服务，真正的全球覆盖",
            "competitor_limitation": f"{competitor['name']}的全球覆盖有限，国际区域较少",
            "business_impact": "AWS 全球基础设施让您的业务能够轻松拓展到全球市场"
        })
    else:
        comparison_points.append({
            "category": "全球基础设施",
            "aws_advantage": "AWS 在全球 25+ 区域、80+ 可用区提供服务，领先的全球覆盖",
            "competitor_limitation": "覆盖范围有限，无法满足全球业务需求",
            "business_impact": "AWS 全球基础设施让您的业务能够轻松拓展到全球市场"
        })
    
    # Service breadth comparison
    comparison_points.append({
        "category": "服务丰富度",
        "aws_advantage": "提供 200+ 全功能云服务，包括计算、存储、数据库、分析、机器学习等",
        "competitor_limitation": f"{competitor['name']}提供的服务数量和深度有限",
        "business_impact": "AWS 丰富的服务能够满足您当前和未来的各种业务需求，无需多个供应商"
    })
    
    # Reliability comparison
    comparison_points.append({
        "category": "可靠性与成熟度",
        "aws_advantage": "15+ 年云服务经验，为全球数百万客户提供服务，成熟的架构和运营实践",
        "competitor_limitation": f"{competitor['name']}在云服务领域经验相对较少，可靠性有待验证",
        "business_impact": "AWS 的高可靠性意味着您的业务面临的中断风险更低"
    })
    
    # Security comparison
    comparison_points.append({
        "category": "安全与合规",
        "aws_advantage": "最全面的安全控制和合规认证，包括 ISO、SOC、PCI DSS、GDPR 等",
        "competitor_limitation": f"{competitor['name']}的安全控制和合规认证相对有限",
        "business_impact": "AWS 的安全能力帮助您满足严格的合规要求，保护关键数据和应用"
    })
    
    # Ecosystem comparison
    comparison_points.append({
        "category": "生态系统",
        "aws_advantage": "庞大的合作伙伴网络，丰富的第三方集成，活跃的开发者社区",
        "competitor_limitation": f"{competitor['name']}的合作伙伴生态系统相对有限",
        "business_impact": "AWS 丰富的生态系统为您提供更多选择和支持，加速创新"
    })
    
    # Cost optimization comparison
    comparison_points.append({
        "category": "成本优化",
        "aws_advantage": "丰富的成本优化选项，包括预留实例、Savings Plans、Spot 实例等",
        "competitor_limitation": f"{competitor['name']}的成本优化选项较少",
        "business_impact": "AWS 的灵活定价模式帮助您显著降低云基础设施成本"
    })
    
    # Performance comparison
    comparison_points.append({
        "category": "性能",
        "aws_advantage": "持续创新的高性能实例类型和服务，如 Graviton 处理器、EBS io2 Block Express 等",
        "competitor_limitation": f"{competitor['name']}的性能创新相对滞后",
        "business_impact": "AWS 的高性能服务帮助您提升应用响应速度，改善用户体验"
    })
    
    # Generate TCO analysis
    tco_analysis = {
        "aws_advantages": [
            "按需付费模式，无需前期资本投入",
            "多种成本优化选项，如预留实例和 Savings Plans",
            "自动扩展能力，优化资源利用率",
            "完善的成本管理工具，如 AWS Cost Explorer 和 AWS Budgets"
        ],
        "estimated_savings": "20-40%",
        "savings_factors": [
            "消除硬件更新和维护成本",
            "优化人力资源配置，减少运维负担",
            "提高资源利用率，避免过度配置",
            "根据实际使用量付费，避免资源浪费"
        ]
    }
    
    return {
        "competitor_name": competitor["name"],
        "comparison_points": comparison_points,
        "tco_analysis": tco_analysis,
        "customer_success_stories": [
            {
                "industry": "金融服务",
                "challenge": "需要满足严格的安全和合规要求，同时提高系统可扩展性",
                "solution": "迁移至 AWS，利用 AWS 的安全服务和全球基础设施",
                "results": "合规成本降低 30%，系统可扩展性提高 5 倍，上市时间缩短 50%"
            },
            {
                "industry": "零售",
                "challenge": "季节性流量波动大，需要灵活的基础设施以应对销售高峰",
                "solution": "采用 AWS 弹性架构，实现自动扩展",
                "results": "高峰期零宕机，基础设施成本降低 45%，客户满意度提高 25%"
            },
            {
                "industry": "制造业",
                "challenge": "需要整合全球运营数据，提高决策效率",
                "solution": "使用 AWS 数据湖和分析服务构建统一数据平台",
                "results": "数据处理时间缩短 80%，运营效率提高 35%，新见解推动收入增长 15%"
            }
        ]
    }