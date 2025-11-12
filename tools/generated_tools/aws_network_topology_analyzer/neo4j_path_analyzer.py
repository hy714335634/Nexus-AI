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
def neo4j_path_analyzer(
    source_node_type: str,
    source_properties: Dict[str, Any],
    target_node_type: str,
    target_properties: Dict[str, Any],
    max_depth: int = 5,
    relationship_types: Optional[List[str]] = None,
    direction: str = "outgoing",
    connection_id: str = "default",
    database: str = "neo4j",
    limit: int = 10,
    include_node_details: bool = True
) -> str:
    """
    分析网络路径
    
    Args:
        source_node_type: 源节点类型
        source_properties: 源节点属性字典，用于查找源节点
        target_node_type: 目标节点类型
        target_properties: 目标节点属性字典，用于查找目标节点
        max_depth: 最大路径深度（可选，默认为5）
        relationship_types: 要包含的关系类型列表（可选，默认为所有类型）
        direction: 路径方向，可选值："outgoing", "incoming", "both"（可选，默认为"outgoing"）
        connection_id: 数据库连接ID（可选，默认为"default"）
        database: 数据库名称（可选，默认为"neo4j"）
        limit: 结果限制数量（可选，默认为10）
        include_node_details: 是否包含节点详细信息（可选，默认为True）
        
    Returns:
        str: JSON格式的路径分析结果
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
        
        # 构建源节点查询条件
        source_conditions = []
        for key, value in source_properties.items():
            source_conditions.append(f"a.{key} = ${key}")
        source_where_clause = " AND ".join(source_conditions)
        
        # 构建目标节点查询条件
        target_conditions = []
        for key, value in target_properties.items():
            target_conditions.append(f"b.{key} = ${key}")
        target_where_clause = " AND ".join(target_conditions)
        
        # 构建关系类型过滤
        rel_type_filter = ""
        if relationship_types:
            rel_types = "|".join(relationship_types)
            rel_type_filter = f":{rel_types}"
        
        # 构建路径方向
        if direction == "outgoing":
            path_direction = "-[r" + rel_type_filter + "]->"
        elif direction == "incoming":
            path_direction = "<-[r" + rel_type_filter + "]-"
        else:  # both
            path_direction = "-[r" + rel_type_filter + "]-"
        
        # 准备参数
        params = {}
        params.update(source_properties)
        
        # 为目标属性添加前缀，避免与源属性冲突
        target_params = {}
        for key, value in target_properties.items():
            target_key = f"target_{key}"
            target_params[target_key] = value
            target_conditions = [cond.replace(f"b.{key} = ${key}", f"b.{key} = ${target_key}") for cond in target_conditions]
        target_where_clause = " AND ".join(target_conditions)
        
        params.update(target_params)
        params["limit"] = limit
        params["max_depth"] = max_depth
        
        # 构建查询
        query = f"""
        MATCH (a:{source_node_type}), (b:{target_node_type})
        WHERE {source_where_clause} AND {target_where_clause}
        MATCH path = shortestPath((a){path_direction}*(1..{max_depth})(b))
        RETURN path
        LIMIT $limit
        """
        
        # 执行查询
        with driver.session(database=database) as session:
            start_time = time.time()
            
            try:
                result = session.run(query, params)
                
                # 收集路径结果
                paths = []
                
                for record in result:
                    path = record["path"]
                    
                    path_data = {
                        "length": len(path),
                        "nodes": [],
                        "relationships": []
                    }
                    
                    # 处理节点
                    for node in path.nodes:
                        if include_node_details:
                            node_data = {
                                "id": node.id,
                                "labels": list(node.labels),
                                "properties": dict(node.items())
                            }
                        else:
                            node_data = {
                                "id": node.id,
                                "labels": list(node.labels),
                                "resource_id": node.get("resource_id", None)
                            }
                        
                        path_data["nodes"].append(node_data)
                    
                    # 处理关系
                    for rel in path.relationships:
                        rel_data = {
                            "id": rel.id,
                            "type": rel.type,
                            "start_node_id": rel.start_node.id,
                            "end_node_id": rel.end_node.id
                        }
                        
                        if include_node_details:
                            rel_data["properties"] = dict(rel.items())
                        
                        path_data["relationships"].append(rel_data)
                    
                    paths.append(path_data)
                
                end_time = time.time()
                query_duration = round(end_time - start_time, 3)
                
                # 准备返回结果
                response = {
                    "status": "success",
                    "message": f"Found {len(paths)} paths between nodes",
                    "source_node_type": source_node_type,
                    "target_node_type": target_node_type,
                    "max_depth": max_depth,
                    "relationship_types": relationship_types,
                    "direction": direction,
                    "query_duration_seconds": query_duration,
                    "paths_count": len(paths),
                    "paths": paths
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
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)

@tool
def neo4j_reachability_analyzer(
    source_node_type: str,
    source_properties: Dict[str, Any],
    target_node_type: str,
    target_properties: Optional[Dict[str, Any]] = None,
    max_depth: int = 5,
    relationship_types: Optional[List[str]] = None,
    direction: str = "outgoing",
    connection_id: str = "default",
    database: str = "neo4j",
    include_paths: bool = False,
    limit: int = 10
) -> str:
    """
    分析节点可达性
    
    Args:
        source_node_type: 源节点类型
        source_properties: 源节点属性字典，用于查找源节点
        target_node_type: 目标节点类型
        target_properties: 目标节点属性字典，用于查找目标节点（可选，默认为None，表示查找所有可达的目标节点类型）
        max_depth: 最大路径深度（可选，默认为5）
        relationship_types: 要包含的关系类型列表（可选，默认为所有类型）
        direction: 路径方向，可选值："outgoing", "incoming", "both"（可选，默认为"outgoing"）
        connection_id: 数据库连接ID（可选，默认为"default"）
        database: 数据库名称（可选，默认为"neo4j"）
        include_paths: 是否包含路径详情（可选，默认为False）
        limit: 结果限制数量（可选，默认为10）
        
    Returns:
        str: JSON格式的可达性分析结果
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
        
        # 构建源节点查询条件
        source_conditions = []
        for key, value in source_properties.items():
            source_conditions.append(f"a.{key} = ${key}")
        source_where_clause = " AND ".join(source_conditions)
        
        # 构建目标节点查询条件
        target_where_clause = ""
        if target_properties:
            target_conditions = []
            for key, value in target_properties.items():
                target_conditions.append(f"b.{key} = ${key}")
            target_where_clause = " AND " + " AND ".join(target_conditions)
        
        # 构建关系类型过滤
        rel_type_filter = ""
        if relationship_types:
            rel_types = "|".join(relationship_types)
            rel_type_filter = f":{rel_types}"
        
        # 构建路径方向
        if direction == "outgoing":
            path_direction = "-[r" + rel_type_filter + "]->"
        elif direction == "incoming":
            path_direction = "<-[r" + rel_type_filter + "]-"
        else:  # both
            path_direction = "-[r" + rel_type_filter + "]-"
        
        # 准备参数
        params = {}
        params.update(source_properties)
        
        # 如果有目标属性，添加到参数中
        if target_properties:
            # 为目标属性添加前缀，避免与源属性冲突
            target_params = {}
            for key, value in target_properties.items():
                target_key = f"target_{key}"
                target_params[target_key] = value
                target_conditions = [cond.replace(f"b.{key} = ${key}", f"b.{key} = ${target_key}") for cond in target_conditions]
            target_where_clause = " AND " + " AND ".join(target_conditions)
            
            params.update(target_params)
        
        params["limit"] = limit
        params["max_depth"] = max_depth
        
        # 构建查询
        if include_paths:
            query = f"""
            MATCH (a:{source_node_type})
            WHERE {source_where_clause}
            MATCH path = (a){path_direction}*(1..{max_depth})(b:{target_node_type})
            WHERE b <> a{target_where_clause}
            RETURN b, path
            LIMIT $limit
            """
        else:
            query = f"""
            MATCH (a:{source_node_type})
            WHERE {source_where_clause}
            MATCH path = (a){path_direction}*(1..{max_depth})(b:{target_node_type})
            WHERE b <> a{target_where_clause}
            RETURN b, length(path) as path_length
            LIMIT $limit
            """
        
        # 执行查询
        with driver.session(database=database) as session:
            start_time = time.time()
            
            try:
                result = session.run(query, params)
                
                # 收集可达节点结果
                reachable_nodes = []
                
                for record in result:
                    node = record["b"]
                    
                    node_data = {
                        "id": node.id,
                        "labels": list(node.labels),
                        "properties": dict(node.items()),
                        "path_length": record["path_length"] if "path_length" in record else len(record["path"])
                    }
                    
                    # 如果包含路径，处理路径信息
                    if include_paths and "path" in record:
                        path = record["path"]
                        
                        path_data = {
                            "length": len(path),
                            "nodes": [],
                            "relationships": []
                        }
                        
                        # 处理节点
                        for path_node in path.nodes:
                            path_node_data = {
                                "id": path_node.id,
                                "labels": list(path_node.labels),
                                "resource_id": path_node.get("resource_id", None)
                            }
                            
                            path_data["nodes"].append(path_node_data)
                        
                        # 处理关系
                        for rel in path.relationships:
                            rel_data = {
                                "id": rel.id,
                                "type": rel.type,
                                "start_node_id": rel.start_node.id,
                                "end_node_id": rel.end_node.id
                            }
                            
                            path_data["relationships"].append(rel_data)
                        
                        node_data["path"] = path_data
                    
                    reachable_nodes.append(node_data)
                
                end_time = time.time()
                query_duration = round(end_time - start_time, 3)
                
                # 准备返回结果
                response = {
                    "status": "success",
                    "message": f"Found {len(reachable_nodes)} reachable nodes",
                    "source_node_type": source_node_type,
                    "target_node_type": target_node_type,
                    "max_depth": max_depth,
                    "relationship_types": relationship_types,
                    "direction": direction,
                    "query_duration_seconds": query_duration,
                    "reachable_nodes_count": len(reachable_nodes),
                    "reachable_nodes": reachable_nodes
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
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)

