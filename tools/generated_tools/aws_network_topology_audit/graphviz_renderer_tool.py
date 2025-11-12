"""
AWS Network Topology Visualizer - Graphviz Renderer Tool

This module provides tools for rendering network topology graphs using Graphviz,
with specialized styling for AWS network resources.
"""

from typing import Dict, List, Optional, Any, Tuple, Set, Union
import os
import json
import logging
import tempfile
import base64
import graphviz
from strands import tool

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Cache directory
CACHE_DIR = os.path.join(".cache", "aws_network_topology_visualizer")
os.makedirs(CACHE_DIR, exist_ok=True)

# AWS resource type to shape/color mapping
AWS_RESOURCE_STYLES = {
    # VPC and networking
    "vpc": {"shape": "box3d", "style": "filled", "fillcolor": "#F9DFCF", "color": "#E78F24"},
    "subnet": {"shape": "box", "style": "filled", "fillcolor": "#EBF3E7", "color": "#8DC348"},
    "internet_gateway": {"shape": "house", "style": "filled", "fillcolor": "#D9EAF7", "color": "#3B82F6"},
    "nat_gateway": {"shape": "diamond", "style": "filled", "fillcolor": "#D9EAF7", "color": "#3B82F6"},
    "route_table": {"shape": "folder", "style": "filled", "fillcolor": "#F5F5F5", "color": "#666666"},
    "security_group": {"shape": "hexagon", "style": "filled", "fillcolor": "#FFEBEE", "color": "#E53935"},
    "network_acl": {"shape": "septagon", "style": "filled", "fillcolor": "#FFEBEE", "color": "#E53935"},
    "transit_gateway": {"shape": "doublecircle", "style": "filled", "fillcolor": "#E1F5FE", "color": "#039BE5"},
    "vpc_endpoint": {"shape": "oval", "style": "filled", "fillcolor": "#E8F5E9", "color": "#43A047"},
    
    # Compute
    "ec2_instance": {"shape": "box", "style": "filled", "fillcolor": "#FFF9C4", "color": "#FBC02D"},
    "auto_scaling_group": {"shape": "box", "style": "filled", "fillcolor": "#FFF9C4", "color": "#FBC02D", "peripheries": "2"},
    "lambda_function": {"shape": "component", "style": "filled", "fillcolor": "#F3E5F5", "color": "#8E24AA"},
    
    # Database
    "rds_instance": {"shape": "cylinder", "style": "filled", "fillcolor": "#E3F2FD", "color": "#1976D2"},
    "dynamodb_table": {"shape": "cylinder", "style": "filled", "fillcolor": "#E8EAF6", "color": "#3F51B5"},
    
    # Storage
    "s3_bucket": {"shape": "folder", "style": "filled", "fillcolor": "#E0F7FA", "color": "#00ACC1"},
    "ebs_volume": {"shape": "cylinder", "style": "filled", "fillcolor": "#FFF3E0", "color": "#FB8C00"},
    
    # Load balancing
    "elb": {"shape": "trapezium", "style": "filled", "fillcolor": "#F3E5F5", "color": "#9C27B0"},
    "alb": {"shape": "trapezium", "style": "filled", "fillcolor": "#F3E5F5", "color": "#9C27B0"},
    "nlb": {"shape": "trapezium", "style": "filled", "fillcolor": "#F3E5F5", "color": "#9C27B0"},
    
    # Default
    "default": {"shape": "ellipse", "style": "filled", "fillcolor": "#F5F5F5", "color": "#9E9E9E"}
}

# AWS connection type to edge style mapping
AWS_CONNECTION_STYLES = {
    "vpc_peering": {"style": "solid", "color": "#4CAF50", "penwidth": "2.0"},
    "transit_gateway": {"style": "solid", "color": "#2196F3", "penwidth": "2.0"},
    "vpc_endpoint": {"style": "dashed", "color": "#9C27B0", "penwidth": "1.5"},
    "internet_gateway": {"style": "solid", "color": "#F44336", "penwidth": "2.0"},
    "nat_gateway": {"style": "solid", "color": "#FF9800", "penwidth": "1.5"},
    "route_table": {"style": "dotted", "color": "#607D8B", "penwidth": "1.0"},
    "security_group": {"style": "dashed", "color": "#E91E63", "penwidth": "1.0"},
    "network_acl": {"style": "dashed", "color": "#9C27B0", "penwidth": "1.0"},
    "privatelink": {"style": "dashed", "color": "#673AB7", "penwidth": "1.5"},
    "direct_connect": {"style": "bold", "color": "#00BCD4", "penwidth": "2.5"},
    "vpn": {"style": "bold", "color": "#8BC34A", "penwidth": "1.5"},
    "cross_region": {"style": "dashed", "color": "#FF5722", "penwidth": "2.0", "constraint": "false"},
    "cross_account": {"style": "dashed", "color": "#795548", "penwidth": "2.0", "constraint": "false"},
    "default": {"style": "solid", "color": "#9E9E9E", "penwidth": "1.0"}
}

