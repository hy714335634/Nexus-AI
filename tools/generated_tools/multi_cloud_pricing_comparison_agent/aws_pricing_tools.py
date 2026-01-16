"""
AWS价格查询工具集

提供AWS各类服务的真实价格查询功能，通过boto3 pricing client调用AWS Pricing API获取实时价格数据。

支持的服务：
- EC2: 弹性计算实例
- EBS: 弹性块存储
- S3: 对象存储
- RDS: 关系数据库服务
- ElastiCache: 缓存服务
- OpenSearch: 搜索服务
- ELB: 负载均衡器
- 网络流量: 数据传输费用

作者: Nexus-AI Build Workflow
日期: 2026-01-14
"""

import json
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AWSPricingClient:
    """AWS Pricing API客户端封装类"""
    
    def __init__(self, region: str = "us-east-1"):
        """
        初始化AWS Pricing客户端
        
        Args:
            region: AWS区域，Pricing API仅在us-east-1和ap-south-1可用
        """
        try:
            self.client = boto3.client('pricing', region_name=region)
            logger.info(f"AWS Pricing客户端初始化成功，区域: {region}")
        except Exception as e:
            logger.error(f"初始化AWS Pricing客户端失败: {str(e)}")
            raise
    
    def get_products(
        self,
        service_code: str,
        filters: List[Dict[str, Any]],
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询AWS产品价格
        
        Args:
            service_code: 服务代码（如AmazonEC2、AmazonS3）
            filters: 过滤条件列表
            max_results: 最大返回结果数
            
        Returns:
            产品价格列表
        """
        try:
            response = self.client.get_products(
                ServiceCode=service_code,
                Filters=filters,
                MaxResults=max_results
            )
            
            products = []
            for price_item in response.get('PriceList', []):
                product_data = json.loads(price_item)
                products.append(product_data)
            
            logger.info(f"成功获取 {len(products)} 个产品价格")
            return products
            
        except ClientError as e:
            logger.error(f"AWS API调用失败: {e.response['Error']['Message']}")
            raise
        except Exception as e:
            logger.error(f"获取产品价格失败: {str(e)}")
            raise
    
    def extract_price_from_product(self, product: Dict[str, Any]) -> Optional[float]:
        """
        从产品数据中提取价格
        
        Args:
            product: 产品数据
            
        Returns:
            价格（USD/小时或USD/GB-月），如果无法提取则返回None
        """
        try:
            terms = product.get('terms', {})
            
            # 优先获取按需定价
            on_demand = terms.get('OnDemand', {})
            if on_demand:
                for offer_term in on_demand.values():
                    price_dimensions = offer_term.get('priceDimensions', {})
                    for price_dim in price_dimensions.values():
                        price_per_unit = price_dim.get('pricePerUnit', {})
                        usd_price = price_per_unit.get('USD')
                        if usd_price and usd_price != '0':
                            return float(usd_price)
            
            # 如果没有按需定价，尝试获取预留定价
            reserved = terms.get('Reserved', {})
            if reserved:
                for offer_term in reserved.values():
                    price_dimensions = offer_term.get('priceDimensions', {})
                    for price_dim in price_dimensions.values():
                        price_per_unit = price_dim.get('pricePerUnit', {})
                        usd_price = price_per_unit.get('USD')
                        if usd_price and usd_price != '0':
                            return float(usd_price)
            
            return None
            
        except Exception as e:
            logger.warning(f"提取价格失败: {str(e)}")
            return None


# 全局客户端实例
_pricing_client = None


def get_pricing_client() -> AWSPricingClient:
    """获取或创建全局Pricing客户端"""
    global _pricing_client
    if _pricing_client is None:
        _pricing_client = AWSPricingClient()
    return _pricing_client


@tool
def get_aws_ec2_pricing(
    instance_type: str,
    region: str = "us-east-1",
    operating_system: str = "Linux",
    tenancy: str = "Shared",
    term_type: str = "OnDemand"
) -> str:
    """
    查询AWS EC2实例价格
    
    Args:
        instance_type: 实例类型（如t3.micro、m5.large）
        region: AWS区域（如us-east-1、ap-southeast-1）
        operating_system: 操作系统（Linux、Windows、RHEL、SUSE）
        tenancy: 租户类型（Shared、Dedicated、Host）
        term_type: 定价类型（OnDemand、Reserved）
        
    Returns:
        JSON格式的价格信息，包含hourly_price（USD/小时）、monthly_price（USD/月）、annual_price（USD/年）
    """
    try:
        client = get_pricing_client()
        
        # 构建过滤条件
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
            {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': _get_location_name(region)},
            {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': operating_system},
            {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': tenancy},
            {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
            {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'}
        ]
        
        # 查询产品价格
        products = client.get_products(
            service_code='AmazonEC2',
            filters=filters,
            max_results=10
        )
        
        if not products:
            return json.dumps({
                "success": False,
                "error": f"未找到 {instance_type} 在 {region} 的价格信息",
                "instance_type": instance_type,
                "region": region
            }, ensure_ascii=False)
        
        # 提取价格
        hourly_price = client.extract_price_from_product(products[0])
        
        if hourly_price is None:
            return json.dumps({
                "success": False,
                "error": "无法从返回的数据中提取价格",
                "instance_type": instance_type,
                "region": region
            }, ensure_ascii=False)
        
        # 计算月度和年度价格
        monthly_price = hourly_price * 730  # 平均每月730小时
        annual_price = hourly_price * 8760  # 每年8760小时
        
        result = {
            "success": True,
            "service": "EC2",
            "instance_type": instance_type,
            "region": region,
            "operating_system": operating_system,
            "tenancy": tenancy,
            "term_type": term_type,
            "hourly_price": round(hourly_price, 4),
            "monthly_price": round(monthly_price, 2),
            "annual_price": round(annual_price, 2),
            "currency": "USD",
            "documentation": "https://aws.amazon.com/ec2/pricing/"
        }
        
        logger.info(f"成功获取EC2价格: {instance_type} @ {region} = ${hourly_price}/小时")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取EC2价格失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "instance_type": instance_type,
            "region": region
        }, ensure_ascii=False)


@tool
def get_aws_ebs_pricing(
    volume_type: str,
    region: str = "us-east-1"
) -> str:
    """
    查询AWS EBS存储价格
    
    Args:
        volume_type: 卷类型（gp2、gp3、io1、io2、st1、sc1、standard）
        region: AWS区域
        
    Returns:
        JSON格式的价格信息，包含gb_month_price（USD/GB-月）
    """
    try:
        client = get_pricing_client()
        
        # 卷类型映射
        volume_type_map = {
            "gp2": "General Purpose",
            "gp3": "General Purpose",
            "io1": "Provisioned IOPS",
            "io2": "Provisioned IOPS",
            "st1": "Throughput Optimized HDD",
            "sc1": "Cold HDD",
            "standard": "Magnetic"
        }
        
        volume_api_name = volume_type_map.get(volume_type.lower())
        if not volume_api_name:
            return json.dumps({
                "success": False,
                "error": f"不支持的卷类型: {volume_type}",
                "volume_type": volume_type
            }, ensure_ascii=False)
        
        # 构建过滤条件
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'volumeApiName', 'Value': volume_type.lower()},
            {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': _get_location_name(region)},
            {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'}
        ]
        
        # 查询产品价格
        products = client.get_products(
            service_code='AmazonEC2',
            filters=filters,
            max_results=10
        )
        
        if not products:
            return json.dumps({
                "success": False,
                "error": f"未找到 {volume_type} 在 {region} 的价格信息",
                "volume_type": volume_type,
                "region": region
            }, ensure_ascii=False)
        
        # 提取价格
        gb_month_price = client.extract_price_from_product(products[0])
        
        if gb_month_price is None:
            return json.dumps({
                "success": False,
                "error": "无法从返回的数据中提取价格",
                "volume_type": volume_type,
                "region": region
            }, ensure_ascii=False)
        
        result = {
            "success": True,
            "service": "EBS",
            "volume_type": volume_type,
            "region": region,
            "gb_month_price": round(gb_month_price, 4),
            "currency": "USD",
            "documentation": "https://aws.amazon.com/ebs/pricing/"
        }
        
        logger.info(f"成功获取EBS价格: {volume_type} @ {region} = ${gb_month_price}/GB-月")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取EBS价格失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "volume_type": volume_type,
            "region": region
        }, ensure_ascii=False)


@tool
def get_aws_s3_pricing(
    storage_class: str,
    region: str = "us-east-1"
) -> str:
    """
    查询AWS S3对象存储价格
    
    Args:
        storage_class: 存储类别（Standard、Standard-IA、OneZone-IA、Glacier、Glacier Deep Archive）
        region: AWS区域
        
    Returns:
        JSON格式的价格信息，包含gb_month_price（USD/GB-月）
    """
    try:
        client = get_pricing_client()
        
        # 存储类别映射
        storage_class_map = {
            "standard": "General Purpose",
            "standard-ia": "Infrequent Access",
            "onezone-ia": "One Zone - Infrequent Access",
            "glacier": "Archive",
            "glacier deep archive": "Deep Archive"
        }
        
        storage_class_value = storage_class_map.get(storage_class.lower())
        if not storage_class_value:
            return json.dumps({
                "success": False,
                "error": f"不支持的存储类别: {storage_class}",
                "storage_class": storage_class
            }, ensure_ascii=False)
        
        # 构建过滤条件
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': _get_location_name(region)},
            {'Type': 'TERM_MATCH', 'Field': 'storageClass', 'Value': storage_class_value},
            {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'}
        ]
        
        # 查询产品价格
        products = client.get_products(
            service_code='AmazonS3',
            filters=filters,
            max_results=10
        )
        
        if not products:
            return json.dumps({
                "success": False,
                "error": f"未找到 {storage_class} 在 {region} 的价格信息",
                "storage_class": storage_class,
                "region": region
            }, ensure_ascii=False)
        
        # 提取价格
        gb_month_price = client.extract_price_from_product(products[0])
        
        if gb_month_price is None:
            return json.dumps({
                "success": False,
                "error": "无法从返回的数据中提取价格",
                "storage_class": storage_class,
                "region": region
            }, ensure_ascii=False)
        
        result = {
            "success": True,
            "service": "S3",
            "storage_class": storage_class,
            "region": region,
            "gb_month_price": round(gb_month_price, 4),
            "currency": "USD",
            "documentation": "https://aws.amazon.com/s3/pricing/"
        }
        
        logger.info(f"成功获取S3价格: {storage_class} @ {region} = ${gb_month_price}/GB-月")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取S3价格失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "storage_class": storage_class,
            "region": region
        }, ensure_ascii=False)


@tool
def get_aws_rds_pricing(
    instance_type: str,
    database_engine: str,
    region: str = "us-east-1",
    deployment_option: str = "Single-AZ"
) -> str:
    """
    查询AWS RDS数据库价格
    
    Args:
        instance_type: 实例类型（如db.t3.micro、db.m5.large）
        database_engine: 数据库引擎（MySQL、PostgreSQL、MariaDB、Oracle、SQL Server）
        region: AWS区域
        deployment_option: 部署选项（Single-AZ、Multi-AZ）
        
    Returns:
        JSON格式的价格信息，包含hourly_price、monthly_price、annual_price
    """
    try:
        client = get_pricing_client()
        
        # 构建过滤条件
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
            {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': _get_location_name(region)},
            {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': database_engine},
            {'Type': 'TERM_MATCH', 'Field': 'deploymentOption', 'Value': deployment_option}
        ]
        
        # 查询产品价格
        products = client.get_products(
            service_code='AmazonRDS',
            filters=filters,
            max_results=10
        )
        
        if not products:
            return json.dumps({
                "success": False,
                "error": f"未找到 {instance_type} ({database_engine}) 在 {region} 的价格信息",
                "instance_type": instance_type,
                "database_engine": database_engine,
                "region": region
            }, ensure_ascii=False)
        
        # 提取价格
        hourly_price = client.extract_price_from_product(products[0])
        
        if hourly_price is None:
            return json.dumps({
                "success": False,
                "error": "无法从返回的数据中提取价格",
                "instance_type": instance_type,
                "database_engine": database_engine,
                "region": region
            }, ensure_ascii=False)
        
        # 计算月度和年度价格
        monthly_price = hourly_price * 730
        annual_price = hourly_price * 8760
        
        result = {
            "success": True,
            "service": "RDS",
            "instance_type": instance_type,
            "database_engine": database_engine,
            "region": region,
            "deployment_option": deployment_option,
            "hourly_price": round(hourly_price, 4),
            "monthly_price": round(monthly_price, 2),
            "annual_price": round(annual_price, 2),
            "currency": "USD",
            "documentation": "https://aws.amazon.com/rds/pricing/"
        }
        
        logger.info(f"成功获取RDS价格: {instance_type} ({database_engine}) @ {region} = ${hourly_price}/小时")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取RDS价格失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "instance_type": instance_type,
            "database_engine": database_engine,
            "region": region
        }, ensure_ascii=False)


@tool
def get_aws_elasticache_pricing(
    instance_type: str,
    cache_engine: str,
    region: str = "us-east-1"
) -> str:
    """
    查询AWS ElastiCache缓存服务价格
    
    Args:
        instance_type: 实例类型（如cache.t3.micro、cache.m5.large）
        cache_engine: 缓存引擎（Redis、Memcached）
        region: AWS区域
        
    Returns:
        JSON格式的价格信息，包含hourly_price、monthly_price、annual_price
    """
    try:
        client = get_pricing_client()
        
        # 构建过滤条件
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
            {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': _get_location_name(region)},
            {'Type': 'TERM_MATCH', 'Field': 'cacheEngine', 'Value': cache_engine}
        ]
        
        # 查询产品价格
        products = client.get_products(
            service_code='AmazonElastiCache',
            filters=filters,
            max_results=10
        )
        
        if not products:
            return json.dumps({
                "success": False,
                "error": f"未找到 {instance_type} ({cache_engine}) 在 {region} 的价格信息",
                "instance_type": instance_type,
                "cache_engine": cache_engine,
                "region": region
            }, ensure_ascii=False)
        
        # 提取价格
        hourly_price = client.extract_price_from_product(products[0])
        
        if hourly_price is None:
            return json.dumps({
                "success": False,
                "error": "无法从返回的数据中提取价格",
                "instance_type": instance_type,
                "cache_engine": cache_engine,
                "region": region
            }, ensure_ascii=False)
        
        # 计算月度和年度价格
        monthly_price = hourly_price * 730
        annual_price = hourly_price * 8760
        
        result = {
            "success": True,
            "service": "ElastiCache",
            "instance_type": instance_type,
            "cache_engine": cache_engine,
            "region": region,
            "hourly_price": round(hourly_price, 4),
            "monthly_price": round(monthly_price, 2),
            "annual_price": round(annual_price, 2),
            "currency": "USD",
            "documentation": "https://aws.amazon.com/elasticache/pricing/"
        }
        
        logger.info(f"成功获取ElastiCache价格: {instance_type} ({cache_engine}) @ {region} = ${hourly_price}/小时")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取ElastiCache价格失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "instance_type": instance_type,
            "cache_engine": cache_engine,
            "region": region
        }, ensure_ascii=False)


@tool
def get_aws_opensearch_pricing(
    instance_type: str,
    region: str = "us-east-1"
) -> str:
    """
    查询AWS OpenSearch服务价格
    
    Args:
        instance_type: 实例类型（如t3.small.search、m5.large.search）
        region: AWS区域
        
    Returns:
        JSON格式的价格信息，包含hourly_price、monthly_price、annual_price
    """
    try:
        client = get_pricing_client()
        
        # 构建过滤条件
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
            {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': _get_location_name(region)}
        ]
        
        # 查询产品价格
        products = client.get_products(
            service_code='AmazonES',
            filters=filters,
            max_results=10
        )
        
        if not products:
            return json.dumps({
                "success": False,
                "error": f"未找到 {instance_type} 在 {region} 的价格信息",
                "instance_type": instance_type,
                "region": region
            }, ensure_ascii=False)
        
        # 提取价格
        hourly_price = client.extract_price_from_product(products[0])
        
        if hourly_price is None:
            return json.dumps({
                "success": False,
                "error": "无法从返回的数据中提取价格",
                "instance_type": instance_type,
                "region": region
            }, ensure_ascii=False)
        
        # 计算月度和年度价格
        monthly_price = hourly_price * 730
        annual_price = hourly_price * 8760
        
        result = {
            "success": True,
            "service": "OpenSearch",
            "instance_type": instance_type,
            "region": region,
            "hourly_price": round(hourly_price, 4),
            "monthly_price": round(monthly_price, 2),
            "annual_price": round(annual_price, 2),
            "currency": "USD",
            "documentation": "https://aws.amazon.com/opensearch-service/pricing/"
        }
        
        logger.info(f"成功获取OpenSearch价格: {instance_type} @ {region} = ${hourly_price}/小时")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取OpenSearch价格失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "instance_type": instance_type,
            "region": region
        }, ensure_ascii=False)


@tool
def get_aws_elb_pricing(
    load_balancer_type: str,
    region: str = "us-east-1"
) -> str:
    """
    查询AWS ELB负载均衡器价格
    
    Args:
        load_balancer_type: 负载均衡器类型（ALB、NLB、CLB、GWLB）
        region: AWS区域
        
    Returns:
        JSON格式的价格信息，包含hourly_price、lcu_hour_price（ALB/NLB）
    """
    try:
        client = get_pricing_client()
        
        # 负载均衡器类型映射
        lb_type_map = {
            "alb": "Application",
            "nlb": "Network",
            "clb": "Classic",
            "gwlb": "Gateway"
        }
        
        lb_type_value = lb_type_map.get(load_balancer_type.lower())
        if not lb_type_value:
            return json.dumps({
                "success": False,
                "error": f"不支持的负载均衡器类型: {load_balancer_type}",
                "load_balancer_type": load_balancer_type
            }, ensure_ascii=False)
        
        # 构建过滤条件
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': _get_location_name(region)},
            {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Load Balancer'}
        ]
        
        if load_balancer_type.lower() != "clb":
            filters.append({'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': f'LoadBalancerUsage'})
        
        # 查询产品价格
        products = client.get_products(
            service_code='AWSELB',
            filters=filters,
            max_results=10
        )
        
        if not products:
            return json.dumps({
                "success": False,
                "error": f"未找到 {load_balancer_type} 在 {region} 的价格信息",
                "load_balancer_type": load_balancer_type,
                "region": region
            }, ensure_ascii=False)
        
        # 提取价格
        hourly_price = client.extract_price_from_product(products[0])
        
        if hourly_price is None:
            return json.dumps({
                "success": False,
                "error": "无法从返回的数据中提取价格",
                "load_balancer_type": load_balancer_type,
                "region": region
            }, ensure_ascii=False)
        
        result = {
            "success": True,
            "service": "ELB",
            "load_balancer_type": load_balancer_type,
            "region": region,
            "hourly_price": round(hourly_price, 4),
            "monthly_price": round(hourly_price * 730, 2),
            "annual_price": round(hourly_price * 8760, 2),
            "currency": "USD",
            "documentation": "https://aws.amazon.com/elasticloadbalancing/pricing/"
        }
        
        logger.info(f"成功获取ELB价格: {load_balancer_type} @ {region} = ${hourly_price}/小时")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取ELB价格失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "load_balancer_type": load_balancer_type,
            "region": region
        }, ensure_ascii=False)


@tool
def get_aws_network_pricing(
    transfer_type: str,
    region: str = "us-east-1"
) -> str:
    """
    查询AWS网络数据传输价格
    
    Args:
        transfer_type: 传输类型（DataTransfer-Out-Bytes、DataTransfer-In-Bytes、InterRegion-Out、InterRegion-In）
        region: AWS区域
        
    Returns:
        JSON格式的价格信息，包含gb_price（USD/GB）
    """
    try:
        client = get_pricing_client()
        
        # 构建过滤条件
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': _get_location_name(region)},
            {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Data Transfer'}
        ]
        
        # 查询产品价格
        products = client.get_products(
            service_code='AmazonEC2',
            filters=filters,
            max_results=50
        )
        
        if not products:
            return json.dumps({
                "success": False,
                "error": f"未找到网络传输价格在 {region}",
                "transfer_type": transfer_type,
                "region": region
            }, ensure_ascii=False)
        
        # 提取价格
        gb_price = client.extract_price_from_product(products[0])
        
        if gb_price is None:
            return json.dumps({
                "success": False,
                "error": "无法从返回的数据中提取价格",
                "transfer_type": transfer_type,
                "region": region
            }, ensure_ascii=False)
        
        result = {
            "success": True,
            "service": "Network",
            "transfer_type": transfer_type,
            "region": region,
            "gb_price": round(gb_price, 4),
            "currency": "USD",
            "documentation": "https://aws.amazon.com/ec2/pricing/on-demand/"
        }
        
        logger.info(f"成功获取网络传输价格: {transfer_type} @ {region} = ${gb_price}/GB")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取网络传输价格失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "transfer_type": transfer_type,
            "region": region
        }, ensure_ascii=False)


def _get_location_name(region: str) -> str:
    """
    将AWS区域代码转换为位置名称
    
    Args:
        region: AWS区域代码（如us-east-1）
        
    Returns:
        位置名称（如US East (N. Virginia)）
    """
    region_map = {
        "us-east-1": "US East (N. Virginia)",
        "us-east-2": "US East (Ohio)",
        "us-west-1": "US West (N. California)",
        "us-west-2": "US West (Oregon)",
        "ca-central-1": "Canada (Central)",
        "eu-west-1": "EU (Ireland)",
        "eu-west-2": "EU (London)",
        "eu-west-3": "EU (Paris)",
        "eu-central-1": "EU (Frankfurt)",
        "eu-north-1": "EU (Stockholm)",
        "ap-south-1": "Asia Pacific (Mumbai)",
        "ap-northeast-1": "Asia Pacific (Tokyo)",
        "ap-northeast-2": "Asia Pacific (Seoul)",
        "ap-northeast-3": "Asia Pacific (Osaka)",
        "ap-southeast-1": "Asia Pacific (Singapore)",
        "ap-southeast-2": "Asia Pacific (Sydney)",
        "sa-east-1": "South America (Sao Paulo)",
        "cn-north-1": "China (Beijing)",
        "cn-northwest-1": "China (Ningxia)"
    }
    
    return region_map.get(region, region)


@tool
def recommend_aws_instances(
    vcpu: int,
    memory_gb: float,
    environment: str = "production",
    region: str = "us-east-1"
) -> str:
    """
    根据vCPU和内存需求推荐AWS实例类型
    
    Args:
        vcpu: vCPU核心数
        memory_gb: 内存大小（GB）
        environment: 环境类型（production、development、test）
        region: AWS区域
        
    Returns:
        JSON格式的推荐结果，包含recommended_instances列表，每个实例包含instance_type、vcpu、memory、price等信息
    """
    try:
        # AWS实例规格数据库（简化版，实际应从API或数据库获取）
        instance_specs = {
            # 通用型 - 当前代
            "m6i.large": {"vcpu": 2, "memory": 8, "generation": "6", "family": "m", "burstable": False},
            "m6i.xlarge": {"vcpu": 4, "memory": 16, "generation": "6", "family": "m", "burstable": False},
            "m6i.2xlarge": {"vcpu": 8, "memory": 32, "generation": "6", "family": "m", "burstable": False},
            "m6i.4xlarge": {"vcpu": 16, "memory": 64, "generation": "6", "family": "m", "burstable": False},
            "m5.large": {"vcpu": 2, "memory": 8, "generation": "5", "family": "m", "burstable": False},
            "m5.xlarge": {"vcpu": 4, "memory": 16, "generation": "5", "family": "m", "burstable": False},
            "m5.2xlarge": {"vcpu": 8, "memory": 32, "generation": "5", "family": "m", "burstable": False},
            "m5.4xlarge": {"vcpu": 16, "memory": 64, "generation": "5", "family": "m", "burstable": False},
            
            # 计算优化型
            "c6i.large": {"vcpu": 2, "memory": 4, "generation": "6", "family": "c", "burstable": False},
            "c6i.xlarge": {"vcpu": 4, "memory": 8, "generation": "6", "family": "c", "burstable": False},
            "c6i.2xlarge": {"vcpu": 8, "memory": 16, "generation": "6", "family": "c", "burstable": False},
            "c5.large": {"vcpu": 2, "memory": 4, "generation": "5", "family": "c", "burstable": False},
            "c5.xlarge": {"vcpu": 4, "memory": 8, "generation": "5", "family": "c", "burstable": False},
            
            # 内存优化型
            "r6i.large": {"vcpu": 2, "memory": 16, "generation": "6", "family": "r", "burstable": False},
            "r6i.xlarge": {"vcpu": 4, "memory": 32, "generation": "6", "family": "r", "burstable": False},
            "r6i.2xlarge": {"vcpu": 8, "memory": 64, "generation": "6", "family": "r", "burstable": False},
            "r5.large": {"vcpu": 2, "memory": 16, "generation": "5", "family": "r", "burstable": False},
            "r5.xlarge": {"vcpu": 4, "memory": 32, "generation": "5", "family": "r", "burstable": False},
            
            # 突发性能型（仅用于测试/开发）
            "t3.micro": {"vcpu": 2, "memory": 1, "generation": "3", "family": "t", "burstable": True},
            "t3.small": {"vcpu": 2, "memory": 2, "generation": "3", "family": "t", "burstable": True},
            "t3.medium": {"vcpu": 2, "memory": 4, "generation": "3", "family": "t", "burstable": True},
            "t3.large": {"vcpu": 2, "memory": 8, "generation": "3", "family": "t", "burstable": True}
        }
        
        # 计算每个实例的匹配分数
        candidates = []
        for instance_type, specs in instance_specs.items():
            # 生产环境排除突发性能实例
            if environment.lower() == "production" and specs["burstable"]:
                continue
            
            # 计算vCPU和内存的匹配度
            vcpu_diff = abs(specs["vcpu"] - vcpu)
            memory_diff = abs(specs["memory"] - memory_gb)
            
            # 计算综合评分（越小越好）
            score = vcpu_diff * 2 + memory_diff
            
            # 优先推荐当前代实例
            if specs["generation"] == "6":
                score -= 5
            
            # 如果实例规格小于需求，增加惩罚分
            if specs["vcpu"] < vcpu or specs["memory"] < memory_gb:
                score += 20
            
            candidates.append({
                "instance_type": instance_type,
                "vcpu": specs["vcpu"],
                "memory": specs["memory"],
                "generation": specs["generation"],
                "family": specs["family"],
                "burstable": specs["burstable"],
                "score": score
            })
        
        # 按分数排序，取前3个
        candidates.sort(key=lambda x: x["score"])
        top_candidates = candidates[:3]
        
        # 获取每个候选实例的价格
        recommended_instances = []
        for candidate in top_candidates:
            try:
                price_result = get_aws_ec2_pricing(
                    instance_type=candidate["instance_type"],
                    region=region
                )
                price_data = json.loads(price_result)
                
                if price_data.get("success"):
                    recommended_instances.append({
                        "instance_type": candidate["instance_type"],
                        "vcpu": candidate["vcpu"],
                        "memory": candidate["memory"],
                        "generation": candidate["generation"],
                        "family": candidate["family"],
                        "burstable": candidate["burstable"],
                        "hourly_price": price_data.get("hourly_price"),
                        "monthly_price": price_data.get("monthly_price"),
                        "annual_price": price_data.get("annual_price"),
                        "match_score": candidate["score"]
                    })
            except Exception as e:
                logger.warning(f"获取实例 {candidate['instance_type']} 价格失败: {str(e)}")
                continue
        
        if not recommended_instances:
            return json.dumps({
                "success": False,
                "error": "无法找到匹配的实例类型或获取价格失败",
                "vcpu": vcpu,
                "memory_gb": memory_gb,
                "environment": environment
            }, ensure_ascii=False)
        
        result = {
            "success": True,
            "requested_vcpu": vcpu,
            "requested_memory_gb": memory_gb,
            "environment": environment,
            "region": region,
            "recommended_instances": recommended_instances,
            "recommendation_notes": [
                "生产环境已排除突发性能实例（t系列）",
                "优先推荐当前代实例（第6代）",
                "价格为按需实例定价",
                "建议考虑预留实例或Savings Plans以节省成本"
            ]
        }
        
        logger.info(f"成功推荐 {len(recommended_instances)} 个AWS实例")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"推荐AWS实例失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "vcpu": vcpu,
            "memory_gb": memory_gb,
            "environment": environment
        }, ensure_ascii=False)
