"""
Parse IT product descriptions from natural language text.

This tool analyzes IT product descriptions and extracts structured information including 
product type, specifications, and pricing. It supports common enterprise IT infrastructure 
products like servers, storage arrays, networking equipment, and database systems.

Examples:
    Input: "产品：Dell PowerEdge R740 服务器，规格：2x Intel Xeon Gold 6248R，384GB RAM，8TB SSD存储，价格：¥120,000"
    Output: JSON structured data with product type, specifications, and pricing information
"""
from strands import tool
import re
import json
from typing import Dict, Any, List, Optional

# Define product type keywords for classification
PRODUCT_TYPE_KEYWORDS = {
    "server": ["服务器", "server", "poweredge", "proliant", "系统", "主机", "计算"],
    "storage": ["存储", "storage", "阵列", "磁盘阵列", "nas", "san", "硬盘", "ssd", "hdd"],
    "network": ["网络", "switch", "router", "防火墙", "firewall", "交换机", "路由器", "负载均衡"],
    "database": ["数据库", "database", "db", "oracle", "sql server", "mysql", "postgresql"]
}

@tool
def parse_product_description(input_text: str) -> str:
    """
    Parse IT product descriptions from natural language text.
    
    Args:
        input_text (str): Raw product description text with pricing
        
    Returns:
        str: JSON string containing structured product data with specifications and pricing
    
    Raises:
        ValueError: If input text cannot be parsed or is missing critical information
    """
    # Initialize empty result list for multiple products
    parsed_products = []
    
    # Split text by blank lines to handle multiple products
    product_texts = [p.strip() for p in re.split(r'\n\s*\n', input_text) if p.strip()]
    
    if not product_texts:
        product_texts = [input_text]
    
    # Process each product
    for product_text in product_texts:
        try:
            product_data = _parse_single_product(product_text)
            parsed_products.append(product_data)
        except Exception as e:
            # Add partial data with error indication
            parsed_products.append({
                "error": str(e),
                "original_text": product_text,
                "partial_data": _extract_partial_data(product_text)
            })
    
    # Return JSON string representation
    return json.dumps(parsed_products, ensure_ascii=False, indent=2)

def _parse_single_product(text: str) -> Dict[str, Any]:
    """Parse a single product entry."""
    product_data = {
        "product_name": "",
        "type": "",
        "specs": {},
        "price": {
            "amount": 0,
            "currency": "CNY"
        }
    }
    
    # Extract product name
    name_match = re.search(r'[产品|设备|产品名称][:：]?\s*([^，。,\n]+)', text)
    if name_match:
        product_data["product_name"] = name_match.group(1).strip()
    else:
        # Try to find the first line or sentence as product name
        first_line = text.split('\n')[0].strip()
        if first_line:
            name_end = first_line.find('，')
            name_end = name_end if name_end != -1 else len(first_line)
            product_data["product_name"] = first_line[:name_end].strip()
    
    # Determine product type based on keywords
    product_data["type"] = _determine_product_type(text)
    
    # Extract specifications
    specs = {}
    
    # Look for CPU info
    cpu_match = re.search(r'((\d+)\s*[x×]\s*)?(Intel|AMD)?\s*([^，。,\n]+?)\s*(CPU|处理器|核心|核)', text, re.IGNORECASE)
    if cpu_match:
        cpu_count = cpu_match.group(2) or "1"
        cpu_brand = cpu_match.group(3) or ""
        cpu_model = cpu_match.group(4).strip()
        specs["cpu"] = f"{cpu_count}x {cpu_brand} {cpu_model}".strip()
    
    # Look for memory
    memory_match = re.search(r'(\d+)\s*(GB|TB|MB)?\s*(RAM|内存|memory)', text, re.IGNORECASE)
    if memory_match:
        memory_size = memory_match.group(1)
        memory_unit = memory_match.group(2) or "GB"
        specs["memory"] = f"{memory_size}{memory_unit}"
    
    # Look for storage
    storage_match = re.search(r'(\d+)\s*(GB|TB|PB)?\s*(存储|硬盘|磁盘|storage|SSD|HDD|NVMe)', text, re.IGNORECASE)
    if storage_match:
        storage_size = storage_match.group(1)
        storage_unit = storage_match.group(2) or "GB"
        storage_type = storage_match.group(3) or "存储"
        specs["storage"] = f"{storage_size}{storage_unit} {storage_type}"
    
    # Look for networking features if it's networking equipment
    if product_data["type"] == "network":
        network_match = re.search(r'(\d+)\s*(Gbps|Mbps|端口|ports)', text, re.IGNORECASE)
        if network_match:
            network_speed = network_match.group(1)
            network_unit = network_match.group(2)
            specs["network"] = f"{network_speed}{network_unit}"
    
    # Extract any additional specifications
    specs_match = re.search(r'[规格|配置|参数][:：]?\s*([^，。,\n]+)', text)
    if specs_match:
        specs_text = specs_match.group(1).strip()
        # Parse specs text for additional specifications
        for spec in specs_text.split('，'):
            parts = spec.split('：')
            if len(parts) == 2:
                key, value = parts[0].strip(), parts[1].strip()
                specs[key] = value
    
    product_data["specs"] = specs
    
    # Extract price information
    price_match = re.search(r'[价格|成本|费用][:：]?\s*([¥￥$€£])?(\d[\d,\.\s]+)', text)
    if price_match:
        currency_symbol = price_match.group(1) or "¥"
        price_amount = price_match.group(2).replace(',', '').replace(' ', '')
        
        # Determine currency based on symbol
        currency = "CNY"
        if currency_symbol in ["$"]:
            currency = "USD"
        elif currency_symbol in ["€"]:
            currency = "EUR"
        elif currency_symbol in ["£"]:
            currency = "GBP"
        
        product_data["price"] = {
            "amount": float(price_amount),
            "currency": currency
        }
    
    return product_data

def _determine_product_type(text: str) -> str:
    """Determine product type based on keywords in text."""
    text_lower = text.lower()
    
    # Count occurrences of keywords for each type
    type_scores = {product_type: 0 for product_type in PRODUCT_TYPE_KEYWORDS}
    
    for product_type, keywords in PRODUCT_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                type_scores[product_type] += 1
    
    # Find type with highest score
    max_score = 0
    max_type = "server"  # Default to server if no keywords match
    
    for product_type, score in type_scores.items():
        if score > max_score:
            max_score = score
            max_type = product_type
    
    return max_type

def _extract_partial_data(text: str) -> Dict[str, Any]:
    """Extract whatever data can be found in case of parsing error."""
    partial_data = {}
    
    # Try to get product name
    name_match = re.search(r'[产品|设备|产品名称][:：]?\s*([^，。,\n]+)', text)
    if name_match:
        partial_data["product_name"] = name_match.group(1).strip()
    
    # Try to get price
    price_match = re.search(r'[价格|成本|费用][:：]?\s*([¥￥$€£])?(\d[\d,\.\s]+)', text)
    if price_match:
        partial_data["price_text"] = price_match.group(0).strip()
    
    return partial_data