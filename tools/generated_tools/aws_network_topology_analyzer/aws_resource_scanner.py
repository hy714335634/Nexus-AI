from strands import tool
from typing import Dict, List, Optional, Any, Union
import boto3
import json
import logging
import time
from botocore.exceptions import ClientError, ProfileNotFound

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AWS资源类型常量
AWS_NETWORK_RESOURCES = [
    "vpc", "subnet", "route_table", "internet_gateway", "nat_gateway", 
    "transit_gateway", "vpc_peering", "vpn_gateway", "vpn_connection", 
    "direct_connect_gateway", "vpc_endpoint", "security_group",
    "network_acl", "elastic_ip", "flow_log"
]

AWS_COMPUTE_RESOURCES = ["ec2", "rds"]


def paginate_with_optional_limit(paginator, max_items=None, **kwargs):
    """包装boto3分页器，允许省略MaxItems以返回全部结果"""
    pagination_config = {}
    if max_items is not None:
        pagination_config["MaxItems"] = max_items
    if pagination_config:
        kwargs["PaginationConfig"] = pagination_config
    return paginator.paginate(**kwargs)

@tool
def aws_resource_scanner(
    profile_name: str,
    region: str,
    resource_types: List[str],
    max_items: Optional[int] = None,
    include_tags: bool = True
) -> str:
    """
    扫描AWS网络资源
    
    Args:
        profile_name: AWS配置文件名称
        region: AWS区域
        resource_types: 要扫描的资源类型列表，可选值包括: vpc, subnet, route_table, internet_gateway, nat_gateway, 
                       transit_gateway, vpc_peering, vpn_gateway, vpn_connection, direct_connect_gateway, 
                       vpc_endpoint, security_group, network_acl, elastic_ip, flow_log, ec2, rds, all_network, all_compute
        max_items: 每种资源类型最大返回数量；为None时不限制
        include_tags: 是否包含资源标签（默认True）
        
    Returns:
        str: JSON格式的扫描结果
    """
    try:
        # 创建会话
        session = boto3.Session(profile_name=profile_name, region_name=region)
        
        # 处理特殊资源类型组
        if "all_network" in resource_types:
            resource_types.remove("all_network")
            resource_types.extend(AWS_NETWORK_RESOURCES)
        
        if "all_compute" in resource_types:
            resource_types.remove("all_compute")
            resource_types.extend(AWS_COMPUTE_RESOURCES)
        
        # 去重
        resource_types = list(set(resource_types))
        
        # 初始化结果
        result = {
            "status": "success",
            "profile": profile_name,
            "region": region,
            "scan_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "resources": {},
            "resource_counts": {},
            "errors": []
        }
        
        # 获取账户ID
        try:
            sts_client = session.client('sts')
            account_id = sts_client.get_caller_identity()["Account"]
            result["account_id"] = account_id
        except Exception as e:
            logger.warning(f"无法获取账户ID: {str(e)}")
            result["account_id"] = "unknown"
        
        # 扫描请求的资源类型
        for resource_type in resource_types:
            try:
                resources = scan_resource(session, resource_type, region, max_items, include_tags)
                result["resources"][resource_type] = resources
                result["resource_counts"][resource_type] = len(resources)
            except Exception as e:
                error_msg = f"扫描{resource_type}资源时出错: {str(e)}"
                logger.error(error_msg)
                result["errors"].append({
                    "resource_type": resource_type,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                result["resources"][resource_type] = []
                result["resource_counts"][resource_type] = 0
        
        # 计算总资源数
        total_resources = sum(result["resource_counts"].values())
        result["total_resources"] = total_resources
        
        # 添加摘要信息
        result["summary"] = {
            "total_resources": total_resources,
            "resource_types_scanned": len(resource_types),
            "resource_types_with_data": sum(1 for count in result["resource_counts"].values() if count > 0),
            "errors": len(result["errors"])
        }
        
        return json.dumps(result, indent=2, default=str)
    
    except ProfileNotFound:
        error_result = {
            "status": "error",
            "message": f"Profile '{profile_name}' not found",
            "error_type": "ProfileNotFound"
        }
        return json.dumps(error_result, indent=2)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)

def scan_resource(session, resource_type, region, max_items, include_tags):
    """扫描指定类型的AWS资源"""
    
    if resource_type == "vpc":
        return scan_vpcs(session, max_items, include_tags)
    elif resource_type == "subnet":
        return scan_subnets(session, max_items, include_tags)
    elif resource_type == "route_table":
        return scan_route_tables(session, max_items, include_tags)
    elif resource_type == "internet_gateway":
        return scan_internet_gateways(session, max_items, include_tags)
    elif resource_type == "nat_gateway":
        return scan_nat_gateways(session, max_items, include_tags)
    elif resource_type == "transit_gateway":
        return scan_transit_gateways(session, max_items, include_tags)
    elif resource_type == "vpc_peering":
        return scan_vpc_peerings(session, max_items, include_tags)
    elif resource_type == "vpn_gateway":
        return scan_vpn_gateways(session, max_items, include_tags)
    elif resource_type == "vpn_connection":
        return scan_vpn_connections(session, max_items, include_tags)
    elif resource_type == "direct_connect_gateway":
        return scan_direct_connect_gateways(session, max_items, include_tags)
    elif resource_type == "vpc_endpoint":
        return scan_vpc_endpoints(session, max_items, include_tags)
    elif resource_type == "security_group":
        return scan_security_groups(session, max_items, include_tags)
    elif resource_type == "network_acl":
        return scan_network_acls(session, max_items, include_tags)
    elif resource_type == "elastic_ip":
        return scan_elastic_ips(session, max_items)
    elif resource_type == "flow_log":
        return scan_flow_logs(session, max_items, include_tags)
    elif resource_type == "ec2":
        return scan_ec2_instances(session, max_items, include_tags)
    elif resource_type == "rds":
        return scan_rds_instances(session, max_items, include_tags)
    else:
        raise ValueError(f"Unsupported resource type: {resource_type}")

def extract_tags(tags_list):
    """从AWS标签列表中提取标签字典"""
    if not tags_list:
        return {}
    return {tag.get('Key', ''): tag.get('Value', '') for tag in tags_list}

def scan_vpcs(session, max_items, include_tags):
    """扫描VPC资源"""
    ec2_client = session.client('ec2')
    vpcs = []
    
    paginator = ec2_client.get_paginator('describe_vpcs')
    page_iterator = paginate_with_optional_limit(paginator, max_items)
    
    for page in page_iterator:
        for vpc in page['Vpcs']:
            vpc_data = {
                "resource_id": vpc['VpcId'],
                "resource_type": "vpc",
                "cidr_block": vpc.get('CidrBlock', ''),
                "state": vpc.get('State', ''),
                "is_default": vpc.get('IsDefault', False),
                "dhcp_options_id": vpc.get('DhcpOptionsId', ''),
                "owner_id": vpc.get('OwnerId', ''),
                "instance_tenancy": vpc.get('InstanceTenancy', '')
            }
            
            # 添加CIDR关联
            if 'CidrBlockAssociationSet' in vpc:
                vpc_data['cidr_associations'] = vpc['CidrBlockAssociationSet']
            
            # 添加IPv6 CIDR关联
            if 'Ipv6CidrBlockAssociationSet' in vpc:
                vpc_data['ipv6_cidr_associations'] = vpc['Ipv6CidrBlockAssociationSet']
            
            # 添加标签
            if include_tags and 'Tags' in vpc:
                vpc_data['tags'] = extract_tags(vpc['Tags'])
            
            vpcs.append(vpc_data)
    
    return vpcs

def scan_subnets(session, max_items, include_tags):
    """扫描子网资源"""
    ec2_client = session.client('ec2')
    subnets = []
    
    paginator = ec2_client.get_paginator('describe_subnets')
    page_iterator = paginate_with_optional_limit(paginator, max_items)
    
    for page in page_iterator:
        for subnet in page['Subnets']:
            subnet_data = {
                "resource_id": subnet['SubnetId'],
                "resource_type": "subnet",
                "vpc_id": subnet.get('VpcId', ''),
                "cidr_block": subnet.get('CidrBlock', ''),
                "availability_zone": subnet.get('AvailabilityZone', ''),
                "state": subnet.get('State', ''),
                "available_ip_address_count": subnet.get('AvailableIpAddressCount', 0),
                "map_public_ip_on_launch": subnet.get('MapPublicIpOnLaunch', False),
                "owner_id": subnet.get('OwnerId', '')
            }
            
            # 添加IPv6 CIDR关联
            if 'Ipv6CidrBlockAssociationSet' in subnet:
                subnet_data['ipv6_cidr_associations'] = subnet['Ipv6CidrBlockAssociationSet']
            
            # 添加标签
            if include_tags and 'Tags' in subnet:
                subnet_data['tags'] = extract_tags(subnet['Tags'])
            
            subnets.append(subnet_data)
    
    return subnets

def scan_route_tables(session, max_items, include_tags):
    """扫描路由表资源"""
    ec2_client = session.client('ec2')
    route_tables = []
    
    paginator = ec2_client.get_paginator('describe_route_tables')
    page_iterator = paginate_with_optional_limit(paginator, max_items)
    
    for page in page_iterator:
        for rt in page['RouteTables']:
            rt_data = {
                "resource_id": rt['RouteTableId'],
                "resource_type": "route_table",
                "vpc_id": rt.get('VpcId', ''),
                "owner_id": rt.get('OwnerId', ''),
                "associations": [],
                "routes": []
            }
            
            # 添加关联信息
            if 'Associations' in rt:
                for assoc in rt['Associations']:
                    association = {
                        "id": assoc.get('RouteTableAssociationId', ''),
                        "main": assoc.get('Main', False)
                    }
                    
                    if 'SubnetId' in assoc:
                        association['subnet_id'] = assoc['SubnetId']
                    
                    if 'GatewayId' in assoc:
                        association['gateway_id'] = assoc['GatewayId']
                    
                    rt_data['associations'].append(association)
            
            # 添加路由信息
            if 'Routes' in rt:
                for route in rt['Routes']:
                    route_info = {
                        "destination_cidr_block": route.get('DestinationCidrBlock', ''),
                        "destination_ipv6_cidr_block": route.get('DestinationIpv6CidrBlock', ''),
                        "destination_prefix_list_id": route.get('DestinationPrefixListId', ''),
                        "gateway_id": route.get('GatewayId', ''),
                        "instance_id": route.get('InstanceId', ''),
                        "nat_gateway_id": route.get('NatGatewayId', ''),
                        "network_interface_id": route.get('NetworkInterfaceId', ''),
                        "vpc_peering_connection_id": route.get('VpcPeeringConnectionId', ''),
                        "transit_gateway_id": route.get('TransitGatewayId', ''),
                        "state": route.get('State', '')
                    }
                    
                    # 清理空值
                    route_info = {k: v for k, v in route_info.items() if v}
                    
                    rt_data['routes'].append(route_info)
            
            # 添加标签
            if include_tags and 'Tags' in rt:
                rt_data['tags'] = extract_tags(rt['Tags'])
            
            route_tables.append(rt_data)
    
    return route_tables

def scan_internet_gateways(session, max_items, include_tags):
    """扫描互联网网关资源"""
    ec2_client = session.client('ec2')
    igws = []
    
    paginator = ec2_client.get_paginator('describe_internet_gateways')
    page_iterator = paginate_with_optional_limit(paginator, max_items)
    
    for page in page_iterator:
        for igw in page['InternetGateways']:
            igw_data = {
                "resource_id": igw['InternetGatewayId'],
                "resource_type": "internet_gateway",
                "owner_id": igw.get('OwnerId', ''),
                "attachments": []
            }
            
            # 添加附件信息
            if 'Attachments' in igw:
                for attachment in igw['Attachments']:
                    igw_data['attachments'].append({
                        "vpc_id": attachment.get('VpcId', ''),
                        "state": attachment.get('State', '')
                    })
            
            # 添加标签
            if include_tags and 'Tags' in igw:
                igw_data['tags'] = extract_tags(igw['Tags'])
            
            igws.append(igw_data)
    
    return igws

def scan_nat_gateways(session, max_items, include_tags):
    """扫描NAT网关资源"""
    ec2_client = session.client('ec2')
    nat_gateways = []
    
    paginator = ec2_client.get_paginator('describe_nat_gateways')
    page_iterator = paginate_with_optional_limit(paginator, max_items)
    
    for page in page_iterator:
        for nat in page['NatGateways']:
            nat_data = {
                "resource_id": nat['NatGatewayId'],
                "resource_type": "nat_gateway",
                "vpc_id": nat.get('VpcId', ''),
                "subnet_id": nat.get('SubnetId', ''),
                "state": nat.get('State', ''),
                "connectivity_type": nat.get('ConnectivityType', ''),
                "create_time": nat.get('CreateTime', ''),
                "delete_time": nat.get('DeleteTime', ''),
                "failure_code": nat.get('FailureCode', ''),
                "failure_message": nat.get('FailureMessage', ''),
                "addresses": []
            }
            
            # 添加地址信息
            if 'NatGatewayAddresses' in nat:
                for addr in nat['NatGatewayAddresses']:
                    nat_data['addresses'].append({
                        "allocation_id": addr.get('AllocationId', ''),
                        "network_interface_id": addr.get('NetworkInterfaceId', ''),
                        "private_ip": addr.get('PrivateIp', ''),
                        "public_ip": addr.get('PublicIp', '')
                    })
            
            # 添加标签
            if include_tags and 'Tags' in nat:
                nat_data['tags'] = extract_tags(nat['Tags'])
            
            nat_gateways.append(nat_data)
    
    return nat_gateways

def scan_transit_gateways(session, max_items, include_tags):
    """扫描Transit Gateway资源"""
    ec2_client = session.client('ec2')
    transit_gateways = []
    
    try:
        paginator = ec2_client.get_paginator('describe_transit_gateways')
        page_iterator = paginate_with_optional_limit(paginator, max_items)
        
        for page in page_iterator:
            for tgw in page['TransitGateways']:
                tgw_data = {
                    "resource_id": tgw['TransitGatewayId'],
                    "resource_type": "transit_gateway",
                    "state": tgw.get('State', ''),
                    "owner_id": tgw.get('OwnerId', ''),
                    "description": tgw.get('Description', ''),
                    "creation_time": tgw.get('CreationTime', ''),
                    "options": {}
                }
                
                # 添加选项信息
                if 'Options' in tgw:
                    options = tgw['Options']
                    tgw_data['options'] = {
                        "amazon_side_asn": options.get('AmazonSideAsn', 0),
                        "auto_accept_shared_attachments": options.get('AutoAcceptSharedAttachments', ''),
                        "default_route_table_association": options.get('DefaultRouteTableAssociation', ''),
                        "default_route_table_propagation": options.get('DefaultRouteTablePropagation', ''),
                        "vpn_ecmp_support": options.get('VpnEcmpSupport', ''),
                        "dns_support": options.get('DnsSupport', '')
                    }
                
                # 添加标签
                if include_tags and 'Tags' in tgw:
                    tgw_data['tags'] = extract_tags(tgw['Tags'])
                
                transit_gateways.append(tgw_data)
                
        # 获取Transit Gateway附件
        try:
            tgw_attachments = {}
            paginator = ec2_client.get_paginator('describe_transit_gateway_attachments')
            page_iterator = paginate_with_optional_limit(paginator, max_items)
            
            for page in page_iterator:
                for attachment in page['TransitGatewayAttachments']:
                    tgw_id = attachment.get('TransitGatewayId', '')
                    if tgw_id not in tgw_attachments:
                        tgw_attachments[tgw_id] = []
                    
                    tgw_attachments[tgw_id].append({
                        "id": attachment.get('TransitGatewayAttachmentId', ''),
                        "type": attachment.get('ResourceType', ''),
                        "resource_id": attachment.get('ResourceId', ''),
                        "state": attachment.get('State', '')
                    })
            
            # 将附件信息添加到对应的Transit Gateway
            for tgw in transit_gateways:
                tgw_id = tgw['resource_id']
                if tgw_id in tgw_attachments:
                    tgw['attachments'] = tgw_attachments[tgw_id]
                else:
                    tgw['attachments'] = []
        
        except Exception as e:
            logger.warning(f"无法获取Transit Gateway附件: {str(e)}")
    
    except Exception as e:
        logger.warning(f"无法获取Transit Gateway: {str(e)}")
    
    return transit_gateways

def scan_vpc_peerings(session, max_items, include_tags):
    """扫描VPC对等连接资源"""
    ec2_client = session.client('ec2')
    vpc_peerings = []
    
    paginator = ec2_client.get_paginator('describe_vpc_peering_connections')
    page_iterator = paginate_with_optional_limit(paginator, max_items)
    
    for page in page_iterator:
        for peering in page['VpcPeeringConnections']:
            peering_data = {
                "resource_id": peering['VpcPeeringConnectionId'],
                "resource_type": "vpc_peering",
                "status": peering.get('Status', {}).get('Code', ''),
                "expiration_time": peering.get('ExpirationTime', '')
            }
            
            # 添加请求者VPC信息
            if 'RequesterVpcInfo' in peering:
                req_info = peering['RequesterVpcInfo']
                peering_data['requester_vpc'] = {
                    "vpc_id": req_info.get('VpcId', ''),
                    "cidr_block": req_info.get('CidrBlock', ''),
                    "owner_id": req_info.get('OwnerId', ''),
                    "region": req_info.get('Region', '')
                }
            
            # 添加接受者VPC信息
            if 'AccepterVpcInfo' in peering:
                acc_info = peering['AccepterVpcInfo']
                peering_data['accepter_vpc'] = {
                    "vpc_id": acc_info.get('VpcId', ''),
                    "cidr_block": acc_info.get('CidrBlock', ''),
                    "owner_id": acc_info.get('OwnerId', ''),
                    "region": acc_info.get('Region', '')
                }
            
            # 添加标签
            if include_tags and 'Tags' in peering:
                peering_data['tags'] = extract_tags(peering['Tags'])
            
            vpc_peerings.append(peering_data)
    
    return vpc_peerings

def scan_vpn_gateways(session, max_items, include_tags):
    """扫描VPN网关资源"""
    ec2_client = session.client('ec2')
    vpn_gateways = []
    
    paginator = ec2_client.get_paginator('describe_vpn_gateways')
    page_iterator = paginate_with_optional_limit(paginator, max_items)
    
    for page in page_iterator:
        for vgw in page['VpnGateways']:
            vgw_data = {
                "resource_id": vgw['VpnGatewayId'],
                "resource_type": "vpn_gateway",
                "state": vgw.get('State', ''),
                "type": vgw.get('Type', ''),
                "availability_zone": vgw.get('AvailabilityZone', ''),
                "amazon_side_asn": vgw.get('AmazonSideAsn', ''),
                "attachments": []
            }
            
            # 添加附件信息
            if 'VpcAttachments' in vgw:
                for attachment in vgw['VpcAttachments']:
                    vgw_data['attachments'].append({
                        "vpc_id": attachment.get('VpcId', ''),
                        "state": attachment.get('State', '')
                    })
            
            # 添加标签
            if include_tags and 'Tags' in vgw:
                vgw_data['tags'] = extract_tags(vgw['Tags'])
            
            vpn_gateways.append(vgw_data)
    
    return vpn_gateways

def scan_vpn_connections(session, max_items, include_tags):
    """扫描VPN连接资源"""
    ec2_client = session.client('ec2')
    vpn_connections = []
    
    paginator = ec2_client.get_paginator('describe_vpn_connections')
    page_iterator = paginate_with_optional_limit(paginator, max_items)
    
    for page in page_iterator:
        for vpn in page['VpnConnections']:
            vpn_data = {
                "resource_id": vpn['VpnConnectionId'],
                "resource_type": "vpn_connection",
                "state": vpn.get('State', ''),
                "type": vpn.get('Type', ''),
                "customer_gateway_id": vpn.get('CustomerGatewayId', ''),
                "vpn_gateway_id": vpn.get('VpnGatewayId', ''),
                "transit_gateway_id": vpn.get('TransitGatewayId', ''),
                "category": vpn.get('Category', '')
            }
            
            # 添加选项信息
            if 'Options' in vpn:
                vpn_data['options'] = vpn['Options']
            
            # 添加路由信息
            if 'Routes' in vpn:
                vpn_data['routes'] = vpn['Routes']
            
            # 添加标签
            if include_tags and 'Tags' in vpn:
                vpn_data['tags'] = extract_tags(vpn['Tags'])
            
            vpn_connections.append(vpn_data)
    
    return vpn_connections

def scan_direct_connect_gateways(session, max_items, include_tags):
    """扫描Direct Connect网关资源"""
    try:
        dx_client = session.client('directconnect')
        direct_connect_gateways = []
        
        # Direct Connect Gateway没有分页器，需要手动实现
        kwargs = {}
        if max_items is not None:
            kwargs["maxResults"] = max_items
        response = dx_client.describe_direct_connect_gateways(**kwargs)
        
        for dcgw in response.get('directConnectGateways', []):
            dcgw_data = {
                "resource_id": dcgw.get('directConnectGatewayId', ''),
                "resource_type": "direct_connect_gateway",
                "name": dcgw.get('directConnectGatewayName', ''),
                "amazon_side_asn": dcgw.get('amazonSideAsn', ''),
                "owner_account": dcgw.get('ownerAccount', ''),
                "state": dcgw.get('directConnectGatewayState', '')
            }
            
            # 获取关联的虚拟接口
            try:
                vi_kwargs = {"directConnectGatewayId": dcgw_data['resource_id']}
                if max_items is not None:
                    vi_kwargs["maxResults"] = max_items
                vi_response = dx_client.describe_direct_connect_gateway_attachments(**vi_kwargs)
                
                dcgw_data['attachments'] = []
                for attachment in vi_response.get('directConnectGatewayAttachments', []):
                    dcgw_data['attachments'].append({
                        "virtual_interface_id": attachment.get('virtualInterfaceId', ''),
                        "virtual_interface_region": attachment.get('virtualInterfaceRegion', ''),
                        "virtual_interface_owner_account": attachment.get('virtualInterfaceOwnerAccount', ''),
                        "attachment_state": attachment.get('attachmentState', '')
                    })
            except Exception as e:
                logger.warning(f"无法获取Direct Connect Gateway附件: {str(e)}")
            
            # 获取关联的VGW
            try:
                assoc_kwargs = {"directConnectGatewayId": dcgw_data['resource_id']}
                if max_items is not None:
                    assoc_kwargs["maxResults"] = max_items
                vgw_response = dx_client.describe_direct_connect_gateway_associations(**assoc_kwargs)
                
                dcgw_data['associations'] = []
                for assoc in vgw_response.get('directConnectGatewayAssociations', []):
                    association = {
                        "association_state": assoc.get('associationState', '')
                    }
                    
                    if 'virtualGatewayId' in assoc:
                        association['virtual_gateway_id'] = assoc['virtualGatewayId']
                        association['virtual_gateway_region'] = assoc.get('virtualGatewayRegion', '')
                        association['virtual_gateway_owner_account'] = assoc.get('virtualGatewayOwnerAccount', '')
                    
                    if 'transitGatewayId' in assoc:
                        association['transit_gateway_id'] = assoc['transitGatewayId']
                        association['transit_gateway_region'] = assoc.get('transitGatewayRegion', '')
                        association['transit_gateway_owner_account'] = assoc.get('transitGatewayOwnerAccount', '')
                    
                    dcgw_data['associations'].append(association)
            except Exception as e:
                logger.warning(f"无法获取Direct Connect Gateway关联: {str(e)}")
            
            direct_connect_gateways.append(dcgw_data)
        
        return direct_connect_gateways
    
    except Exception as e:
        logger.warning(f"无法获取Direct Connect Gateway: {str(e)}")
        return []

def scan_vpc_endpoints(session, max_items, include_tags):
    """扫描VPC终端节点资源"""
    ec2_client = session.client('ec2')
    vpc_endpoints = []
    
    paginator = ec2_client.get_paginator('describe_vpc_endpoints')
    page_iterator = paginate_with_optional_limit(paginator, max_items)
    
    for page in page_iterator:
        for endpoint in page['VpcEndpoints']:
            endpoint_data = {
                "resource_id": endpoint['VpcEndpointId'],
                "resource_type": "vpc_endpoint",
                "vpc_id": endpoint.get('VpcId', ''),
                "service_name": endpoint.get('ServiceName', ''),
                "state": endpoint.get('State', ''),
                "endpoint_type": endpoint.get('VpcEndpointType', ''),
                "private_dns_enabled": endpoint.get('PrivateDnsEnabled', False),
                "requester_managed": endpoint.get('RequesterManaged', False),
                "network_interface_ids": endpoint.get('NetworkInterfaceIds', []),
                "subnet_ids": endpoint.get('SubnetIds', []),
                "route_table_ids": endpoint.get('RouteTableIds', []),
                "groups": []
            }
            
            # 添加安全组信息
            if 'Groups' in endpoint:
                for group in endpoint['Groups']:
                    endpoint_data['groups'].append({
                        "group_id": group.get('GroupId', ''),
                        "group_name": group.get('GroupName', '')
                    })
            
            # 添加策略文档
            if 'PolicyDocument' in endpoint:
                endpoint_data['policy_document'] = endpoint['PolicyDocument']
            
            # 添加标签
            if include_tags and 'Tags' in endpoint:
                endpoint_data['tags'] = extract_tags(endpoint['Tags'])
            
            vpc_endpoints.append(endpoint_data)
    
    return vpc_endpoints

def scan_security_groups(session, max_items, include_tags):
    """扫描安全组资源"""
    ec2_client = session.client('ec2')
    security_groups = []
    
    paginator = ec2_client.get_paginator('describe_security_groups')
    page_iterator = paginate_with_optional_limit(paginator, max_items)
    
    for page in page_iterator:
        for sg in page['SecurityGroups']:
            sg_data = {
                "resource_id": sg['GroupId'],
                "resource_type": "security_group",
                "name": sg.get('GroupName', ''),
                "description": sg.get('Description', ''),
                "vpc_id": sg.get('VpcId', ''),
                "owner_id": sg.get('OwnerId', ''),
                "inbound_rules": [],
                "outbound_rules": []
            }
            
            # 添加入站规则
            if 'IpPermissions' in sg:
                for rule in sg['IpPermissions']:
                    rule_data = {
                        "ip_protocol": rule.get('IpProtocol', ''),
                        "from_port": rule.get('FromPort', ''),
                        "to_port": rule.get('ToPort', ''),
                        "ip_ranges": [],
                        "ipv6_ranges": [],
                        "prefix_list_ids": [],
                        "user_id_group_pairs": []
                    }
                    
                    # 添加IP范围
                    if 'IpRanges' in rule:
                        for ip_range in rule['IpRanges']:
                            rule_data['ip_ranges'].append({
                                "cidr_ip": ip_range.get('CidrIp', ''),
                                "description": ip_range.get('Description', '')
                            })
                    
                    # 添加IPv6范围
                    if 'Ipv6Ranges' in rule:
                        for ipv6_range in rule['Ipv6Ranges']:
                            rule_data['ipv6_ranges'].append({
                                "cidr_ipv6": ipv6_range.get('CidrIpv6', ''),
                                "description": ipv6_range.get('Description', '')
                            })
                    
                    # 添加前缀列表ID
                    if 'PrefixListIds' in rule:
                        for prefix in rule['PrefixListIds']:
                            rule_data['prefix_list_ids'].append({
                                "prefix_list_id": prefix.get('PrefixListId', ''),
                                "description": prefix.get('Description', '')
                            })
                    
                    # 添加用户组对
                    if 'UserIdGroupPairs' in rule:
                        for group_pair in rule['UserIdGroupPairs']:
                            rule_data['user_id_group_pairs'].append({
                                "group_id": group_pair.get('GroupId', ''),
                                "user_id": group_pair.get('UserId', ''),
                                "vpc_id": group_pair.get('VpcId', ''),
                                "vpc_peering_connection_id": group_pair.get('VpcPeeringConnectionId', ''),
                                "description": group_pair.get('Description', '')
                            })
                    
                    sg_data['inbound_rules'].append(rule_data)
            
            # 添加出站规则
            if 'IpPermissionsEgress' in sg:
                for rule in sg['IpPermissionsEgress']:
                    rule_data = {
                        "ip_protocol": rule.get('IpProtocol', ''),
                        "from_port": rule.get('FromPort', ''),
                        "to_port": rule.get('ToPort', ''),
                        "ip_ranges": [],
                        "ipv6_ranges": [],
                        "prefix_list_ids": [],
                        "user_id_group_pairs": []
                    }
                    
                    # 添加IP范围
                    if 'IpRanges' in rule:
                        for ip_range in rule['IpRanges']:
                            rule_data['ip_ranges'].append({
                                "cidr_ip": ip_range.get('CidrIp', ''),
                                "description": ip_range.get('Description', '')
                            })
                    
                    # 添加IPv6范围
                    if 'Ipv6Ranges' in rule:
                        for ipv6_range in rule['Ipv6Ranges']:
                            rule_data['ipv6_ranges'].append({
                                "cidr_ipv6": ipv6_range.get('CidrIpv6', ''),
                                "description": ipv6_range.get('Description', '')
                            })
                    
                    # 添加前缀列表ID
                    if 'PrefixListIds' in rule:
                        for prefix in rule['PrefixListIds']:
                            rule_data['prefix_list_ids'].append({
                                "prefix_list_id": prefix.get('PrefixListId', ''),
                                "description": prefix.get('Description', '')
                            })
                    
                    # 添加用户组对
                    if 'UserIdGroupPairs' in rule:
                        for group_pair in rule['UserIdGroupPairs']:
                            rule_data['user_id_group_pairs'].append({
                                "group_id": group_pair.get('GroupId', ''),
                                "user_id": group_pair.get('UserId', ''),
                                "vpc_id": group_pair.get('VpcId', ''),
                                "vpc_peering_connection_id": group_pair.get('VpcPeeringConnectionId', ''),
                                "description": group_pair.get('Description', '')
                            })
                    
                    sg_data['outbound_rules'].append(rule_data)
            
            # 添加标签
            if include_tags and 'Tags' in sg:
                sg_data['tags'] = extract_tags(sg['Tags'])
            
            security_groups.append(sg_data)
    
    return security_groups

def scan_network_acls(session, max_items, include_tags):
    """扫描网络ACL资源"""
    ec2_client = session.client('ec2')
    network_acls = []
    
    paginator = ec2_client.get_paginator('describe_network_acls')
    page_iterator = paginate_with_optional_limit(paginator, max_items)
    
    for page in page_iterator:
        for acl in page['NetworkAcls']:
            acl_data = {
                "resource_id": acl['NetworkAclId'],
                "resource_type": "network_acl",
                "vpc_id": acl.get('VpcId', ''),
                "is_default": acl.get('IsDefault', False),
                "owner_id": acl.get('OwnerId', ''),
                "associations": [],
                "entries": []
            }
            
            # 添加关联信息
            if 'Associations' in acl:
                for assoc in acl['Associations']:
                    acl_data['associations'].append({
                        "network_acl_association_id": assoc.get('NetworkAclAssociationId', ''),
                        "subnet_id": assoc.get('SubnetId', '')
                    })
            
            # 添加条目信息
            if 'Entries' in acl:
                for entry in acl['Entries']:
                    entry_data = {
                        "rule_number": entry.get('RuleNumber', 0),
                        "protocol": entry.get('Protocol', ''),
                        "rule_action": entry.get('RuleAction', ''),
                        "egress": entry.get('Egress', False),
                        "cidr_block": entry.get('CidrBlock', ''),
                        "ipv6_cidr_block": entry.get('Ipv6CidrBlock', '')
                    }
                    
                    # 添加端口范围
                    if 'PortRange' in entry:
                        entry_data['port_range'] = {
                            "from": entry['PortRange'].get('From', 0),
                            "to": entry['PortRange'].get('To', 0)
                        }
                    
                    acl_data['entries'].append(entry_data)
            
            # 添加标签
            if include_tags and 'Tags' in acl:
                acl_data['tags'] = extract_tags(acl['Tags'])
            
            network_acls.append(acl_data)
    
    return network_acls

def scan_elastic_ips(session, max_items):
    """扫描弹性IP资源"""
    ec2_client = session.client('ec2')
    elastic_ips = []
    
    paginator = ec2_client.get_paginator('describe_addresses')
    page_iterator = paginate_with_optional_limit(paginator, max_items)
    
    for page in page_iterator:
        for eip in page['Addresses']:
            eip_data = {
                "resource_id": eip.get('AllocationId', ''),
                "resource_type": "elastic_ip",
                "public_ip": eip.get('PublicIp', ''),
                "private_ip_address": eip.get('PrivateIpAddress', ''),
                "domain": eip.get('Domain', ''),
                "instance_id": eip.get('InstanceId', ''),
                "network_interface_id": eip.get('NetworkInterfaceId', ''),
                "network_interface_owner_id": eip.get('NetworkInterfaceOwnerId', ''),
                "association_id": eip.get('AssociationId', ''),
                "public_ipv4_pool": eip.get('PublicIpv4Pool', '')
            }
            
            elastic_ips.append(eip_data)
    
    return elastic_ips

def scan_flow_logs(session, max_items, include_tags):
    """扫描流日志资源"""
    ec2_client = session.client('ec2')
    flow_logs = []
    
    paginator = ec2_client.get_paginator('describe_flow_logs')
    page_iterator = paginate_with_optional_limit(paginator, max_items)
    
    for page in page_iterator:
        for log in page['FlowLogs']:
            log_data = {
                "resource_id": log['FlowLogId'],
                "resource_type": "flow_log",
                "creation_time": log.get('CreationTime', ''),
                "deliver_logs_status": log.get('DeliverLogsStatus', ''),
                "deliver_logs_error_message": log.get('DeliverLogsErrorMessage', ''),
                "flow_log_status": log.get('FlowLogStatus', ''),
                "log_group_name": log.get('LogGroupName', ''),
                "resource_ids": log.get('ResourceIds', []),
                "traffic_type": log.get('TrafficType', ''),
                "log_destination_type": log.get('LogDestinationType', ''),
                "log_destination": log.get('LogDestination', '')
            }
            
            # 添加标签
            if include_tags and 'Tags' in log:
                log_data['tags'] = extract_tags(log['Tags'])
            
            flow_logs.append(log_data)
    
    return flow_logs

def scan_ec2_instances(session, max_items, include_tags):
    """扫描EC2实例资源"""
    ec2_client = session.client('ec2')
    ec2_instances = []
    
    paginator = ec2_client.get_paginator('describe_instances')
    page_iterator = paginate_with_optional_limit(paginator, max_items)
    
    for page in page_iterator:
        for reservation in page['Reservations']:
            for instance in reservation['Instances']:
                instance_data = {
                    "resource_id": instance['InstanceId'],
                    "resource_type": "ec2",
                    "instance_type": instance.get('InstanceType', ''),
                    "state": instance.get('State', {}).get('Name', ''),
                    "private_ip_address": instance.get('PrivateIpAddress', ''),
                    "public_ip_address": instance.get('PublicIpAddress', ''),
                    "vpc_id": instance.get('VpcId', ''),
                    "subnet_id": instance.get('SubnetId', ''),
                    "availability_zone": instance.get('Placement', {}).get('AvailabilityZone', ''),
                    "launch_time": instance.get('LaunchTime', ''),
                    "security_groups": [],
                    "network_interfaces": []
                }
                
                # 添加安全组信息
                if 'SecurityGroups' in instance:
                    for sg in instance['SecurityGroups']:
                        instance_data['security_groups'].append({
                            "group_id": sg.get('GroupId', ''),
                            "group_name": sg.get('GroupName', '')
                        })
                
                # 添加网络接口信息
                if 'NetworkInterfaces' in instance:
                    for ni in instance['NetworkInterfaces']:
                        ni_data = {
                            "network_interface_id": ni.get('NetworkInterfaceId', ''),
                            "status": ni.get('Status', ''),
                            "subnet_id": ni.get('SubnetId', ''),
                            "vpc_id": ni.get('VpcId', ''),
                            "private_ip_address": ni.get('PrivateIpAddress', ''),
                            "private_dns_name": ni.get('PrivateDnsName', ''),
                            "association": {}
                        }
                        
                        # 添加关联信息
                        if 'Association' in ni:
                            assoc = ni['Association']
                            ni_data['association'] = {
                                "public_ip": assoc.get('PublicIp', ''),
                                "public_dns_name": assoc.get('PublicDnsName', '')
                            }
                        
                        # 添加安全组信息
                        if 'Groups' in ni:
                            ni_data['groups'] = []
                            for group in ni['Groups']:
                                ni_data['groups'].append({
                                    "group_id": group.get('GroupId', ''),
                                    "group_name": group.get('GroupName', '')
                                })
                        
                        instance_data['network_interfaces'].append(ni_data)
                
                # 添加标签
                if include_tags and 'Tags' in instance:
                    instance_data['tags'] = extract_tags(instance['Tags'])
                
                ec2_instances.append(instance_data)
    
    return ec2_instances

def scan_rds_instances(session, max_items, include_tags):
    """扫描RDS实例资源"""
    rds_client = session.client('rds')
    rds_instances = []
    
    paginator = rds_client.get_paginator('describe_db_instances')
    page_iterator = paginate_with_optional_limit(paginator, max_items)
    
    for page in page_iterator:
        for instance in page['DBInstances']:
            instance_data = {
                "resource_id": instance['DBInstanceIdentifier'],
                "resource_type": "rds",
                "engine": instance.get('Engine', ''),
                "engine_version": instance.get('EngineVersion', ''),
                "status": instance.get('DBInstanceStatus', ''),
                "instance_class": instance.get('DBInstanceClass', ''),
                "allocated_storage": instance.get('AllocatedStorage', 0),
                "storage_type": instance.get('StorageType', ''),
                "availability_zone": instance.get('AvailabilityZone', ''),
                "multi_az": instance.get('MultiAZ', False),
                "publicly_accessible": instance.get('PubliclyAccessible', False),
                "vpc_id": instance.get('DBSubnetGroup', {}).get('VpcId', ''),
                "subnet_group": instance.get('DBSubnetGroup', {}).get('DBSubnetGroupName', ''),
                "endpoint": {},
                "vpc_security_groups": []
            }
            
            # 添加端点信息
            if 'Endpoint' in instance:
                instance_data['endpoint'] = {
                    "address": instance['Endpoint'].get('Address', ''),
                    "port": instance['Endpoint'].get('Port', 0),
                    "hosted_zone_id": instance['Endpoint'].get('HostedZoneId', '')
                }
            
            # 添加安全组信息
            if 'VpcSecurityGroups' in instance:
                for sg in instance['VpcSecurityGroups']:
                    instance_data['vpc_security_groups'].append({
                        "vpc_security_group_id": sg.get('VpcSecurityGroupId', ''),
                        "status": sg.get('Status', '')
                    })
            
            # 添加子网信息
            if 'DBSubnetGroup' in instance and 'Subnets' in instance['DBSubnetGroup']:
                instance_data['subnets'] = []
                for subnet in instance['DBSubnetGroup']['Subnets']:
                    instance_data['subnets'].append({
                        "subnet_identifier": subnet.get('SubnetIdentifier', ''),
                        "subnet_availability_zone": subnet.get('SubnetAvailabilityZone', {}).get('Name', ''),
                        "subnet_status": subnet.get('SubnetStatus', '')
                    })
            
            # 添加标签
            if include_tags:
                try:
                    tags_response = rds_client.list_tags_for_resource(
                        ResourceName=instance['DBInstanceArn']
                    )
                    if 'TagList' in tags_response:
                        instance_data['tags'] = extract_tags(tags_response['TagList'])
                except Exception as e:
                    logger.warning(f"无法获取RDS实例标签: {str(e)}")
            
            rds_instances.append(instance_data)
    
    return rds_instances