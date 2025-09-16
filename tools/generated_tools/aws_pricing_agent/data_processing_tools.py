"""
Data Processing Tools

This module provides tools for parsing TSV files and matching configurations to AWS products.
It supports processing cloud platform bills and IDC configuration inventories.
"""

import json
import csv
import io
import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from strands import tool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants for configuration matching
COMPUTE_PATTERNS = {
    'instance_type': [
        r'(?:instance|vm|server)\s*(?:type|class|size)?\s*[:\-=]?\s*([a-z]\d[a-z]?\.[a-z0-9]+)',
        r'([a-z]\d[a-z]?\.[a-z0-9]+)\s*(?:instance|vm|server)',
        r'type\s*[:\-=]?\s*([a-z]\d[a-z]?\.[a-z0-9]+)'
    ],
    'vcpu': [
        r'(?:vcpu|cpu|processor|core)s?\s*[:\-=]?\s*(\d+)',
        r'(\d+)\s*(?:vcpu|cpu|processor|core)s?',
        r'cpu\s*count\s*[:\-=]?\s*(\d+)'
    ],
    'memory': [
        r'(?:memory|ram)\s*[:\-=]?\s*(\d+(?:\.\d+)?)\s*(?:gb|gib|g)',
        r'(\d+(?:\.\d+)?)\s*(?:gb|gib|g)\s*(?:memory|ram)',
        r'mem\s*[:\-=]?\s*(\d+(?:\.\d+)?)'
    ],
    'os': [
        r'(?:os|operating\s*system)\s*[:\-=]?\s*([a-z0-9]+)',
        r'([a-z0-9]+)\s*(?:os|operating\s*system)',
        r'system\s*[:\-=]?\s*([a-z0-9]+)'
    ]
}

STORAGE_PATTERNS = {
    'storage_type': [
        r'(?:storage|volume)\s*(?:type|class)?\s*[:\-=]?\s*([a-z0-9]+)',
        r'([a-z0-9]+)\s*(?:storage|volume)',
        r'type\s*[:\-=]?\s*([a-z0-9]+)'
    ],
    'size': [
        r'(?:size|capacity)\s*[:\-=]?\s*(\d+(?:\.\d+)?)\s*(?:gb|gib|g|tb|tib|t)',
        r'(\d+(?:\.\d+)?)\s*(?:gb|gib|g|tb|tib|t)\s*(?:size|capacity)',
        r'volume\s*size\s*[:\-=]?\s*(\d+(?:\.\d+)?)'
    ],
    'iops': [
        r'(?:iops|io)\s*[:\-=]?\s*(\d+)',
        r'(\d+)\s*(?:iops|io)',
        r'provisioned\s*iops\s*[:\-=]?\s*(\d+)'
    ]
}

DATABASE_PATTERNS = {
    'db_instance_class': [
        r'(?:db|database|rds)\s*(?:instance|class)?\s*[:\-=]?\s*(db\.[a-z0-9]+\.[a-z0-9]+)',
        r'(db\.[a-z0-9]+\.[a-z0-9]+)\s*(?:instance|class)',
        r'instance\s*[:\-=]?\s*(db\.[a-z0-9]+\.[a-z0-9]+)'
    ],
    'engine': [
        r'(?:engine|db\s*engine)\s*[:\-=]?\s*([a-z0-9]+)',
        r'([a-z0-9]+)\s*(?:engine|db\s*engine)',
        r'database\s*type\s*[:\-=]?\s*([a-z0-9]+)'
    ],
    'deployment': [
        r'(?:deployment|az)\s*[:\-=]?\s*([a-z0-9\-]+)',
        r'([a-z0-9\-]+)\s*(?:deployment|az)',
        r'multi\s*az\s*[:\-=]?\s*([a-z0-9]+)'
    ]
}

NETWORK_PATTERNS = {
    'service_type': [
        r'(?:service|network)\s*(?:type|class)?\s*[:\-=]?\s*([a-z0-9]+)',
        r'([a-z0-9]+)\s*(?:service|network)',
        r'type\s*[:\-=]?\s*([a-z0-9]+)'
    ],
    'bandwidth': [
        r'(?:bandwidth|throughput)\s*[:\-=]?\s*(\d+(?:\.\d+)?)\s*(?:gbps|mbps)',
        r'(\d+(?:\.\d+)?)\s*(?:gbps|mbps)\s*(?:bandwidth|throughput)',
        r'speed\s*[:\-=]?\s*(\d+(?:\.\d+)?)'
    ]
}

