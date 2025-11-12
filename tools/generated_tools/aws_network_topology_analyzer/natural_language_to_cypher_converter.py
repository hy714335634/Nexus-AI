from strands import tool
from typing import Dict, List, Optional, Any, Union
import json
import logging
import time
import re
from neo4j import GraphDatabase, Driver, Session, Result
from neo4j.exceptions import ServiceUnavailable, AuthError, DatabaseError, CypherSyntaxError

# Import the get_connection function from neo4j_database_connector
from tools.generated_tools.aws_network_topology_analyzer.neo4j_database_connector import get_connection

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import AWS Bedrock client for Claude, but make it optional
try:
    import boto3
    BEDROCK_AVAILABLE = True
except ImportError:
    logger.warning("AWS Bedrock client not available. Install boto3 for AWS Bedrock support.")
    BEDROCK_AVAILABLE = False

@tool
def natural_language_to_cypher_converter(
    query: str,
    connection_id: str = "default",
    database: str = "neo4j",
    use_schema: bool = True,
    max_schema_items: int = 100,
    execute_query: bool = False,
    region: str = "us-east-1",
    model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
) -> str:
    """
    将自然语言转换为Cypher查询
    
    Args:
        query: 自然语言查询
        connection_id: 数据库连接ID（可选，默认为"default"）
        database: 数据库名称（可选，默认为"neo4j"）
        use_schema: 是否使用数据库模式信息来改进查询转换（可选，默认为True）
        max_schema_items: 从数据库获取的最大模式项数（可选，默认为100）
        execute_query: 是否执行生成的查询（可选，默认为False）
        region: AWS区域，用于Bedrock调用（可选，默认为"us-east-1"）
        model_id: Bedrock模型ID（可选，默认为"anthropic.claude-3-sonnet-20240229-v1:0"）
        
    Returns:
        str: JSON格式的转换结果，包含生成的Cypher查询
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
        
        # 准备模式信息
        schema_info = {}
        
        if use_schema:
            try:
                with driver.session(database=database) as session:
                    # 获取所有标签
                    labels_result = session.run("CALL db.labels() YIELD label RETURN label ORDER BY label LIMIT $limit", 
                                               {"limit": max_schema_items})
                    schema_info["labels"] = [record["label"] for record in labels_result]
                    
                    # 获取所有关系类型
                    rel_types_result = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType LIMIT $limit",
                                                  {"limit": max_schema_items})
                    schema_info["relationship_types"] = [record["relationshipType"] for record in rel_types_result]
                    
                    # 获取标签的属性
                    schema_info["label_properties"] = {}
                    for label in schema_info["labels"]:
                        props_result = session.run(f"MATCH (n:{label}) UNWIND keys(n) AS key RETURN DISTINCT key ORDER BY key LIMIT $limit",
                                                 {"limit": max_schema_items})
                        schema_info["label_properties"][label] = [record["key"] for record in props_result]
                    
                    # 获取关系的属性
                    schema_info["relationship_properties"] = {}
                    for rel_type in schema_info["relationship_types"]:
                        props_result = session.run(f"MATCH ()-[r:{rel_type}]->() UNWIND keys(r) AS key RETURN DISTINCT key ORDER BY key LIMIT $limit",
                                                 {"limit": max_schema_items})
                        schema_info["relationship_properties"][rel_type] = [record["key"] for record in props_result]
                    
                    # 获取关系模式
                    patterns_result = session.run("""
                    MATCH (a)-[r]->(b)
                    WITH labels(a) AS source_labels, type(r) AS rel_type, labels(b) AS target_labels
                    RETURN DISTINCT source_labels, rel_type, target_labels
                    LIMIT $limit
                    """, {"limit": max_schema_items})
                    
                    schema_info["patterns"] = []
                    for record in patterns_result:
                        pattern = {
                            "source_labels": record["source_labels"],
                            "relationship_type": record["rel_type"],
                            "target_labels": record["target_labels"]
                        }
                        schema_info["patterns"].append(pattern)
                    
                    # 获取一些示例节点
                    examples_result = session.run("""
                    MATCH (n)
                    WITH labels(n) AS labels, n
                    RETURN labels, properties(n) AS properties
                    LIMIT 10
                    """)
                    
                    schema_info["examples"] = []
                    for record in examples_result:
                        example = {
                            "labels": record["labels"],
                            "properties": record["properties"]
                        }
                        schema_info["examples"].append(example)
            
            except Exception as e:
                logger.warning(f"Error retrieving schema information: {str(e)}")
                schema_info = {}
        
        # 准备提示
        prompt = generate_prompt(query, schema_info)
        
        # 使用Bedrock生成Cypher查询
        cypher_query = ""
        explanation = ""
        
        if BEDROCK_AVAILABLE:
            try:
                # 创建Bedrock客户端
                bedrock_runtime = boto3.client(
                    service_name="bedrock-runtime",
                    region_name=region
                )
                
                # 准备请求体
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
                
                # 调用模型
                response = bedrock_runtime.invoke_model(
                    modelId=model_id,
                    body=json.dumps(request_body)
                )
                
                # 解析响应
                response_body = json.loads(response.get('body').read())
                
                # 提取生成的内容
                generated_text = response_body.get('content', [{}])[0].get('text', '')
                
                # 解析生成的内容
                cypher_query, explanation = parse_generated_text(generated_text)
            
            except Exception as e:
                logger.warning(f"Error using AWS Bedrock: {str(e)}")
                # 如果Bedrock调用失败，使用基于规则的转换
                cypher_query, explanation = rule_based_conversion(query, schema_info)
        else:
            # 如果Bedrock不可用，使用基于规则的转换
            cypher_query, explanation = rule_based_conversion(query, schema_info)
        
        # 如果需要执行查询
        execution_result = None
        if execute_query and cypher_query:
            try:
                with driver.session(database=database) as session:
                    start_time = time.time()
                    result = session.run(cypher_query)
                    
                    # 收集结果
                    records = []
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
                                    "properties": dict(value.items())
                                }
                            # 处理路径
                            elif hasattr(value, "start_node") and hasattr(value, "relationships"):
                                path_data = {
                                    "nodes": [],
                                    "relationships": []
                                }
                                
                                # 添加起始节点
                                start_node = value.start_node
                                path_data["nodes"].append({
                                    "id": start_node.id,
                                    "labels": list(start_node.labels),
                                    "properties": dict(start_node.items())
                                })
                                
                                # 添加关系和节点
                                for rel in value.relationships:
                                    path_data["relationships"].append({
                                        "id": rel.id,
                                        "type": rel.type,
                                        "properties": dict(rel.items())
                                    })
                                    
                                    end_node = rel.end_node
                                    path_data["nodes"].append({
                                        "id": end_node.id,
                                        "labels": list(end_node.labels),
                                        "properties": dict(end_node.items())
                                    })
                                
                                record_dict[key] = path_data
                            else:
                                # 这是一个普通值
                                record_dict[key] = value
                        
                        records.append(record_dict)
                    
                    # 获取查询统计信息
                    summary = result.consume()
                    
                    end_time = time.time()
                    query_duration = round(end_time - start_time, 3)
                    
                    execution_result = {
                        "status": "success",
                        "records": records,
                        "record_count": len(records),
                        "query_duration_seconds": query_duration,
                        "stats": {
                            "nodes_created": summary.counters.nodes_created,
                            "nodes_deleted": summary.counters.nodes_deleted,
                            "relationships_created": summary.counters.relationships_created,
                            "relationships_deleted": summary.counters.relationships_deleted,
                            "properties_set": summary.counters.properties_set,
                            "labels_added": summary.counters.labels_added,
                            "contains_updates": summary.counters.contains_updates
                        }
                    }
            
            except CypherSyntaxError as e:
                execution_result = {
                    "status": "error",
                    "message": f"Cypher syntax error: {str(e)}",
                    "error_type": "CypherSyntaxError"
                }
            
            except DatabaseError as e:
                execution_result = {
                    "status": "error",
                    "message": f"Database error: {str(e)}",
                    "error_type": "DatabaseError"
                }
            
            except Exception as e:
                execution_result = {
                    "status": "error",
                    "message": f"Execution error: {str(e)}",
                    "error_type": type(e).__name__
                }
        
        # 准备返回结果
        response = {
            "status": "success",
            "natural_language_query": query,
            "cypher_query": cypher_query,
            "explanation": explanation
        }
        
        # 如果有执行结果，添加到响应中
        if execution_result:
            response["execution_result"] = execution_result
        
        return json.dumps(response, indent=2, default=str)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)

@tool
def cypher_query_builder(
    entity_type: str,
    action: str,
    filters: Optional[Dict[str, Any]] = None,
    return_fields: Optional[List[str]] = None,
    relationship_type: Optional[str] = None,
    target_entity_type: Optional[str] = None,
    target_filters: Optional[Dict[str, Any]] = None,
    limit: int = 100,
    connection_id: str = "default",
    database: str = "neo4j",
    execute_query: bool = False
) -> str:
    """
    构建并可选执行Cypher查询
    
    Args:
        entity_type: 实体类型（节点标签）
        action: 操作类型，可选值："find", "count", "create", "update", "delete", "find_related"
        filters: 过滤条件字典（可选）
        return_fields: 要返回的字段列表（可选，默认为所有字段）
        relationship_type: 关系类型，用于find_related操作（可选）
        target_entity_type: 目标实体类型，用于find_related操作（可选）
        target_filters: 目标过滤条件字典，用于find_related操作（可选）
        limit: 结果限制数量（可选，默认为100）
        connection_id: 数据库连接ID（可选，默认为"default"）
        database: 数据库名称（可选，默认为"neo4j"）
        execute_query: 是否执行生成的查询（可选，默认为False）
        
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
        
        # 构建查询
        cypher_query = ""
        params = {}
        
        if action == "find":
            # 构建MATCH子句
            cypher_query = f"MATCH (n:{entity_type})"
            
            # 添加WHERE子句
            if filters:
                where_conditions = []
                for key, value in filters.items():
                    param_name = f"filter_{key}"
                    where_conditions.append(f"n.{key} = ${param_name}")
                    params[param_name] = value
                
                if where_conditions:
                    cypher_query += f" WHERE {' AND '.join(where_conditions)}"
            
            # 添加RETURN子句
            if return_fields:
                return_items = [f"n.{field}" for field in return_fields]
                cypher_query += f" RETURN {', '.join(return_items)}"
            else:
                cypher_query += " RETURN n"
            
            # 添加LIMIT子句
            cypher_query += f" LIMIT {limit}"
        
        elif action == "count":
            # 构建COUNT查询
            cypher_query = f"MATCH (n:{entity_type})"
            
            # 添加WHERE子句
            if filters:
                where_conditions = []
                for key, value in filters.items():
                    param_name = f"filter_{key}"
                    where_conditions.append(f"n.{key} = ${param_name}")
                    params[param_name] = value
                
                if where_conditions:
                    cypher_query += f" WHERE {' AND '.join(where_conditions)}"
            
            # 添加RETURN子句
            cypher_query += " RETURN count(n) as count"
        
        elif action == "create":
            # 构建CREATE查询
            if not filters:
                return json.dumps({
                    "status": "error",
                    "message": "Properties are required for create operation"
                }, indent=2)
            
            # 构建属性字符串
            properties_list = []
            for key, value in filters.items():
                param_name = f"prop_{key}"
                properties_list.append(f"{key}: ${param_name}")
                params[param_name] = value
            
            properties_str = ", ".join(properties_list)
            cypher_query = f"CREATE (n:{entity_type} {{{properties_str}}}) RETURN n"
        
        elif action == "update":
            # 构建UPDATE查询
            if not filters:
                return json.dumps({
                    "status": "error",
                    "message": "Filters are required for update operation"
                }, indent=2)
            
            # 至少需要一个过滤条件和一个更新属性
            if len(filters) < 2:
                return json.dumps({
                    "status": "error",
                    "message": "At least one filter and one update property are required"
                }, indent=2)
            
            # 假设第一个属性是过滤条件，其余是更新属性
            filter_key = list(filters.keys())[0]
            filter_value = filters[filter_key]
            param_name = f"filter_{filter_key}"
            params[param_name] = filter_value
            
            cypher_query = f"MATCH (n:{entity_type} {{{filter_key}: ${param_name}}})"
            
            # 构建SET子句
            set_items = []
            for key, value in list(filters.items())[1:]:
                param_name = f"prop_{key}"
                set_items.append(f"n.{key} = ${param_name}")
                params[param_name] = value
            
            if set_items:
                cypher_query += f" SET {', '.join(set_items)} RETURN n"
            else:
                cypher_query += " RETURN n"
        
        elif action == "delete":
            # 构建DELETE查询
            cypher_query = f"MATCH (n:{entity_type})"
            
            # 添加WHERE子句
            if filters:
                where_conditions = []
                for key, value in filters.items():
                    param_name = f"filter_{key}"
                    where_conditions.append(f"n.{key} = ${param_name}")
                    params[param_name] = value
                
                if where_conditions:
                    cypher_query += f" WHERE {' AND '.join(where_conditions)}"
            
            # 添加DELETE子句
            cypher_query += " DELETE n"
            
            # 如果没有过滤条件，添加警告
            if not filters:
                cypher_query = "// WARNING: This query will delete all nodes with label " + entity_type + "\n" + cypher_query
        
        elif action == "find_related":
            # 构建关系查询
            if not relationship_type or not target_entity_type:
                return json.dumps({
                    "status": "error",
                    "message": "Relationship type and target entity type are required for find_related operation"
                }, indent=2)
            
            # 构建MATCH子句
            cypher_query = f"MATCH (n:{entity_type})"
            
            # 添加源节点WHERE子句
            if filters:
                where_conditions = []
                for key, value in filters.items():
                    param_name = f"filter_{key}"
                    where_conditions.append(f"n.{key} = ${param_name}")
                    params[param_name] = value
                
                if where_conditions:
                    cypher_query += f" WHERE {' AND '.join(where_conditions)}"
            
            # 添加关系和目标节点
            cypher_query += f" MATCH (n)-[r:{relationship_type}]->(m:{target_entity_type})"
            
            # 添加目标节点WHERE子句
            if target_filters:
                where_conditions = []
                for key, value in target_filters.items():
                    param_name = f"target_filter_{key}"
                    where_conditions.append(f"m.{key} = ${param_name}")
                    params[param_name] = value
                
                if where_conditions:
                    cypher_query += f" WHERE {' AND '.join(where_conditions)}"
            
            # 添加RETURN子句
            if return_fields:
                return_items = []
                for field in return_fields:
                    if field.startswith("n."):
                        return_items.append(field)
                    elif field.startswith("m."):
                        return_items.append(field)
                    elif field.startswith("r."):
                        return_items.append(field)
                    else:
                        return_items.append(f"n.{field}")
                
                cypher_query += f" RETURN {', '.join(return_items)}"
            else:
                cypher_query += " RETURN n, r, m"
            
            # 添加LIMIT子句
            cypher_query += f" LIMIT {limit}"
        
        else:
            return json.dumps({
                "status": "error",
                "message": f"Invalid action: {action}. Supported actions: find, count, create, update, delete, find_related"
            }, indent=2)
        
        # 如果需要执行查询
        execution_result = None
        if execute_query:
            try:
                with driver.session(database=database) as session:
                    start_time = time.time()
                    result = session.run(cypher_query, params)
                    
                    # 收集结果
                    records = []
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
                                    "properties": dict(value.items())
                                }
                            else:
                                # 这是一个普通值
                                record_dict[key] = value
                        
                        records.append(record_dict)
                    
                    # 获取查询统计信息
                    summary = result.consume()
                    
                    end_time = time.time()
                    query_duration = round(end_time - start_time, 3)
                    
                    execution_result = {
                        "status": "success",
                        "records": records,
                        "record_count": len(records),
                        "query_duration_seconds": query_duration,
                        "stats": {
                            "nodes_created": summary.counters.nodes_created,
                            "nodes_deleted": summary.counters.nodes_deleted,
                            "relationships_created": summary.counters.relationships_created,
                            "relationships_deleted": summary.counters.relationships_deleted,
                            "properties_set": summary.counters.properties_set,
                            "labels_added": summary.counters.labels_added,
                            "contains_updates": summary.counters.contains_updates
                        }
                    }
            
            except CypherSyntaxError as e:
                execution_result = {
                    "status": "error",
                    "message": f"Cypher syntax error: {str(e)}",
                    "error_type": "CypherSyntaxError"
                }
            
            except DatabaseError as e:
                execution_result = {
                    "status": "error",
                    "message": f"Database error: {str(e)}",
                    "error_type": "DatabaseError"
                }
            
            except Exception as e:
                execution_result = {
                    "status": "error",
                    "message": f"Execution error: {str(e)}",
                    "error_type": type(e).__name__
                }
        
        # 准备返回结果
        response = {
            "status": "success",
            "entity_type": entity_type,
            "action": action,
            "cypher_query": cypher_query,
            "parameters": params
        }
        
        # 如果有执行结果，添加到响应中
        if execution_result:
            response["execution_result"] = execution_result
        
        return json.dumps(response, indent=2, default=str)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)