# Boundary style mapping
BOUNDARY_STYLES = {
    "account": {"style": "dashed", "color": "#795548", "penwidth": "3.0"},
    "region": {"style": "dashed", "color": "#FF5722", "penwidth": "3.0"},
    "vpc": {"style": "dashed", "color": "#E78F24", "penwidth": "2.0"},
    "security": {"style": "dashed", "color": "#E53935", "penwidth": "2.0"},
    "default": {"style": "dashed", "color": "#9E9E9E", "penwidth": "1.5"}
}

@tool
def render_network_graph(
    graph_json: Dict[str, Any],
    output_format: str = "png",
    layout_engine: str = "dot",
    show_labels: bool = True,
    show_attributes: bool = False,
    custom_styles: Optional[Dict[str, Dict[str, str]]] = None,
    highlight_nodes: Optional[List[str]] = None,
    highlight_edges: Optional[List[Tuple[str, str]]] = None,
    cluster_by: Optional[str] = None,
    title: Optional[str] = None,
    dpi: int = 300,
    base64_encode: bool = False
) -> Dict[str, Any]:
    """
    Render a NetworkX graph of AWS network resources using Graphviz.
    
    This tool renders a graph representation of AWS network resources using Graphviz,
    with specialized styling for different resource and connection types.
    
    Args:
        graph_json: Serialized graph in JSON format (as returned by create_network_graph)
        output_format: Output format (png, jpg, svg, pdf) (default: "png")
        layout_engine: Graphviz layout engine (dot, neato, fdp, sfdp, twopi, circo) (default: "dot")
        show_labels: Whether to show node and edge labels (default: True)
        show_attributes: Whether to show node and edge attributes (default: False)
        custom_styles: Optional dictionary of custom styles for nodes and edges
        highlight_nodes: Optional list of node IDs to highlight
        highlight_edges: Optional list of edge tuples (source, target) to highlight
        cluster_by: Optional attribute to cluster nodes by (e.g., "region", "account_id", "vpc_id")
        title: Optional title for the graph
        dpi: DPI for raster formats (default: 300)
        base64_encode: Whether to return the graph as a base64-encoded string (default: False)
        
    Returns:
        Dictionary with rendering results:
        {
            "status": "success" or "error",
            "format": output format,
            "file_path": path to the rendered file (if base64_encode is False),
            "base64_data": base64-encoded graph data (if base64_encode is True),
            "graph_stats": statistics about the rendered graph,
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "format": output_format,
            "graph_stats": {}
        }
        
        # Validate output format
        valid_formats = ["png", "jpg", "jpeg", "svg", "pdf", "dot"]
        if output_format not in valid_formats:
            return {
                "status": "error",
                "error": f"Invalid output format: {output_format}. Valid formats are: {', '.join(valid_formats)}"
            }
        
        # Validate layout engine
        valid_engines = ["dot", "neato", "fdp", "sfdp", "twopi", "circo"]
        if layout_engine not in valid_engines:
            return {
                "status": "error",
                "error": f"Invalid layout engine: {layout_engine}. Valid engines are: {', '.join(valid_engines)}"
            }
        
        # Normalize jpg to jpeg for graphviz
        if output_format == "jpg":
            output_format = "jpeg"
        
        # Create a new Graphviz graph
        if graph_json.get("directed", False):
            dot = graphviz.Digraph(format=output_format, engine=layout_engine)
        else:
            dot = graphviz.Graph(format=output_format, engine=layout_engine)
        
        # Set graph attributes
        dot.attr(rankdir="TB", ranksep="1.5", nodesep="0.8", overlap="false", splines="true")
        dot.attr(dpi=str(dpi))
        
        # Add title if provided
        if title:
            dot.attr(label=title, fontsize="24", fontname="Arial", labelloc="t")
        
        # Create style lookup with custom styles if provided
        node_styles = dict(AWS_RESOURCE_STYLES)
        edge_styles = dict(AWS_CONNECTION_STYLES)
        
        if custom_styles:
            if "nodes" in custom_styles:
                for node_type, style in custom_styles["nodes"].items():
                    if node_type in node_styles:
                        node_styles[node_type].update(style)
                    else:
                        node_styles[node_type] = style
            
            if "edges" in custom_styles:
                for edge_type, style in custom_styles["edges"].items():
                    if edge_type in edge_styles:
                        edge_styles[edge_type].update(style)
                    else:
                        edge_styles[edge_type] = style
        
        # Prepare clustering if requested
        clusters = {}
        if cluster_by:
            for node_id, attrs in graph_json.get("nodes", {}).items():
                if cluster_by in attrs:
                    cluster_value = attrs[cluster_by]
                    if cluster_value not in clusters:
                        clusters[cluster_value] = []
                    clusters[cluster_value].append((node_id, attrs))
        
        # Track statistics
        node_count = 0
        edge_count = 0
        node_types = {}
        edge_types = {}
        
        # Process nodes
        if not cluster_by:
            for node_id, attrs in graph_json.get("nodes", {}).items():
                node_type = attrs.get("type", "default")
                
                # Get style for this node type
                style = node_styles.get(node_type, node_styles["default"]).copy()
                
                # Highlight node if requested
                if highlight_nodes and node_id in highlight_nodes:
                    style["penwidth"] = "3.0"
                    style["color"] = "#FF0000"
                
                # Prepare node label
                if show_labels:
                    label = attrs.get("name", node_id)
                    if show_attributes:
                        attr_str = "\n".join([f"{k}: {v}" for k, v in attrs.items() 
                                             if k not in ["name", "id", "type"] and v])
                        if attr_str:
                            label = f"{label}\n{attr_str}"
                else:
                    label = ""
                
                # Add node to graph
                dot.node(node_id, label=label, **style)
                
                # Update statistics
                node_count += 1
                node_types[node_type] = node_types.get(node_type, 0) + 1
        
        # Process clusters if clustering is requested
        else:
            for cluster_value, nodes in clusters.items():
                with dot.subgraph(name=f"cluster_{cluster_value}") as c:
                    c.attr(label=str(cluster_value), style="filled", color="#E8E8E8", fillcolor="#F8F8F8")
                    
                    for node_id, attrs in nodes:
                        node_type = attrs.get("type", "default")
                        
                        # Get style for this node type
                        style = node_styles.get(node_type, node_styles["default"]).copy()
                        
                        # Highlight node if requested
                        if highlight_nodes and node_id in highlight_nodes:
                            style["penwidth"] = "3.0"
                            style["color"] = "#FF0000"
                        
                        # Prepare node label
                        if show_labels:
                            label = attrs.get("name", node_id)
                            if show_attributes:
                                attr_str = "\n".join([f"{k}: {v}" for k, v in attrs.items() 
                                                    if k not in ["name", "id", "type", cluster_by] and v])
                                if attr_str:
                                    label = f"{label}\n{attr_str}"
                        else:
                            label = ""
                        
                        # Add node to cluster
                        c.node(node_id, label=label, **style)
                        
                        # Update statistics
                        node_count += 1
                        node_types[node_type] = node_types.get(node_type, 0) + 1
        
        # Process edges
        for edge_id, attrs in graph_json.get("edges", {}).items():
            # Parse edge ID to get source and target
            if graph_json.get("multigraph", False):
                try:
                    source, target, _ = edge_id.split('_')
                except ValueError:
                    logger.warning(f"Invalid edge ID format for multigraph: {edge_id}")
                    continue
            else:
                try:
                    source, target = edge_id.split('_')
                except ValueError:
                    logger.warning(f"Invalid edge ID format: {edge_id}")
                    continue
            
            edge_type = attrs.get("type", "default")
            
            # Get style for this edge type
            style = edge_styles.get(edge_type, edge_styles["default"]).copy()
            
            # Highlight edge if requested
            if highlight_edges and (source, target) in highlight_edges:
                style["penwidth"] = "3.0"
                style["color"] = "#FF0000"
            
            # Prepare edge label
            if show_labels:
                label = attrs.get("name", edge_type)
                if show_attributes:
                    attr_str = "\n".join([f"{k}: {v}" for k, v in attrs.items() 
                                         if k not in ["name", "type"] and v])
                    if attr_str:
                        label = f"{label}\n{attr_str}"
            else:
                label = ""
            
            # Add edge to graph
            dot.edge(source, target, label=label, **style)
            
            # Update statistics
            edge_count += 1
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
        
        # Update graph statistics
        result["graph_stats"] = {
            "node_count": node_count,
            "edge_count": edge_count,
            "node_types": node_types,
            "edge_types": edge_types,
            "clusters": len(clusters) if cluster_by else 0
        }
        
        # Render the graph
        if base64_encode:
            # Render to a temporary file and read as base64
            with tempfile.NamedTemporaryFile(suffix=f".{output_format}") as tmp:
                dot.render(tmp.name, cleanup=True)
                with open(f"{tmp.name}.{output_format}", "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                os.remove(f"{tmp.name}.{output_format}")
                result["base64_data"] = encoded
        else:
            # Render to a file in the cache directory
            timestamp = int(time.time())
            output_file = os.path.join(CACHE_DIR, f"network_graph_{timestamp}")
            dot.render(output_file, cleanup=True)
            result["file_path"] = f"{output_file}.{output_format}"
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error rendering network graph: {str(e)}"
        }


@tool
def render_network_boundaries(
    graph_json: Dict[str, Any],
    boundaries_json: Dict[str, Any],
    output_format: str = "png",
    layout_engine: str = "dot",
    show_labels: bool = True,
    show_attributes: bool = False,
    highlight_boundary_types: Optional[List[str]] = None,
    title: Optional[str] = None,
    dpi: int = 300,
    base64_encode: bool = False
) -> Dict[str, Any]:
    """
    Render a NetworkX graph with highlighted network boundaries using Graphviz.
    
    This tool renders a graph representation of AWS network resources with highlighted
    boundaries such as account boundaries, region boundaries, and VPC boundaries.
    
    Args:
        graph_json: Serialized graph in JSON format (as returned by create_network_graph)
        boundaries_json: Boundaries information (as returned by identify_network_boundaries)
        output_format: Output format (png, jpg, svg, pdf) (default: "png")
        layout_engine: Graphviz layout engine (dot, neato, fdp, sfdp, twopi, circo) (default: "dot")
        show_labels: Whether to show node and edge labels (default: True)
        show_attributes: Whether to show node and edge attributes (default: False)
        highlight_boundary_types: Optional list of boundary types to highlight (e.g., ["account", "region"])
        title: Optional title for the graph
        dpi: DPI for raster formats (default: 300)
        base64_encode: Whether to return the graph as a base64-encoded string (default: False)
        
    Returns:
        Dictionary with rendering results:
        {
            "status": "success" or "error",
            "format": output format,
            "file_path": path to the rendered file (if base64_encode is False),
            "base64_data": base64-encoded graph data (if base64_encode is True),
            "graph_stats": statistics about the rendered graph,
            "boundary_stats": statistics about the rendered boundaries,
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "format": output_format,
            "graph_stats": {},
            "boundary_stats": {}
        }
        
        # Validate output format
        valid_formats = ["png", "jpg", "jpeg", "svg", "pdf", "dot"]
        if output_format not in valid_formats:
            return {
                "status": "error",
                "error": f"Invalid output format: {output_format}. Valid formats are: {', '.join(valid_formats)}"
            }
        
        # Validate layout engine
        valid_engines = ["dot", "neato", "fdp", "sfdp", "twopi", "circo"]
        if layout_engine not in valid_engines:
            return {
                "status": "error",
                "error": f"Invalid layout engine: {layout_engine}. Valid engines are: {', '.join(valid_engines)}"
            }
        
        # Normalize jpg to jpeg for graphviz
        if output_format == "jpg":
            output_format = "jpeg"
        
        # Create a new Graphviz graph
        if graph_json.get("directed", False):
            dot = graphviz.Digraph(format=output_format, engine=layout_engine)
        else:
            dot = graphviz.Graph(format=output_format, engine=layout_engine)
        
        # Set graph attributes
        dot.attr(rankdir="TB", ranksep="1.5", nodesep="0.8", overlap="false", splines="true")
        dot.attr(dpi=str(dpi))
        
        # Add title if provided
        if title:
            dot.attr(label=title, fontsize="24", fontname="Arial", labelloc="t")
        
        # Filter boundary types if requested
        boundary_types = list(boundaries_json.get("boundaries", {}).keys())
        if highlight_boundary_types:
            boundary_types = [bt for bt in boundary_types if bt in highlight_boundary_types]
        
        # Track statistics
        node_count = 0
        edge_count = 0
        boundary_counts = {}
        
        # Create clusters for each boundary type
        for boundary_type in boundary_types:
            boundaries = boundaries_json.get("boundaries", {}).get(boundary_type, [])
            boundary_counts[boundary_type] = len(boundaries)
            
            for i, boundary in enumerate(boundaries):
                boundary_id = boundary.get("id", f"{boundary_type}_{i}")
                boundary_name = boundary.get("name", boundary_id)
                
                # Get boundary style
                style = BOUNDARY_STYLES.get(boundary_type, BOUNDARY_STYLES["default"]).copy()
                
                # Create a subgraph/cluster for this boundary
                with dot.subgraph(name=f"cluster_{boundary_type}_{i}") as c:
                    c.attr(label=f"{boundary_type}: {boundary_name}", **style)
                    
                    # Add nodes to this boundary
                    nodes = boundary.get("nodes", [])
                    for node_id in nodes:
                        # Get node attributes from graph_json
                        attrs = graph_json.get("nodes", {}).get(node_id, {})
                        node_type = attrs.get("type", "default")
                        
                        # Get style for this node type
                        style = AWS_RESOURCE_STYLES.get(node_type, AWS_RESOURCE_STYLES["default"]).copy()
                        
                        # Prepare node label
                        if show_labels:
                            label = attrs.get("name", node_id)
                            if show_attributes:
                                attr_str = "\n".join([f"{k}: {v}" for k, v in attrs.items() 
                                                     if k not in ["name", "id", "type"] and v])
                                if attr_str:
                                    label = f"{label}\n{attr_str}"
                        else:
                            label = ""
                        
                        # Add node to cluster
                        c.node(node_id, label=label, **style)
                        node_count += 1
        
        # Add nodes that are not part of any boundary
        boundary_nodes = set()
        for boundary_type in boundary_types:
            for boundary in boundaries_json.get("boundaries", {}).get(boundary_type, []):
                boundary_nodes.update(boundary.get("nodes", []))
        
        for node_id, attrs in graph_json.get("nodes", {}).items():
            if node_id not in boundary_nodes:
                node_type = attrs.get("type", "default")
                
                # Get style for this node type
                style = AWS_RESOURCE_STYLES.get(node_type, AWS_RESOURCE_STYLES["default"]).copy()
                
                # Prepare node label
                if show_labels:
                    label = attrs.get("name", node_id)
                    if show_attributes:
                        attr_str = "\n".join([f"{k}: {v}" for k, v in attrs.items() 
                                             if k not in ["name", "id", "type"] and v])
                        if attr_str:
                            label = f"{label}\n{attr_str}"
                else:
                    label = ""
                
                # Add node to graph
                dot.node(node_id, label=label, **style)
                node_count += 1
        
        # Add edges
        for edge_id, attrs in graph_json.get("edges", {}).items():
            # Parse edge ID to get source and target
            if graph_json.get("multigraph", False):
                try:
                    source, target, _ = edge_id.split('_')
                except ValueError:
                    logger.warning(f"Invalid edge ID format for multigraph: {edge_id}")
                    continue
            else:
                try:
                    source, target = edge_id.split('_')
                except ValueError:
                    logger.warning(f"Invalid edge ID format: {edge_id}")
                    continue
            
            edge_type = attrs.get("type", "default")
            
            # Get style for this edge type
            style = AWS_CONNECTION_STYLES.get(edge_type, AWS_CONNECTION_STYLES["default"]).copy()
            
            # Check if this edge crosses a boundary
            is_boundary_crossing = False
            for boundary_type in boundary_types:
                crossings = boundaries_json.get("boundary_crossings", {}).get(boundary_type, [])
                for crossing in crossings:
                    if crossing.get("source") == source and crossing.get("target") == target:
                        is_boundary_crossing = True
                        # Use boundary crossing style
                        boundary_style = BOUNDARY_STYLES.get(boundary_type, BOUNDARY_STYLES["default"]).copy()
                        style["color"] = boundary_style["color"]
                        style["penwidth"] = "2.5"
                        style["style"] = "bold"
                        break
                if is_boundary_crossing:
                    break
            
            # Prepare edge label
            if show_labels:
                label = attrs.get("name", edge_type)
                if is_boundary_crossing:
                    label = f"{label} (boundary crossing)"
                if show_attributes:
                    attr_str = "\n".join([f"{k}: {v}" for k, v in attrs.items() 
                                         if k not in ["name", "type"] and v])
                    if attr_str:
                        label = f"{label}\n{attr_str}"
            else:
                label = ""
            
            # Add edge to graph
            dot.edge(source, target, label=label, **style)
            edge_count += 1
        
        # Update statistics
        result["graph_stats"] = {
            "node_count": node_count,
            "edge_count": edge_count
        }
        
        result["boundary_stats"] = {
            "boundary_types": boundary_types,
            "boundary_counts": boundary_counts,
            "total_boundaries": sum(boundary_counts.values())
        }
        
        # Render the graph
        if base64_encode:
            # Render to a temporary file and read as base64
            with tempfile.NamedTemporaryFile(suffix=f".{output_format}") as tmp:
                dot.render(tmp.name, cleanup=True)
                with open(f"{tmp.name}.{output_format}", "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                os.remove(f"{tmp.name}.{output_format}")
                result["base64_data"] = encoded
        else:
            # Render to a file in the cache directory
            timestamp = int(time.time())
            output_file = os.path.join(CACHE_DIR, f"network_boundaries_{timestamp}")
            dot.render(output_file, cleanup=True)
            result["file_path"] = f"{output_file}.{output_format}"
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error rendering network boundaries: {str(e)}"
        }


