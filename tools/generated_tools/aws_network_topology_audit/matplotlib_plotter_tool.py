"""
AWS Network Topology Visualizer - Matplotlib Plotter Tool

This module provides tools for creating and customizing graph outputs using Matplotlib,
offering alternative visualization options to Graphviz.
"""

from typing import Dict, List, Optional, Any, Tuple, Set, Union
import os
import json
import logging
import tempfile
import base64
import io
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import networkx as nx
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

# AWS resource type to color mapping
AWS_RESOURCE_COLORS = {
    # VPC and networking
    "vpc": "#E78F24",
    "subnet": "#8DC348",
    "internet_gateway": "#3B82F6",
    "nat_gateway": "#3B82F6",
    "route_table": "#666666",
    "security_group": "#E53935",
    "network_acl": "#E53935",
    "transit_gateway": "#039BE5",
    "vpc_endpoint": "#43A047",
    
    # Compute
    "ec2_instance": "#FBC02D",
    "auto_scaling_group": "#FBC02D",
    "lambda_function": "#8E24AA",
    
    # Database
    "rds_instance": "#1976D2",
    "dynamodb_table": "#3F51B5",
    
    # Storage
    "s3_bucket": "#00ACC1",
    "ebs_volume": "#FB8C00",
    
    # Load balancing
    "elb": "#9C27B0",
    "alb": "#9C27B0",
    "nlb": "#9C27B0",
    
    # Default
    "default": "#9E9E9E"
}

# AWS connection type to color mapping
AWS_CONNECTION_COLORS = {
    "vpc_peering": "#4CAF50",
    "transit_gateway": "#2196F3",
    "vpc_endpoint": "#9C27B0",
    "internet_gateway": "#F44336",
    "nat_gateway": "#FF9800",
    "route_table": "#607D8B",
    "security_group": "#E91E63",
    "network_acl": "#9C27B0",
    "privatelink": "#673AB7",
    "direct_connect": "#00BCD4",
    "vpn": "#8BC34A",
    "cross_region": "#FF5722",
    "cross_account": "#795548",
    "default": "#9E9E9E"
}

# Boundary color mapping
BOUNDARY_COLORS = {
    "account": "#795548",
    "region": "#FF5722",
    "vpc": "#E78F24",
    "security": "#E53935",
    "default": "#9E9E9E"
}