def generate_prompt(query, schema_info):
    """生成提示以将自然语言转换为Cypher查询"""
    prompt = """
You are a specialized Neo4j Cypher query generator for AWS network topology analysis. Your task is to convert natural language questions about AWS network resources into precise Cypher queries.

CONTEXT:
The Neo4j database contains AWS network topology information with resources organized in a hierarchical structure:
- Account -> Region -> Network Service -> VPC -> Route Table/Security Group -> EC2/RDS
- Network components include: Transit Gateway, VPC Peering, Privatelink, VPC, Direct Connect Gateway, Internet Gateway, etc.
- Relationships represent network connections and hierarchical relationships

INSTRUCTIONS:
1. Generate a valid Cypher query that answers the user's question
2. Focus on network topology analysis, path finding, and resource relationships
3. Use appropriate labels and relationship types from the schema
4. Include only necessary conditions and return values
5. Provide a brief explanation of how the query works
6. Format your response with a Cypher code block and explanation

USER QUESTION:
"""
    
    prompt += query + "\n\n"
    
    if schema_info:
        prompt += "DATABASE SCHEMA:\n"
        
        # Add labels
        if "labels" in schema_info:
            prompt += "Node Labels: " + ", ".join(schema_info["labels"]) + "\n"
        
        # Add relationship types
        if "relationship_types" in schema_info:
            prompt += "Relationship Types: " + ", ".join(schema_info["relationship_types"]) + "\n"
        
        # Add key properties for important labels
        if "label_properties" in schema_info:
            prompt += "Key Properties:\n"
            for label, properties in schema_info["label_properties"].items():
                if properties:
                    prompt += f"- {label}: {', '.join(properties[:10])}\n"
        
        # Add common patterns
        if "patterns" in schema_info and schema_info["patterns"]:
            prompt += "Common Patterns:\n"
            for i, pattern in enumerate(schema_info["patterns"][:5]):
                source = pattern["source_labels"][0] if pattern["source_labels"] else "Node"
                target = pattern["target_labels"][0] if pattern["target_labels"] else "Node"
                rel_type = pattern["relationship_type"]
                prompt += f"- ({source})-[:{rel_type}]->({target})\n"
    
    prompt += """
RESPONSE FORMAT:
```cypher
// Your Cypher query here
```

EXPLANATION:
Brief explanation of the query logic and how it addresses the user's question.
"""
    
    return prompt

