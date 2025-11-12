from strands import tool
from typing import Dict, List, Optional, Any, Union
import json
import logging
import time
from neo4j import GraphDatabase, Driver, Session, Result
from neo4j.exceptions import ServiceUnavailable, AuthError, DatabaseError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global connection pool to reuse connections
_connection_pool = {}

@tool
def neo4j_database_connector(
    action: str,
    uri: str = "neo4j://localhost:7687",
    username: str = "neo4j",
    password: str = "neo4jneo4j",
    database: str = "neo4j",
    connection_id: str = "default",
    timeout: int = 60
) -> str:
    """
    连接Neo4j数据库
    
    Args:
        action: 执行的操作，可选值: connect, disconnect, test, status, list
        uri: Neo4j数据库URI，默认为neo4j://localhost:7687
        username: 用户名，默认为neo4j
        password: 密码，默认为neo4jneo4j
        database: 数据库名称，默认为neo4j
        connection_id: 连接ID，用于在多连接场景中标识不同的连接，默认为default
        timeout: 连接超时时间（秒），默认为60秒
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        global _connection_pool
        result = {}
        
        if action == "connect":
            # 检查是否已存在连接
            if connection_id in _connection_pool and _connection_pool[connection_id]["driver"] is not None:
                # 检查连接是否有效
                try:
                    with _connection_pool[connection_id]["driver"].session(database=database) as session:
                        session.run("RETURN 1")
                    
                    result = {
                        "status": "success",
                        "message": f"Connection '{connection_id}' already exists and is valid",
                        "connection_id": connection_id,
                        "uri": uri,
                        "database": database,
                        "username": username,
                        "connection_time": _connection_pool[connection_id]["connection_time"]
                    }
                except Exception:
                    # 连接无效，关闭并重新创建
                    try:
                        _connection_pool[connection_id]["driver"].close()
                    except Exception:
                        pass
                    
                    _connection_pool[connection_id] = None
            
            # 创建新连接
            if connection_id not in _connection_pool or _connection_pool[connection_id] is None:
                try:
                    start_time = time.time()
                    driver = GraphDatabase.driver(uri, auth=(username, password))
                    
                    # 验证连接
                    with driver.session(database=database) as session:
                        session.run("RETURN 1")
                    
                    connection_time = time.strftime("%Y-%m-%d %H:%M:%S")
                    _connection_pool[connection_id] = {
                        "driver": driver,
                        "uri": uri,
                        "database": database,
                        "username": username,
                        "connection_time": connection_time
                    }
                    
                    end_time = time.time()
                    connection_duration = round(end_time - start_time, 2)
                    
                    result = {
                        "status": "success",
                        "message": f"Successfully connected to Neo4j database at {uri}",
                        "connection_id": connection_id,
                        "uri": uri,
                        "database": database,
                        "username": username,
                        "connection_time": connection_time,
                        "connection_duration_seconds": connection_duration
                    }
                except AuthError as e:
                    result = {
                        "status": "error",
                        "message": f"Authentication failed: {str(e)}",
                        "error_type": "AuthError",
                        "connection_id": connection_id,
                        "uri": uri
                    }
                except ServiceUnavailable as e:
                    result = {
                        "status": "error",
                        "message": f"Neo4j service unavailable: {str(e)}",
                        "error_type": "ServiceUnavailable",
                        "connection_id": connection_id,
                        "uri": uri
                    }
                except Exception as e:
                    result = {
                        "status": "error",
                        "message": f"Failed to connect to Neo4j database: {str(e)}",
                        "error_type": type(e).__name__,
                        "connection_id": connection_id,
                        "uri": uri
                    }
        
        elif action == "disconnect":
            if connection_id in _connection_pool and _connection_pool[connection_id] is not None:
                try:
                    _connection_pool[connection_id]["driver"].close()
                    connection_info = _connection_pool[connection_id].copy()
                    del connection_info["driver"]
                    del _connection_pool[connection_id]
                    
                    result = {
                        "status": "success",
                        "message": f"Successfully disconnected from Neo4j database",
                        "connection_id": connection_id,
                        "connection_info": connection_info
                    }
                except Exception as e:
                    result = {
                        "status": "error",
                        "message": f"Error disconnecting from Neo4j database: {str(e)}",
                        "error_type": type(e).__name__,
                        "connection_id": connection_id
                    }
            else:
                result = {
                    "status": "warning",
                    "message": f"No active connection found with ID '{connection_id}'",
                    "connection_id": connection_id
                }
        
        elif action == "test":
            if connection_id in _connection_pool and _connection_pool[connection_id] is not None:
                try:
                    start_time = time.time()
                    with _connection_pool[connection_id]["driver"].session(database=database) as session:
                        # 执行简单查询测试连接
                        test_result = session.run("RETURN 1 as test").single().get("test")
                        
                        # 获取数据库版本
                        version_result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions").single()
                        db_name = version_result.get("name")
                        db_version = version_result.get("versions")[0] if version_result.get("versions") else "Unknown"
                        
                        # 获取标签和关系类型数量
                        labels_count = session.run("CALL db.labels() YIELD label RETURN count(label) as count").single().get("count")
                        rel_types_count = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN count(relationshipType) as count").single().get("count")
                        
                        # 获取节点和关系数量
                        counts = session.run("MATCH (n) RETURN count(n) as nodes, size([()-[r]->() | r]) as relationships").single()
                        nodes_count = counts.get("nodes")
                        relationships_count = counts.get("relationships")
                    
                    end_time = time.time()
                    query_duration = round(end_time - start_time, 2)
                    
                    result = {
                        "status": "success",
                        "message": "Neo4j database connection is valid",
                        "connection_id": connection_id,
                        "uri": _connection_pool[connection_id]["uri"],
                        "database": _connection_pool[connection_id]["database"],
                        "username": _connection_pool[connection_id]["username"],
                        "connection_time": _connection_pool[connection_id]["connection_time"],
                        "database_info": {
                            "name": db_name,
                            "version": db_version,
                            "labels_count": labels_count,
                            "relationship_types_count": rel_types_count,
                            "nodes_count": nodes_count,
                            "relationships_count": relationships_count
                        },
                        "test_duration_seconds": query_duration
                    }
                except Exception as e:
                    result = {
                        "status": "error",
                        "message": f"Connection test failed: {str(e)}",
                        "error_type": type(e).__name__,
                        "connection_id": connection_id
                    }
            else:
                result = {
                    "status": "error",
                    "message": f"No active connection found with ID '{connection_id}'",
                    "connection_id": connection_id
                }
        
        elif action == "status":
            if connection_id in _connection_pool and _connection_pool[connection_id] is not None:
                connection_info = _connection_pool[connection_id].copy()
                driver_info = connection_info["driver"]
                del connection_info["driver"]
                
                # 检查连接是否有效
                try:
                    with driver_info.session(database=database) as session:
                        session.run("RETURN 1")
                        is_valid = True
                except Exception:
                    is_valid = False
                
                result = {
                    "status": "success",
                    "connection_id": connection_id,
                    "is_connected": True,
                    "is_valid": is_valid,
                    "connection_info": connection_info
                }
            else:
                result = {
                    "status": "success",
                    "connection_id": connection_id,
                    "is_connected": False,
                    "message": f"No active connection found with ID '{connection_id}'"
                }
        
        elif action == "list":
            connections = []
            for conn_id, conn_info in _connection_pool.items():
                if conn_info is not None:
                    # 检查连接是否有效
                    try:
                        with conn_info["driver"].session(database=conn_info["database"]) as session:
                            session.run("RETURN 1")
                            is_valid = True
                    except Exception:
                        is_valid = False
                    
                    connection_data = conn_info.copy()
                    del connection_data["driver"]
                    connection_data["connection_id"] = conn_id
                    connection_data["is_valid"] = is_valid
                    
                    connections.append(connection_data)
            
            result = {
                "status": "success",
                "connections_count": len(connections),
                "connections": connections
            }
        
        else:
            result = {
                "status": "error",
                "message": f"Invalid action: {action}. Supported actions: connect, disconnect, test, status, list"
            }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)

def get_connection(connection_id: str = "default") -> Optional[Driver]:
    """
    获取指定ID的数据库连接
    
    Args:
        connection_id: 连接ID
        
    Returns:
        Optional[Driver]: Neo4j驱动对象，如果连接不存在则返回None
    """
    global _connection_pool
    if connection_id in _connection_pool and _connection_pool[connection_id] is not None:
        return _connection_pool[connection_id]["driver"]
    return None