@tool
def render_network_paths(
    graph_json: Dict[str, Any],
    paths_json: Dict[str, Any],
    output_format: str = "png",
    layout_engine: str = "dot",
    show_labels: bool = True,
    show_attributes: bool = False,
    highlight_critical_paths: bool = True,
    path_colors: Optional[List[str]] = None,
    title: Optional[str] = None,
    dpi: int = 300,
    base64_encode: bool = False
) -> Dict[str, Any]:
    """
    Render network paths in an AWS network topology graph using Graphviz.
    
    This tool renders network paths between source and target nodes in an AWS network
    topology graph, with options to highlight critical paths and use custom colors.
    
    Args:
        graph_json: Serialized graph in JSON format (as returned by create_network_graph)
        paths_json: Paths information (as returned by find_network_paths)
        output_format: Output format (png, jpg, svg, pdf) (default: "png")
        layout_engine: Graphviz layout engine (dot, neato, fdp, sfdp, twopi, circo) (default: "dot")
        show_labels: Whether to show node and edge labels (default: True)
        show_attributes: Whether to show node and edge attributes (default: False)
        highlight_critical_paths: Whether to highlight critical paths (default: True)
        path_colors: Optional list of colors to use for different paths
        title: Optional title for the graph
        dpi: DPI for raster formats (default: 300)
        base64_encode: Whether to return the graph as a base64-encoded string (default: False)
        
    Returns:
        Dictionary with rendering results:
        {
            "status": "success" or "error",
            "format": output format,
            "file_path": path to the rendered file (if base64_encode is False),
            "base64_data": base64-encoded graph data (if base64_encode is True),
            "graph_stats": statistics about the rendered graph,
            "path_stats": statistics about the rendered paths,
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "format": output_format,
            "graph_stats": {},
            "path_stats": {}
        }
        
        # Validate output format
        valid_formats = ["png", "jpg", "jpeg", "svg", "pdf", "dot"]
        if output_format not in valid_formats:
            return {
                "status": "error",
                "error": f"Invalid output format: {output_format}. Valid formats are: {', '.join(valid_formats)}"
            }
        
        # Validate layout engine
        valid_engines = ["dot", "neato", "fdp", "sfdp", "twopi", "circo"]
        if layout_engine not in valid_engines:
            return {
                "status": "error",
                "error": f"Invalid layout engine: {layout_engine}. Valid engines are: {', '.join(valid_engines)}"
            }
        
        # Normalize jpg to jpeg for graphviz
        if output_format == "jpg":
            output_format = "jpeg"
        
        # Create a new Graphviz graph
        if graph_json.get("directed", False):
            dot = graphviz.Digraph(format=output_format, engine=layout_engine)
        else:
            dot = graphviz.Graph(format=output_format, engine=layout_engine)
        
        # Set graph attributes
        dot.attr(rankdir="TB", ranksep="1.5", nodesep="0.8", overlap="false", splines="true")
        dot.attr(dpi=str(dpi))
        
        # Add title if provided
        if title:
            dot.attr(label=title, fontsize="24", fontname="Arial", labelloc="t")
        
        # Set default path colors if not provided
        if not path_colors:
            path_colors = ["#E53935", "#1E88E5", "#43A047", "#FBC02D", "#8E24AA", "#00ACC1", "#F4511E", "#3949AB"]
        
        # Get paths from paths_json
        paths = paths_json.get("paths", [])
        
        # Track nodes and edges in paths
        path_nodes = set()
        path_edges = set()
        
        # Track statistics
        node_count = 0
        edge_count = 0
        path_lengths = []
        
        # Add paths to graph
        for i, path in enumerate(paths):
            path_color = path_colors[i % len(path_colors)]
            path_nodes_list = path.get("nodes", [])
            path_length = path.get("length", len(path_nodes_list) - 1)
            path_lengths.append(path_length)
            
            # Add nodes in this path
            for node_id in path_nodes_list:
                if node_id not in path_nodes:
                    # Get node attributes from graph_json
                    attrs = graph_json.get("nodes", {}).get(node_id, {})
                    node_type = attrs.get("type", "default")
                    
                    # Get style for this node type
                    style = AWS_RESOURCE_STYLES.get(node_type, AWS_RESOURCE_STYLES["default"]).copy()
                    
                    # Highlight source and target nodes
                    if node_id == path.get("source") or node_id == path.get("target"):
                        style["penwidth"] = "3.0"
                        style["color"] = path_color
                    
                    # Prepare node label
                    if show_labels:
                        label = attrs.get("name", node_id)
                        if show_attributes:
                            attr_str = "\n".join([f"{k}: {v}" for k, v in attrs.items() 
                                                 if k not in ["name", "id", "type"] and v])
                            if attr_str:
                                label = f"{label}\n{attr_str}"
                    else:
                        label = ""
                    
                    # Add node to graph
                    dot.node(node_id, label=label, **style)
                    path_nodes.add(node_id)
                    node_count += 1
            
            # Add edges in this path
            for j in range(len(path_nodes_list) - 1):
                source = path_nodes_list[j]
                target = path_nodes_list[j + 1]
                edge_key = f"{source}_{target}"
                
                if edge_key not in path_edges:
                    # Get edge attributes from graph_json
                    attrs = {}
                    for edge_id, edge_attrs in graph_json.get("edges", {}).items():
                        if edge_id.startswith(f"{source}_{target}") or edge_id.startswith(f"{target}_{source}"):
                            attrs = edge_attrs
                            break
                    
                    edge_type = attrs.get("type", "default")
                    
                    # Get style for this edge type
                    style = AWS_CONNECTION_STYLES.get(edge_type, AWS_CONNECTION_STYLES["default"]).copy()
                    
                    # Use path color for this edge
                    style["color"] = path_color
                    style["penwidth"] = "2.5"
                    
                    # Prepare edge label
                    if show_labels:
                        label = attrs.get("name", edge_type)
                        if show_attributes:
                            attr_str = "\n".join([f"{k}: {v}" for k, v in attrs.items() 
                                                 if k not in ["name", "type"] and v])
                            if attr_str:
                                label = f"{label}\n{attr_str}"
                    else:
                        label = ""
                    
                    # Add edge to graph
                    dot.edge(source, target, label=label, **style)
                    path_edges.add(edge_key)
                    edge_count += 1
        
        # Add non-path nodes and edges with faded style
        for node_id, attrs in graph_json.get("nodes", {}).items():
            if node_id not in path_nodes:
                node_type = attrs.get("type", "default")
                
                # Get style for this node type with faded appearance
                style = AWS_RESOURCE_STYLES.get(node_type, AWS_RESOURCE_STYLES["default"]).copy()
                style["color"] = "#CCCCCC"
                style["fillcolor"] = "#F8F8F8"
                style["style"] = "filled,dashed"
                
                # Prepare node label
                if show_labels:
                    label = attrs.get("name", node_id)
                    if show_attributes:
                        attr_str = "\n".join([f"{k}: {v}" for k, v in attrs.items() 
                                             if k not in ["name", "id", "type"] and v])
                        if attr_str:
                            label = f"{label}\n{attr_str}"
                else:
                    label = ""
                
                # Add node to graph
                dot.node(node_id, label=label, **style)
                node_count += 1
        
        for edge_id, attrs in graph_json.get("edges", {}).items():
            # Parse edge ID to get source and target
            if graph_json.get("multigraph", False):
                try:
                    source, target, _ = edge_id.split('_')
                except ValueError:
                    logger.warning(f"Invalid edge ID format for multigraph: {edge_id}")
                    continue
            else:
                try:
                    source, target = edge_id.split('_')
                except ValueError:
                    logger.warning(f"Invalid edge ID format: {edge_id}")
                    continue
            
            edge_key = f"{source}_{target}"
            if edge_key not in path_edges:
                edge_type = attrs.get("type", "default")
                
                # Get style for this edge type with faded appearance
                style = AWS_CONNECTION_STYLES.get(edge_type, AWS_CONNECTION_STYLES["default"]).copy()
                style["color"] = "#CCCCCC"
                style["style"] = "dotted"
                style["penwidth"] = "0.5"
                
                # Prepare edge label
                if show_labels:
                    label = attrs.get("name", edge_type)
                    if show_attributes:
                        attr_str = "\n".join([f"{k}: {v}" for k, v in attrs.items() 
                                             if k not in ["name", "type"] and v])
                        if attr_str:
                            label = f"{label}\n{attr_str}"
                else:
                    label = ""
                
                # Add edge to graph
                dot.edge(source, target, label=label, **style)
                edge_count += 1
        
        # Update statistics
        result["graph_stats"] = {
            "node_count": node_count,
            "edge_count": edge_count
        }
        
        result["path_stats"] = {
            "path_count": len(paths),
            "min_path_length": min(path_lengths) if path_lengths else 0,
            "max_path_length": max(path_lengths) if path_lengths else 0,
            "avg_path_length": sum(path_lengths) / len(path_lengths) if path_lengths else 0,
            "total_path_nodes": len(path_nodes),
            "total_path_edges": len(path_edges)
        }
        
        # Render the graph
        if base64_encode:
            # Render to a temporary file and read as base64
            with tempfile.NamedTemporaryFile(suffix=f".{output_format}") as tmp:
                dot.render(tmp.name, cleanup=True)
                with open(f"{tmp.name}.{output_format}", "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                os.remove(f"{tmp.name}.{output_format}")
                result["base64_data"] = encoded
        else:
            # Render to a file in the cache directory
            timestamp = int(time.time())
            output_file = os.path.join(CACHE_DIR, f"network_paths_{timestamp}")
            dot.render(output_file, cleanup=True)
            result["file_path"] = f"{output_file}.{output_format}"
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error rendering network paths: {str(e)}"
        }


@tool
def create_network_legend(
    resource_types: List[str] = None,
    connection_types: List[str] = None,
    boundary_types: List[str] = None,
    output_format: str = "png",
    title: str = "AWS Network Topology Legend",
    dpi: int = 300,
    base64_encode: bool = False
) -> Dict[str, Any]:
    """
    Create a legend for AWS network topology graphs.
    
    This tool creates a legend showing the visual representation of different
    AWS resource types, connection types, and boundary types used in the graphs.
    
    Args:
        resource_types: List of resource types to include in the legend (default: all)
        connection_types: List of connection types to include in the legend (default: all)
        boundary_types: List of boundary types to include in the legend (default: all)
        output_format: Output format (png, jpg, svg, pdf) (default: "png")
        title: Title for the legend (default: "AWS Network Topology Legend")
        dpi: DPI for raster formats (default: 300)
        base64_encode: Whether to return the legend as a base64-encoded string (default: False)
        
    Returns:
        Dictionary with legend creation results:
        {
            "status": "success" or "error",
            "format": output format,
            "file_path": path to the rendered file (if base64_encode is False),
            "base64_data": base64-encoded legend data (if base64_encode is True),
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "format": output_format
        }
        
        # Validate output format
        valid_formats = ["png", "jpg", "jpeg", "svg", "pdf", "dot"]
        if output_format not in valid_formats:
            return {
                "status": "error",
                "error": f"Invalid output format: {output_format}. Valid formats are: {', '.join(valid_formats)}"
            }
        
        # Normalize jpg to jpeg for graphviz
        if output_format == "jpg":
            output_format = "jpeg"
        
        # Create a new Graphviz graph for the legend
        dot = graphviz.Digraph(format=output_format, engine="dot")
        
        # Set graph attributes
        dot.attr(rankdir="LR", ranksep="0.5", nodesep="0.5")
        dot.attr(dpi=str(dpi))
        dot.attr(label=title, fontsize="20", fontname="Arial", labelloc="t")
        
        # Filter resource types if specified
        if not resource_types:
            resource_types = list(AWS_RESOURCE_STYLES.keys())
            # Remove default from the list
            if "default" in resource_types:
                resource_types.remove("default")
        
        # Filter connection types if specified
        if not connection_types:
            connection_types = list(AWS_CONNECTION_STYLES.keys())
            # Remove default from the list
            if "default" in connection_types:
                connection_types.remove("default")
        
        # Filter boundary types if specified
        if not boundary_types:
            boundary_types = list(BOUNDARY_STYLES.keys())
            # Remove default from the list
            if "default" in boundary_types:
                boundary_types.remove("default")
        
        # Create a subgraph for resource types
        with dot.subgraph(name="cluster_resources") as c:
            c.attr(label="Resource Types", style="rounded", color="#333333", fontsize="16")
            
            for i, resource_type in enumerate(resource_types):
                style = AWS_RESOURCE_STYLES.get(resource_type, AWS_RESOURCE_STYLES["default"]).copy()
                c.node(f"resource_{i}", label=resource_type, **style)
        
        # Create a subgraph for connection types
        with dot.subgraph(name="cluster_connections") as c:
            c.attr(label="Connection Types", style="rounded", color="#333333", fontsize="16")
            
            for i, connection_type in enumerate(connection_types):
                style = AWS_CONNECTION_STYLES.get(connection_type, AWS_CONNECTION_STYLES["default"]).copy()
                
                # Create two nodes and connect them to show the edge style
                c.node(f"conn_source_{i}", label="", shape="point", width="0.1", height="0.1")
                c.node(f"conn_target_{i}", label=connection_type, shape="plaintext")
                c.edge(f"conn_source_{i}", f"conn_target_{i}", **style)
        
        # Create a subgraph for boundary types
        with dot.subgraph(name="cluster_boundaries") as c:
            c.attr(label="Boundary Types", style="rounded", color="#333333", fontsize="16")
            
            for i, boundary_type in enumerate(boundary_types):
                style = BOUNDARY_STYLES.get(boundary_type, BOUNDARY_STYLES["default"]).copy()
                
                # Create a small cluster to show the boundary style
                with c.subgraph(name=f"cluster_boundary_{i}") as b:
                    b.attr(label=boundary_type, **style)
                    b.node(f"boundary_{i}", label="", shape="point", width="0.1", height="0.1")
        
        # Render the legend
        if base64_encode:
            # Render to a temporary file and read as base64
            with tempfile.NamedTemporaryFile(suffix=f".{output_format}") as tmp:
                dot.render(tmp.name, cleanup=True)
                with open(f"{tmp.name}.{output_format}", "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                os.remove(f"{tmp.name}.{output_format}")
                result["base64_data"] = encoded
        else:
            # Render to a file in the cache directory
            timestamp = int(time.time())
            output_file = os.path.join(CACHE_DIR, f"network_legend_{timestamp}")
            dot.render(output_file, cleanup=True)
            result["file_path"] = f"{output_file}.{output_format}"
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error creating network legend: {str(e)}"
        }

# Import missing module
import time