# EC2 instance type mapping
EC2_INSTANCE_MAPPING = {
    'small': 't3.small',
    'medium': 't3.medium',
    'large': 't3.large',
    'xlarge': 't3.xlarge',
    '2xlarge': 't3.2xlarge',
    '4xlarge': 'c5.4xlarge',
    '8xlarge': 'c5.9xlarge',
    '16xlarge': 'c5.18xlarge'
}

# Storage type mapping
STORAGE_TYPE_MAPPING = {
    'standard': 'gp2',
    'ssd': 'gp3',
    'fast': 'io1',
    'cold': 'sc1',
    'archive': 'standard',  # S3 Standard
    'infrequent': 'standard_ia',  # S3 Standard-IA
    'glacier': 'glacier'  # S3 Glacier
}

# Database engine mapping
DB_ENGINE_MAPPING = {
    'mysql': 'MySQL',
    'postgres': 'PostgreSQL',
    'postgresql': 'PostgreSQL',
    'oracle': 'Oracle',
    'sqlserver': 'SQL Server',
    'mariadb': 'MariaDB',
    'aurora': 'Aurora MySQL'
}

@tool
def tsv_parser(file_content: str, header_row: int = 0, has_header: bool = True) -> str:
    """Parse TSV format cloud platform bills or IDC configuration inventories.
    
    This tool can process various formats of TSV files, extract product type,
    configuration parameters, quantities, and other key information.
    
    Args:
        file_content: TSV file content as a string
        header_row: Row number for the header (default: 0)
        has_header: Whether the file has a header row (default: True)
        
    Returns:
        JSON string containing the parsed data with product type, 
        configuration parameters, and quantities
        
    Example:
        >>> tsv_parser("Product\\tType\\tQuantity\\nServer\\tt3.large\\t5")
    """
    result = {
        "status": "success",
        "message": "TSV file parsed successfully",
        "data": {
            "items": [],
            "summary": {
                "total_items": 0,
                "product_types": {},
                "detected_format": None
            }
        },
        "error": None
    }
    
    try:
        # Detect delimiter
        delimiter = detect_delimiter(file_content)
        result["data"]["summary"]["detected_format"] = f"TSV with '{delimiter}' delimiter"
        
        # Parse the TSV content
        rows = []
        reader = csv.reader(io.StringIO(file_content), delimiter=delimiter)
        
        for i, row in enumerate(reader):
            if i >= header_row:
                rows.append(row)
        
        if not rows:
            raise ValueError("No data found in the TSV file")
            
        # Extract header and data rows
        if has_header:
            headers = [h.strip() for h in rows[0]]
            data_rows = rows[1:]
        else:
            # Generate generic headers
            headers = [f"Column{i+1}" for i in range(len(rows[0]))]
            data_rows = rows
        
        # Process each row
        items = []
        product_types = {}
        
        for row in data_rows:
            if not any(row):  # Skip empty rows
                continue
                
            # Ensure row has same length as headers
            if len(row) < len(headers):
                row.extend([''] * (len(headers) - len(row)))
            elif len(row) > len(headers):
                row = row[:len(headers)]
                
            # Create item dictionary
            item = {headers[i]: value.strip() for i, value in enumerate(row) if i < len(headers)}
            
            # Try to identify product type and configuration
            product_info = identify_product_type(item, headers)
            item.update(product_info)
            
            # Count product types
            product_type = product_info.get("product_type", "unknown")
            product_types[product_type] = product_types.get(product_type, 0) + 1
            
            items.append(item)
        
        # Update result
        result["data"]["items"] = items
        result["data"]["summary"]["total_items"] = len(items)
        result["data"]["summary"]["product_types"] = product_types
        result["data"]["headers"] = headers
        
    except Exception as e:
        result["status"] = "error"
        result["message"] = "Failed to parse TSV file"
        result["error"] = {
            "type": str(type(e).__name__),
            "message": str(e)
        }
        logger.error(f"Error parsing TSV file: {str(e)}")
    
    return json.dumps(result, ensure_ascii=False)