@tool
def plot_network_graph(
    graph_json: Dict[str, Any],
    output_format: str = "png",
    layout_type: str = "spring",
    show_labels: bool = True,
    node_size: int = 300,
    font_size: int = 8,
    figsize: Tuple[int, int] = (12, 10),
    dpi: int = 300,
    custom_colors: Optional[Dict[str, str]] = None,
    highlight_nodes: Optional[List[str]] = None,
    highlight_edges: Optional[List[Tuple[str, str]]] = None,
    group_by: Optional[str] = None,
    title: Optional[str] = None,
    base64_encode: bool = False
) -> Dict[str, Any]:
    """
    Plot a NetworkX graph of AWS network resources using Matplotlib.
    
    This tool renders a graph representation of AWS network resources using Matplotlib,
    with specialized coloring for different resource and connection types.
    
    Args:
        graph_json: Serialized graph in JSON format (as returned by create_network_graph)
        output_format: Output format (png, jpg, svg, pdf) (default: "png")
        layout_type: Layout algorithm (spring, kamada_kawai, spectral, circular, shell) (default: "spring")
        show_labels: Whether to show node labels (default: True)
        node_size: Size of nodes (default: 300)
        font_size: Size of labels (default: 8)
        figsize: Figure size in inches (width, height) (default: (12, 10))
        dpi: DPI for raster formats (default: 300)
        custom_colors: Optional dictionary of custom colors for nodes and edges
        highlight_nodes: Optional list of node IDs to highlight
        highlight_edges: Optional list of edge tuples (source, target) to highlight
        group_by: Optional attribute to group nodes by (e.g., "region", "account_id", "vpc_id")
        title: Optional title for the graph
        base64_encode: Whether to return the graph as a base64-encoded string (default: False)
        
    Returns:
        Dictionary with plotting results:
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
        valid_formats = ["png", "jpg", "jpeg", "svg", "pdf"]
        if output_format not in valid_formats:
            return {
                "status": "error",
                "error": f"Invalid output format: {output_format}. Valid formats are: {', '.join(valid_formats)}"
            }
        
        # Validate layout type
        valid_layouts = ["spring", "kamada_kawai", "spectral", "circular", "shell", "random"]
        if layout_type not in valid_layouts:
            return {
                "status": "error",
                "error": f"Invalid layout type: {layout_type}. Valid layouts are: {', '.join(valid_layouts)}"
            }
        
        # Normalize jpg to jpeg for matplotlib
        if output_format == "jpg":
            output_format = "jpeg"
        
        # Create a NetworkX graph from the JSON
        directed = graph_json.get("directed", False)
        multigraph = graph_json.get("multigraph", False)
        
        if directed and multigraph:
            G = nx.MultiDiGraph()
        elif directed and not multigraph:
            G = nx.DiGraph()
        elif not directed and multigraph:
            G = nx.MultiGraph()
        else:
            G = nx.Graph()
        
        # Add graph-level attributes
        G.graph.update(graph_json.get("graph", {}))
        
        # Add nodes with attributes
        for node_id, attrs in graph_json.get("nodes", {}).items():
            G.add_node(node_id, **attrs)
        
        # Add edges with attributes
        for edge_id, attrs in graph_json.get("edges", {}).items():
            # Parse edge ID to get source and target
            if multigraph:
                try:
                    source, target, key = edge_id.split('_')
                    key = int(key)
                except ValueError:
                    logger.warning(f"Invalid edge ID format for multigraph: {edge_id}")
                    continue
                G.add_edge(source, target, key=key, **attrs)
            else:
                try:
                    source, target = edge_id.split('_')
                except ValueError:
                    logger.warning(f"Invalid edge ID format: {edge_id}")
                    continue
                G.add_edge(source, target, **attrs)
        
        # Handle empty graph case
        if G.number_of_nodes() == 0:
            return {
                "status": "error",
                "error": "Empty graph: no nodes were added"
            }
        
        # Create color lookup with custom colors if provided
        node_colors = dict(AWS_RESOURCE_COLORS)
        edge_colors = dict(AWS_CONNECTION_COLORS)
        
        if custom_colors:
            if "nodes" in custom_colors:
                for node_type, color in custom_colors["nodes"].items():
                    node_colors[node_type] = color
            
            if "edges" in custom_colors:
                for edge_type, color in custom_colors["edges"].items():
                    edge_colors[edge_type] = color
        
        # Create the figure and axis
        plt.figure(figsize=figsize, dpi=dpi)
        ax = plt.gca()
        
        # Compute layout
        if layout_type == "spring":
            pos = nx.spring_layout(G, k=0.3, iterations=50)
        elif layout_type == "kamada_kawai":
            pos = nx.kamada_kawai_layout(G)
        elif layout_type == "spectral":
            try:
                pos = nx.spectral_layout(G)
            except:
                # Fallback to spring layout if spectral fails
                pos = nx.spring_layout(G, k=0.3, iterations=50)
        elif layout_type == "circular":
            pos = nx.circular_layout(G)
        elif layout_type == "shell":
            # Group nodes by the specified attribute if provided
            if group_by and group_by in next(iter(G.nodes(data=True)))[1]:
                groups = {}
                for node, attrs in G.nodes(data=True):
                    group_val = attrs.get(group_by)
                    if group_val not in groups:
                        groups[group_val] = []
                    groups[group_val].append(node)
                shells = [groups[g] for g in sorted(groups.keys())]
                pos = nx.shell_layout(G, shells)
            else:
                pos = nx.shell_layout(G)
        else:  # random layout
            pos = nx.random_layout(G)
        
        # Prepare node colors and sizes
        node_color_list = []
        node_size_list = []
        
        for node in G.nodes():
            node_type = G.nodes[node].get("type", "default")
            color = node_colors.get(node_type, node_colors["default"])
            
            # Highlight node if requested
            if highlight_nodes and node in highlight_nodes:
                node_color_list.append("red")
                node_size_list.append(node_size * 1.5)
            else:
                node_color_list.append(color)
                node_size_list.append(node_size)
        
        # Prepare edge colors and widths
        edge_color_list = []
        edge_width_list = []
        
        for u, v, attrs in G.edges(data=True):
            edge_type = attrs.get("type", "default")
            color = edge_colors.get(edge_type, edge_colors["default"])
            
            # Highlight edge if requested
            if highlight_edges and (u, v) in highlight_edges:
                edge_color_list.append("red")
                edge_width_list.append(2.0)
            else:
                edge_color_list.append(color)
                edge_width_list.append(1.0)
        
        # Draw the graph
        nx.draw_networkx_nodes(G, pos, node_color=node_color_list, node_size=node_size_list, alpha=0.8)
        
        if directed:
            nx.draw_networkx_edges(G, pos, edge_color=edge_color_list, width=edge_width_list, alpha=0.7, arrowsize=10)
        else:
            nx.draw_networkx_edges(G, pos, edge_color=edge_color_list, width=edge_width_list, alpha=0.7)
        
        if show_labels:
            # Create labels using node names or IDs
            labels = {}
            for node in G.nodes():
                labels[node] = G.nodes[node].get("name", node)
            
            nx.draw_networkx_labels(G, pos, labels=labels, font_size=font_size, font_family="sans-serif")
        
        # Add title if provided
        if title:
            plt.title(title, fontsize=16)
        
        # Create legend for node types
        node_types = set(nx.get_node_attributes(G, "type").values())
        legend_elements = []
        
        for node_type in node_types:
            color = node_colors.get(node_type, node_colors["default"])
            legend_elements.append(mpatches.Patch(color=color, label=node_type))
        
        if legend_elements:
            plt.legend(handles=legend_elements, loc="best", fontsize=8)
        
        # Remove axis
        plt.axis("off")
        
        # Update graph statistics
        result["graph_stats"] = {
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "node_types": list(node_types),
            "layout": layout_type
        }
        
        # Save or encode the figure
        if base64_encode:
            buf = io.BytesIO()
            plt.savefig(buf, format=output_format, bbox_inches="tight")
            buf.seek(0)
            encoded = base64.b64encode(buf.read()).decode("utf-8")
            plt.close()
            result["base64_data"] = encoded
        else:
            timestamp = int(time.time())
            output_file = os.path.join(CACHE_DIR, f"network_graph_{timestamp}.{output_format}")
            plt.savefig(output_file, format=output_format, bbox_inches="tight")
            plt.close()
            result["file_path"] = output_file
        
        return result
        
    except Exception as e:
        plt.close()  # Ensure figure is closed on error
        return {
            "status": "error",
            "error": f"Error plotting network graph: {str(e)}"
        }


@tool
def plot_network_boundaries(
    graph_json: Dict[str, Any],
    boundaries_json: Dict[str, Any],
    output_format: str = "png",
    layout_type: str = "spring",
    show_labels: bool = True,
    node_size: int = 300,
    font_size: int = 8,
    figsize: Tuple[int, int] = (12, 10),
    dpi: int = 300,
    highlight_boundary_types: Optional[List[str]] = None,
    title: Optional[str] = None,
    base64_encode: bool = False
) -> Dict[str, Any]:
    """
    Plot a NetworkX graph with highlighted network boundaries using Matplotlib.
    
    This tool renders a graph representation of AWS network resources with highlighted
    boundaries such as account boundaries, region boundaries, and VPC boundaries.
    
    Args:
        graph_json: Serialized graph in JSON format (as returned by create_network_graph)
        boundaries_json: Boundaries information (as returned by identify_network_boundaries)
        output_format: Output format (png, jpg, svg, pdf) (default: "png")
        layout_type: Layout algorithm (spring, kamada_kawai, spectral, circular, shell) (default: "spring")
        show_labels: Whether to show node labels (default: True)
        node_size: Size of nodes (default: 300)
        font_size: Size of labels (default: 8)
        figsize: Figure size in inches (width, height) (default: (12, 10))
        dpi: DPI for raster formats (default: 300)
        highlight_boundary_types: Optional list of boundary types to highlight (e.g., ["account", "region"])
        title: Optional title for the graph
        base64_encode: Whether to return the graph as a base64-encoded string (default: False)
        
    Returns:
        Dictionary with plotting results:
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
        valid_formats = ["png", "jpg", "jpeg", "svg", "pdf"]
        if output_format not in valid_formats:
            return {
                "status": "error",
                "error": f"Invalid output format: {output_format}. Valid formats are: {', '.join(valid_formats)}"
            }
        
        # Validate layout type
        valid_layouts = ["spring", "kamada_kawai", "spectral", "circular", "shell", "random"]
        if layout_type not in valid_layouts:
            return {
                "status": "error",
                "error": f"Invalid layout type: {layout_type}. Valid layouts are: {', '.join(valid_layouts)}"
            }
        
        # Normalize jpg to jpeg for matplotlib
        if output_format == "jpg":
            output_format = "jpeg"
        
        # Create a NetworkX graph from the JSON
        directed = graph_json.get("directed", False)
        multigraph = graph_json.get("multigraph", False)
        
        if directed and multigraph:
            G = nx.MultiDiGraph()
        elif directed and not multigraph:
            G = nx.DiGraph()
        elif not directed and multigraph:
            G = nx.MultiGraph()
        else:
            G = nx.Graph()
        
        # Add graph-level attributes
        G.graph.update(graph_json.get("graph", {}))
        
        # Add nodes with attributes
        for node_id, attrs in graph_json.get("nodes", {}).items():
            G.add_node(node_id, **attrs)
        
        # Add edges with attributes
        for edge_id, attrs in graph_json.get("edges", {}).items():
            # Parse edge ID to get source and target
            if multigraph:
                try:
                    source, target, key = edge_id.split('_')
                    key = int(key)
                except ValueError:
                    logger.warning(f"Invalid edge ID format for multigraph: {edge_id}")
                    continue
                G.add_edge(source, target, key=key, **attrs)
            else:
                try:
                    source, target = edge_id.split('_')
                except ValueError:
                    logger.warning(f"Invalid edge ID format: {edge_id}")
                    continue
                G.add_edge(source, target, **attrs)
        
        # Handle empty graph case
        if G.number_of_nodes() == 0:
            return {
                "status": "error",
                "error": "Empty graph: no nodes were added"
            }
        
        # Filter boundary types if requested
        boundary_types = list(boundaries_json.get("boundaries", {}).keys())
        if highlight_boundary_types:
            boundary_types = [bt for bt in boundary_types if bt in highlight_boundary_types]
        
        # Create the figure and axis
        plt.figure(figsize=figsize, dpi=dpi)
        ax = plt.gca()
        
        # Compute layout
        if layout_type == "spring":
            pos = nx.spring_layout(G, k=0.3, iterations=50)
        elif layout_type == "kamada_kawai":
            pos = nx.kamada_kawai_layout(G)
        elif layout_type == "spectral":
            try:
                pos = nx.spectral_layout(G)
            except:
                # Fallback to spring layout if spectral fails
                pos = nx.spring_layout(G, k=0.3, iterations=50)
        elif layout_type == "circular":
            pos = nx.circular_layout(G)
        elif layout_type == "shell":
            pos = nx.shell_layout(G)
        else:  # random layout
            pos = nx.random_layout(G)
        
        # Track boundary nodes and crossings
        boundary_nodes = set()
        boundary_crossings = []
        boundary_counts = {}
        
        # Draw boundaries as convex hulls
        for boundary_type in boundary_types:
            boundaries = boundaries_json.get("boundaries", {}).get(boundary_type, [])
            boundary_counts[boundary_type] = len(boundaries)
            
            for i, boundary in enumerate(boundaries):
                boundary_id = boundary.get("id", f"{boundary_type}_{i}")
                boundary_name = boundary.get("name", boundary_id)
                
                # Get nodes in this boundary
                nodes = boundary.get("nodes", [])
                if not nodes:
                    continue
                
                boundary_nodes.update(nodes)
                
                # Get node positions
                node_positions = [pos[node] for node in nodes if node in pos]
                if not node_positions:
                    continue
                
                # Create convex hull
                points = np.array(node_positions)
                try:
                    from scipy.spatial import ConvexHull
                    hull = ConvexHull(points)
                    
                    # Draw convex hull
                    for simplex in hull.simplices:
                        ax.plot(points[simplex, 0], points[simplex, 1], 
                                color=BOUNDARY_COLORS.get(boundary_type, BOUNDARY_COLORS["default"]),
                                linestyle="--", linewidth=2, alpha=0.7)
                    
                    # Add boundary label
                    centroid = np.mean(points[hull.vertices], axis=0)
                    ax.text(centroid[0], centroid[1], boundary_name, 
                            fontsize=font_size+2, color=BOUNDARY_COLORS.get(boundary_type, BOUNDARY_COLORS["default"]),
                            ha="center", va="center", bbox=dict(facecolor="white", alpha=0.7, boxstyle="round,pad=0.3"))
                    
                except Exception as e:
                    logger.warning(f"Failed to create convex hull for boundary {boundary_id}: {str(e)}")
                    # Fallback: just draw a circle around the centroid
                    centroid = np.mean(points, axis=0)
                    radius = max([np.linalg.norm(p - centroid) for p in points]) * 1.1
                    circle = plt.Circle(centroid, radius, fill=False, 
                                       color=BOUNDARY_COLORS.get(boundary_type, BOUNDARY_COLORS["default"]),
                                       linestyle="--", linewidth=2, alpha=0.7)
                    ax.add_patch(circle)
                    ax.text(centroid[0], centroid[1], boundary_name, 
                            fontsize=font_size+2, color=BOUNDARY_COLORS.get(boundary_type, BOUNDARY_COLORS["default"]),
                            ha="center", va="center", bbox=dict(facecolor="white", alpha=0.7, boxstyle="round,pad=0.3"))
            
            # Get boundary crossings
            crossings = boundaries_json.get("boundary_crossings", {}).get(boundary_type, [])
            boundary_crossings.extend(crossings)
        
        # Prepare node colors and sizes
        node_color_list = []
        node_size_list = []
        
        for node in G.nodes():
            node_type = G.nodes[node].get("type", "default")
            color = AWS_RESOURCE_COLORS.get(node_type, AWS_RESOURCE_COLORS["default"])
            
            # Use darker color for boundary nodes
            if node in boundary_nodes:
                node_color_list.append(color)
                node_size_list.append(node_size)
            else:
                # Use lighter color for non-boundary nodes
                rgb = mcolors.hex2color(color)
                lighter_color = mcolors.rgb2hex([min(1.0, c * 1.5) for c in rgb])
                node_color_list.append(lighter_color)
                node_size_list.append(node_size * 0.8)
        
        # Prepare edge colors and widths
        edge_color_list = []
        edge_width_list = []
        
        for u, v, attrs in G.edges(data=True):
            edge_type = attrs.get("type", "default")
            color = AWS_CONNECTION_COLORS.get(edge_type, AWS_CONNECTION_COLORS["default"])
            
            # Check if this edge is a boundary crossing
            is_crossing = False
            for crossing in boundary_crossings:
                if crossing.get("source") == u and crossing.get("target") == v:
                    is_crossing = True
                    edge_color_list.append("red")
                    edge_width_list.append(2.0)
                    break
            
            if not is_crossing:
                edge_color_list.append(color)
                edge_width_list.append(1.0)
        
        # Draw the graph
        nx.draw_networkx_nodes(G, pos, node_color=node_color_list, node_size=node_size_list, alpha=0.8)
        
        if directed:
            nx.draw_networkx_edges(G, pos, edge_color=edge_color_list, width=edge_width_list, alpha=0.7, arrowsize=10)
        else:
            nx.draw_networkx_edges(G, pos, edge_color=edge_color_list, width=edge_width_list, alpha=0.7)
        
        if show_labels:
            # Create labels using node names or IDs
            labels = {}
            for node in G.nodes():
                labels[node] = G.nodes[node].get("name", node)
            
            nx.draw_networkx_labels(G, pos, labels=labels, font_size=font_size, font_family="sans-serif")
        
        # Add title if provided
        if title:
            plt.title(title, fontsize=16)
        
        # Create legend for boundary types
        legend_elements = []
        for boundary_type in boundary_types:
            color = BOUNDARY_COLORS.get(boundary_type, BOUNDARY_COLORS["default"])
            legend_elements.append(mpatches.Patch(color=color, alpha=0.5, label=f"{boundary_type} boundary"))
        
        # Add legend for boundary crossing
        legend_elements.append(mpatches.Patch(color="red", alpha=0.7, label="Boundary crossing"))
        
        if legend_elements:
            plt.legend(handles=legend_elements, loc="best", fontsize=8)
        
        # Remove axis
        plt.axis("off")
        
        # Update statistics
        result["graph_stats"] = {
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "layout": layout_type
        }
        
        result["boundary_stats"] = {
            "boundary_types": boundary_types,
            "boundary_counts": boundary_counts,
            "total_boundaries": sum(boundary_counts.values()),
            "boundary_crossings": len(boundary_crossings)
        }
        
        # Save or encode the figure
        if base64_encode:
            buf = io.BytesIO()
            plt.savefig(buf, format=output_format, bbox_inches="tight")
            buf.seek(0)
            encoded = base64.b64encode(buf.read()).decode("utf-8")
            plt.close()
            result["base64_data"] = encoded
        else:
            timestamp = int(time.time())
            output_file = os.path.join(CACHE_DIR, f"network_boundaries_{timestamp}.{output_format}")
            plt.savefig(output_file, format=output_format, bbox_inches="tight")
            plt.close()
            result["file_path"] = output_file
        
        return result
        
    except Exception as e:
        plt.close()  # Ensure figure is closed on error
        return {
            "status": "error",
            "error": f"Error plotting network boundaries: {str(e)}"
        }


