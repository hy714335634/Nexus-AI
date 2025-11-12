from strands import tool
from typing import Dict, List, Optional, Any, Union
import json
import logging
import time
import re
from neo4j import GraphDatabase, Driver, Session, Result
from neo4j.exceptions import ServiceUnavailable, AuthError, DatabaseError, CypherSyntaxError, ConstraintError

# Import the get_connection function from neo4j_database_connector
from tools.generated_tools.aws_network_topology_analyzer.neo4j_database_connector import get_connection

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@tool
def error_analyzer_and_resolver(
    error_message: str,
    error_context: Optional[Dict[str, Any]] = None,
    connection_id: str = "default",
    database: str = "neo4j",
    auto_resolve: bool = False
) -> str:
    """
    分析和解决错误
    
    Args:
        error_message: 错误信息
        error_context: 错误上下文，包含相关信息（可选）
        connection_id: 数据库连接ID（可选，默认为"default"）
        database: 数据库名称（可选，默认为"neo4j"）
        auto_resolve: 是否自动尝试解决问题（可选，默认为False）
        
    Returns:
        str: JSON格式的错误分析和解决方案
    """
    try:
        # 分析错误类型
        error_type = analyze_error_type(error_message)
        
        # 解析错误上下文
        context = error_context if error_context else {}
        
        # 获取解决方案
        solution = get_solution(error_type, error_message, context)
        
        # 如果需要自动解决，尝试解决问题
        resolution_result = None
        if auto_resolve and solution["can_auto_resolve"]:
            resolution_result = try_auto_resolve(error_type, error_message, context, connection_id, database)
        
        # 准备返回结果
        response = {
            "status": "success",
            "error_message": error_message,
            "error_type": error_type,
            "analysis": solution["analysis"],
            "solution": solution["solution"],
            "can_auto_resolve": solution["can_auto_resolve"]
        }
        
        # 如果有解决结果，添加到响应中
        if resolution_result:
            response["resolution_result"] = resolution_result
        
        return json.dumps(response, indent=2)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"An unexpected error occurred during error analysis: {str(e)}",
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)