@tool
def config_matcher(config_data: str, product_type: str, region: str = 'us-east-1') -> str:
    """Match parsed configuration data to AWS products.
    
    This tool maps the parsed configuration data to matching AWS products,
    supports compute, storage, network, and database products, and provides
    confidence scores for the matches.
    
    Args:
        config_data: Parsed configuration data as a JSON string
        product_type: Product type (compute, storage, network, database)
        region: AWS region code (default: us-east-1)
        
    Returns:
        JSON string containing matched AWS products with configuration details
        and confidence scores
        
    Example:
        >>> config_matcher('{"items":[{"product_type":"compute","vcpu":"4","memory":"16GB"}]}', 'compute')
    """
    result = {
        "status": "success",
        "message": "Configuration matched successfully",
        "data": {
            "matches": [],
            "summary": {
                "total_items": 0,
                "matched_items": 0,
                "average_confidence": 0.0
            }
        },
        "error": None
    }
    
    try:
        # Parse the input config data
        config = json.loads(config_data)
        items = config.get("data", {}).get("items", [])
        
        if not items:
            items = config.get("items", [])
            
        if not items:
            raise ValueError("No configuration items found in the input data")
            
        # Process each item
        matches = []
        total_confidence = 0.0
        matched_count = 0
        
        for item in items:
            # Skip items that don't match the requested product type
            item_product_type = item.get("product_type", "").lower()
            if item_product_type and product_type.lower() != item_product_type:
                continue
                
            # Match the configuration
            match_result = match_configuration(item, product_type, region)
            
            if match_result:
                matches.append(match_result)
                total_confidence += match_result["confidence"]
                matched_count += 1
        
        # Update result
        result["data"]["matches"] = matches
        result["data"]["summary"]["total_items"] = len(items)
        result["data"]["summary"]["matched_items"] = matched_count
        
        if matched_count > 0:
            result["data"]["summary"]["average_confidence"] = round(total_confidence / matched_count, 2)
        
    except Exception as e:
        result["status"] = "error"
        result["message"] = "Failed to match configuration"
        result["error"] = {
            "type": str(type(e).__name__),
            "message": str(e)
        }
        logger.error(f"Error matching configuration: {str(e)}")
    
    return json.dumps(result, ensure_ascii=False)

# Helper functions

def detect_delimiter(content: str) -> str:
    """Detect the delimiter used in the file content.
    
    Args:
        content: File content as a string
        
    Returns:
        Detected delimiter character
    """
    # Check for common delimiters
    delimiters = ['\t', ',', ';', '|']
    counts = {d: content.count(d) for d in delimiters}
    
    # Return the delimiter with the highest count
    max_delimiter = max(counts, key=counts.get)
    
    # If no delimiter found, default to tab
    return max_delimiter if counts[max_delimiter] > 0 else '\t'

def identify_product_type(item: Dict[str, str], headers: List[str]) -> Dict[str, Any]:
    """Identify the product type and extract configuration details.
    
    Args:
        item: Dictionary containing row data
        headers: List of column headers
        
    Returns:
        Dictionary with product type and configuration details
    """
    result = {"product_type": "unknown", "configuration": {}}
    
    # Convert all values to lowercase for case-insensitive matching
    lower_item = {k.lower(): v.lower() for k, v in item.items()}
    lower_headers = [h.lower() for h in headers]
    
    # Check for product type indicators in headers and values
    compute_indicators = ['instance', 'server', 'vm', 'compute', 'ec2', 'vcpu', 'cpu', 'processor']
    storage_indicators = ['storage', 'disk', 'volume', 's3', 'ebs', 'capacity']
    database_indicators = ['database', 'db', 'rds', 'sql', 'mysql', 'postgres', 'oracle']
    network_indicators = ['network', 'vpc', 'elb', 'load balancer', 'nat', 'bandwidth']
    
    # Check headers
    header_text = ' '.join(lower_headers)
    item_text = ' '.join(lower_item.values())
    combined_text = header_text + ' ' + item_text
    
    # Count indicators
    compute_count = sum(1 for ind in compute_indicators if ind in combined_text)
    storage_count = sum(1 for ind in storage_indicators if ind in combined_text)
    database_count = sum(1 for ind in database_indicators if ind in combined_text)
    network_count = sum(1 for ind in network_indicators if ind in combined_text)
    
    # Determine product type based on indicator counts
    max_count = max(compute_count, storage_count, database_count, network_count)
    
    if max_count > 0:
        if compute_count == max_count:
            result["product_type"] = "compute"
            result["configuration"] = extract_compute_config(lower_item)
        elif storage_count == max_count:
            result["product_type"] = "storage"
            result["configuration"] = extract_storage_config(lower_item)
        elif database_count == max_count:
            result["product_type"] = "database"
            result["configuration"] = extract_database_config(lower_item)
        elif network_count == max_count:
            result["product_type"] = "network"
            result["configuration"] = extract_network_config(lower_item)
    
    # Extract quantity information
    quantity = extract_quantity(lower_item)
    if quantity:
        result["quantity"] = quantity
    
    return result

