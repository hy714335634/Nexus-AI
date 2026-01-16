"""
Azure价格查询工具集

提供Azure各类服务的真实价格查询功能，通过Azure Retail Prices REST API获取实时价格数据。

支持的服务：
- Virtual Machines: 虚拟机
- Managed Disks: 托管磁盘
- Blob Storage: 对象存储
- Azure SQL Database: 关系数据库
- Azure Cache for Redis: 缓存服务
- Azure Cognitive Search: 搜索服务
- Application Gateway/Load Balancer: 负载均衡器
- 带宽: 数据传输费用

作者: Nexus-AI Build Workflow
日期: 2026-01-14
"""

import json
import logging
from typing import Dict, Any, List, Optional
import requests
from urllib.parse import quote
from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Azure Retail Prices API端点
AZURE_PRICING_API = "https://prices.azure.com/api/retail/prices"


class AzurePricingClient:
    """Azure Retail Prices API客户端封装类"""
    
    def __init__(self, api_endpoint: str = AZURE_PRICING_API):
        """
        初始化Azure Pricing客户端
        
        Args:
            api_endpoint: API端点URL
        """
        self.api_endpoint = api_endpoint
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Nexus-AI-Multi-Cloud-Pricing-Agent/1.0'
        })
        logger.info(f"Azure Pricing客户端初始化成功")
    
    def get_prices(
        self,
        filter_query: str,
        currency: str = "USD",
        top: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询Azure产品价格
        
        Args:
            filter_query: OData过滤查询字符串
            currency: 货币代码（USD、EUR、GBP等）
            top: 最大返回结果数
            
        Returns:
            产品价格列表
        """
        try:
            params = {
                '$filter': filter_query,
                'currencyCode': currency,
                '$top': top
            }
            
            response = self.session.get(
                self.api_endpoint,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            items = data.get('Items', [])
            
            logger.info(f"成功获取 {len(items)} 个Azure产品价格")
            return items
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Azure API调用失败: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"获取Azure产品价格失败: {str(e)}")
            raise
    
    def extract_unit_price(self, price_item: Dict[str, Any]) -> Optional[float]:
        """
        从价格数据中提取单价
        
        Args:
            price_item: 价格数据项
            
        Returns:
            单价，如果无法提取则返回None
        """
        try:
            # 优先获取零售价
            retail_price = price_item.get('retailPrice')
            if retail_price is not None and retail_price > 0:
                return float(retail_price)
            
            # 如果没有零售价，尝试获取单价
            unit_price = price_item.get('unitPrice')
            if unit_price is not None and unit_price > 0:
                return float(unit_price)
            
            return None
            
        except Exception as e:
            logger.warning(f"提取价格失败: {str(e)}")
            return None


# 全局客户端实例
_pricing_client = None


def get_pricing_client() -> AzurePricingClient:
    """获取或创建全局Pricing客户端"""
    global _pricing_client
    if _pricing_client is None:
        _pricing_client = AzurePricingClient()
    return _pricing_client


@tool
def get_azure_vm_pricing(
    vm_size: str,
    region: str = "eastus",
    os_type: str = "Linux"
) -> str:
    """
    查询Azure Virtual Machines价格
    
    Args:
        vm_size: VM大小（如Standard_B2s、Standard_D4s_v3）
        region: Azure区域（如eastus、westeurope）
        os_type: 操作系统类型（Linux、Windows）
        
    Returns:
        JSON格式的价格信息，包含hourly_price、monthly_price、annual_price
    """
    try:
        client = get_pricing_client()
        
        # 构建OData过滤查询
        filter_query = (
            f"serviceName eq 'Virtual Machines' "
            f"and armRegionName eq '{region}' "
            f"and armSkuName eq '{vm_size}' "
            f"and priceType eq 'Consumption'"
        )
        
        # 查询产品价格
        items = client.get_prices(filter_query=filter_query, top=50)
        
        # 过滤匹配的项
        # 注意：Linux VM 的 productName 中不包含 "Linux"，而是不包含 "Windows"
        # Windows VM 的 productName 中包含 "Windows"
        matched_items = []
        for item in items:
            product_name = item.get('productName', '').lower()
            sku_name = item.get('skuName', '').lower()
            
            # 排除 Spot 和 Low Priority 实例
            if 'spot' in sku_name or 'low priority' in sku_name:
                continue
            
            # 根据 OS 类型过滤
            if os_type.lower() == 'linux':
                # Linux 实例的 productName 不包含 "Windows"
                if 'windows' not in product_name:
                    matched_items.append(item)
            elif os_type.lower() == 'windows':
                # Windows 实例的 productName 包含 "Windows"
                if 'windows' in product_name:
                    matched_items.append(item)
        
        if not matched_items:
            return json.dumps({
                "success": False,
                "error": f"未找到 {vm_size} ({os_type}) 在 {region} 的价格信息",
                "vm_size": vm_size,
                "region": region,
                "os_type": os_type
            }, ensure_ascii=False)
        
        # 提取价格
        price_item = matched_items[0]
        hourly_price = client.extract_unit_price(price_item)
        
        if hourly_price is None:
            return json.dumps({
                "success": False,
                "error": "无法从返回的数据中提取价格",
                "vm_size": vm_size,
                "region": region,
                "os_type": os_type
            }, ensure_ascii=False)
        
        # 计算月度和年度价格
        monthly_price = hourly_price * 730
        annual_price = hourly_price * 8760
        
        result = {
            "success": True,
            "service": "Virtual Machines",
            "vm_size": vm_size,
            "region": region,
            "os_type": os_type,
            "hourly_price": round(hourly_price, 4),
            "monthly_price": round(monthly_price, 2),
            "annual_price": round(annual_price, 2),
            "currency": "USD",
            "product_name": price_item.get('productName'),
            "documentation": "https://azure.microsoft.com/pricing/details/virtual-machines/"
        }
        
        logger.info(f"成功获取Azure VM价格: {vm_size} @ {region} = ${hourly_price}/小时")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取Azure VM价格失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "vm_size": vm_size,
            "region": region,
            "os_type": os_type
        }, ensure_ascii=False)


@tool
def get_azure_disk_pricing(
    disk_type: str,
    region: str = "eastus"
) -> str:
    """
    查询Azure Managed Disks价格
    
    Args:
        disk_type: 磁盘类型（Premium SSD、Standard SSD、Standard HDD）
        region: Azure区域
        
    Returns:
        JSON格式的价格信息，包含gb_month_price
    """
    try:
        client = get_pricing_client()
        
        # 磁盘类型映射
        disk_type_map = {
            "premium ssd": "Premium SSD",
            "standard ssd": "Standard SSD",
            "standard hdd": "Standard HDD",
            "ultra ssd": "Ultra SSD"
        }
        
        disk_type_value = disk_type_map.get(disk_type.lower(), disk_type)
        
        # 构建OData过滤查询
        filter_query = (
            f"serviceName eq 'Storage' "
            f"and armRegionName eq '{region}' "
            f"and priceType eq 'Consumption'"
        )
        
        # 查询产品价格
        items = client.get_prices(filter_query=filter_query, top=100)
        
        # 过滤匹配的项
        matched_items = [
            item for item in items
            if disk_type_value.lower() in item.get('productName', '').lower()
            and 'managed disk' in item.get('productName', '').lower()
            and item.get('unitOfMeasure') == '1/Month'
        ]
        
        if not matched_items:
            return json.dumps({
                "success": False,
                "error": f"未找到 {disk_type} 在 {region} 的价格信息",
                "disk_type": disk_type,
                "region": region
            }, ensure_ascii=False)
        
        # 提取价格
        price_item = matched_items[0]
        gb_month_price = client.extract_unit_price(price_item)
        
        if gb_month_price is None:
            return json.dumps({
                "success": False,
                "error": "无法从返回的数据中提取价格",
                "disk_type": disk_type,
                "region": region
            }, ensure_ascii=False)
        
        result = {
            "success": True,
            "service": "Managed Disks",
            "disk_type": disk_type,
            "region": region,
            "gb_month_price": round(gb_month_price, 4),
            "currency": "USD",
            "product_name": price_item.get('productName'),
            "documentation": "https://azure.microsoft.com/pricing/details/managed-disks/"
        }
        
        logger.info(f"成功获取Azure Disk价格: {disk_type} @ {region} = ${gb_month_price}/GB-月")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取Azure Disk价格失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "disk_type": disk_type,
            "region": region
        }, ensure_ascii=False)


@tool
def get_azure_blob_pricing(
    access_tier: str,
    region: str = "eastus"
) -> str:
    """
    查询Azure Blob Storage价格
    
    Args:
        access_tier: 访问层（Hot、Cool、Archive）
        region: Azure区域
        
    Returns:
        JSON格式的价格信息，包含gb_month_price
    """
    try:
        client = get_pricing_client()
        
        # 访问层映射
        tier_map = {
            "hot": "Hot",
            "cool": "Cool",
            "archive": "Archive"
        }
        
        tier_value = tier_map.get(access_tier.lower(), access_tier)
        
        # 构建OData过滤查询
        filter_query = (
            f"serviceName eq 'Storage' "
            f"and armRegionName eq '{region}' "
            f"and priceType eq 'Consumption'"
        )
        
        # 查询产品价格
        items = client.get_prices(filter_query=filter_query, top=100)
        
        # 过滤匹配的项
        matched_items = [
            item for item in items
            if 'blob storage' in item.get('productName', '').lower()
            and tier_value.lower() in item.get('productName', '').lower()
            and 'lrs' in item.get('productName', '').lower()
            and item.get('unitOfMeasure') == '1 GB/Month'
        ]
        
        if not matched_items:
            return json.dumps({
                "success": False,
                "error": f"未找到 {access_tier} 在 {region} 的价格信息",
                "access_tier": access_tier,
                "region": region
            }, ensure_ascii=False)
        
        # 提取价格
        price_item = matched_items[0]
        gb_month_price = client.extract_unit_price(price_item)
        
        if gb_month_price is None:
            return json.dumps({
                "success": False,
                "error": "无法从返回的数据中提取价格",
                "access_tier": access_tier,
                "region": region
            }, ensure_ascii=False)
        
        result = {
            "success": True,
            "service": "Blob Storage",
            "access_tier": access_tier,
            "region": region,
            "gb_month_price": round(gb_month_price, 4),
            "currency": "USD",
            "product_name": price_item.get('productName'),
            "documentation": "https://azure.microsoft.com/pricing/details/storage/blobs/"
        }
        
        logger.info(f"成功获取Azure Blob价格: {access_tier} @ {region} = ${gb_month_price}/GB-月")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取Azure Blob价格失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "access_tier": access_tier,
            "region": region
        }, ensure_ascii=False)


@tool
def get_azure_sql_pricing(
    service_tier: str,
    compute_tier: str,
    region: str = "eastus"
) -> str:
    """
    查询Azure SQL Database价格
    
    Args:
        service_tier: 服务层级（Basic、Standard、Premium、GeneralPurpose、BusinessCritical）
        compute_tier: 计算层级（如S0、S1、P1、Gen5 2 vCore）
        region: Azure区域
        
    Returns:
        JSON格式的价格信息，包含hourly_price、monthly_price、annual_price
    """
    try:
        client = get_pricing_client()
        
        # 构建OData过滤查询
        filter_query = (
            f"serviceName eq 'SQL Database' "
            f"and armRegionName eq '{region}' "
            f"and priceType eq 'Consumption'"
        )
        
        # 查询产品价格
        items = client.get_prices(filter_query=filter_query, top=100)
        
        # 过滤匹配的项
        matched_items = [
            item for item in items
            if service_tier.lower() in item.get('productName', '').lower()
            and compute_tier.lower() in item.get('skuName', '').lower()
        ]
        
        if not matched_items:
            return json.dumps({
                "success": False,
                "error": f"未找到 {service_tier} ({compute_tier}) 在 {region} 的价格信息",
                "service_tier": service_tier,
                "compute_tier": compute_tier,
                "region": region
            }, ensure_ascii=False)
        
        # 提取价格
        price_item = matched_items[0]
        
        # 根据单位判断是小时还是月度价格
        unit_of_measure = price_item.get('unitOfMeasure', '')
        unit_price = client.extract_unit_price(price_item)
        
        if unit_price is None:
            return json.dumps({
                "success": False,
                "error": "无法从返回的数据中提取价格",
                "service_tier": service_tier,
                "compute_tier": compute_tier,
                "region": region
            }, ensure_ascii=False)
        
        # 转换为小时价格
        if '1 Hour' in unit_of_measure:
            hourly_price = unit_price
        elif '1/Month' in unit_of_measure:
            hourly_price = unit_price / 730
        else:
            hourly_price = unit_price
        
        monthly_price = hourly_price * 730
        annual_price = hourly_price * 8760
        
        result = {
            "success": True,
            "service": "Azure SQL Database",
            "service_tier": service_tier,
            "compute_tier": compute_tier,
            "region": region,
            "hourly_price": round(hourly_price, 4),
            "monthly_price": round(monthly_price, 2),
            "annual_price": round(annual_price, 2),
            "currency": "USD",
            "product_name": price_item.get('productName'),
            "documentation": "https://azure.microsoft.com/pricing/details/sql-database/"
        }
        
        logger.info(f"成功获取Azure SQL价格: {service_tier} ({compute_tier}) @ {region} = ${hourly_price}/小时")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取Azure SQL价格失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "service_tier": service_tier,
            "compute_tier": compute_tier,
            "region": region
        }, ensure_ascii=False)


@tool
def get_azure_redis_pricing(
    cache_size: str,
    region: str = "eastus"
) -> str:
    """
    查询Azure Cache for Redis价格
    
    Args:
        cache_size: 缓存大小（如C0、C1、P1）
        region: Azure区域
        
    Returns:
        JSON格式的价格信息，包含hourly_price、monthly_price、annual_price
    """
    try:
        client = get_pricing_client()
        
        # 构建OData过滤查询
        filter_query = (
            f"serviceName eq 'Azure Cache for Redis' "
            f"and armRegionName eq '{region}' "
            f"and priceType eq 'Consumption'"
        )
        
        # 查询产品价格
        items = client.get_prices(filter_query=filter_query, top=100)
        
        # 过滤匹配的项
        matched_items = [
            item for item in items
            if cache_size.lower() in item.get('skuName', '').lower()
        ]
        
        if not matched_items:
            return json.dumps({
                "success": False,
                "error": f"未找到 {cache_size} 在 {region} 的价格信息",
                "cache_size": cache_size,
                "region": region
            }, ensure_ascii=False)
        
        # 提取价格
        price_item = matched_items[0]
        hourly_price = client.extract_unit_price(price_item)
        
        if hourly_price is None:
            return json.dumps({
                "success": False,
                "error": "无法从返回的数据中提取价格",
                "cache_size": cache_size,
                "region": region
            }, ensure_ascii=False)
        
        monthly_price = hourly_price * 730
        annual_price = hourly_price * 8760
        
        result = {
            "success": True,
            "service": "Azure Cache for Redis",
            "cache_size": cache_size,
            "region": region,
            "hourly_price": round(hourly_price, 4),
            "monthly_price": round(monthly_price, 2),
            "annual_price": round(annual_price, 2),
            "currency": "USD",
            "product_name": price_item.get('productName'),
            "documentation": "https://azure.microsoft.com/pricing/details/cache/"
        }
        
        logger.info(f"成功获取Azure Redis价格: {cache_size} @ {region} = ${hourly_price}/小时")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取Azure Redis价格失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "cache_size": cache_size,
            "region": region
        }, ensure_ascii=False)


@tool
def get_azure_search_pricing(
    service_tier: str,
    region: str = "eastus"
) -> str:
    """
    查询Azure Cognitive Search价格
    
    Args:
        service_tier: 服务层级（Free、Basic、Standard、Storage Optimized）
        region: Azure区域
        
    Returns:
        JSON格式的价格信息，包含hourly_price、monthly_price、annual_price
    """
    try:
        client = get_pricing_client()
        
        # 构建OData过滤查询
        filter_query = (
            f"serviceName eq 'Azure Cognitive Search' "
            f"and armRegionName eq '{region}' "
            f"and priceType eq 'Consumption'"
        )
        
        # 查询产品价格
        items = client.get_prices(filter_query=filter_query, top=100)
        
        # 过滤匹配的项
        matched_items = [
            item for item in items
            if service_tier.lower() in item.get('productName', '').lower()
        ]
        
        if not matched_items:
            return json.dumps({
                "success": False,
                "error": f"未找到 {service_tier} 在 {region} 的价格信息",
                "service_tier": service_tier,
                "region": region
            }, ensure_ascii=False)
        
        # 提取价格
        price_item = matched_items[0]
        hourly_price = client.extract_unit_price(price_item)
        
        if hourly_price is None:
            return json.dumps({
                "success": False,
                "error": "无法从返回的数据中提取价格",
                "service_tier": service_tier,
                "region": region
            }, ensure_ascii=False)
        
        monthly_price = hourly_price * 730
        annual_price = hourly_price * 8760
        
        result = {
            "success": True,
            "service": "Azure Cognitive Search",
            "service_tier": service_tier,
            "region": region,
            "hourly_price": round(hourly_price, 4),
            "monthly_price": round(monthly_price, 2),
            "annual_price": round(annual_price, 2),
            "currency": "USD",
            "product_name": price_item.get('productName'),
            "documentation": "https://azure.microsoft.com/pricing/details/search/"
        }
        
        logger.info(f"成功获取Azure Search价格: {service_tier} @ {region} = ${hourly_price}/小时")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取Azure Search价格失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "service_tier": service_tier,
            "region": region
        }, ensure_ascii=False)


@tool
def get_azure_gateway_pricing(
    gateway_type: str,
    region: str = "eastus"
) -> str:
    """
    查询Azure Application Gateway/Load Balancer价格
    
    Args:
        gateway_type: 网关类型（Application Gateway、Load Balancer）
        region: Azure区域
        
    Returns:
        JSON格式的价格信息，包含hourly_price、monthly_price、annual_price
    """
    try:
        client = get_pricing_client()
        
        # 构建OData过滤查询
        service_name = "Application Gateway" if "application" in gateway_type.lower() else "Load Balancer"
        
        filter_query = (
            f"serviceName eq '{service_name}' "
            f"and armRegionName eq '{region}' "
            f"and priceType eq 'Consumption'"
        )
        
        # 查询产品价格
        items = client.get_prices(filter_query=filter_query, top=50)
        
        if not items:
            return json.dumps({
                "success": False,
                "error": f"未找到 {gateway_type} 在 {region} 的价格信息",
                "gateway_type": gateway_type,
                "region": region
            }, ensure_ascii=False)
        
        # 提取价格
        price_item = items[0]
        hourly_price = client.extract_unit_price(price_item)
        
        if hourly_price is None:
            return json.dumps({
                "success": False,
                "error": "无法从返回的数据中提取价格",
                "gateway_type": gateway_type,
                "region": region
            }, ensure_ascii=False)
        
        monthly_price = hourly_price * 730
        annual_price = hourly_price * 8760
        
        result = {
            "success": True,
            "service": service_name,
            "gateway_type": gateway_type,
            "region": region,
            "hourly_price": round(hourly_price, 4),
            "monthly_price": round(monthly_price, 2),
            "annual_price": round(annual_price, 2),
            "currency": "USD",
            "product_name": price_item.get('productName'),
            "documentation": f"https://azure.microsoft.com/pricing/details/{service_name.lower().replace(' ', '-')}/"
        }
        
        logger.info(f"成功获取Azure Gateway价格: {gateway_type} @ {region} = ${hourly_price}/小时")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取Azure Gateway价格失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "gateway_type": gateway_type,
            "region": region
        }, ensure_ascii=False)


@tool
def get_azure_bandwidth_pricing(
    transfer_type: str,
    region: str = "eastus"
) -> str:
    """
    查询Azure带宽价格
    
    Args:
        transfer_type: 传输类型（Outbound、Inbound）
        region: Azure区域
        
    Returns:
        JSON格式的价格信息，包含gb_price
    """
    try:
        client = get_pricing_client()
        
        # 构建OData过滤查询
        filter_query = (
            f"serviceName eq 'Bandwidth' "
            f"and armRegionName eq '{region}' "
            f"and priceType eq 'Consumption'"
        )
        
        # 查询产品价格
        items = client.get_prices(filter_query=filter_query, top=50)
        
        # 过滤匹配的项
        matched_items = [
            item for item in items
            if transfer_type.lower() in item.get('productName', '').lower()
        ]
        
        if not matched_items:
            return json.dumps({
                "success": False,
                "error": f"未找到 {transfer_type} 在 {region} 的价格信息",
                "transfer_type": transfer_type,
                "region": region
            }, ensure_ascii=False)
        
        # 提取价格
        price_item = matched_items[0]
        gb_price = client.extract_unit_price(price_item)
        
        if gb_price is None:
            return json.dumps({
                "success": False,
                "error": "无法从返回的数据中提取价格",
                "transfer_type": transfer_type,
                "region": region
            }, ensure_ascii=False)
        
        result = {
            "success": True,
            "service": "Bandwidth",
            "transfer_type": transfer_type,
            "region": region,
            "gb_price": round(gb_price, 4),
            "currency": "USD",
            "product_name": price_item.get('productName'),
            "documentation": "https://azure.microsoft.com/pricing/details/bandwidth/"
        }
        
        logger.info(f"成功获取Azure Bandwidth价格: {transfer_type} @ {region} = ${gb_price}/GB")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取Azure Bandwidth价格失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "transfer_type": transfer_type,
            "region": region
        }, ensure_ascii=False)


@tool
def recommend_azure_instances(
    vcpu: int,
    memory_gb: float,
    environment: str = "production",
    region: str = "eastus"
) -> str:
    """
    根据vCPU和内存需求推荐Azure实例类型
    
    Args:
        vcpu: vCPU核心数
        memory_gb: 内存大小（GB）
        environment: 环境类型（production、development、test）
        region: Azure区域
        
    Returns:
        JSON格式的推荐结果，包含recommended_instances列表
    """
    try:
        # Azure实例规格数据库（简化版）
        instance_specs = {
            # 通用型 - 当前代（D系列v5）
            "Standard_D2s_v5": {"vcpu": 2, "memory": 8, "generation": "5", "family": "D", "burstable": False},
            "Standard_D4s_v5": {"vcpu": 4, "memory": 16, "generation": "5", "family": "D", "burstable": False},
            "Standard_D8s_v5": {"vcpu": 8, "memory": 32, "generation": "5", "family": "D", "burstable": False},
            "Standard_D16s_v5": {"vcpu": 16, "memory": 64, "generation": "5", "family": "D", "burstable": False},
            
            # 通用型 - 上一代（D系列v4）
            "Standard_D2s_v4": {"vcpu": 2, "memory": 8, "generation": "4", "family": "D", "burstable": False},
            "Standard_D4s_v4": {"vcpu": 4, "memory": 16, "generation": "4", "family": "D", "burstable": False},
            "Standard_D8s_v4": {"vcpu": 8, "memory": 32, "generation": "4", "family": "D", "burstable": False},
            
            # 计算优化型
            "Standard_F2s_v2": {"vcpu": 2, "memory": 4, "generation": "2", "family": "F", "burstable": False},
            "Standard_F4s_v2": {"vcpu": 4, "memory": 8, "generation": "2", "family": "F", "burstable": False},
            "Standard_F8s_v2": {"vcpu": 8, "memory": 16, "generation": "2", "family": "F", "burstable": False},
            
            # 内存优化型
            "Standard_E2s_v5": {"vcpu": 2, "memory": 16, "generation": "5", "family": "E", "burstable": False},
            "Standard_E4s_v5": {"vcpu": 4, "memory": 32, "generation": "5", "family": "E", "burstable": False},
            "Standard_E8s_v5": {"vcpu": 8, "memory": 64, "generation": "5", "family": "E", "burstable": False},
            
            # 突发性能型（仅用于测试/开发）
            "Standard_B1s": {"vcpu": 1, "memory": 1, "generation": "1", "family": "B", "burstable": True},
            "Standard_B2s": {"vcpu": 2, "memory": 4, "generation": "1", "family": "B", "burstable": True},
            "Standard_B4ms": {"vcpu": 4, "memory": 16, "generation": "1", "family": "B", "burstable": True}
        }
        
        # 计算每个实例的匹配分数
        candidates = []
        for vm_size, specs in instance_specs.items():
            # 生产环境排除突发性能实例
            if environment.lower() == "production" and specs["burstable"]:
                continue
            
            # 计算vCPU和内存的匹配度
            vcpu_diff = abs(specs["vcpu"] - vcpu)
            memory_diff = abs(specs["memory"] - memory_gb)
            
            # 计算综合评分（越小越好）
            score = vcpu_diff * 2 + memory_diff
            
            # 优先推荐当前代实例
            if specs["generation"] == "5":
                score -= 5
            
            # 如果实例规格小于需求，增加惩罚分
            if specs["vcpu"] < vcpu or specs["memory"] < memory_gb:
                score += 20
            
            candidates.append({
                "vm_size": vm_size,
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
                price_result = get_azure_vm_pricing(
                    vm_size=candidate["vm_size"],
                    region=region
                )
                price_data = json.loads(price_result)
                
                if price_data.get("success"):
                    recommended_instances.append({
                        "vm_size": candidate["vm_size"],
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
                logger.warning(f"获取实例 {candidate['vm_size']} 价格失败: {str(e)}")
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
                "生产环境已排除突发性能实例（B系列）",
                "优先推荐当前代实例（v5系列）",
                "价格为按需实例定价",
                "建议考虑预留实例以节省成本"
            ]
        }
        
        logger.info(f"成功推荐 {len(recommended_instances)} 个Azure实例")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"推荐Azure实例失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "vcpu": vcpu,
            "memory_gb": memory_gb,
            "environment": environment
        }, ensure_ascii=False)
