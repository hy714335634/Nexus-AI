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
def neo4j_edge_creator(
    source_node_type: str,
    source_properties: Dict[str, Any],
    target_node_type: str,
    target_properties: Dict[str, Any],
    relationship_type: str,
    relationship_properties: Optional[Dict[str, Any]] = None,
    source_merge_keys: Optional[List[str]] = None,
    target_merge_keys: Optional[List[str]] = None,
    connection_id: str = "default",
    database: str = "neo4j",
    create_missing_nodes: bool = True,
    return_relationship: bool = True
) -> str:
    """
    创建Neo4j边/关系
    
    Args:
        source_node_type: 源节点类型
        source_properties: 源节点属性字典，用于查找源节点
        target_node_type: 目标节点类型
        target_properties: 目标节点属性字典，用于查找目标节点
        relationship_type: 关系类型
        relationship_properties: 关系属性字典（可选）
        source_merge_keys: 用于查找源节点的键列表（可选，默认使用resource_id或id）
        target_merge_keys: 用于查找目标节点的键列表（可选，默认使用resource_id或id）
        connection_id: 数据库连接ID（可选，默认为"default"）
        database: 数据库名称（可选，默认为"neo4j"）
        create_missing_nodes: 是否创建不存在的节点（可选，默认为True）
        return_relationship: 是否返回创建的关系（可选，默认为True）
        
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
        
        # 确定用于查找源节点的键
        if not source_merge_keys:
            if "resource_id" in source_properties:
                source_merge_keys = ["resource_id"]
            elif "id" in source_properties:
                source_merge_keys = ["id"]
            else:
                # 如果没有明确的唯一标识符，使用所有属性
                source_merge_keys = list(source_properties.keys())
        
        # 确定用于查找目标节点的键
        if not target_merge_keys:
            if "resource_id" in target_properties:
                target_merge_keys = ["resource_id"]
            elif "id" in target_properties:
                target_merge_keys = ["id"]
            else:
                # 如果没有明确的唯一标识符，使用所有属性
                target_merge_keys = list(target_properties.keys())
        
        # 构建源节点查找条件
        source_conditions = " AND ".join([f"a.{key} = $source_{key}" for key in source_merge_keys])
        
        # 构建目标节点查找条件
        target_conditions = " AND ".join([f"b.{key} = $target_{key}" for key in target_merge_keys])
        
        # 准备关系属性
        rel_props = relationship_properties if relationship_properties else {}
        
        # 执行关系创建操作
        with driver.session(database=database) as session:
            start_time = time.time()
            
            # 构建查询
            if create_missing_nodes:
                query = f"""
                MERGE (a:{source_node_type} {{{source_conditions}}})
                {f"SET a += $source_properties" if create_missing_nodes else ""}
                MERGE (b:{target_node_type} {{{target_conditions}}})
                {f"SET b += $target_properties" if create_missing_nodes else ""}
                MERGE (a)-[r:{relationship_type}]->(b)
                SET r += $rel_props
                {f"RETURN a, r, b" if return_relationship else ""}
                """
            else:
                query = f"""
                MATCH (a:{source_node_type} {{{source_conditions}}})
                MATCH (b:{target_node_type} {{{target_conditions}}})
                MERGE (a)-[r:{relationship_type}]->(b)
                SET r += $rel_props
                {f"RETURN a, r, b" if return_relationship else ""}
                """
            
            # 准备参数
            params = {}
            for key in source_merge_keys:
                params[f"source_{key}"] = source_properties[key]
            
            for key in target_merge_keys:
                params[f"target_{key}"] = target_properties[key]
            
            if create_missing_nodes:
                params["source_properties"] = source_properties
                params["target_properties"] = target_properties
            
            params["rel_props"] = rel_props
            
            # 执行查询
            result = session.run(query, params)
            
            # 处理结果
            summary = result.consume()
            
            if return_relationship and result.peek():
                record = result.single()
                source_node = dict(record["a"].items())
                source_labels = list(record["a"].labels)
                relationship = dict(record["r"].items())
                relationship_type_name = type(record["r"]).__name__
                target_node = dict(record["b"].items())
                target_labels = list(record["b"].labels)
                
                relationship_data = {
                    "source_node": {
                        "properties": source_node,
                        "labels": source_labels
                    },
                    "relationship": {
                        "type": relationship_type_name,
                        "properties": relationship
                    },
                    "target_node": {
                        "properties": target_node,
                        "labels": target_labels
                    }
                }
            else:
                relationship_data = None
            
            end_time = time.time()
            operation_duration = round(end_time - start_time, 3)
            
            # 准备返回结果
            response = {
                "status": "success",
                "message": f"Relationship created/updated successfully",
                "source_node_type": source_node_type,
                "target_node_type": target_node_type,
                "relationship_type": relationship_type,
                "source_merge_keys": source_merge_keys,
                "target_merge_keys": target_merge_keys,
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
            
            # 如果请求返回关系数据，添加到响应中
            if return_relationship and relationship_data:
                response["relationship_data"] = relationship_data
            
            return json.dumps(response, indent=2, default=str)
    
    except DatabaseError as e:
        error_result = {
            "status": "error",
            "message": f"Database error: {str(e)}",
            "error_type": "DatabaseError",
            "source_node_type": source_node_type,
            "target_node_type": target_node_type,
            "relationship_type": relationship_type
        }
        return json.dumps(error_result, indent=2)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "error_type": type(e).__name__,
            "source_node_type": source_node_type,
            "target_node_type": target_node_type,
            "relationship_type": relationship_type
        }
        return json.dumps(error_result, indent=2)

@tool
def neo4j_batch_edge_creator(
    edges: List[Dict[str, Any]],
    connection_id: str = "default",
    database: str = "neo4j",
    create_missing_nodes: bool = True
) -> str:
    """
    批量创建Neo4j边/关系
    
    Args:
        edges: 边列表，每个边是一个包含源节点、目标节点和关系信息的字典
        connection_id: 数据库连接ID（可选，默认为"default"）
        database: 数据库名称（可选，默认为"neo4j"）
        create_missing_nodes: 是否创建不存在的节点（可选，默认为True）
        
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
        
        # 执行批量关系创建操作
        start_time = time.time()
        results = []
        success_count = 0
        error_count = 0
        
        for edge in edges:
            try:
                source_node_type = edge.get("source_node_type")
                source_properties = edge.get("source_properties", {})
                target_node_type = edge.get("target_node_type")
                target_properties = edge.get("target_properties", {})
                relationship_type = edge.get("relationship_type")
                relationship_properties = edge.get("relationship_properties", {})
                source_merge_keys = edge.get("source_merge_keys")
                target_merge_keys = edge.get("target_merge_keys")
                
                # 确定用于查找源节点的键
                if not source_merge_keys:
                    if "resource_id" in source_properties:
                        source_merge_keys = ["resource_id"]
                    elif "id" in source_properties:
                        source_merge_keys = ["id"]
                    else:
                        # 如果没有明确的唯一标识符，使用所有属性
                        source_merge_keys = list(source_properties.keys())
                
                # 确定用于查找目标节点的键
                if not target_merge_keys:
                    if "resource_id" in target_properties:
                        target_merge_keys = ["resource_id"]
                    elif "id" in target_properties:
                        target_merge_keys = ["id"]
                    else:
                        # 如果没有明确的唯一标识符，使用所有属性
                        target_merge_keys = list(target_properties.keys())
                
                # 构建源节点查找条件
                source_conditions = " AND ".join([f"a.{key} = $source_{key}" for key in source_merge_keys])
                
                # 构建目标节点查找条件
                target_conditions = " AND ".join([f"b.{key} = $target_{key}" for key in target_merge_keys])
                
                # 准备关系属性
                rel_props = relationship_properties if relationship_properties else {}
                
                with driver.session(database=database) as session:
                    # 构建查询
                    if create_missing_nodes:
                        query = f"""
                        MERGE (a:{source_node_type} {{{source_conditions}}})
                        {f"SET a += $source_properties" if create_missing_nodes else ""}
                        MERGE (b:{target_node_type} {{{target_conditions}}})
                        {f"SET b += $target_properties" if create_missing_nodes else ""}
                        MERGE (a)-[r:{relationship_type}]->(b)
                        SET r += $rel_props
                        """
                    else:
                        query = f"""
                        MATCH (a:{source_node_type} {{{source_conditions}}})
                        MATCH (b:{target_node_type} {{{target_conditions}}})
                        MERGE (a)-[r:{relationship_type}]->(b)
                        SET r += $rel_props
                        """
                    
                    # 准备参数
                    params = {}
                    for key in source_merge_keys:
                        params[f"source_{key}"] = source_properties[key]
                    
                    for key in target_merge_keys:
                        params[f"target_{key}"] = target_properties[key]
                    
                    if create_missing_nodes:
                        params["source_properties"] = source_properties
                        params["target_properties"] = target_properties
                    
                    params["rel_props"] = rel_props
                    
                    # 执行查询
                    result = session.run(query, params)
                    
                    # 处理结果
                    summary = result.consume()
                    
                    # 准备边结果
                    edge_result = {
                        "status": "success",
                        "source_node_type": source_node_type,
                        "target_node_type": target_node_type,
                        "relationship_type": relationship_type,
                        "source_merge_keys": source_merge_keys,
                        "target_merge_keys": target_merge_keys,
                        "counters": {
                            "nodes_created": summary.counters.nodes_created,
                            "nodes_deleted": summary.counters.nodes_deleted,
                            "relationships_created": summary.counters.relationships_created,
                            "relationships_deleted": summary.counters.relationships_deleted,
                            "properties_set": summary.counters.properties_set,
                            "labels_added": summary.counters.labels_added
                        }
                    }
                    
                    results.append(edge_result)
                    success_count += 1
            
            except Exception as e:
                error_result = {
                    "status": "error",
                    "message": f"Error processing edge: {str(e)}",
                    "error_type": type(e).__name__,
                    "edge": edge
                }
                results.append(error_result)
                error_count += 1
        
        end_time = time.time()
        operation_duration = round(end_time - start_time, 3)
        
        # 准备返回结果
        response = {
            "status": "success",
            "message": f"Batch edge creation completed: {success_count} succeeded, {error_count} failed",
            "total_edges": len(edges),
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

@tool
def neo4j_hierarchical_relationship_creator(
    resource_hierarchy: Dict[str, Any],
    connection_id: str = "default",
    database: str = "neo4j",
    create_missing_nodes: bool = True
) -> str:
    """
    创建层级结构的关系
    
    Args:
        resource_hierarchy: 资源层级结构，包含account、region、services等层级信息
        connection_id: 数据库连接ID（可选，默认为"default"）
        database: 数据库名称（可选，默认为"neo4j"）
        create_missing_nodes: 是否创建不存在的节点（可选，默认为True）
        
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
        
        # 验证资源层级结构
        if "account" not in resource_hierarchy:
            return json.dumps({
                "status": "error",
                "message": "Resource hierarchy must contain 'account' information"
            }, indent=2)
        
        # 获取账户信息
        account = resource_hierarchy.get("account", {})
        account_id = account.get("account_id", "")
        
        if not account_id:
            return json.dumps({
                "status": "error",
                "message": "Account ID is required in resource hierarchy"
            }, indent=2)
        
        # 创建账户节点
        account_properties = {
            "resource_id": account_id,
            "account_id": account_id
        }
        if "name" in account:
            account_properties["name"] = account["name"]
        
        # 执行层级关系创建操作
        start_time = time.time()
        results = {
            "nodes_created": 0,
            "relationships_created": 0,
            "errors": []
        }
        
        # 创建账户节点
        with driver.session(database=database) as session:
            account_query = """
            MERGE (a:Account {account_id: $account_id})
            SET a += $properties
            RETURN a
            """
            
            session.run(account_query, {
                "account_id": account_id,
                "properties": account_properties
            })
            
            results["nodes_created"] += 1
        
        # 处理区域节点和关系
        if "regions" in resource_hierarchy:
            regions = resource_hierarchy["regions"]
            
            for region in regions:
                region_name = region.get("region_name", "")
                
                if not region_name:
                    results["errors"].append({
                        "message": "Region name is required",
                        "region": region
                    })
                    continue
                
                # 创建区域节点和与账户的关系
                try:
                    region_properties = {
                        "resource_id": region_name,
                        "region_name": region_name
                    }
                    
                    with driver.session(database=database) as session:
                        region_query = """
                        MATCH (a:Account {account_id: $account_id})
                        MERGE (r:Region {region_name: $region_name})
                        SET r += $properties
                        MERGE (a)-[rel:HAS_REGION]->(r)
                        RETURN a, rel, r
                        """
                        
                        session.run(region_query, {
                            "account_id": account_id,
                            "region_name": region_name,
                            "properties": region_properties
                        })
                        
                        results["nodes_created"] += 1
                        results["relationships_created"] += 1
                    
                    # 处理网络服务节点和关系
                    if "network_services" in region:
                        network_services = region["network_services"]
                        
                        for service in network_services:
                            service_type = service.get("service_type", "")
                            service_id = service.get("service_id", "")
                            
                            if not service_type or not service_id:
                                results["errors"].append({
                                    "message": "Service type and ID are required",
                                    "service": service
                                })
                                continue
                            
                            # 创建服务节点和与区域的关系
                            try:
                                service_properties = {
                                    "resource_id": service_id,
                                    "service_id": service_id,
                                    "service_type": service_type
                                }
                                
                                # 添加其他属性
                                for key, value in service.items():
                                    if key not in ["service_type", "service_id", "resources"]:
                                        service_properties[key] = value
                                
                                with driver.session(database=database) as session:
                                    service_query = """
                                    MATCH (r:Region {region_name: $region_name})
                                    MERGE (s:{service_type} {{service_id: $service_id}})
                                    SET s += $properties
                                    MERGE (r)-[rel:HAS_SERVICE]->(s)
                                    RETURN r, rel, s
                                    """.format(service_type=service_type)
                                    
                                    session.run(service_query, {
                                        "region_name": region_name,
                                        "service_id": service_id,
                                        "properties": service_properties
                                    })
                                    
                                    results["nodes_created"] += 1
                                    results["relationships_created"] += 1
                                
                                # 处理服务资源节点和关系
                                if "resources" in service:
                                    resources = service["resources"]
                                    
                                    for resource in resources:
                                        resource_type = resource.get("resource_type", "")
                                        resource_id = resource.get("resource_id", "")
                                        
                                        if not resource_type or not resource_id:
                                            results["errors"].append({
                                                "message": "Resource type and ID are required",
                                                "resource": resource
                                            })
                                            continue
                                        
                                        # 创建资源节点和与服务的关系
                                        try:
                                            resource_properties = {
                                                "resource_id": resource_id,
                                                "resource_type": resource_type
                                            }
                                            
                                            # 添加其他属性
                                            for key, value in resource.items():
                                                if key not in ["resource_type", "resource_id", "sub_resources"]:
                                                    resource_properties[key] = value
                                            
                                            with driver.session(database=database) as session:
                                                resource_query = """
                                                MATCH (s:{service_type} {{service_id: $service_id}})
                                                MERGE (r:{resource_type} {{resource_id: $resource_id}})
                                                SET r += $properties
                                                MERGE (s)-[rel:HAS_RESOURCE]->(r)
                                                RETURN s, rel, r
                                                """.format(
                                                    service_type=service_type,
                                                    resource_type=resource_type
                                                )
                                                
                                                session.run(resource_query, {
                                                    "service_id": service_id,
                                                    "resource_id": resource_id,
                                                    "properties": resource_properties
                                                })
                                                
                                                results["nodes_created"] += 1
                                                results["relationships_created"] += 1
                                            
                                            # 处理子资源节点和关系
                                            if "sub_resources" in resource:
                                                sub_resources = resource["sub_resources"]
                                                
                                                for sub_resource in sub_resources:
                                                    sub_resource_type = sub_resource.get("resource_type", "")
                                                    sub_resource_id = sub_resource.get("resource_id", "")
                                                    
                                                    if not sub_resource_type or not sub_resource_id:
                                                        results["errors"].append({
                                                            "message": "Sub-resource type and ID are required",
                                                            "sub_resource": sub_resource
                                                        })
                                                        continue
                                                    
                                                    # 创建子资源节点和与资源的关系
                                                    try:
                                                        sub_resource_properties = {
                                                            "resource_id": sub_resource_id,
                                                            "resource_type": sub_resource_type
                                                        }
                                                        
                                                        # 添加其他属性
                                                        for key, value in sub_resource.items():
                                                            if key not in ["resource_type", "resource_id"]:
                                                                sub_resource_properties[key] = value
                                                        
                                                        with driver.session(database=database) as session:
                                                            sub_resource_query = """
                                                            MATCH (r:{resource_type} {{resource_id: $resource_id}})
                                                            MERGE (sr:{sub_resource_type} {{resource_id: $sub_resource_id}})
                                                            SET sr += $properties
                                                            MERGE (r)-[rel:HAS_SUB_RESOURCE]->(sr)
                                                            RETURN r, rel, sr
                                                            """.format(
                                                                resource_type=resource_type,
                                                                sub_resource_type=sub_resource_type
                                                            )
                                                            
                                                            session.run(sub_resource_query, {
                                                                "resource_id": resource_id,
                                                                "sub_resource_id": sub_resource_id,
                                                                "properties": sub_resource_properties
                                                            })
                                                            
                                                            results["nodes_created"] += 1
                                                            results["relationships_created"] += 1
                                                    
                                                    except Exception as e:
                                                        results["errors"].append({
                                                            "message": f"Error creating sub-resource: {str(e)}",
                                                            "sub_resource": sub_resource,
                                                            "error_type": type(e).__name__
                                                        })
                                        
                                        except Exception as e:
                                            results["errors"].append({
                                                "message": f"Error creating resource: {str(e)}",
                                                "resource": resource,
                                                "error_type": type(e).__name__
                                            })
                            
                            except Exception as e:
                                results["errors"].append({
                                    "message": f"Error creating service: {str(e)}",
                                    "service": service,
                                    "error_type": type(e).__name__
                                })
                
                except Exception as e:
                    results["errors"].append({
                        "message": f"Error creating region: {str(e)}",
                        "region": region,
                        "error_type": type(e).__name__
                    })
        
        end_time = time.time()
        operation_duration = round(end_time - start_time, 3)
        
        # 准备返回结果
        response = {
            "status": "success",
            "message": f"Hierarchical relationship creation completed",
            "nodes_created": results["nodes_created"],
            "relationships_created": results["relationships_created"],
            "errors_count": len(results["errors"]),
            "operation_duration_seconds": operation_duration
        }
        
        # 如果有错误，添加到响应中
        if results["errors"]:
            response["errors"] = results["errors"]
        
        return json.dumps(response, indent=2, default=str)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)