def extract_compute_config(item: Dict[str, str]) -> Dict[str, Any]:
    """Extract compute configuration details.
    
    Args:
        item: Dictionary containing row data in lowercase
        
    Returns:
        Dictionary with compute configuration details
    """
    config = {}
    
    # Extract instance type
    instance_type = extract_pattern_value(item, COMPUTE_PATTERNS['instance_type'])
    if instance_type:
        config["instance_type"] = instance_type
    
    # Extract vCPU
    vcpu = extract_pattern_value(item, COMPUTE_PATTERNS['vcpu'])
    if vcpu:
        config["vcpu"] = vcpu
    
    # Extract memory
    memory = extract_pattern_value(item, COMPUTE_PATTERNS['memory'])
    if memory:
        config["memory"] = memory
    
    # Extract OS
    os = extract_pattern_value(item, COMPUTE_PATTERNS['os'])
    if os:
        config["os"] = os
    
    return config

def extract_storage_config(item: Dict[str, str]) -> Dict[str, Any]:
    """Extract storage configuration details.
    
    Args:
        item: Dictionary containing row data in lowercase
        
    Returns:
        Dictionary with storage configuration details
    """
    config = {}
    
    # Extract storage type
    storage_type = extract_pattern_value(item, STORAGE_PATTERNS['storage_type'])
    if storage_type:
        config["storage_type"] = storage_type
    
    # Extract size
    size = extract_pattern_value(item, STORAGE_PATTERNS['size'])
    if size:
        config["size"] = size
    
    # Extract IOPS
    iops = extract_pattern_value(item, STORAGE_PATTERNS['iops'])
    if iops:
        config["iops"] = iops
    
    return config

def extract_database_config(item: Dict[str, str]) -> Dict[str, Any]:
    """Extract database configuration details.
    
    Args:
        item: Dictionary containing row data in lowercase
        
    Returns:
        Dictionary with database configuration details
    """
    config = {}
    
    # Extract DB instance class
    db_instance_class = extract_pattern_value(item, DATABASE_PATTERNS['db_instance_class'])
    if db_instance_class:
        config["db_instance_class"] = db_instance_class
    
    # Extract engine
    engine = extract_pattern_value(item, DATABASE_PATTERNS['engine'])
    if engine:
        config["engine"] = engine
    
    # Extract deployment
    deployment = extract_pattern_value(item, DATABASE_PATTERNS['deployment'])
    if deployment:
        config["deployment"] = deployment
    
    return config

def extract_network_config(item: Dict[str, str]) -> Dict[str, Any]:
    """Extract network configuration details.
    
    Args:
        item: Dictionary containing row data in lowercase
        
    Returns:
        Dictionary with network configuration details
    """
    config = {}
    
    # Extract service type
    service_type = extract_pattern_value(item, NETWORK_PATTERNS['service_type'])
    if service_type:
        config["service_type"] = service_type
    
    # Extract bandwidth
    bandwidth = extract_pattern_value(item, NETWORK_PATTERNS['bandwidth'])
    if bandwidth:
        config["bandwidth"] = bandwidth
    
    return config

def extract_pattern_value(item: Dict[str, str], patterns: List[str]) -> Optional[str]:
    """Extract value using regex patterns.
    
    Args:
        item: Dictionary containing row data
        patterns: List of regex patterns to try
        
    Returns:
        Extracted value or None if not found
    """
    # First check if the value is directly in the keys
    for key, value in item.items():
        for pattern in patterns:
            match = re.search(pattern, key + ': ' + value)
            if match:
                return match.group(1)
    
    # Then check all values
    all_text = ' '.join(item.values())
    for pattern in patterns:
        match = re.search(pattern, all_text)
        if match:
            return match.group(1)
    
    return None

