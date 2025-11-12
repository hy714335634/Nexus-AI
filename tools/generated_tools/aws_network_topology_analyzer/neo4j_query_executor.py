from strands import tool
from typing import Dict, List, Optional, Any, Union
import json
import logging
import time
from neo4j import GraphDatabase, Driver, Session, Result
from neo4j.exceptions import ServiceUnavailable, AuthError, DatabaseError, CypherSyntaxError

# Import the get_connection function from neo4j_database_connector
from tools.generated_tools.aws_network_topology_analyzer.neo4j_database_connector import get_connection

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@tool
def neo4j_query_executor(
    query: str,
    parameters: Optional[Dict[str, Any]] = None,
    connection_id: str = "default",
    database: str = "neo4j",
    timeout: int = 60,
    include_stats: bool = True,
    result_format: str = "default"
) -> str:
    """
    执行Neo4j查询
    
    Args:
        query: Cypher查询语句
        parameters: 查询参数字典（可选）
        connection_id: 数据库连接ID（可选，默认为"default"）
        database: 数据库名称（可选，默认为"neo4j"）
        timeout: 查询超时时间（秒）（可选，默认为60秒）
        include_stats: 是否包含查询统计信息（可选，默认为True）
        result_format: 结果格式（可选，默认为"default"，可选值："default", "graph", "table", "raw"）
        
    Returns:
        str: JSON格式的查询结果
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
        
        # 准备参数
        params = parameters if parameters else {}
        
        # 执行查询
        with driver.session(database=database) as session:
            start_time = time.time()
            
            try:
                result = session.run(query, params, timeout=timeout)
                
                # 收集结果
                records = []
                
                # 处理不同的结果格式
                if result_format == "graph":
                    # 图形格式，适合可视化
                    nodes = []
                    relationships = []
                    node_ids = set()
                    
                    for record in result:
                        for key, value in record.items():
                            if hasattr(value, "id") and hasattr(value, "labels"):
                                # 这是一个节点
                                if value.id not in node_ids:
                                    node_ids.add(value.id)
                                    nodes.append({
                                        "id": value.id,
                                        "labels": list(value.labels),
                                        "properties": dict(value.items())
                                    })
                            elif hasattr(value, "type") and hasattr(value, "start_node") and hasattr(value, "end_node"):
                                # 这是一个关系
                                relationships.append({
                                    "id": value.id,
                                    "type": value.type,
                                    "start_node": value.start_node.id,
                                    "end_node": value.end_node.id,
                                    "properties": dict(value.items())
                                })
                            elif isinstance(value, list):
                                # 处理列表中的节点和关系
                                for item in value:
                                    if hasattr(item, "id") and hasattr(item, "labels"):
                                        # 这是一个节点
                                        if item.id not in node_ids:
                                            node_ids.add(item.id)
                                            nodes.append({
                                                "id": item.id,
                                                "labels": list(item.labels),
                                                "properties": dict(item.items())
                                            })
                                    elif hasattr(item, "type") and hasattr(item, "start_node") and hasattr(item, "end_node"):
                                        # 这是一个关系
                                        relationships.append({
                                            "id": item.id,
                                            "type": item.type,
                                            "start_node": item.start_node.id,
                                            "end_node": item.end_node.id,
                                            "properties": dict(item.items())
                                        })
                    
                    records = {
                        "nodes": nodes,
                        "relationships": relationships
                    }
                
                elif result_format == "table":
                    # 表格格式，适合表格展示
                    columns = result.keys()
                    rows = []
                    
                    for record in result:
                        row = {}
                        for key in columns:
                            value = record[key]
                            
                            # 处理Neo4j节点和关系
                            if hasattr(value, "id") and hasattr(value, "labels"):
                                # 这是一个节点
                                row[key] = {
                                    "type": "node",
                                    "id": value.id,
                                    "labels": list(value.labels),
                                    "properties": dict(value.items())
                                }
                            elif hasattr(value, "type") and hasattr(value, "start_node") and hasattr(value, "end_node"):
                                # 这是一个关系
                                row[key] = {
                                    "type": "relationship",
                                    "id": value.id,
                                    "relationship_type": value.type,
                                    "start_node": value.start_node.id,
                                    "end_node": value.end_node.id,
                                    "properties": dict(value.items())
                                }
                            else:
                                # 这是一个普通值
                                row[key] = value
                        
                        rows.append(row)
                    
                    records = {
                        "columns": columns,
                        "rows": rows
                    }
                
                elif result_format == "raw":
                    # 原始格式，保留Neo4j返回的原始结构
                    for record in result:
                        record_dict = {}
                        for key, value in record.items():
                            # 处理Neo4j节点
                            if hasattr(value, "id") and hasattr(value, "labels"):
                                record_dict[key] = {
                                    "id": value.id,
                                    "labels": list(value.labels),
                                    "properties": dict(value.items())
                                }
                            # 处理Neo4j关系
                            elif hasattr(value, "type") and hasattr(value, "start_node") and hasattr(value, "end_node"):
                                record_dict[key] = {
                                    "id": value.id,
                                    "type": value.type,
                                    "start_node_id": value.start_node.id,
                                    "end_node_id": value.end_node.id,
                                    "properties": dict(value.items())
                                }
                            # 处理路径
                            elif hasattr(value, "start_node") and hasattr(value, "relationships"):
                                path_nodes = []
                                path_rels = []
                                
                                # 添加起始节点
                                start_node = value.start_node
                                path_nodes.append({
                                    "id": start_node.id,
                                    "labels": list(start_node.labels),
                                    "properties": dict(start_node.items())
                                })
                                
                                # 添加关系和节点
                                for rel in value.relationships:
                                    path_rels.append({
                                        "id": rel.id,
                                        "type": rel.type,
                                        "properties": dict(rel.items())
                                    })
                                    
                                    end_node = rel.end_node
                                    path_nodes.append({
                                        "id": end_node.id,
                                        "labels": list(end_node.labels),
                                        "properties": dict(end_node.items())
                                    })
                                
                                record_dict[key] = {
                                    "type": "path",
                                    "nodes": path_nodes,
                                    "relationships": path_rels
                                }
                            # 处理列表
                            elif isinstance(value, list):
                                processed_list = []
                                for item in value:
                                    if hasattr(item, "id") and hasattr(item, "labels"):
                                        # 这是一个节点
                                        processed_list.append({
                                            "id": item.id,
                                            "labels": list(item.labels),
                                            "properties": dict(item.items())
                                        })
                                    elif hasattr(item, "type") and hasattr(item, "start_node") and hasattr(item, "end_node"):
                                        # 这是一个关系
                                        processed_list.append({
                                            "id": item.id,
                                            "type": item.type,
                                            "start_node_id": item.start_node.id,
                                            "end_node_id": item.end_node.id,
                                            "properties": dict(item.items())
                                        })
                                    else:
                                        # 这是一个普通值
                                        processed_list.append(item)
                                
                                record_dict[key] = processed_list
                            else:
                                # 这是一个普通值
                                record_dict[key] = value
                        
                        records.append(record_dict)
                
                else:  # default format
                    # 默认格式，简化的记录列表
                    for record in result:
                        record_dict = {}
                        for key, value in record.items():
                            # 处理Neo4j节点
                            if hasattr(value, "id") and hasattr(value, "labels"):
                                record_dict[key] = dict(value.items())
                                record_dict[key]["_labels"] = list(value.labels)
                            # 处理Neo4j关系
                            elif hasattr(value, "type") and hasattr(value, "start_node") and hasattr(value, "end_node"):
                                record_dict[key] = dict(value.items())
                                record_dict[key]["_type"] = value.type
                            # 处理路径
                            elif hasattr(value, "start_node") and hasattr(value, "relationships"):
                                path_data = {
                                    "nodes": [],
                                    "relationships": []
                                }
                                
                                # 添加起始节点
                                start_node = value.start_node
                                path_data["nodes"].append({
                                    "properties": dict(start_node.items()),
                                    "labels": list(start_node.labels)
                                })
                                
                                # 添加关系和节点
                                for rel in value.relationships:
                                    path_data["relationships"].append({
                                        "type": rel.type,
                                        "properties": dict(rel.items())
                                    })
                                    
                                    end_node = rel.end_node
                                    path_data["nodes"].append({
                                        "properties": dict(end_node.items()),
                                        "labels": list(end_node.labels)
                                    })
                                
                                record_dict[key] = path_data
                            # 处理列表
                            elif isinstance(value, list):
                                processed_list = []
                                for item in value:
                                    if hasattr(item, "id") and hasattr(item, "labels"):
                                        # 这是一个节点
                                        item_dict = dict(item.items())
                                        item_dict["_labels"] = list(item.labels)
                                        processed_list.append(item_dict)
                                    elif hasattr(item, "type") and hasattr(item, "start_node") and hasattr(item, "end_node"):
                                        # 这是一个关系
                                        item_dict = dict(item.items())
                                        item_dict["_type"] = item.type
                                        processed_list.append(item_dict)
                                    else:
                                        # 这是一个普通值
                                        processed_list.append(item)
                                
                                record_dict[key] = processed_list
                            else:
                                # 这是一个普通值
                                record_dict[key] = value
                        
                        records.append(record_dict)
                
                # 获取查询统计信息
                summary = result.consume()
                
                end_time = time.time()
                query_duration = round(end_time - start_time, 3)
                
                # 准备返回结果
                response = {
                    "status": "success",
                    "message": "Query executed successfully",
                    "result_count": len(records) if isinstance(records, list) else 1,
                    "query_duration_seconds": query_duration,
                    "result_format": result_format,
                    "results": records
                }
                
                # 如果请求包含统计信息，添加到响应中
                if include_stats:
                    response["stats"] = {
                        "nodes_created": summary.counters.nodes_created,
                        "nodes_deleted": summary.counters.nodes_deleted,
                        "relationships_created": summary.counters.relationships_created,
                        "relationships_deleted": summary.counters.relationships_deleted,
                        "properties_set": summary.counters.properties_set,
                        "labels_added": summary.counters.labels_added,
                        "contains_updates": summary.counters.contains_updates,
                        "contains_system_updates": summary.counters.contains_system_updates
                    }
                
                return json.dumps(response, indent=2, default=str)
            
            except CypherSyntaxError as e:
                error_result = {
                    "status": "error",
                    "message": f"Cypher syntax error: {str(e)}",
                    "error_type": "CypherSyntaxError",
                    "query": query
                }
                return json.dumps(error_result, indent=2)
            
            except DatabaseError as e:
                error_result = {
                    "status": "error",
                    "message": f"Database error: {str(e)}",
                    "error_type": "DatabaseError",
                    "query": query
                }
                return json.dumps(error_result, indent=2)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "error_type": type(e).__name__,
            "query": query
        }
        return json.dumps(error_result, indent=2)

@tool
def neo4j_schema_inspector(
    connection_id: str = "default",
    database: str = "neo4j",
    include_counts: bool = True,
    include_indexes: bool = True,
    include_constraints: bool = True
) -> str:
    """
    检查Neo4j数据库模式
    
    Args:
        connection_id: 数据库连接ID（可选，默认为"default"）
        database: 数据库名称（可选，默认为"neo4j"）
        include_counts: 是否包含节点和关系计数（可选，默认为True）
        include_indexes: 是否包含索引信息（可选，默认为True）
        include_constraints: 是否包含约束信息（可选，默认为True）
        
    Returns:
        str: JSON格式的数据库模式信息
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
        
        schema_info = {
            "labels": [],
            "relationship_types": []
        }
        
        with driver.session(database=database) as session:
            # 获取所有标签
            labels_result = session.run("CALL db.labels()")
            for record in labels_result:
                label = record["label"]
                label_info = {"name": label}
                
                # 如果需要，获取节点计数
                if include_counts:
                    count_result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                    label_info["count"] = count_result.single()["count"]
                
                # 获取标签的属性键
                props_result = session.run(f"MATCH (n:{label}) UNWIND keys(n) AS key RETURN DISTINCT key")
                label_info["properties"] = [record["key"] for record in props_result]
                
                schema_info["labels"].append(label_info)
            
            # 获取所有关系类型
            rel_types_result = session.run("CALL db.relationshipTypes()")
            for record in rel_types_result:
                rel_type = record["relationshipType"]
                rel_type_info = {"name": rel_type}
                
                # 如果需要，获取关系计数
                if include_counts:
                    count_result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count")
                    rel_type_info["count"] = count_result.single()["count"]
                
                # 获取关系的属性键
                props_result = session.run(f"MATCH ()-[r:{rel_type}]->() UNWIND keys(r) AS key RETURN DISTINCT key")
                rel_type_info["properties"] = [record["key"] for record in props_result]
                
                # 获取关系的起始和结束标签
                patterns_result = session.run(f"""
                MATCH (a)-[r:{rel_type}]->(b)
                RETURN DISTINCT labels(a) AS source_labels, labels(b) AS target_labels
                LIMIT 10
                """)
                
                patterns = []
                for pattern in patterns_result:
                    patterns.append({
                        "source_labels": pattern["source_labels"],
                        "target_labels": pattern["target_labels"]
                    })
                
                rel_type_info["patterns"] = patterns
                
                schema_info["relationship_types"].append(rel_type_info)
            
            # 如果需要，获取索引信息
            if include_indexes:
                indexes_result = session.run("SHOW INDEXES")
                schema_info["indexes"] = [dict(record["indexes"]) for record in indexes_result]
            
            # 如果需要，获取约束信息
            if include_constraints:
                constraints_result = session.run("SHOW CONSTRAINTS")
                schema_info["constraints"] = [dict(record["constraints"]) for record in constraints_result]
        
        # 准备返回结果
        response = {
            "status": "success",
            "message": "Schema inspection completed successfully",
            "database": database,
            "schema": schema_info
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
def neo4j_common_queries(
    query_type: str,
    parameters: Optional[Dict[str, Any]] = None,
    connection_id: str = "default",
    database: str = "neo4j",
    limit: int = 100
) -> str:
    """
    执行常用Neo4j查询
    
    Args:
        query_type: 查询类型，可选值：
                    "all_labels", "all_relationship_types", "node_count", "relationship_count",
                    "nodes_by_label", "relationships_by_type", "node_properties", "relationship_properties",
                    "orphan_nodes", "leaf_nodes", "central_nodes", "isolated_nodes",
                    "densest_relationships", "longest_paths"
        parameters: 查询参数字典（可选）
        connection_id: 数据库连接ID（可选，默认为"default"）
        database: 数据库名称（可选，默认为"neo4j"）
        limit: 结果限制数量（可选，默认为100）
        
    Returns:
        str: JSON格式的查询结果
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
        
        # 准备参数
        params = parameters if parameters else {}
        params["limit"] = limit
        
        # 定义常用查询
        queries = {
            "all_labels": "CALL db.labels() YIELD label RETURN label ORDER BY label",
            
            "all_relationship_types": "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType",
            
            "node_count": "MATCH (n) RETURN count(n) as node_count",
            
            "relationship_count": "MATCH ()-[r]->() RETURN count(r) as relationship_count",
            
            "nodes_by_label": """
                MATCH (n{label_filter})
                RETURN n
                LIMIT $limit
            """,
            
            "relationships_by_type": """
                MATCH ()-[r{rel_filter}]->()
                RETURN r
                LIMIT $limit
            """,
            
            "node_properties": """
                MATCH (n{label_filter})
                UNWIND keys(n) AS property
                RETURN DISTINCT property
                ORDER BY property
            """,
            
            "relationship_properties": """
                MATCH ()-[r{rel_filter}]->()
                UNWIND keys(r) AS property
                RETURN DISTINCT property
                ORDER BY property
            """,
            
            "orphan_nodes": """
                MATCH (n)
                WHERE NOT (n)--()
                RETURN n
                LIMIT $limit
            """,
            
            "leaf_nodes": """
                MATCH (n)-[]->(m)
                WHERE NOT (m)-->()
                RETURN DISTINCT m as leaf_node
                LIMIT $limit
            """,
            
            "central_nodes": """
                MATCH (n)
                WITH n, size((n)--()) as connections
                ORDER BY connections DESC
                LIMIT $limit
                RETURN n, connections
            """,
            
            "isolated_nodes": """
                MATCH (n)
                WHERE NOT (n)--()
                RETURN n
                LIMIT $limit
            """,
            
            "densest_relationships": """
                MATCH (a)-[r]->(b)
                WITH a, b, count(r) as rel_count
                ORDER BY rel_count DESC
                LIMIT $limit
                MATCH (a)-[r]->(b)
                RETURN a, collect(r) as relationships, b, rel_count
            """,
            
            "longest_paths": """
                MATCH path = (a)-[*1..{max_depth}]->(b)
                WITH path, length(path) as path_length
                ORDER BY path_length DESC
                LIMIT $limit
                RETURN path, path_length
            """
        }
        
        # 检查查询类型是否有效
        if query_type not in queries:
            return json.dumps({
                "status": "error",
                "message": f"Invalid query type: {query_type}",
                "valid_query_types": list(queries.keys())
            }, indent=2)
        
        # 获取基本查询
        query = queries[query_type]
        
        # 处理特殊参数
        if query_type == "nodes_by_label":
            label = params.get("label", "")
            query = query.replace("{label_filter}", f":{label}" if label else "")
        
        elif query_type == "relationships_by_type":
            rel_type = params.get("relationship_type", "")
            query = query.replace("{rel_filter}", f":{rel_type}" if rel_type else "")
        
        elif query_type == "node_properties":
            label = params.get("label", "")
            query = query.replace("{label_filter}", f":{label}" if label else "")
        
        elif query_type == "relationship_properties":
            rel_type = params.get("relationship_type", "")
            query = query.replace("{rel_filter}", f":{rel_type}" if rel_type else "")
        
        elif query_type == "longest_paths":
            max_depth = params.get("max_depth", 5)
            query = query.replace("{max_depth}", str(max_depth))
        
        # 执行查询
        with driver.session(database=database) as session:
            start_time = time.time()
            
            try:
                result = session.run(query, params)
                
                # 收集结果
                records = []
                for record in result:
                    record_dict = {}
                    for key, value in record.items():
                        # 处理Neo4j节点
                        if hasattr(value, "id") and hasattr(value, "labels"):
                            record_dict[key] = dict(value.items())
                            record_dict[key]["_labels"] = list(value.labels)
                        # 处理Neo4j关系
                        elif hasattr(value, "type") and hasattr(value, "start_node") and hasattr(value, "end_node"):
                            record_dict[key] = dict(value.items())
                            record_dict[key]["_type"] = value.type
                        # 处理路径
                        elif hasattr(value, "start_node") and hasattr(value, "relationships"):
                            path_data = {
                                "nodes": [],
                                "relationships": []
                            }
                            
                            # 添加起始节点
                            start_node = value.start_node
                            path_data["nodes"].append({
                                "properties": dict(start_node.items()),
                                "labels": list(start_node.labels)
                            })
                            
                            # 添加关系和节点
                            for rel in value.relationships:
                                path_data["relationships"].append({
                                    "type": rel.type,
                                    "properties": dict(rel.items())
                                })
                                
                                end_node = rel.end_node
                                path_data["nodes"].append({
                                    "properties": dict(end_node.items()),
                                    "labels": list(end_node.labels)
                                })
                            
                            record_dict[key] = path_data
                        # 处理列表
                        elif isinstance(value, list):
                            processed_list = []
                            for item in value:
                                if hasattr(item, "id") and hasattr(item, "labels"):
                                    # 这是一个节点
                                    item_dict = dict(item.items())
                                    item_dict["_labels"] = list(item.labels)
                                    processed_list.append(item_dict)
                                elif hasattr(item, "type") and hasattr(item, "start_node") and hasattr(item, "end_node"):
                                    # 这是一个关系
                                    item_dict = dict(item.items())
                                    item_dict["_type"] = item.type
                                    processed_list.append(item_dict)
                                else:
                                    # 这是一个普通值
                                    processed_list.append(item)
                            
                            record_dict[key] = processed_list
                        else:
                            # 这是一个普通值
                            record_dict[key] = value
                    
                    records.append(record_dict)
                
                # 获取查询统计信息
                summary = result.consume()
                
                end_time = time.time()
                query_duration = round(end_time - start_time, 3)
                
                # 准备返回结果
                response = {
                    "status": "success",
                    "message": "Query executed successfully",
                    "query_type": query_type,
                    "result_count": len(records),
                    "query_duration_seconds": query_duration,
                    "results": records,
                    "query": query
                }
                
                return json.dumps(response, indent=2, default=str)
            
            except CypherSyntaxError as e:
                error_result = {
                    "status": "error",
                    "message": f"Cypher syntax error: {str(e)}",
                    "error_type": "CypherSyntaxError",
                    "query_type": query_type,
                    "query": query
                }
                return json.dumps(error_result, indent=2)
            
            except DatabaseError as e:
                error_result = {
                    "status": "error",
                    "message": f"Database error: {str(e)}",
                    "error_type": "DatabaseError",
                    "query_type": query_type,
                    "query": query
                }
                return json.dumps(error_result, indent=2)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "error_type": type(e).__name__,
            "query_type": query_type
        }
        return json.dumps(error_result, indent=2)