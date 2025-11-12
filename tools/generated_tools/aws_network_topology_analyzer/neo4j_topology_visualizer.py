from strands import tool
from typing import Dict, List, Optional, Any, Union
import json
import logging
import time
import base64
import os
from io import BytesIO
from neo4j import GraphDatabase, Driver, Session, Result
from neo4j.exceptions import ServiceUnavailable, AuthError, DatabaseError, CypherSyntaxError

# Import the get_connection function from neo4j_database_connector
from tools.generated_tools.aws_network_topology_analyzer.neo4j_database_connector import get_connection

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import visualization libraries, but make them optional
try:
    import matplotlib.pyplot as plt
    import networkx as nx
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap
    VISUALIZATION_AVAILABLE = True
except ImportError:
    logger.warning("Visualization libraries not available. Install matplotlib, networkx, and numpy for visualization support.")
    VISUALIZATION_AVAILABLE = False

@tool
def neo4j_topology_visualizer(
    query: str,
    parameters: Optional[Dict[str, Any]] = None,
    connection_id: str = "default",
    database: str = "neo4j",
    format: str = "json",
    node_label_property: str = "resource_id",
    node_size_property: Optional[str] = None,
    node_color_property: Optional[str] = None,
    layout: str = "spring",
    include_properties: bool = False,
    limit_nodes: int = 100
) -> str:
    """
    可视化网络拓扑
    
    Args:
        query: Cypher查询语句，必须返回包含节点和关系的路径或图结构
        parameters: 查询参数字典（可选）
        connection_id: 数据库连接ID（可选，默认为"default"）
        database: 数据库名称（可选，默认为"neo4j"）
        format: 输出格式，可选值："json", "graph_json", "base64_image"（可选，默认为"json"）
        node_label_property: 用于节点标签的属性名（可选，默认为"resource_id"）
        node_size_property: 用于节点大小的属性名（可选）
        node_color_property: 用于节点颜色的属性名（可选）
        layout: 图布局算法，可选值："spring", "circular", "random", "shell", "kamada_kawai"（可选，默认为"spring"）
        include_properties: 是否包含节点和边的所有属性（可选，默认为False）
        limit_nodes: 限制节点数量以避免过大的可视化（可选，默认为100）
        
    Returns:
        str: 根据format参数返回不同格式的可视化结果
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
                result = session.run(query, params)
                
                # 收集图数据
                nodes = {}
                edges = {}
                
                for record in result:
                    for value in record.values():
                        # 处理路径
                        if hasattr(value, "start_node") and hasattr(value, "relationships"):
                            path = value
                            
                            # 添加起始节点
                            start_node = path.start_node
                            if start_node.id not in nodes and len(nodes) < limit_nodes:
                                nodes[start_node.id] = extract_node_data(start_node, node_label_property, include_properties)
                            
                            # 添加关系和节点
                            for rel in path.relationships:
                                if rel.id not in edges:
                                    edges[rel.id] = extract_edge_data(rel, include_properties)
                                
                                end_node = rel.end_node
                                if end_node.id not in nodes and len(nodes) < limit_nodes:
                                    nodes[end_node.id] = extract_node_data(end_node, node_label_property, include_properties)
                        
                        # 处理节点
                        elif hasattr(value, "id") and hasattr(value, "labels"):
                            node = value
                            if node.id not in nodes and len(nodes) < limit_nodes:
                                nodes[node.id] = extract_node_data(node, node_label_property, include_properties)
                        
                        # 处理关系
                        elif hasattr(value, "type") and hasattr(value, "start_node") and hasattr(value, "end_node"):
                            rel = value
                            if rel.id not in edges:
                                edges[rel.id] = extract_edge_data(rel, include_properties)
                            
                            # 添加关系的两端节点
                            start_node = rel.start_node
                            if start_node.id not in nodes and len(nodes) < limit_nodes:
                                nodes[start_node.id] = extract_node_data(start_node, node_label_property, include_properties)
                            
                            end_node = rel.end_node
                            if end_node.id not in nodes and len(nodes) < limit_nodes:
                                nodes[end_node.id] = extract_node_data(end_node, node_label_property, include_properties)
                        
                        # 处理列表
                        elif isinstance(value, list):
                            for item in value:
                                # 处理列表中的节点
                                if hasattr(item, "id") and hasattr(item, "labels"):
                                    node = item
                                    if node.id not in nodes and len(nodes) < limit_nodes:
                                        nodes[node.id] = extract_node_data(node, node_label_property, include_properties)
                                
                                # 处理列表中的关系
                                elif hasattr(item, "type") and hasattr(item, "start_node") and hasattr(item, "end_node"):
                                    rel = item
                                    if rel.id not in edges:
                                        edges[rel.id] = extract_edge_data(rel, include_properties)
                                    
                                    # 添加关系的两端节点
                                    start_node = rel.start_node
                                    if start_node.id not in nodes and len(nodes) < limit_nodes:
                                        nodes[start_node.id] = extract_node_data(start_node, node_label_property, include_properties)
                                    
                                    end_node = rel.end_node
                                    if end_node.id not in nodes and len(nodes) < limit_nodes:
                                        nodes[end_node.id] = extract_node_data(end_node, node_label_property, include_properties)
                
                end_time = time.time()
                query_duration = round(end_time - start_time, 3)
                
                # 检查是否有足够的数据进行可视化
                if not nodes:
                    return json.dumps({
                        "status": "warning",
                        "message": "No nodes found in query result",
                        "query_duration_seconds": query_duration
                    }, indent=2)
                
                # 根据格式返回结果
                if format == "json":
                    # 返回节点和边的列表
                    response = {
                        "status": "success",
                        "message": f"Visualization data prepared successfully",
                        "query_duration_seconds": query_duration,
                        "nodes_count": len(nodes),
                        "edges_count": len(edges),
                        "nodes": list(nodes.values()),
                        "edges": list(edges.values())
                    }
                    
                    return json.dumps(response, indent=2, default=str)
                
                elif format == "graph_json":
                    # 返回D3.js兼容的图格式
                    graph_data = {
                        "nodes": [
                            {
                                "id": str(node_id),
                                "label": node_data["label"],
                                "labels": node_data["labels"],
                                "properties": node_data.get("properties", {})
                            }
                            for node_id, node_data in nodes.items()
                        ],
                        "links": [
                            {
                                "source": str(edge_data["source"]),
                                "target": str(edge_data["target"]),
                                "type": edge_data["type"],
                                "properties": edge_data.get("properties", {})
                            }
                            for edge_data in edges.values()
                        ]
                    }
                    
                    response = {
                        "status": "success",
                        "message": f"Graph data prepared successfully",
                        "query_duration_seconds": query_duration,
                        "nodes_count": len(nodes),
                        "edges_count": len(edges),
                        "graph": graph_data
                    }
                    
                    return json.dumps(response, indent=2, default=str)
                
                elif format == "base64_image":
                    # 检查可视化库是否可用
                    if not VISUALIZATION_AVAILABLE:
                        return json.dumps({
                            "status": "error",
                            "message": "Visualization libraries not available. Install matplotlib, networkx, and numpy for visualization support."
                        }, indent=2)
                    
                    # 创建NetworkX图
                    G = nx.DiGraph()
                    
                    # 添加节点
                    for node_id, node_data in nodes.items():
                        G.add_node(node_id, **node_data)
                    
                    # 添加边
                    for edge_data in edges.values():
                        G.add_edge(edge_data["source"], edge_data["target"], 
                                   key=edge_data["id"], 
                                   type=edge_data["type"],
                                   **edge_data.get("properties", {}))
                    
                    # 创建图像
                    plt.figure(figsize=(12, 10))
                    
                    # 设置节点颜色
                    if node_color_property and all(node_color_property in node_data.get("properties", {}) for node_data in nodes.values()):
                        # 使用指定属性作为颜色
                        color_values = [nodes[node_id].get("properties", {}).get(node_color_property, 0) for node_id in G.nodes()]
                        
                        # 创建颜色映射
                        cmap = plt.cm.viridis
                        
                        # 如果所有值相同，使用单一颜色
                        if len(set(color_values)) == 1:
                            node_colors = ['#1f77b4'] * len(G.nodes())
                        else:
                            # 归一化颜色值
                            min_val = min(color_values)
                            max_val = max(color_values)
                            if min_val != max_val:
                                normalized_values = [(val - min_val) / (max_val - min_val) for val in color_values]
                                node_colors = [cmap(val) for val in normalized_values]
                            else:
                                node_colors = ['#1f77b4'] * len(G.nodes())
                    else:
                        # 根据节点标签分配颜色
                        unique_labels = set()
                        for node_data in nodes.values():
                            unique_labels.update(node_data["labels"])
                        
                        label_colors = {}
                        cmap = plt.cm.tab20
                        for i, label in enumerate(unique_labels):
                            label_colors[label] = cmap(i % 20)
                        
                        node_colors = []
                        for node_id in G.nodes():
                            node_labels = nodes[node_id]["labels"]
                            if node_labels:
                                # 使用第一个标签的颜色
                                node_colors.append(label_colors[node_labels[0]])
                            else:
                                node_colors.append('#1f77b4')  # 默认蓝色
                    
                    # 设置节点大小
                    if node_size_property and all(node_size_property in node_data.get("properties", {}) for node_data in nodes.values()):
                        # 使用指定属性作为大小
                        size_values = [nodes[node_id].get("properties", {}).get(node_size_property, 300) for node_id in G.nodes()]
                        
                        # 确保大小在合理范围内
                        min_size = 100
                        max_size = 1000
                        
                        # 如果所有值相同，使用默认大小
                        if len(set(size_values)) == 1:
                            node_sizes = [300] * len(G.nodes())
                        else:
                            # 归一化大小值
                            min_val = min(size_values)
                            max_val = max(size_values)
                            if min_val != max_val:
                                normalized_values = [(val - min_val) / (max_val - min_val) for val in size_values]
                                node_sizes = [min_size + (max_size - min_size) * val for val in normalized_values]
                            else:
                                node_sizes = [300] * len(G.nodes())
                    else:
                        # 根据节点连接数确定大小
                        node_sizes = [100 + 50 * G.degree(node_id) for node_id in G.nodes()]
                    
                    # 选择布局算法
                    if layout == "spring":
                        pos = nx.spring_layout(G, seed=42)
                    elif layout == "circular":
                        pos = nx.circular_layout(G)
                    elif layout == "random":
                        pos = nx.random_layout(G, seed=42)
                    elif layout == "shell":
                        pos = nx.shell_layout(G)
                    elif layout == "kamada_kawai":
                        try:
                            pos = nx.kamada_kawai_layout(G)
                        except:
                            # 如果失败，回退到spring布局
                            pos = nx.spring_layout(G, seed=42)
                    else:
                        pos = nx.spring_layout(G, seed=42)
                    
                    # 绘制节点
                    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color=node_colors, alpha=0.8)
                    
                    # 绘制边
                    edge_labels = {(u, v): d["type"] for u, v, d in G.edges(data=True)}
                    nx.draw_networkx_edges(G, pos, arrowsize=15, alpha=0.5)
                    
                    # 绘制节点标签
                    labels = {node_id: nodes[node_id]["label"] for node_id in G.nodes()}
                    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)
                    
                    # 添加图例
                    if len(unique_labels) > 0:
                        legend_patches = []
                        from matplotlib.patches import Patch
                        for label, color in label_colors.items():
                            legend_patches.append(Patch(color=color, label=label))
                        
                        plt.legend(handles=legend_patches, loc='upper right', fontsize=8)
                    
                    # 添加标题
                    plt.title(f"Network Topology Visualization ({len(nodes)} nodes, {len(edges)} edges)")
                    
                    # 关闭坐标轴
                    plt.axis('off')
                    
                    # 保存为base64编码的图像
                    buffer = BytesIO()
                    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
                    plt.close()
                    
                    buffer.seek(0)
                    image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
                    
                    response = {
                        "status": "success",
                        "message": f"Visualization image created successfully",
                        "query_duration_seconds": query_duration,
                        "nodes_count": len(nodes),
                        "edges_count": len(edges),
                        "image_format": "png",
                        "image_base64": image_base64
                    }
                    
                    return json.dumps(response, indent=2, default=str)
                
                else:
                    return json.dumps({
                        "status": "error",
                        "message": f"Invalid format: {format}. Supported formats: json, graph_json, base64_image"
                    }, indent=2)
            
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
def neo4j_topology_subgraph_visualizer(
    node_type: Optional[str] = None,
    node_properties: Optional[Dict[str, Any]] = None,
    depth: int = 1,
    relationship_types: Optional[List[str]] = None,
    connection_id: str = "default",
    database: str = "neo4j",
    format: str = "json",
    node_label_property: str = "resource_id",
    layout: str = "spring",
    include_properties: bool = False,
    limit_nodes: int = 100
) -> str:
    """
    可视化子图拓扑
    
    Args:
        node_type: 起始节点类型（可选，默认为None，表示所有节点类型）
        node_properties: 起始节点属性字典，用于过滤节点（可选，默认为None）
        depth: 探索深度（可选，默认为1）
        relationship_types: 要包含的关系类型列表（可选，默认为所有类型）
        connection_id: 数据库连接ID（可选，默认为"default"）
        database: 数据库名称（可选，默认为"neo4j"）
        format: 输出格式，可选值："json", "graph_json", "base64_image"（可选，默认为"json"）
        node_label_property: 用于节点标签的属性名（可选，默认为"resource_id"）
        layout: 图布局算法，可选值："spring", "circular", "random", "shell", "kamada_kawai"（可选，默认为"spring"）
        include_properties: 是否包含节点和边的所有属性（可选，默认为False）
        limit_nodes: 限制节点数量以避免过大的可视化（可选，默认为100）
        
    Returns:
        str: 根据format参数返回不同格式的可视化结果
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
        
        # 构建节点类型过滤条件
        node_type_filter = ""
        if node_type:
            node_type_filter = f":{node_type}"
        
        # 构建节点属性过滤条件
        where_clause = ""
        if node_properties:
            conditions = []
            for key, value in node_properties.items():
                conditions.append(f"n.{key} = ${key}")
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # 构建关系类型过滤
        rel_type_filter = ""
        if relationship_types:
            rel_types = "|".join(relationship_types)
            rel_type_filter = f":{rel_types}"
        
        # 准备参数
        params = {}
        if node_properties:
            params.update(node_properties)
        
        params["depth"] = depth
        params["limit"] = limit_nodes
        
        # 构建查询
        query = f"""
        MATCH (n{node_type_filter})
        {where_clause}
        CALL {{
            WITH n
            MATCH path = (n)-[r{rel_type_filter}*1..{depth}]-(m)
            RETURN path
            LIMIT $limit
        }}
        RETURN path
        """
        
        # 使用可视化工具
        return neo4j_topology_visualizer(
            query=query,
            parameters=params,
            connection_id=connection_id,
            database=database,
            format=format,
            node_label_property=node_label_property,
            layout=layout,
            include_properties=include_properties,
            limit_nodes=limit_nodes
        )
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)

def extract_node_data(node, label_property, include_properties):
    """从Neo4j节点提取数据"""
    node_data = {
        "id": node.id,
        "labels": list(node.labels)
    }
    
    # 使用指定属性作为标签，如果不存在则使用ID
    if label_property in node:
        node_data["label"] = str(node[label_property])
    else:
        # 尝试其他常见属性
        for prop in ["name", "id", "resource_id", "identifier"]:
            if prop in node:
                node_data["label"] = str(node[prop])
                break
        else:
            # 如果没有找到合适的属性，使用ID
            node_data["label"] = f"Node {node.id}"
    
    # 如果需要，包含所有属性
    if include_properties:
        node_data["properties"] = dict(node.items())
    
    return node_data

def extract_edge_data(relationship, include_properties):
    """从Neo4j关系提取数据"""
    edge_data = {
        "id": relationship.id,
        "source": relationship.start_node.id,
        "target": relationship.end_node.id,
        "type": relationship.type
    }
    
    # 如果需要，包含所有属性
    if include_properties:
        edge_data["properties"] = dict(relationship.items())
    
    return edge_data