def extract_quantity(item: Dict[str, str]) -> Optional[int]:
    """Extract quantity information.
    
    Args:
        item: Dictionary containing row data in lowercase
        
    Returns:
        Quantity as integer or None if not found
    """
    quantity_patterns = [
        r'(?:quantity|count|number|qty)\s*[:\-=]?\s*(\d+)',
        r'(\d+)\s*(?:quantity|count|number|qty)',
        r'x\s*(\d+)'
    ]
    
    # Check for quantity in keys like 'quantity', 'count', etc.
    for key in ['quantity', 'count', 'qty', 'number']:
        if key in item and item[key].isdigit():
            return int(item[key])
    
    # Try regex patterns
    quantity = extract_pattern_value(item, quantity_patterns)
    if quantity and quantity.isdigit():
        return int(quantity)
    
    return None

def match_configuration(item: Dict[str, Any], product_type: str, region: str) -> Dict[str, Any]:
    """Match configuration to AWS products.
    
    Args:
        item: Dictionary containing configuration data
        product_type: Product type (compute, storage, network, database)
        region: AWS region code
        
    Returns:
        Dictionary with matched AWS product details and confidence score
    """
    if product_type.lower() == 'compute':
        return match_compute_configuration(item, region)
    elif product_type.lower() == 'storage':
        return match_storage_configuration(item, region)
    elif product_type.lower() == 'database':
        return match_database_configuration(item, region)
    elif product_type.lower() == 'network':
        return match_network_configuration(item, region)
    else:
        return None

def match_compute_configuration(item: Dict[str, Any], region: str) -> Dict[str, Any]:
    """Match compute configuration to AWS EC2 instances.
    
    Args:
        item: Dictionary containing configuration data
        region: AWS region code
        
    Returns:
        Dictionary with matched EC2 instance details and confidence score
    """
    result = {
        "original_item": item,
        "product_type": "compute",
        "service": "EC2",
        "region": region,
        "matched_product": {},
        "confidence": 0.0,
        "reasoning": []
    }
    
    # Get configuration
    config = item.get("configuration", {})
    
    # Try to match instance type directly
    instance_type = config.get("instance_type")
    vcpu = config.get("vcpu")
    memory = config.get("memory")
    os = config.get("os", "Linux")
    
    # Initialize confidence score
    confidence = 0.0
    reasoning = []
    
    # If we have an instance type, try to use it directly
    if instance_type:
        # Check if it's a valid EC2 instance type pattern
        if re.match(r'^[a-z]\d[a-z]?\.[a-z0-9]+$', instance_type):
            result["matched_product"]["instance_type"] = instance_type
            confidence += 0.8
            reasoning.append(f"Direct match on instance type: {instance_type}")
        else:
            # Try to map to a standard size
            for size_name, ec2_type in EC2_INSTANCE_MAPPING.items():
                if size_name in instance_type:
                    result["matched_product"]["instance_type"] = ec2_type
                    confidence += 0.6
                    reasoning.append(f"Mapped '{instance_type}' to AWS instance type: {ec2_type}")
                    break
    
    # If we don't have an instance type but have vCPU and memory, try to infer
    elif vcpu and memory:
        # Convert to numeric values
        try:
            vcpu_num = int(vcpu)
            
            # Extract numeric part of memory
            memory_match = re.search(r'(\d+(?:\.\d+)?)', str(memory))
            if memory_match:
                memory_num = float(memory_match.group(1))
                
                # Simple mapping based on vCPU and memory
                if vcpu_num <= 2 and memory_num <= 4:
                    result["matched_product"]["instance_type"] = "t3.small"
                elif vcpu_num <= 2 and memory_num <= 8:
                    result["matched_product"]["instance_type"] = "t3.medium"
                elif vcpu_num <= 4 and memory_num <= 16:
                    result["matched_product"]["instance_type"] = "t3.large"
                elif vcpu_num <= 8 and memory_num <= 32:
                    result["matched_product"]["instance_type"] = "t3.2xlarge"
                elif vcpu_num <= 16 and memory_num <= 64:
                    result["matched_product"]["instance_type"] = "c5.4xlarge"
                elif vcpu_num <= 36 and memory_num <= 144:
                    result["matched_product"]["instance_type"] = "c5.9xlarge"
                else:
                    result["matched_product"]["instance_type"] = "c5.18xlarge"
                
                confidence += 0.5
                reasoning.append(f"Inferred instance type from vCPU ({vcpu_num}) and memory ({memory_num}GB)")
        except (ValueError, TypeError):
            pass
    
    # Set OS
    if os:
        normalized_os = os.lower()
        if "linux" in normalized_os:
            result["matched_product"]["os"] = "Linux"
            confidence += 0.1
        elif "windows" in normalized_os:
            result["matched_product"]["os"] = "Windows"
            confidence += 0.1
        else:
            result["matched_product"]["os"] = "Linux"  # Default
            confidence += 0.05
            reasoning.append(f"Defaulting to Linux OS (original: {os})")
    else:
        result["matched_product"]["os"] = "Linux"  # Default
        confidence += 0.05
        reasoning.append("No OS specified, defaulting to Linux")
    
    # Add quantity if available
    quantity = item.get("quantity")
    if quantity:
        result["matched_product"]["quantity"] = quantity
    
    # Set final confidence score (max 1.0)
    result["confidence"] = min(confidence, 1.0)
    result["reasoning"] = reasoning
    
    return result