@tool
def neo4j_data_integrity_checker(
    check_type: str,
    connection_id: str = "default",
    database: str = "neo4j",
    node_label: Optional[str] = None,
    relationship_type: Optional[str] = None,
    fix_issues: bool = False
) -> str:
    """
    检查Neo4j数据完整性
    
    Args:
        check_type: 检查类型，可选值：
                   "orphan_nodes" - 检查孤立节点
                   "missing_properties" - 检查缺失必要属性
                   "dangling_relationships" - 检查悬空关系
                   "duplicate_nodes" - 检查重复节点
                   "constraint_violations" - 检查约束违规
                   "schema_consistency" - 检查模式一致性
        connection_id: 数据库连接ID（可选，默认为"default"）
        database: 数据库名称（可选，默认为"neo4j"）
        node_label: 节点标签，用于过滤检查范围（可选）
        relationship_type: 关系类型，用于过滤检查范围（可选）
        fix_issues: 是否自动修复发现的问题（可选，默认为False）
        
    Returns:
        str: JSON格式的检查结果
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
        
        # 根据检查类型执行相应的检查
        if check_type == "orphan_nodes":
            return check_orphan_nodes(driver, database, node_label, fix_issues)
        
        elif check_type == "missing_properties":
            return check_missing_properties(driver, database, node_label, relationship_type, fix_issues)
        
        elif check_type == "dangling_relationships":
            return check_dangling_relationships(driver, database, relationship_type, fix_issues)
        
        elif check_type == "duplicate_nodes":
            return check_duplicate_nodes(driver, database, node_label, fix_issues)
        
        elif check_type == "constraint_violations":
            return check_constraint_violations(driver, database, fix_issues)
        
        elif check_type == "schema_consistency":
            return check_schema_consistency(driver, database, fix_issues)
        
        else:
            return json.dumps({
                "status": "error",
                "message": f"Invalid check type: {check_type}. Supported types: orphan_nodes, missing_properties, dangling_relationships, duplicate_nodes, constraint_violations, schema_consistency"
            }, indent=2)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"An unexpected error occurred during integrity check: {str(e)}",
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)

def analyze_error_type(error_message):
    """分析错误类型"""
    error_message_lower = error_message.lower()
    
    # Neo4j连接错误
    if any(term in error_message_lower for term in ["connection refused", "unable to connect", "connection error", "connection failed"]):
        return "connection_error"
    
    # 认证错误
    elif any(term in error_message_lower for term in ["authentication failed", "unauthorized", "invalid credentials"]):
        return "authentication_error"
    
    # Cypher语法错误
    elif any(term in error_message_lower for term in ["syntax error", "invalid syntax", "unexpected token"]):
        return "cypher_syntax_error"
    
    # 约束错误
    elif any(term in error_message_lower for term in ["constraint", "already exists with label", "uniqueness"]):
        return "constraint_error"
    
    # 节点不存在错误
    elif any(term in error_message_lower for term in ["not found", "does not exist", "no such node"]):
        return "node_not_found_error"
    
    # 属性错误
    elif any(term in error_message_lower for term in ["property", "missing property", "invalid property"]):
        return "property_error"
    
    # 关系错误
    elif any(term in error_message_lower for term in ["relationship", "invalid relationship", "no relationship"]):
        return "relationship_error"
    
    # 查询超时错误
    elif any(term in error_message_lower for term in ["timeout", "query timeout", "execution time"]):
        return "timeout_error"
    
    # 内存错误
    elif any(term in error_message_lower for term in ["out of memory", "memory limit", "heap space"]):
        return "memory_error"
    
    # AWS API错误
    elif any(term in error_message_lower for term in ["aws", "api", "boto", "access denied", "throttling"]):
        return "aws_api_error"
    
    # 默认为未知错误
    else:
        return "unknown_error"

def get_solution(error_type, error_message, context):
    """获取解决方案"""
    solutions = {
        "connection_error": {
            "analysis": "Neo4j数据库连接错误，可能是由于数据库未运行、网络问题或连接配置错误导致。",
            "solution": [
                "确保Neo4j数据库正在运行",
                "检查数据库URI是否正确",
                "验证网络连接是否正常",
                "检查防火墙设置是否允许连接",
                "尝试使用neo4j_database_connector工具的test操作验证连接"
            ],
            "can_auto_resolve": False
        },
        
        "authentication_error": {
            "analysis": "Neo4j数据库认证错误，用户名或密码不正确。",
            "solution": [
                "检查用户名和密码是否正确",
                "确认用户是否有访问指定数据库的权限",
                "重置Neo4j用户密码（如果有管理员权限）"
            ],
            "can_auto_resolve": False
        },
        
        "cypher_syntax_error": {
            "analysis": "Cypher查询语法错误，查询语句格式不正确。",
            "solution": [
                "检查Cypher查询语法",
                "确认节点标签和关系类型是否正确",
                "验证属性名称是否正确",
                "检查括号、引号和其他语法元素是否匹配"
            ],
            "can_auto_resolve": False
        },
        
        "constraint_error": {
            "analysis": "Neo4j约束错误，可能是尝试创建违反唯一性约束的节点或关系。",
            "solution": [
                "检查是否尝试创建具有相同唯一属性的节点",
                "使用MERGE而不是CREATE来避免重复",
                "查看数据库中的约束列表",
                "考虑修改约束或更新现有节点"
            ],
            "can_auto_resolve": True
        },
        
        "node_not_found_error": {
            "analysis": "节点不存在错误，查询中引用的节点在数据库中不存在。",
            "solution": [
                "确认节点ID或属性是否正确",
                "检查节点是否已被删除",
                "修改查询以先检查节点是否存在",
                "考虑使用MERGE创建不存在的节点"
            ],
            "can_auto_resolve": True
        },
        
        "property_error": {
            "analysis": "属性错误，可能是尝试访问不存在的属性或使用了错误的属性类型。",
            "solution": [
                "确认属性名称是否正确",
                "检查属性是否存在于节点或关系上",
                "验证属性值的类型是否正确",
                "使用OPTIONAL MATCH或条件检查处理可能不存在的属性"
            ],
            "can_auto_resolve": True
        },
        
        "relationship_error": {
            "analysis": "关系错误，可能是关系类型错误或尝试创建无效的关系。",
            "solution": [
                "确认关系类型是否正确",
                "检查关系的方向是否正确",
                "验证关系的起始和结束节点是否存在",
                "检查是否有约束限制关系的创建"
            ],
            "can_auto_resolve": True
        },
        
        "timeout_error": {
            "analysis": "查询超时错误，查询执行时间超过了配置的超时时间。",
            "solution": [
                "优化查询以提高性能",
                "添加适当的索引",
                "限制返回的结果数量",
                "拆分复杂查询为多个简单查询",
                "增加查询超时设置"
            ],
            "can_auto_resolve": False
        },
        
        "memory_error": {
            "analysis": "内存错误，Neo4j数据库内存不足以执行查询。",
            "solution": [
                "优化查询以减少内存使用",
                "限制返回的结果数量",
                "增加Neo4j数据库的内存配置",
                "拆分复杂查询为多个简单查询"
            ],
            "can_auto_resolve": False
        },
        
        "aws_api_error": {
            "analysis": "AWS API错误，与AWS服务交互时出现问题。",
            "solution": [
                "检查AWS凭证是否有效",
                "确认IAM权限是否足够",
                "验证区域设置是否正确",
                "检查是否达到API限制或配额",
                "实现指数退避重试策略"
            ],
            "can_auto_resolve": False
        },
        
        "unknown_error": {
            "analysis": "未知错误，无法确定具体原因。",
            "solution": [
                "检查日志获取更多详细信息",
                "验证所有输入参数",
                "检查Neo4j数据库状态",
                "尝试简化操作以定位问题"
            ],
            "can_auto_resolve": False
        }
    }
    
    # 获取基本解决方案
    solution = solutions.get(error_type, solutions["unknown_error"])
    
    # 根据具体错误信息和上下文进一步细化分析和解决方案
    if error_type == "constraint_error" and "already exists with label" in error_message:
        # 提取违反约束的节点标签和属性
        match = re.search(r"already exists with label `?(\w+)`? and property `?(\w+)`?", error_message)
        if match:
            label, property_name = match.groups()
            property_value = context.get("properties", {}).get(property_name, "unknown")
            
            solution["analysis"] = f"唯一性约束错误：已存在具有标签'{label}'和属性'{property_name}={property_value}'的节点。"
            solution["solution"].insert(0, f"使用MERGE而不是CREATE来处理标签为'{label}'的节点")
            solution["solution"].insert(1, f"查找并更新现有的节点：MATCH (n:{label} {{{property_name}: '{property_value}'}}) RETURN n")
    
    elif error_type == "node_not_found_error" and context.get("node_id"):
        node_id = context.get("node_id")
        solution["analysis"] = f"节点不存在错误：ID为{node_id}的节点不存在于数据库中。"
        solution["solution"].insert(0, f"确认节点ID {node_id} 是否正确")
    
    elif error_type == "aws_api_error" and "AccessDenied" in error_message:
        solution["analysis"] = "AWS访问被拒绝错误：IAM权限不足或凭证无效。"
        solution["solution"].insert(0, "检查IAM策略是否包含所需的权限")
        solution["solution"].insert(1, "验证AWS凭证是否有效且未过期")
    
    return solution

def try_auto_resolve(error_type, error_message, context, connection_id, database):
    """尝试自动解决问题"""
    # 获取数据库连接
    driver = get_connection(connection_id)
    if not driver:
        return {
            "status": "error",
            "message": f"No active connection found with ID '{connection_id}'",
            "auto_resolve_success": False
        }
    
    # 根据错误类型尝试解决
    if error_type == "constraint_error" and "already exists with label" in error_message:
        # 提取违反约束的节点标签和属性
        match = re.search(r"already exists with label `?(\w+)`? and property `?(\w+)`?", error_message)
        if match and "properties" in context:
            label, property_name = match.groups()
            properties = context.get("properties", {})
            
            if property_name in properties:
                property_value = properties[property_name]
                
                try:
                    with driver.session(database=database) as session:
                        # 查找现有节点
                        find_query = f"MATCH (n:{label} {{{property_name}: $value}}) RETURN n"
                        result = session.run(find_query, {"value": property_value})
                        
                        if result.peek():
                            existing_node = result.single()["n"]
                            
                            # 更新现有节点
                            update_query = f"MATCH (n:{label} {{{property_name}: $value}}) SET n += $properties RETURN n"
                            result = session.run(update_query, {"value": property_value, "properties": properties})
                            
                            updated_node = result.single()["n"]
                            
                            return {
                                "status": "success",
                                "message": f"Successfully resolved constraint error by updating existing node",
                                "auto_resolve_success": True,
                                "resolution_method": "update_existing_node",
                                "node_id": existing_node.id,
                                "node_properties": dict(updated_node.items())
                            }
                
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Failed to auto-resolve constraint error: {str(e)}",
                        "auto_resolve_success": False,
                        "error_type": type(e).__name__
                    }
    
    elif error_type == "node_not_found_error" and "node_type" in context and "properties" in context:
        node_type = context.get("node_type")
        properties = context.get("properties", {})
        
        try:
            with driver.session(database=database) as session:
                # 创建缺失的节点
                create_query = f"CREATE (n:{node_type} $properties) RETURN n"
                result = session.run(create_query, {"properties": properties})
                
                created_node = result.single()["n"]
                
                return {
                    "status": "success",
                    "message": f"Successfully resolved node not found error by creating new node",
                    "auto_resolve_success": True,
                    "resolution_method": "create_missing_node",
                    "node_id": created_node.id,
                    "node_type": node_type,
                    "node_properties": dict(created_node.items())
                }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to auto-resolve node not found error: {str(e)}",
                "auto_resolve_success": False,
                "error_type": type(e).__name__
            }
    
    # 默认无法自动解决
    return {
        "status": "warning",
        "message": "Auto-resolution not implemented for this error type or insufficient context",
        "auto_resolve_success": False,
        "error_type": error_type
    }

def check_orphan_nodes(driver, database, node_label, fix_issues):
    """检查孤立节点"""
    try:
        with driver.session(database=database) as session:
            # 构建查询
            query = "MATCH (n"
            if node_label:
                query += f":{node_label}"
            query += ") WHERE NOT (n)--() RETURN n"
            
            # 执行查询
            result = session.run(query)
            
            # 收集孤立节点
            orphan_nodes = []
            for record in result:
                node = record["n"]
                orphan_nodes.append({
                    "id": node.id,
                    "labels": list(node.labels),
                    "properties": dict(node.items())
                })
            
            # 如果需要修复并且有孤立节点
            fix_result = None
            if fix_issues and orphan_nodes:
                # 根据节点标签确定修复策略
                if node_label:
                    # 对特定标签的孤立节点执行修复
                    fix_query = f"""
                    MATCH (n:{node_label}) WHERE NOT (n)--()
                    WITH n LIMIT 100
                    DELETE n
                    RETURN count(*) as deleted_count
                    """
                else:
                    # 对所有孤立节点执行修复
                    fix_query = """
                    MATCH (n) WHERE NOT (n)--()
                    WITH n LIMIT 100
                    DELETE n
                    RETURN count(*) as deleted_count
                    """
                
                fix_result = session.run(fix_query).single()
                
                fix_result = {
                    "action": "delete_orphan_nodes",
                    "deleted_count": fix_result["deleted_count"],
                    "message": f"Deleted {fix_result['deleted_count']} orphan nodes"
                }
            
            # 准备返回结果
            response = {
                "status": "success",
                "check_type": "orphan_nodes",
                "orphan_nodes_count": len(orphan_nodes),
                "orphan_nodes": orphan_nodes[:100] if len(orphan_nodes) > 100 else orphan_nodes
            }
            
            # 如果有修复结果，添加到响应中
            if fix_result:
                response["fix_result"] = fix_result
            
            return json.dumps(response, indent=2)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"Error checking orphan nodes: {str(e)}",
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)

def check_missing_properties(driver, database, node_label, relationship_type, fix_issues):
    """检查缺失必要属性"""
    try:
        with driver.session(database=database) as session:
            # 确定要检查的关键属性
            key_properties = ["resource_id", "id", "name", "account_id", "region"]
            
            # 检查节点的缺失属性
            nodes_with_missing_properties = []
            
            if node_label:
                # 对特定标签的节点检查缺失属性
                for prop in key_properties:
                    query = f"""
                    MATCH (n:{node_label})
                    WHERE NOT EXISTS(n.{prop})
                    RETURN n LIMIT 100
                    """
                    
                    result = session.run(query)
                    
                    for record in result:
                        node = record["n"]
                        nodes_with_missing_properties.append({
                            "id": node.id,
                            "labels": list(node.labels),
                            "properties": dict(node.items()),
                            "missing_property": prop
                        })
            
            # 检查关系的缺失属性
            relationships_with_missing_properties = []
            
            if relationship_type:
                # 对特定类型的关系检查缺失属性
                for prop in ["type", "created_at"]:
                    query = f"""
                    MATCH ()-[r:{relationship_type}]->()
                    WHERE NOT EXISTS(r.{prop})
                    RETURN r LIMIT 100
                    """
                    
                    result = session.run(query)
                    
                    for record in result:
                        rel = record["r"]
                        relationships_with_missing_properties.append({
                            "id": rel.id,
                            "type": rel.type,
                            "properties": dict(rel.items()),
                            "missing_property": prop,
                            "start_node_id": rel.start_node.id,
                            "end_node_id": rel.end_node.id
                        })
            
            # 如果需要修复
            fix_result = None
            if fix_issues:
                fixed_nodes = 0
                fixed_relationships = 0
                
                # 修复节点的缺失属性
                if node_label and nodes_with_missing_properties:
                    # 按缺失的属性分组
                    missing_props = {}
                    for node in nodes_with_missing_properties:
                        prop = node["missing_property"]
                        if prop not in missing_props:
                            missing_props[prop] = []
                        missing_props[prop].append(node["id"])
                    
                    # 为每个缺失的属性执行修复
                    for prop, node_ids in missing_props.items():
                        # 生成默认值
                        default_value = f"{node_label}_{prop}_default"
                        
                        # 构建修复查询
                        fix_query = f"""
                        MATCH (n:{node_label})
                        WHERE id(n) IN $node_ids
                        SET n.{prop} = $default_value
                        RETURN count(*) as fixed_count
                        """
                        
                        result = session.run(fix_query, {"node_ids": node_ids, "default_value": default_value})
                        fixed_nodes += result.single()["fixed_count"]
                
                # 修复关系的缺失属性
                if relationship_type and relationships_with_missing_properties:
                    # 按缺失的属性分组
                    missing_props = {}
                    for rel in relationships_with_missing_properties:
                        prop = rel["missing_property"]
                        if prop not in missing_props:
                            missing_props[prop] = []
                        missing_props[prop].append(rel["id"])
                    
                    # 为每个缺失的属性执行修复
                    for prop, rel_ids in missing_props.items():
                        # 生成默认值
                        default_value = f"{relationship_type}_{prop}_default"
                        
                        # 构建修复查询
                        fix_query = f"""
                        MATCH ()-[r:{relationship_type}]->()
                        WHERE id(r) IN $rel_ids
                        SET r.{prop} = $default_value
                        RETURN count(*) as fixed_count
                        """
                        
                        result = session.run(fix_query, {"rel_ids": rel_ids, "default_value": default_value})
                        fixed_relationships += result.single()["fixed_count"]
                
                fix_result = {
                    "action": "add_missing_properties",
                    "fixed_nodes_count": fixed_nodes,
                    "fixed_relationships_count": fixed_relationships,
                    "message": f"Added default values to {fixed_nodes} nodes and {fixed_relationships} relationships"
                }
            
            # 准备返回结果
            response = {
                "status": "success",
                "check_type": "missing_properties",
                "nodes_with_missing_properties_count": len(nodes_with_missing_properties),
                "nodes_with_missing_properties": nodes_with_missing_properties[:100] if len(nodes_with_missing_properties) > 100 else nodes_with_missing_properties,
                "relationships_with_missing_properties_count": len(relationships_with_missing_properties),
                "relationships_with_missing_properties": relationships_with_missing_properties[:100] if len(relationships_with_missing_properties) > 100 else relationships_with_missing_properties
            }
            
            # 如果有修复结果，添加到响应中
            if fix_result:
                response["fix_result"] = fix_result
            
            return json.dumps(response, indent=2)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"Error checking missing properties: {str(e)}",
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)

def check_dangling_relationships(driver, database, relationship_type, fix_issues):
    """检查悬空关系"""
    try:
        with driver.session(database=database) as session:
            # 构建查询
            query = """
            MATCH ()-[r"""
            
            if relationship_type:
                query += f":{relationship_type}"
            
            query += """]->(m)
            WHERE NOT EXISTS(m)
            RETURN r LIMIT 100
            """
            
            # 执行查询
            result = session.run(query)
            
            # 收集悬空关系
            dangling_relationships = []
            for record in result:
                rel = record["r"]
                dangling_relationships.append({
                    "id": rel.id,
                    "type": rel.type,
                    "properties": dict(rel.items()),
                    "start_node_id": rel.start_node.id
                })
            
            # 如果需要修复并且有悬空关系
            fix_result = None
            if fix_issues and dangling_relationships:
                # 删除悬空关系
                fix_query = """
                MATCH ()-[r]->()
                WHERE id(r) IN $rel_ids
                DELETE r
                RETURN count(*) as deleted_count
                """
                
                rel_ids = [rel["id"] for rel in dangling_relationships]
                fix_result = session.run(fix_query, {"rel_ids": rel_ids}).single()
                
                fix_result = {
                    "action": "delete_dangling_relationships",
                    "deleted_count": fix_result["deleted_count"],
                    "message": f"Deleted {fix_result['deleted_count']} dangling relationships"
                }
            
            # 准备返回结果
            response = {
                "status": "success",
                "check_type": "dangling_relationships",
                "dangling_relationships_count": len(dangling_relationships),
                "dangling_relationships": dangling_relationships
            }
            
            # 如果有修复结果，添加到响应中
            if fix_result:
                response["fix_result"] = fix_result
            
            return json.dumps(response, indent=2)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"Error checking dangling relationships: {str(e)}",
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)

def check_duplicate_nodes(driver, database, node_label, fix_issues):
    """检查重复节点"""
    try:
        with driver.session(database=database) as session:
            # 确定要检查的关键属性
            key_properties = ["resource_id", "id", "name", "account_id", "region"]
            
            duplicate_nodes = []
            
            # 对每个关键属性检查重复节点
            for prop in key_properties:
                # 构建查询
                query = """
                MATCH (n"""
                
                if node_label:
                    query += f":{node_label}"
                
                query += f""")
                WHERE EXISTS(n.{prop})
                WITH n.{prop} as prop_value, collect(n) as nodes
                WHERE size(nodes) > 1
                UNWIND nodes as duplicate_node
                RETURN duplicate_node, prop_value, size(nodes) as duplicate_count
                LIMIT 100
                """
                
                # 执行查询
                result = session.run(query)
                
                # 收集重复节点
                for record in result:
                    node = record["duplicate_node"]
                    duplicate_nodes.append({
                        "id": node.id,
                        "labels": list(node.labels),
                        "properties": dict(node.items()),
                        "duplicate_property": prop,
                        "duplicate_value": record["prop_value"],
                        "duplicate_count": record["duplicate_count"]
                    })
            
            # 如果需要修复并且有重复节点
            fix_result = None
            if fix_issues and duplicate_nodes:
                # 按重复属性和值分组
                duplicates = {}
                for node in duplicate_nodes:
                    key = (node["duplicate_property"], node["duplicate_value"])
                    if key not in duplicates:
                        duplicates[key] = []
                    duplicates[key].append(node["id"])
                
                merged_count = 0
                
                # 为每组重复节点执行合并
                for (prop, value), node_ids in duplicates.items():
                    # 保留第一个节点，删除其他节点
                    kept_node_id = node_ids[0]
                    nodes_to_delete = node_ids[1:]
                    
                    # 将关系转移到保留的节点
                    transfer_query = f"""
                    MATCH (kept_node) WHERE id(kept_node) = $kept_node_id
                    MATCH (n) WHERE id(n) IN $nodes_to_delete
                    MATCH (n)-[r]->(m)
                    WHERE NOT (kept_node)-[:{{type: type(r)}}]->(m)
                    CREATE (kept_node)-[r2:{{type: type(r)}}]->(m)
                    SET r2 = properties(r)
                    WITH kept_node, n
                    MATCH (o)-[r]->(n)
                    WHERE NOT (o)-[:{{type: type(r)}}]->(kept_node)
                    CREATE (o)-[r2:{{type: type(r)}}]->(kept_node)
                    SET r2 = properties(r)
                    RETURN count(*) as transferred_relationships
                    """
                    
                    session.run(transfer_query, {"kept_node_id": kept_node_id, "nodes_to_delete": nodes_to_delete})
                    
                    # 删除多余的节点
                    delete_query = """
                    MATCH (n) WHERE id(n) IN $nodes_to_delete
                    DETACH DELETE n
                    RETURN count(*) as deleted_count
                    """
                    
                    result = session.run(delete_query, {"nodes_to_delete": nodes_to_delete})
                    merged_count += result.single()["deleted_count"]
                
                fix_result = {
                    "action": "merge_duplicate_nodes",
                    "merged_count": merged_count,
                    "message": f"Merged {merged_count} duplicate nodes"
                }
            
            # 准备返回结果
            response = {
                "status": "success",
                "check_type": "duplicate_nodes",
                "duplicate_nodes_count": len(duplicate_nodes),
                "duplicate_nodes": duplicate_nodes
            }
            
            # 如果有修复结果，添加到响应中
            if fix_result:
                response["fix_result"] = fix_result
            
            return json.dumps(response, indent=2)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"Error checking duplicate nodes: {str(e)}",
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)

def check_constraint_violations(driver, database, fix_issues):
    """检查约束违规"""
    try:
        with driver.session(database=database) as session:
            # 获取所有约束
            constraints_query = "SHOW CONSTRAINTS"
            constraints_result = session.run(constraints_query)
            
            constraints = []
            for record in constraints_result:
                constraint = dict(record["constraints"])
                constraints.append(constraint)
            
            # 检查唯一性约束违规
            violations = []
            
            for constraint in constraints:
                if constraint.get("type") == "UNIQUENESS":
                    label = constraint.get("labelsOrTypes")[0] if constraint.get("labelsOrTypes") else None
                    properties = constraint.get("properties", [])
                    
                    if label and properties:
                        property_name = properties[0]
                        
                        # 检查是否有重复值
                        violation_query = f"""
                        MATCH (n:{label})
                        WITH n.{property_name} as prop_value, collect(n) as nodes
                        WHERE size(nodes) > 1
                        RETURN prop_value, size(nodes) as violation_count, nodes
                        LIMIT 10
                        """
                        
                        violation_result = session.run(violation_query)
                        
                        for record in violation_result:
                            prop_value = record["prop_value"]
                            violation_count = record["violation_count"]
                            nodes = record["nodes"]
                            
                            node_ids = []
                            for node in nodes:
                                node_ids.append(node.id)
                            
                            violations.append({
                                "constraint_type": "UNIQUENESS",
                                "label": label,
                                "property": property_name,
                                "value": prop_value,
                                "violation_count": violation_count,
                                "node_ids": node_ids
                            })
            
            # 如果需要修复并且有违规
            fix_result = None
            if fix_issues and violations:
                fixed_count = 0
                
                for violation in violations:
                    if violation["constraint_type"] == "UNIQUENESS":
                        label = violation["label"]
                        property_name = violation["property"]
                        node_ids = violation["node_ids"]
                        
                        # 保留第一个节点，为其他节点添加后缀
                        kept_node_id = node_ids[0]
                        nodes_to_fix = node_ids[1:]
                        
                        for i, node_id in enumerate(nodes_to_fix):
                            # 为重复节点添加后缀
                            fix_query = f"""
                            MATCH (n:{label}) WHERE id(n) = $node_id
                            SET n.{property_name} = n.{property_name} + '_duplicate_' + $suffix
                            RETURN n
                            """
                            
                            session.run(fix_query, {"node_id": node_id, "suffix": str(i + 1)})
                            fixed_count += 1
                
                fix_result = {
                    "action": "fix_constraint_violations",
                    "fixed_count": fixed_count,
                    "message": f"Fixed {fixed_count} constraint violations by adding suffixes to duplicate values"
                }
            
            # 准备返回结果
            response = {
                "status": "success",
                "check_type": "constraint_violations",
                "constraints_count": len(constraints),
                "constraints": constraints,
                "violations_count": len(violations),
                "violations": violations
            }
            
            # 如果有修复结果，添加到响应中
            if fix_result:
                response["fix_result"] = fix_result
            
            return json.dumps(response, indent=2)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"Error checking constraint violations: {str(e)}",
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)

def check_schema_consistency(driver, database, fix_issues):
    """检查模式一致性"""
    try:
        with driver.session(database=database) as session:
            # 获取所有节点标签
            labels_query = "CALL db.labels()"
            labels_result = session.run(labels_query)
            
            labels = [record["label"] for record in labels_result]
            
            # 检查每个标签的属性一致性
            inconsistent_nodes = []
            
            for label in labels:
                # 获取该标签的所有属性
                properties_query = f"""
                MATCH (n:{label})
                UNWIND keys(n) as property
                RETURN DISTINCT property
                """
                
                properties_result = session.run(properties_query)
                all_properties = [record["property"] for record in properties_result]
                
                # 检查缺少属性的节点
                for prop in all_properties:
                    missing_query = f"""
                    MATCH (n:{label})
                    WHERE NOT EXISTS(n.{prop})
                    RETURN n LIMIT 10
                    """
                    
                    missing_result = session.run(missing_query)
                    
                    for record in missing_result:
                        node = record["n"]
                        inconsistent_nodes.append({
                            "id": node.id,
                            "label": label,
                            "properties": dict(node.items()),
                            "missing_property": prop
                        })
            
            # 如果需要修复并且有不一致的节点
            fix_result = None
            if fix_issues and inconsistent_nodes:
                fixed_count = 0
                
                # 按标签和缺失属性分组
                inconsistencies = {}
                for node in inconsistent_nodes:
                    key = (node["label"], node["missing_property"])
                    if key not in inconsistencies:
                        inconsistencies[key] = []
                    inconsistencies[key].append(node["id"])
                
                # 为每组不一致节点执行修复
                for (label, prop), node_ids in inconsistencies.items():
                    # 添加默认值
                    fix_query = f"""
                    MATCH (n:{label}) WHERE id(n) IN $node_ids
                    SET n.{prop} = $default_value
                    RETURN count(*) as fixed_count
                    """
                    
                    result = session.run(fix_query, {"node_ids": node_ids, "default_value": f"{label}_{prop}_default"})
                    fixed_count += result.single()["fixed_count"]
                
                fix_result = {
                    "action": "fix_schema_inconsistencies",
                    "fixed_count": fixed_count,
                    "message": f"Fixed {fixed_count} schema inconsistencies by adding default values"
                }
            
            # 准备返回结果
            response = {
                "status": "success",
                "check_type": "schema_consistency",
                "labels_count": len(labels),
                "labels": labels,
                "inconsistent_nodes_count": len(inconsistent_nodes),
                "inconsistent_nodes": inconsistent_nodes[:100] if len(inconsistent_nodes) > 100 else inconsistent_nodes
            }
            
            # 如果有修复结果，添加到响应中
            if fix_result:
                response["fix_result"] = fix_result
            
            return json.dumps(response, indent=2)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"Error checking schema consistency: {str(e)}",
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)