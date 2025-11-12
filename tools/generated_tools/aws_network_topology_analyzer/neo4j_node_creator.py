from strands import tool
from typing import Dict, List, Optional, Any, Union
import json
import logging
import time
from neo4j import GraphDatabase, Driver, Session, Result
from neo4j.exceptions import ServiceUnavailable, AuthError, DatabaseError, ConstraintError

# Import the get_connection function from neo4j_database_connector
from tools.generated_tools.aws_network_topology_analyzer.neo4j_database_connector import get_connection

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@tool
def neo4j_node_creator(
    node_type: str,
    properties: Dict[str, Any],
    labels: Optional[List[str]] = None,
    merge_keys: Optional[List[str]] = None,
    connection_id: str = "default",
    database: str = "neo4j",
    return_node: bool = True,
    create_constraints: bool = True
) -> str:
    """
    创建Neo4j节点
    
    Args:
        node_type: 节点类型，例如：Account, Region, VPC等
        properties: 节点属性字典
        labels: 额外的标签列表（可选）
        merge_keys: 用于MERGE操作的键列表（可选，默认使用resource_id或id）
        connection_id: 数据库连接ID（可选，默认为"default"）
        database: 数据库名称（可选，默认为"neo4j"）
        return_node: 是否返回创建的节点（可选，默认为True）
        create_constraints: 是否创建约束（可选，默认为True）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 获取数据库连接
        driver = get_connection(connection_id)
        if not driver:
            return json.dumps({
                "status": "error",
                "message": f"No active connection found with ID '{connection_id}'",
                "connection_id": connection_id
            }, indent=2)
        
        # 处理标签
        all_labels = [node_type]
        if labels:
            all_labels.extend(labels)
        
        # 确保属性中包含resource_id
        if "resource_id" not in properties and "id" not in properties:
            # 尝试从其他字段生成resource_id
            if "name" in properties:
                properties["resource_id"] = properties["name"]
            elif "arn" in properties:
                properties["resource_id"] = properties["arn"].split("/")[-1]
            else:
                # 生成唯一ID
                properties["resource_id"] = f"{node_type}_{time.time_ns()}"
        
        # 确定用于MERGE操作的键
        if not merge_keys:
            if "resource_id" in properties:
                merge_keys = ["resource_id"]
            elif "id" in properties:
                merge_keys = ["id"]
            else:
                # 如果没有明确的唯一标识符，使用所有属性
                merge_keys = list(properties.keys())
        
        # 构建MERGE查询
        merge_conditions = " AND ".join([f"n.{key} = ${key}" for key in merge_keys])
        labels_str = ":".join(all_labels)
        
        # 创建约束
        if create_constraints:
            try:
                with driver.session(database=database) as session:
                    # 检查约束是否已存在
                    constraints_query = """
                    SHOW CONSTRAINTS
                    WHERE entityType = 'NODE' 
                    AND labelsOrTypes = $label
                    AND properties = $property
                    """
                    
                    # 为每个merge_key创建或确保存在约束
                    for key in merge_keys:
                        constraints = session.run(
                            constraints_query, 
                            label=[node_type], 
                            property=[key]
                        ).data()
                        
                        # 如果约束不存在，创建它
                        if not constraints:
                            try:
                                constraint_query = f"""
                                CREATE CONSTRAINT {node_type}_{key}_constraint IF NOT EXISTS
                                FOR (n:{node_type})
                                REQUIRE n.{key} IS UNIQUE
                                """
                                session.run(constraint_query)
                                logger.info(f"Created constraint for {node_type}.{key}")
                            except Exception as e:
                                logger.warning(f"Failed to create constraint for {node_type}.{key}: {str(e)}")
            except Exception as e:
                logger.warning(f"Error checking or creating constraints: {str(e)}")
        
        # 执行MERGE操作
        with driver.session(database=database) as session:
            start_time = time.time()
            
            # 构建查询
            query = f"""
            MERGE (n:{labels_str} {{{merge_conditions}}})
            SET n += $properties
            {f"RETURN n" if return_node else ""}
            """
            
            # 准备参数
            params = {key: properties[key] for key in merge_keys}
            params["properties"] = properties
            
            # 执行查询
            result = session.run(query, params)
            
            # 处理结果
            summary = result.consume()
            
            if return_node and result.peek():
                node = result.single()["n"]
                node_data = dict(node.items())
                node_labels = list(node.labels)
            else:
                node_data = None
                node_labels = None
            
            end_time = time.time()
            operation_duration = round(end_time - start_time, 3)
            
            # 准备返回结果
            response = {
                "status": "success",
                "message": f"Node created/updated successfully",
                "node_type": node_type,
                "labels": all_labels,
                "merge_keys": merge_keys,
                "counters": {
                    "nodes_created": summary.counters.nodes_created,
                    "nodes_deleted": summary.counters.nodes_deleted,
                    "relationships_created": summary.counters.relationships_created,
                    "relationships_deleted": summary.counters.relationships_deleted,
                    "properties_set": summary.counters.properties_set,
                    "labels_added": summary.counters.labels_added
                },
                "operation_duration_seconds": operation_duration
            }
            
            # 如果请求返回节点数据，添加到响应中
            if return_node and node_data:
                response["node"] = {
                    "properties": node_data,
                    "labels": node_labels
                }
            
            return json.dumps(response, indent=2, default=str)
    
    except ConstraintError as e:
        error_result = {
            "status": "error",
            "message": f"Constraint violation: {str(e)}",
            "error_type": "ConstraintError",
            "node_type": node_type,
            "merge_keys": merge_keys
        }
        return json.dumps(error_result, indent=2)
    
    except DatabaseError as e:
        error_result = {
            "status": "error",
            "message": f"Database error: {str(e)}",
            "error_type": "DatabaseError",
            "node_type": node_type
        }
        return json.dumps(error_result, indent=2)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "error_type": type(e).__name__,
            "node_type": node_type
        }
        return json.dumps(error_result, indent=2)

@tool
def neo4j_batch_node_creator(
    nodes: List[Dict[str, Any]],
    connection_id: str = "default",
    database: str = "neo4j",
    create_constraints: bool = True
) -> str:
    """
    批量创建Neo4j节点
    
    Args:
        nodes: 节点列表，每个节点是一个包含node_type、properties和可选labels的字典
        connection_id: 数据库连接ID（可选，默认为"default"）
        database: 数据库名称（可选，默认为"neo4j"）
        create_constraints: 是否创建约束（可选，默认为True）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 获取数据库连接
        driver = get_connection(connection_id)
        if not driver:
            return json.dumps({
                "status": "error",
                "message": f"No active connection found with ID '{connection_id}'",
                "connection_id": connection_id
            }, indent=2)
        
        # 创建约束
        if create_constraints:
            try:
                with driver.session(database=database) as session:
                    # 收集所有唯一的节点类型和merge键
                    node_types_keys = {}
                    for node in nodes:
                        node_type = node.get("node_type")
                        properties = node.get("properties", {})
                        
                        # 确定用于MERGE操作的键
                        merge_keys = node.get("merge_keys")
                        if not merge_keys:
                            if "resource_id" in properties:
                                merge_keys = ["resource_id"]
                            elif "id" in properties:
                                merge_keys = ["id"]
                            else:
                                # 如果没有明确的唯一标识符，使用所有属性
                                merge_keys = list(properties.keys())
                        
                        if node_type not in node_types_keys:
                            node_types_keys[node_type] = set()
                        
                        for key in merge_keys:
                            node_types_keys[node_type].add(key)
                    
                    # 检查约束是否已存在并创建
                    constraints_query = """
                    SHOW CONSTRAINTS
                    WHERE entityType = 'NODE' 
                    AND labelsOrTypes = $label
                    AND properties = $property
                    """
                    
                    for node_type, keys in node_types_keys.items():
                        for key in keys:
                            constraints = session.run(
                                constraints_query, 
                                label=[node_type], 
                                property=[key]
                            ).data()
                            
                            # 如果约束不存在，创建它
                            if not constraints:
                                try:
                                    constraint_query = f"""
                                    CREATE CONSTRAINT {node_type}_{key}_constraint IF NOT EXISTS
                                    FOR (n:{node_type})
                                    REQUIRE n.{key} IS UNIQUE
                                    """
                                    session.run(constraint_query)
                                    logger.info(f"Created constraint for {node_type}.{key}")
                                except Exception as e:
                                    logger.warning(f"Failed to create constraint for {node_type}.{key}: {str(e)}")
            except Exception as e:
                logger.warning(f"Error checking or creating constraints: {str(e)}")
        
        # 执行批量MERGE操作
        start_time = time.time()
        results = []
        success_count = 0
        error_count = 0
        
        for node in nodes:
            try:
                node_type = node.get("node_type")
                properties = node.get("properties", {})
                labels = node.get("labels", [])
                merge_keys = node.get("merge_keys")
                
                # 确保属性中包含resource_id
                if "resource_id" not in properties and "id" not in properties:
                    # 尝试从其他字段生成resource_id
                    if "name" in properties:
                        properties["resource_id"] = properties["name"]
                    elif "arn" in properties:
                        properties["resource_id"] = properties["arn"].split("/")[-1]
                    else:
                        # 生成唯一ID
                        properties["resource_id"] = f"{node_type}_{time.time_ns()}"
                
                # 确定用于MERGE操作的键
                if not merge_keys:
                    if "resource_id" in properties:
                        merge_keys = ["resource_id"]
                    elif "id" in properties:
                        merge_keys = ["id"]
                    else:
                        # 如果没有明确的唯一标识符，使用所有属性
                        merge_keys = list(properties.keys())
                
                # 处理标签
                all_labels = [node_type]
                if labels:
                    all_labels.extend(labels)
                
                # 构建MERGE查询
                merge_conditions = " AND ".join([f"n.{key} = ${key}" for key in merge_keys])
                labels_str = ":".join(all_labels)
                
                with driver.session(database=database) as session:
                    # 构建查询
                    query = f"""
                    MERGE (n:{labels_str} {{{merge_conditions}}})
                    SET n += $properties
                    RETURN n
                    """
                    
                    # 准备参数
                    params = {key: properties[key] for key in merge_keys}
                    params["properties"] = properties
                    
                    # 执行查询
                    result = session.run(query, params)
                    
                    # 处理结果
                    summary = result.consume()
                    
                    if result.peek():
                        node_result = result.single()["n"]
                        node_data = dict(node_result.items())
                        node_labels = list(node_result.labels)
                    else:
                        node_data = None
                        node_labels = None
                    
                    # 准备节点结果
                    node_result = {
                        "status": "success",
                        "node_type": node_type,
                        "labels": all_labels,
                        "merge_keys": merge_keys,
                        "counters": {
                            "nodes_created": summary.counters.nodes_created,
                            "nodes_deleted": summary.counters.nodes_deleted,
                            "relationships_created": summary.counters.relationships_created,
                            "relationships_deleted": summary.counters.relationships_deleted,
                            "properties_set": summary.counters.properties_set,
                            "labels_added": summary.counters.labels_added
                        }
                    }
                    
                    # 如果有节点数据，添加到结果中
                    if node_data:
                        node_result["node"] = {
                            "properties": node_data,
                            "labels": node_labels
                        }
                    
                    results.append(node_result)
                    success_count += 1
            
            except Exception as e:
                error_result = {
                    "status": "error",
                    "message": f"Error processing node: {str(e)}",
                    "error_type": type(e).__name__,
                    "node": node
                }
                results.append(error_result)
                error_count += 1
        
        end_time = time.time()
        operation_duration = round(end_time - start_time, 3)
        
        # 准备返回结果
        response = {
            "status": "success",
            "message": f"Batch node creation completed: {success_count} succeeded, {error_count} failed",
            "total_nodes": len(nodes),
            "success_count": success_count,
            "error_count": error_count,
            "operation_duration_seconds": operation_duration,
            "results": results if len(results) <= 100 else f"{len(results)} results (truncated)"
        }
        
        return json.dumps(response, indent=2, default=str)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)