def match_storage_configuration(item: Dict[str, Any], region: str) -> Dict[str, Any]:
    """Match storage configuration to AWS storage services.
    
    Args:
        item: Dictionary containing configuration data
        region: AWS region code
        
    Returns:
        Dictionary with matched storage service details and confidence score
    """
    result = {
        "original_item": item,
        "product_type": "storage",
        "service": "Unknown",
        "region": region,
        "matched_product": {},
        "confidence": 0.0,
        "reasoning": []
    }
    
    # Get configuration
    config = item.get("configuration", {})
    
    # Extract storage type and size
    storage_type = config.get("storage_type")
    size = config.get("size")
    iops = config.get("iops")
    
    # Initialize confidence score
    confidence = 0.0
    reasoning = []
    
    # Determine if this is likely EBS or S3
    is_ebs = False
    is_s3 = False
    
    # Check for EBS indicators
    if storage_type and storage_type.lower() in ['ebs', 'volume', 'disk', 'ssd', 'hdd']:
        is_ebs = True
        result["service"] = "EBS"
        confidence += 0.3
        reasoning.append(f"Identified as EBS based on storage type: {storage_type}")
    
    # Check for S3 indicators
    elif storage_type and storage_type.lower() in ['s3', 'bucket', 'object', 'archive']:
        is_s3 = True
        result["service"] = "S3"
        confidence += 0.3
        reasoning.append(f"Identified as S3 based on storage type: {storage_type}")
    
    # If still unknown, use presence of IOPS as an indicator for EBS
    elif iops:
        is_ebs = True
        result["service"] = "EBS"
        confidence += 0.2
        reasoning.append("Identified as EBS based on IOPS specification")
    
    # Default to EBS if still unknown
    else:
        is_ebs = True
        result["service"] = "EBS"
        confidence += 0.1
        reasoning.append("Defaulting to EBS (no clear indicators for S3)")
    
    # Match EBS volume type
    if is_ebs:
        # Default to gp3 if no type specified
        volume_type = "gp3"
        
        if storage_type:
            # Map to EBS volume type
            normalized_type = storage_type.lower()
            if normalized_type in STORAGE_TYPE_MAPPING:
                volume_type = STORAGE_TYPE_MAPPING[normalized_type]
                confidence += 0.2
                reasoning.append(f"Mapped '{storage_type}' to EBS volume type: {volume_type}")
            elif normalized_type in ['gp2', 'gp3', 'io1', 'io2', 'st1', 'sc1', 'standard']:
                volume_type = normalized_type
                confidence += 0.3
                reasoning.append(f"Direct match on EBS volume type: {volume_type}")
        
        result["matched_product"]["volume_type"] = volume_type
        
        # Set size
        if size:
            try:
                # Extract numeric part
                size_match = re.search(r'(\d+(?:\.\d+)?)', str(size))
                if size_match:
                    size_num = float(size_match.group(1))
                    
                    # Check for TB indicator
                    if 'tb' in str(size).lower() or 't' in str(size).lower():
                        size_num *= 1024  # Convert TB to GB
                    
                    result["matched_product"]["size_gb"] = size_num
                    confidence += 0.2
                    reasoning.append(f"Set volume size to {size_num}GB")
            except (ValueError, TypeError):
                pass
        
        # Set IOPS if specified and using io1/io2
        if iops and volume_type in ['io1', 'io2']:
            try:
                iops_num = int(iops)
                result["matched_product"]["iops"] = iops_num
                confidence += 0.1
                reasoning.append(f"Set provisioned IOPS to {iops_num}")
            except (ValueError, TypeError):
                pass
    
    # Match S3 storage class
    elif is_s3:
        # Default to Standard if no class specified
        storage_class = "Standard"
        
        if storage_type:
            # Map to S3 storage class
            normalized_type = storage_type.lower()
            if normalized_type in STORAGE_TYPE_MAPPING:
                storage_class = STORAGE_TYPE_MAPPING[normalized_type].title()
                confidence += 0.2
                reasoning.append(f"Mapped '{storage_type}' to S3 storage class: {storage_class}")
            elif normalized_type in ['standard', 'standard_ia', 'onezone_ia', 'glacier', 'deep_archive']:
                storage_class = normalized_type.title().replace('_', '-')
                confidence += 0.3
                reasoning.append(f"Direct match on S3 storage class: {storage_class}")
        
        result["matched_product"]["storage_class"] = storage_class
        
        # Set size
        if size:
            try:
                # Extract numeric part
                size_match = re.search(r'(\d+(?:\.\d+)?)', str(size))
                if size_match:
                    size_num = float(size_match.group(1))
                    
                    # Check for TB indicator
                    if 'tb' in str(size).lower() or 't' in str(size).lower():
                        size_num *= 1024  # Convert TB to GB
                    
                    result["matched_product"]["size_gb"] = size_num
                    confidence += 0.2
                    reasoning.append(f"Set storage size to {size_num}GB")
            except (ValueError, TypeError):
                pass
    
    # Add quantity if available
    quantity = item.get("quantity")
    if quantity:
        result["matched_product"]["quantity"] = quantity
    
    # Set final confidence score (max 1.0)
    result["confidence"] = min(confidence, 1.0)
    result["reasoning"] = reasoning
    
    return result