def parse_generated_text(text):
    """从生成的文本中解析Cypher查询和解释"""
    # 提取Cypher查询
    cypher_pattern = r"```(?:cypher)?\s*([\s\S]*?)```"
    cypher_matches = re.findall(cypher_pattern, text)
    
    cypher_query = cypher_matches[0].strip() if cypher_matches else ""
    
    # 提取解释
    explanation = ""
    if "EXPLANATION:" in text:
        explanation = text.split("EXPLANATION:", 1)[1].strip()
    elif "Explanation:" in text:
        explanation = text.split("Explanation:", 1)[1].strip()
    
    return cypher_query, explanation

def rule_based_conversion(query, schema_info):
    """基于规则的自然语言到Cypher转换"""
    # 简单的规则集，用于在Bedrock不可用时进行基本转换
    cypher_query = ""
    explanation = "Generated using rule-based conversion."
    
    # 标准化查询
    query_lower = query.lower()
    
    # 查找所有VPC
    if "all vpc" in query_lower or "list vpc" in query_lower or "show vpc" in query_lower:
        cypher_query = "MATCH (v:VPC) RETURN v LIMIT 100"
        explanation = "This query finds all VPC nodes in the database and returns them."
    
    # 查找特定VPC
    elif "vpc" in query_lower and any(x in query_lower for x in ["find", "show", "get"]):
        vpc_id_match = re.search(r"vpc[- ]([a-z0-9]+)", query_lower)
        if vpc_id_match:
            vpc_id = vpc_id_match.group(1)
            cypher_query = f"MATCH (v:VPC) WHERE v.resource_id = 'vpc-{vpc_id}' RETURN v"
            explanation = f"This query finds a specific VPC with ID vpc-{vpc_id}."
        else:
            cypher_query = "MATCH (v:VPC) RETURN v LIMIT 10"
            explanation = "This query finds VPC nodes in the database and returns them."
    
    # 查找路径
    elif any(x in query_lower for x in ["path", "route", "connection"]) and "between" in query_lower:
        cypher_query = """
        MATCH path = shortestPath((a)-[*]-(b))
        WHERE a.resource_id = $source_id AND b.resource_id = $target_id
        RETURN path
        """
        explanation = "This query finds the shortest path between two resources. Replace $source_id and $target_id with actual resource IDs."
    
    # 查找安全组
    elif "security group" in query_lower:
        cypher_query = "MATCH (sg:SecurityGroup) RETURN sg LIMIT 100"
        explanation = "This query finds all security group nodes in the database and returns them."
    
    # 查找EC2实例
    elif "ec2" in query_lower or "instance" in query_lower:
        cypher_query = "MATCH (ec2:EC2) RETURN ec2 LIMIT 100"
        explanation = "This query finds all EC2 instance nodes in the database and returns them."
    
    # 查找RDS实例
    elif "rds" in query_lower or "database" in query_lower:
        cypher_query = "MATCH (rds:RDS) RETURN rds LIMIT 100"
        explanation = "This query finds all RDS instance nodes in the database and returns them."
    
    # 查找Transit Gateway
    elif "transit gateway" in query_lower or "tgw" in query_lower:
        cypher_query = "MATCH (tgw:TransitGateway) RETURN tgw LIMIT 100"
        explanation = "This query finds all Transit Gateway nodes in the database and returns them."
    
    # 查找VPC Peering
    elif "peering" in query_lower:
        cypher_query = "MATCH (vpc_peering:VpcPeering) RETURN vpc_peering LIMIT 100"
        explanation = "This query finds all VPC Peering nodes in the database and returns them."
    
    # 查找Internet Gateway
    elif "internet gateway" in query_lower or "igw" in query_lower:
        cypher_query = "MATCH (igw:InternetGateway) RETURN igw LIMIT 100"
        explanation = "This query finds all Internet Gateway nodes in the database and returns them."
    
    # 查找所有区域
    elif "region" in query_lower:
        cypher_query = "MATCH (r:Region) RETURN r LIMIT 100"
        explanation = "This query finds all Region nodes in the database and returns them."
    
    # 查找所有账户
    elif "account" in query_lower:
        cypher_query = "MATCH (a:Account) RETURN a LIMIT 100"
        explanation = "This query finds all Account nodes in the database and returns them."
    
    # 默认查询
    else:
        # 尝试从模式信息中提取一些有用的信息
        if schema_info and "labels" in schema_info and schema_info["labels"]:
            # 使用最常见的标签
            common_labels = schema_info["labels"][:3]
            label_conditions = []
            
            for label in common_labels:
                if label.lower() in query_lower:
                    cypher_query = f"MATCH (n:{label}) RETURN n LIMIT 100"
                    explanation = f"This query finds all {label} nodes in the database and returns them."
                    break
            
            if not cypher_query:
                # 默认使用第一个标签
                cypher_query = f"MATCH (n:{common_labels[0]}) RETURN n LIMIT 100"
                explanation = f"This is a default query that finds {common_labels[0]} nodes in the database."
        else:
            cypher_query = "MATCH (n) RETURN n LIMIT 100"
            explanation = "This is a default query that returns a sample of nodes from the database."
    
    return cypher_query, explanation