@tool
def neo4j_network_analyzer(
    node_type: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
    analysis_type: str = "connectivity",
    max_depth: int = 3,
    connection_id: str = "default",
    database: str = "neo4j",
    limit: int = 100
) -> str:
    """
    分析网络拓扑
    
    Args:
        node_type: 节点类型（可选，默认为None，表示所有节点）
        properties: 节点属性字典，用于过滤节点（可选，默认为None）
        analysis_type: 分析类型，可选值：
                      "connectivity" - 连通性分析
                      "centrality" - 中心性分析
                      "bottlenecks" - 瓶颈分析
                      "clusters" - 集群分析
                      "isolated" - 孤立节点分析
                      "density" - 密度分析
        max_depth: 最大分析深度（可选，默认为3）
        connection_id: 数据库连接ID（可选，默认为"default"）
        database: 数据库名称（可选，默认为"neo4j"）
        limit: 结果限制数量（可选，默认为100）
        
    Returns:
        str: JSON格式的网络分析结果
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
        
        # 构建节点过滤条件
        node_filter = ""
        if node_type:
            node_filter = f":{node_type}"
        
        # 构建属性过滤条件
        where_clause = ""
        if properties:
            conditions = []
            for key, value in properties.items():
                conditions.append(f"n.{key} = ${key}")
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # 准备参数
        params = {}
        if properties:
            params.update(properties)
        
        params["limit"] = limit
        params["max_depth"] = max_depth
        
        # 根据分析类型选择查询
        if analysis_type == "connectivity":
            # 连通性分析：查找节点的连接度
            query = f"""
            MATCH (n{node_filter})
            {where_clause}
            WITH n, size((n)--()) as degree
            ORDER BY degree DESC
            LIMIT $limit
            RETURN n, degree,
                   size((n)-->()) as out_degree,
                   size((n)<--()) as in_degree
            """
        
        elif analysis_type == "centrality":
            # 中心性分析：使用PageRank算法计算节点重要性
            query = f"""
            CALL gds.pageRank.stream({{
                nodeProjection: {json.dumps(node_type) if node_type else '*'},
                relationshipProjection: '*',
                maxIterations: 20,
                dampingFactor: 0.85
            }})
            YIELD nodeId, score
            MATCH (n) WHERE id(n) = nodeId
            {f"AND {' AND '.join(conditions)}" if properties else ""}
            RETURN n, score
            ORDER BY score DESC
            LIMIT $limit
            """
            
            # 检查图算法是否可用，如果不可用则使用替代查询
            try:
                with driver.session(database=database) as session:
                    session.run("CALL gds.list()")
            except:
                # 替代查询：使用度中心性
                query = f"""
                MATCH (n{node_filter})
                {where_clause}
                WITH n, size((n)--()) as degree
                ORDER BY degree DESC
                LIMIT $limit
                RETURN n, degree as score,
                       size((n)-->()) as out_degree,
                       size((n)<--()) as in_degree
                """
        
        elif analysis_type == "bottlenecks":
            # 瓶颈分析：查找连接不同组件的节点
            query = f"""
            MATCH (n{node_filter})
            {where_clause}
            MATCH (a)-[*1..{max_depth}]-(n)-[*1..{max_depth}]-(b)
            WHERE a <> b AND NOT (a)-[*1..{max_depth}]-(b)
            WITH n, count(DISTINCT a) + count(DISTINCT b) as connected_components
            ORDER BY connected_components DESC
            LIMIT $limit
            RETURN n, connected_components,
                   size((n)-->()) as out_degree,
                   size((n)<--()) as in_degree
            """
        
        elif analysis_type == "clusters":
            # 集群分析：查找紧密连接的节点组
            query = f"""
            MATCH (n{node_filter})
            {where_clause}
            MATCH (n)-[*1..{max_depth}]-(m)
            WITH n, collect(DISTINCT m) as neighbors
            RETURN n, size(neighbors) as cluster_size,
                   neighbors[0..10] as sample_neighbors
            ORDER BY cluster_size DESC
            LIMIT $limit
            """
        
        elif analysis_type == "isolated":
            # 孤立节点分析：查找没有连接的节点
            query = f"""
            MATCH (n{node_filter})
            {where_clause}
            WHERE NOT (n)--()
            RETURN n
            LIMIT $limit
            """
        
        elif analysis_type == "density":
            # 密度分析：查找连接密度高的区域
            query = f"""
            MATCH (n{node_filter})
            {where_clause}
            MATCH (n)-[r]-(m)
            WITH n, count(DISTINCT r) as connections, collect(DISTINCT m) as neighbors
            RETURN n, connections, size(neighbors) as unique_neighbors,
                   toFloat(connections) / size(neighbors) as density
            ORDER BY density DESC
            LIMIT $limit
            """
        
        else:
            return json.dumps({
                "status": "error",
                "message": f"Invalid analysis type: {analysis_type}",
                "valid_analysis_types": ["connectivity", "centrality", "bottlenecks", "clusters", "isolated", "density"]
            }, indent=2)
        
        # 执行查询
        with driver.session(database=database) as session:
            start_time = time.time()
            
            try:
                result = session.run(query, params)
                
                # 收集分析结果
                analysis_results = []
                
                for record in result:
                    result_item = {}
                    
                    for key, value in record.items():
                        # 处理Neo4j节点
                        if hasattr(value, "id") and hasattr(value, "labels"):
                            result_item[key] = {
                                "id": value.id,
                                "labels": list(value.labels),
                                "properties": dict(value.items())
                            }
                        # 处理节点列表
                        elif isinstance(value, list) and all(hasattr(item, "id") and hasattr(item, "labels") for item in value):
                            result_item[key] = [
                                {
                                    "id": item.id,
                                    "labels": list(item.labels),
                                    "properties": dict(item.items())
                                }
                                for item in value
                            ]
                        else:
                            # 这是一个普通值
                            result_item[key] = value
                    
                    analysis_results.append(result_item)
                
                end_time = time.time()
                query_duration = round(end_time - start_time, 3)
                
                # 准备返回结果
                response = {
                    "status": "success",
                    "message": f"Network analysis completed: {analysis_type}",
                    "node_type": node_type,
                    "analysis_type": analysis_type,
                    "max_depth": max_depth,
                    "query_duration_seconds": query_duration,
                    "results_count": len(analysis_results),
                    "results": analysis_results
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
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)