def match_database_configuration(item: Dict[str, Any], region: str) -> Dict[str, Any]:
    """Match database configuration to AWS RDS instances.
    
    Args:
        item: Dictionary containing configuration data
        region: AWS region code
        
    Returns:
        Dictionary with matched RDS instance details and confidence score
    """
    result = {
        "original_item": item,
        "product_type": "database",
        "service": "RDS",
        "region": region,
        "matched_product": {},
        "confidence": 0.0,
        "reasoning": []
    }
    
    # Get configuration
    config = item.get("configuration", {})
    
    # Extract database configuration
    db_instance_class = config.get("db_instance_class")
    engine = config.get("engine")
    deployment = config.get("deployment")
    
    # Initialize confidence score
    confidence = 0.0
    reasoning = []
    
    # Match DB instance class
    if db_instance_class:
        # Check if it's a valid RDS instance class pattern
        if re.match(r'^db\.[a-z0-9]+\.[a-z0-9]+$', db_instance_class):
            result["matched_product"]["db_instance_class"] = db_instance_class
            confidence += 0.4
            reasoning.append(f"Direct match on DB instance class: {db_instance_class}")
        else:
            # Default to a reasonable instance class
            result["matched_product"]["db_instance_class"] = "db.t3.medium"
            confidence += 0.1
            reasoning.append(f"Defaulting to db.t3.medium (original: {db_instance_class})")
    else:
        # Default to a reasonable instance class
        result["matched_product"]["db_instance_class"] = "db.t3.medium"
        confidence += 0.1
        reasoning.append("No DB instance class specified, defaulting to db.t3.medium")
    
    # Match database engine
    if engine:
        normalized_engine = engine.lower()
        if normalized_engine in DB_ENGINE_MAPPING:
            result["matched_product"]["engine"] = DB_ENGINE_MAPPING[normalized_engine]
            confidence += 0.3
            reasoning.append(f"Mapped '{engine}' to RDS engine: {DB_ENGINE_MAPPING[normalized_engine]}")
        else:
            # Default to MySQL
            result["matched_product"]["engine"] = "MySQL"
            confidence += 0.1
            reasoning.append(f"Defaulting to MySQL engine (original: {engine})")
    else:
        # Default to MySQL
        result["matched_product"]["engine"] = "MySQL"
        confidence += 0.1
        reasoning.append("No database engine specified, defaulting to MySQL")
    
    # Match deployment option
    if deployment:
        normalized_deployment = deployment.lower()
        if "multi" in normalized_deployment or "multiple" in normalized_deployment:
            result["matched_product"]["deployment_option"] = "Multi-AZ"
            confidence += 0.2
            reasoning.append("Set deployment option to Multi-AZ")
        else:
            result["matched_product"]["deployment_option"] = "Single-AZ"
            confidence += 0.1
            reasoning.append("Set deployment option to Single-AZ")
    else:
        # Default to Single-AZ
        result["matched_product"]["deployment_option"] = "Single-AZ"
        confidence += 0.1
        reasoning.append("No deployment option specified, defaulting to Single-AZ")
    
    # Add quantity if available
    quantity = item.get("quantity")
    if quantity:
        result["matched_product"]["quantity"] = quantity
    
    # Set final confidence score (max 1.0)
    result["confidence"] = min(confidence, 1.0)
    result["reasoning"] = reasoning
    
    return result