@tool
def plot_network_paths(
    graph_json: Dict[str, Any],
    paths_json: Dict[str, Any],
    output_format: str = "png",
    layout_type: str = "spring",
    show_labels: bool = True,
    node_size: int = 300,
    font_size: int = 8,
    figsize: Tuple[int, int] = (12, 10),
    dpi: int = 300,
    path_colors: Optional[List[str]] = None,
    title: Optional[str] = None,
    base64_encode: bool = False
) -> Dict[str, Any]:
    """
    Plot network paths in an AWS network topology graph using Matplotlib.
    
    This tool renders network paths between source and target nodes in an AWS network
    topology graph, with options to use custom colors for different paths.
    
    Args:
        graph_json: Serialized graph in JSON format (as returned by create_network_graph)
        paths_json: Paths information (as returned by find_network_paths)
        output_format: Output format (png, jpg, svg, pdf) (default: "png")
        layout_type: Layout algorithm (spring, kamada_kawai, spectral, circular, shell) (default: "spring")
        show_labels: Whether to show node labels (default: True)
        node_size: Size of nodes (default: 300)
        font_size: Size of labels (default: 8)
        figsize: Figure size in inches (width, height) (default: (12, 10))
        dpi: DPI for raster formats (default: 300)
        path_colors: Optional list of colors to use for different paths
        title: Optional title for the graph
        base64_encode: Whether to return the graph as a base64-encoded string (default: False)
        
    Returns:
        Dictionary with plotting results:
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
        valid_formats = ["png", "jpg", "jpeg", "svg", "pdf"]
        if output_format not in valid_formats:
            return {
                "status": "error",
                "error": f"Invalid output format: {output_format}. Valid formats are: {', '.join(valid_formats)}"
            }
        
        # Validate layout type
        valid_layouts = ["spring", "kamada_kawai", "spectral", "circular", "shell", "random"]
        if layout_type not in valid_layouts:
            return {
                "status": "error",
                "error": f"Invalid layout type: {layout_type}. Valid layouts are: {', '.join(valid_layouts)}"
            }
        
        # Normalize jpg to jpeg for matplotlib
        if output_format == "jpg":
            output_format = "jpeg"
        
        # Create a NetworkX graph from the JSON
        directed = graph_json.get("directed", False)
        multigraph = graph_json.get("multigraph", False)
        
        if directed and multigraph:
            G = nx.MultiDiGraph()
        elif directed and not multigraph:
            G = nx.DiGraph()
        elif not directed and multigraph:
            G = nx.MultiGraph()
        else:
            G = nx.Graph()
        
        # Add graph-level attributes
        G.graph.update(graph_json.get("graph", {}))
        
        # Add nodes with attributes
        for node_id, attrs in graph_json.get("nodes", {}).items():
            G.add_node(node_id, **attrs)
        
        # Add edges with attributes
        for edge_id, attrs in graph_json.get("edges", {}).items():
            # Parse edge ID to get source and target
            if multigraph:
                try:
                    source, target, key = edge_id.split('_')
                    key = int(key)
                except ValueError:
                    logger.warning(f"Invalid edge ID format for multigraph: {edge_id}")
                    continue
                G.add_edge(source, target, key=key, **attrs)
            else:
                try:
                    source, target = edge_id.split('_')
                except ValueError:
                    logger.warning(f"Invalid edge ID format: {edge_id}")
                    continue
                G.add_edge(source, target, **attrs)
        
        # Handle empty graph case
        if G.number_of_nodes() == 0:
            return {
                "status": "error",
                "error": "Empty graph: no nodes were added"
            }
        
        # Set default path colors if not provided
        if not path_colors:
            path_colors = ["#E53935", "#1E88E5", "#43A047", "#FBC02D", "#8E24AA", "#00ACC1", "#F4511E", "#3949AB"]
        
        # Get paths from paths_json
        paths = paths_json.get("paths", [])
        
        # Create the figure and axis
        plt.figure(figsize=figsize, dpi=dpi)
        ax = plt.gca()
        
        # Compute layout
        if layout_type == "spring":
            pos = nx.spring_layout(G, k=0.3, iterations=50)
        elif layout_type == "kamada_kawai":
            pos = nx.kamada_kawai_layout(G)
        elif layout_type == "spectral":
            try:
                pos = nx.spectral_layout(G)
            except:
                # Fallback to spring layout if spectral fails
                pos = nx.spring_layout(G, k=0.3, iterations=50)
        elif layout_type == "circular":
            pos = nx.circular_layout(G)
        elif layout_type == "shell":
            pos = nx.shell_layout(G)
        else:  # random layout
            pos = nx.random_layout(G)
        
        # Track nodes and edges in paths
        path_nodes = set()
        path_edges = set()
        path_lengths = []
        
        # Draw all nodes and edges with faded style first
        nx.draw_networkx_nodes(G, pos, node_color="#CCCCCC", node_size=node_size*0.8, alpha=0.4)
        nx.draw_networkx_edges(G, pos, edge_color="#CCCCCC", width=0.5, alpha=0.3, style="dotted")
        
        # Draw paths
        for i, path in enumerate(paths):
            path_color = path_colors[i % len(path_colors)]
            path_nodes_list = path.get("nodes", [])
            path_length = path.get("length", len(path_nodes_list) - 1)
            path_lengths.append(path_length)
            
            # Add nodes in this path to the set
            path_nodes.update(path_nodes_list)
            
            # Add edges in this path to the set
            for j in range(len(path_nodes_list) - 1):
                source = path_nodes_list[j]
                target = path_nodes_list[j + 1]
                path_edges.add((source, target))
            
            # Draw path edges
            edge_list = [(path_nodes_list[j], path_nodes_list[j+1]) for j in range(len(path_nodes_list)-1)]
            nx.draw_networkx_edges(G, pos, edgelist=edge_list, edge_color=path_color, width=2.0, alpha=0.8)
            
            # Draw source and target nodes with special style
            source_node = path_nodes_list[0]
            target_node = path_nodes_list[-1]
            
            nx.draw_networkx_nodes(G, pos, nodelist=[source_node], node_color=path_color, 
                                  node_size=node_size*1.2, alpha=0.9, node_shape="s")  # square for source
            nx.draw_networkx_nodes(G, pos, nodelist=[target_node], node_color=path_color, 
                                  node_size=node_size*1.2, alpha=0.9, node_shape="^")  # triangle for target
            
            # Add path label
            if len(path_nodes_list) > 2:
                # Place label near the middle of the path
                middle_idx = len(path_nodes_list) // 2
                middle_node = path_nodes_list[middle_idx]
                middle_pos = pos[middle_node]
                
                plt.text(middle_pos[0], middle_pos[1] + 0.05, f"Path {i+1}", 
                         color=path_color, fontsize=font_size+2, ha="center", va="center",
                         bbox=dict(facecolor="white", alpha=0.7, boxstyle="round,pad=0.2"))
        
        # Draw path nodes (except source/target which are already drawn)
        path_nodes_to_draw = path_nodes - {p.get("nodes", [])[0] for p in paths if p.get("nodes")} - {p.get("nodes", [])[-1] for p in paths if p.get("nodes")}
        if path_nodes_to_draw:
            nx.draw_networkx_nodes(G, pos, nodelist=list(path_nodes_to_draw), 
                                  node_color="#666666", node_size=node_size, alpha=0.8)
        
        if show_labels:
            # Create labels using node names or IDs
            labels = {}
            for node in G.nodes():
                labels[node] = G.nodes[node].get("name", node)
            
            nx.draw_networkx_labels(G, pos, labels=labels, font_size=font_size, font_family="sans-serif")
        
        # Add title if provided
        if title:
            plt.title(title, fontsize=16)
        
        # Create legend for paths
        legend_elements = []
        for i in range(min(len(paths), len(path_colors))):
            color = path_colors[i % len(path_colors)]
            path = paths[i]
            source = path.get("source", "")
            target = path.get("target", "")
            length = path.get("length", 0)
            legend_elements.append(mpatches.Patch(color=color, alpha=0.7, 
                                                 label=f"Path {i+1}: {source} → {target} (length: {length})"))
        
        if legend_elements:
            plt.legend(handles=legend_elements, loc="best", fontsize=8)
        
        # Remove axis
        plt.axis("off")
        
        # Update statistics
        result["graph_stats"] = {
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "layout": layout_type
        }
        
        result["path_stats"] = {
            "path_count": len(paths),
            "min_path_length": min(path_lengths) if path_lengths else 0,
            "max_path_length": max(path_lengths) if path_lengths else 0,
            "avg_path_length": sum(path_lengths) / len(path_lengths) if path_lengths else 0,
            "total_path_nodes": len(path_nodes),
            "total_path_edges": len(path_edges)
        }
        
        # Save or encode the figure
        if base64_encode:
            buf = io.BytesIO()
            plt.savefig(buf, format=output_format, bbox_inches="tight")
            buf.seek(0)
            encoded = base64.b64encode(buf.read()).decode("utf-8")
            plt.close()
            result["base64_data"] = encoded
        else:
            timestamp = int(time.time())
            output_file = os.path.join(CACHE_DIR, f"network_paths_{timestamp}.{output_format}")
            plt.savefig(output_file, format=output_format, bbox_inches="tight")
            plt.close()
            result["file_path"] = output_file
        
        return result
        
    except Exception as e:
        plt.close()  # Ensure figure is closed on error
        return {
            "status": "error",
            "error": f"Error plotting network paths: {str(e)}"
        }


@tool
def create_network_dashboard(
    graph_json: Dict[str, Any],
    boundaries_json: Optional[Dict[str, Any]] = None,
    paths_json: Optional[Dict[str, Any]] = None,
    output_format: str = "png",
    figsize: Tuple[int, int] = (16, 12),
    dpi: int = 300,
    title: str = "AWS Network Topology Dashboard",
    base64_encode: bool = False
) -> Dict[str, Any]:
    """
    Create a comprehensive dashboard of AWS network topology visualizations.
    
    This tool creates a dashboard with multiple visualizations of an AWS network topology,
    including the main graph, boundaries, paths, and statistics.
    
    Args:
        graph_json: Serialized graph in JSON format (as returned by create_network_graph)
        boundaries_json: Optional boundaries information (as returned by identify_network_boundaries)
        paths_json: Optional paths information (as returned by find_network_paths)
        output_format: Output format (png, jpg, svg, pdf) (default: "png")
        figsize: Figure size in inches (width, height) (default: (16, 12))
        dpi: DPI for raster formats (default: 300)
        title: Title for the dashboard (default: "AWS Network Topology Dashboard")
        base64_encode: Whether to return the dashboard as a base64-encoded string (default: False)
        
    Returns:
        Dictionary with dashboard creation results:
        {
            "status": "success" or "error",
            "format": output format,
            "file_path": path to the rendered file (if base64_encode is False),
            "base64_data": base64-encoded dashboard data (if base64_encode is True),
            "dashboard_stats": statistics about the dashboard components,
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "format": output_format,
            "dashboard_stats": {}
        }
        
        # Validate output format
        valid_formats = ["png", "jpg", "jpeg", "svg", "pdf"]
        if output_format not in valid_formats:
            return {
                "status": "error",
                "error": f"Invalid output format: {output_format}. Valid formats are: {', '.join(valid_formats)}"
            }
        
        # Normalize jpg to jpeg for matplotlib
        if output_format == "jpg":
            output_format = "jpeg"
        
        # Create a NetworkX graph from the JSON
        directed = graph_json.get("directed", False)
        multigraph = graph_json.get("multigraph", False)
        
        if directed and multigraph:
            G = nx.MultiDiGraph()
        elif directed and not multigraph:
            G = nx.DiGraph()
        elif not directed and multigraph:
            G = nx.MultiGraph()
        else:
            G = nx.Graph()
        
        # Add graph-level attributes
        G.graph.update(graph_json.get("graph", {}))
        
        # Add nodes with attributes
        for node_id, attrs in graph_json.get("nodes", {}).items():
            G.add_node(node_id, **attrs)
        
        # Add edges with attributes
        for edge_id, attrs in graph_json.get("edges", {}).items():
            # Parse edge ID to get source and target
            if multigraph:
                try:
                    source, target, key = edge_id.split('_')
                    key = int(key)
                except ValueError:
                    logger.warning(f"Invalid edge ID format for multigraph: {edge_id}")
                    continue
                G.add_edge(source, target, key=key, **attrs)
            else:
                try:
                    source, target = edge_id.split('_')
                except ValueError:
                    logger.warning(f"Invalid edge ID format: {edge_id}")
                    continue
                G.add_edge(source, target, **attrs)
        
        # Handle empty graph case
        if G.number_of_nodes() == 0:
            return {
                "status": "error",
                "error": "Empty graph: no nodes were added"
            }
        
        # Determine dashboard layout based on available data
        has_boundaries = boundaries_json is not None and "boundaries" in boundaries_json
        has_paths = paths_json is not None and "paths" in paths_json and len(paths_json.get("paths", [])) > 0
        
        if has_boundaries and has_paths:
            # 2x2 grid: main graph, boundaries, paths, stats
            fig, axs = plt.subplots(2, 2, figsize=figsize, dpi=dpi)
            axs = axs.flatten()
        elif has_boundaries or has_paths:
            # 2x1 grid: main graph, boundaries/paths, stats (spanning bottom row)
            fig = plt.figure(figsize=figsize, dpi=dpi)
            gs = fig.add_gridspec(2, 2)
            axs = [
                fig.add_subplot(gs[0, 0]),  # Main graph
                fig.add_subplot(gs[0, 1]),  # Boundaries or paths
                fig.add_subplot(gs[1, :])   # Stats (spanning bottom row)
            ]
        else:
            # 1x2 grid: main graph, stats
            fig, axs = plt.subplots(1, 2, figsize=figsize, dpi=dpi)
        
        # Add dashboard title
        fig.suptitle(title, fontsize=20)
        
        # Compute layout for the graph
        pos = nx.spring_layout(G, k=0.3, iterations=50)
        
        # Plot main graph
        ax = axs[0]
        ax.set_title("Network Topology Graph", fontsize=14)
        
        # Prepare node colors
        node_colors = []
        for node in G.nodes():
            node_type = G.nodes[node].get("type", "default")
            color = AWS_RESOURCE_COLORS.get(node_type, AWS_RESOURCE_COLORS["default"])
            node_colors.append(color)
        
        # Prepare edge colors
        edge_colors = []
        for u, v, attrs in G.edges(data=True):
            edge_type = attrs.get("type", "default")
            color = AWS_CONNECTION_COLORS.get(edge_type, AWS_CONNECTION_COLORS["default"])
            edge_colors.append(color)
        
        # Draw the graph
        nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=200, alpha=0.8)
        
        if directed:
            nx.draw_networkx_edges(G, pos, ax=ax, edge_color=edge_colors, width=1.0, alpha=0.7, arrowsize=10)
        else:
            nx.draw_networkx_edges(G, pos, ax=ax, edge_color=edge_colors, width=1.0, alpha=0.7)
        
        # Create legend for node types
        node_types = set(nx.get_node_attributes(G, "type").values())
        legend_elements = []
        
        for node_type in node_types:
            color = AWS_RESOURCE_COLORS.get(node_type, AWS_RESOURCE_COLORS["default"])
            legend_elements.append(mpatches.Patch(color=color, label=node_type))
        
        if legend_elements:
            ax.legend(handles=legend_elements, loc="best", fontsize=8)
        
        ax.axis("off")
        
        # Plot boundaries if available
        if has_boundaries:
            ax = axs[1]
            ax.set_title("Network Boundaries", fontsize=14)
            
            # Filter boundary types (limit to 3 for clarity)
            boundary_types = list(boundaries_json.get("boundaries", {}).keys())[:3]
            
            # Draw boundaries as convex hulls
            for boundary_type in boundary_types:
                boundaries = boundaries_json.get("boundaries", {}).get(boundary_type, [])
                
                for i, boundary in enumerate(boundaries):
                    # Get nodes in this boundary
                    nodes = boundary.get("nodes", [])
                    if not nodes:
                        continue
                    
                    # Get node positions
                    node_positions = [pos[node] for node in nodes if node in pos]
                    if not node_positions:
                        continue
                    
                    # Create convex hull
                    points = np.array(node_positions)
                    try:
                        from scipy.spatial import ConvexHull
                        hull = ConvexHull(points)
                        
                        # Draw convex hull
                        for simplex in hull.simplices:
                            ax.plot(points[simplex, 0], points[simplex, 1], 
                                    color=BOUNDARY_COLORS.get(boundary_type, BOUNDARY_COLORS["default"]),
                                    linestyle="--", linewidth=2, alpha=0.7)
                        
                    except Exception as e:
                        logger.warning(f"Failed to create convex hull: {str(e)}")
                        # Fallback: just draw a circle around the centroid
                        centroid = np.mean(points, axis=0)
                        radius = max([np.linalg.norm(p - centroid) for p in points]) * 1.1
                        circle = plt.Circle(centroid, radius, fill=False, 
                                           color=BOUNDARY_COLORS.get(boundary_type, BOUNDARY_COLORS["default"]),
                                           linestyle="--", linewidth=2, alpha=0.7)
                        ax.add_patch(circle)
            
            # Draw nodes and edges
            nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=100, alpha=0.6)
            nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#CCCCCC", width=0.5, alpha=0.4)
            
            # Create legend for boundary types
            legend_elements = []
            for boundary_type in boundary_types:
                color = BOUNDARY_COLORS.get(boundary_type, BOUNDARY_COLORS["default"])
                legend_elements.append(mpatches.Patch(color=color, alpha=0.5, label=f"{boundary_type} boundary"))
            
            if legend_elements:
                ax.legend(handles=legend_elements, loc="best", fontsize=8)
            
            ax.axis("off")
        
        # Plot paths if available
        if has_paths:
            ax_idx = 1 if not has_boundaries else 2
            ax = axs[ax_idx]
            ax.set_title("Network Paths", fontsize=14)
            
            # Set path colors
            path_colors = ["#E53935", "#1E88E5", "#43A047", "#FBC02D", "#8E24AA"]
            
            # Get paths from paths_json (limit to 5 for clarity)
            paths = paths_json.get("paths", [])[:5]
            
            # Draw all nodes and edges with faded style first
            nx.draw_networkx_nodes(G, pos, ax=ax, node_color="#CCCCCC", node_size=100, alpha=0.4)
            nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#CCCCCC", width=0.5, alpha=0.3, style="dotted")
            
            # Draw paths
            for i, path in enumerate(paths):
                path_color = path_colors[i % len(path_colors)]
                path_nodes_list = path.get("nodes", [])
                
                # Draw path edges
                edge_list = [(path_nodes_list[j], path_nodes_list[j+1]) for j in range(len(path_nodes_list)-1)]
                nx.draw_networkx_edges(G, pos, ax=ax, edgelist=edge_list, edge_color=path_color, width=2.0, alpha=0.8)
                
                # Draw source and target nodes with special style
                source_node = path_nodes_list[0]
                target_node = path_nodes_list[-1]
                
                nx.draw_networkx_nodes(G, pos, ax=ax, nodelist=[source_node], node_color=path_color, 
                                      node_size=150, alpha=0.9, node_shape="s")  # square for source
                nx.draw_networkx_nodes(G, pos, ax=ax, nodelist=[target_node], node_color=path_color, 
                                      node_size=150, alpha=0.9, node_shape="^")  # triangle for target
            
            # Create legend for paths
            legend_elements = []
            for i, path in enumerate(paths):
                color = path_colors[i % len(path_colors)]
                source = path.get("source", "")
                target = path.get("target", "")
                length = path.get("length", 0)
                legend_elements.append(mpatches.Patch(color=color, alpha=0.7, 
                                                     label=f"Path {i+1}: {source[:5]}...→{target[:5]}... ({length})"))
            
            if legend_elements:
                ax.legend(handles=legend_elements, loc="best", fontsize=8)
            
            ax.axis("off")
        
        # Plot statistics
        ax_idx = 1 if not (has_boundaries or has_paths) else (2 if has_boundaries != has_paths else 3)
        ax = axs[ax_idx]
        ax.set_title("Network Statistics", fontsize=14)
        
        # Calculate statistics
        node_count = G.number_of_nodes()
        edge_count = G.number_of_edges()
        
        # Count node types
        node_type_counts = {}
        for node, attrs in G.nodes(data=True):
            node_type = attrs.get("type", "default")
            node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1
        
        # Count edge types
        edge_type_counts = {}
        for u, v, attrs in G.edges(data=True):
            edge_type = attrs.get("type", "default")
            edge_type_counts[edge_type] = edge_type_counts.get(edge_type, 0) + 1
        
        # Create bar charts for node types
        ax.axis("on")
        ax.grid(True, linestyle="--", alpha=0.7)
        
        # Plot node type distribution
        node_types = list(node_type_counts.keys())
        node_counts = [node_type_counts[nt] for nt in node_types]
        node_colors = [AWS_RESOURCE_COLORS.get(nt, AWS_RESOURCE_COLORS["default"]) for nt in node_types]
        
        y_pos = np.arange(len(node_types))
        ax.barh(y_pos, node_counts, color=node_colors, alpha=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(node_types)
        ax.set_xlabel("Count")
        ax.set_ylabel("Node Type")
        
        # Add count labels to bars
        for i, v in enumerate(node_counts):
            ax.text(v + 0.1, i, str(v), color="black", fontweight="bold", va="center")
        
        # Add summary text with additional statistics
        summary_text = f"Total Nodes: {node_count}\nTotal Edges: {edge_count}\n"
        
        if has_boundaries:
            boundary_counts = {bt: len(boundaries_json.get("boundaries", {}).get(bt, [])) 
                              for bt in boundaries_json.get("boundaries", {})}
            summary_text += f"\nBoundaries:\n"
            for bt, count in boundary_counts.items():
                summary_text += f"- {bt}: {count}\n"
        
        if has_paths:
            path_count = len(paths_json.get("paths", []))
            path_lengths = [p.get("length", 0) for p in paths_json.get("paths", [])]
            if path_lengths:
                avg_length = sum(path_lengths) / len(path_lengths)
                summary_text += f"\nPaths:\n- Count: {path_count}\n- Avg Length: {avg_length:.1f}"
        
        # Add text box with summary
        props = dict(boxstyle="round", facecolor="wheat", alpha=0.5)
        ax.text(0.05, 0.95, summary_text, transform=ax.transAxes, fontsize=10,
                verticalalignment="top", bbox=props)
        
        # Adjust layout
        plt.tight_layout(rect=[0, 0, 1, 0.95])  # Make room for the suptitle
        
        # Update statistics
        result["dashboard_stats"] = {
            "node_count": node_count,
            "edge_count": edge_count,
            "node_types": node_type_counts,
            "edge_types": edge_type_counts
        }
        
        if has_boundaries:
            result["dashboard_stats"]["boundaries"] = {
                bt: len(boundaries_json.get("boundaries", {}).get(bt, []))
                for bt in boundaries_json.get("boundaries", {})
            }
        
        if has_paths:
            result["dashboard_stats"]["paths"] = {
                "count": len(paths_json.get("paths", [])),
                "avg_length": sum(path_lengths) / len(path_lengths) if path_lengths else 0
            }
        
        # Save or encode the figure
        if base64_encode:
            buf = io.BytesIO()
            plt.savefig(buf, format=output_format, bbox_inches="tight")
            buf.seek(0)
            encoded = base64.b64encode(buf.read()).decode("utf-8")
            plt.close()
            result["base64_data"] = encoded
        else:
            timestamp = int(time.time())
            output_file = os.path.join(CACHE_DIR, f"network_dashboard_{timestamp}.{output_format}")
            plt.savefig(output_file, format=output_format, bbox_inches="tight")
            plt.close()
            result["file_path"] = output_file
        
        return result
        
    except Exception as e:
        plt.close()  # Ensure figure is closed on error
        return {
            "status": "error",
            "error": f"Error creating network dashboard: {str(e)}"
        }

# Import missing module
import time