def match_network_configuration(item: Dict[str, Any], region: str) -> Dict[str, Any]:
    """Match network configuration to AWS network services.
    
    Args:
        item: Dictionary containing configuration data
        region: AWS region code
        
    Returns:
        Dictionary with matched network service details and confidence score
    """
    result = {
        "original_item": item,
        "product_type": "network",
        "service": "Unknown",
        "region": region,
        "matched_product": {},
        "confidence": 0.0,
        "reasoning": []
    }
    
    # Get configuration
    config = item.get("configuration", {})
    
    # Extract network configuration
    service_type = config.get("service_type")
    bandwidth = config.get("bandwidth")
    
    # Initialize confidence score
    confidence = 0.0
    reasoning = []
    
    # Determine network service type
    if service_type:
        normalized_type = service_type.lower()
        
        if "elb" in normalized_type or "load" in normalized_type or "balancer" in normalized_type:
            result["service"] = "ELB"
            result["matched_product"]["service_type"] = "LoadBalancer"
            
            # Determine load balancer type
            if "application" in normalized_type or "alb" in normalized_type:
                result["matched_product"]["lb_type"] = "ALB"
            elif "network" in normalized_type or "nlb" in normalized_type:
                result["matched_product"]["lb_type"] = "NLB"
            else:
                result["matched_product"]["lb_type"] = "ALB"  # Default to ALB
                
            confidence += 0.4
            reasoning.append(f"Identified as ELB ({result['matched_product']['lb_type']})")
            
        elif "vpc" in normalized_type or "nat" in normalized_type or "gateway" in normalized_type:
            result["service"] = "VPC"
            
            # Determine VPC component
            if "nat" in normalized_type:
                result["matched_product"]["service_type"] = "NatGateway"
            elif "vpn" in normalized_type:
                result["matched_product"]["service_type"] = "VpnConnection"
            else:
                result["matched_product"]["service_type"] = "VpcEndpoint"
                
            confidence += 0.4
            reasoning.append(f"Identified as VPC ({result['matched_product']['service_type']})")
            
        else:
            # Default to VPC
            result["service"] = "VPC"
            result["matched_product"]["service_type"] = "VpcEndpoint"
            confidence += 0.2
            reasoning.append(f"Defaulting to VPC service (original: {service_type})")
    else:
        # Default to VPC
        result["service"] = "VPC"
        result["matched_product"]["service_type"] = "VpcEndpoint"
        confidence += 0.1
        reasoning.append("No service type specified, defaulting to VPC")
    
    # Set bandwidth if specified
    if bandwidth:
        try:
            # Extract numeric part
            bandwidth_match = re.search(r'(\d+(?:\.\d+)?)', str(bandwidth))
            if bandwidth_match:
                bandwidth_num = float(bandwidth_match.group(1))
                
                # Check for Gbps indicator
                if 'gbps' in str(bandwidth).lower():
                    result["matched_product"]["bandwidth_gbps"] = bandwidth_num
                else:
                    # Assume Mbps and convert to Gbps
                    result["matched_product"]["bandwidth_gbps"] = bandwidth_num / 1000
                
                confidence += 0.2
                reasoning.append(f"Set bandwidth to {result['matched_product']['bandwidth_gbps']}Gbps")
        except (ValueError, TypeError):
            pass
    
    # Add quantity if available
    quantity = item.get("quantity")
    if quantity:
        result["matched_product"]["quantity"] = quantity
    
    # Set final confidence score (max 1.0)
    result["confidence"] = min(confidence, 1.0)
    result["reasoning"] = reasoning
    
    return result