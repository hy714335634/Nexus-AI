"""
AWS Network Topology Visualizer - NetworkX Graph Tool

This module provides tools for building and analyzing network topology graphs
using the NetworkX library, specialized for AWS network resources.
"""

from typing import Dict, List, Optional, Any, Tuple, Set, Union
import os
import json
import logging
import networkx as nx
from networkx.algorithms import community
from networkx.algorithms.components import connected_components
from networkx.algorithms.shortest_paths import shortest_path
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

@tool
def create_network_graph(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    directed: bool = True,
    multigraph: bool = False,
    graph_attrs: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a NetworkX graph from nodes and edges representing AWS network resources.
    
    This tool creates a graph representation of AWS network resources, where nodes
    represent resources like VPCs, subnets, and edges represent connections between them.
    
    Args:
        nodes: List of node dictionaries, each containing at least 'id' and 'type' keys
              and optionally other attributes like 'name', 'region', 'account_id', etc.
        edges: List of edge dictionaries, each containing at least 'source', 'target', and 'type' keys
               and optionally other attributes like 'name', 'state', etc.
        directed: Whether to create a directed graph (default: True)
        multigraph: Whether to allow multiple edges between the same nodes (default: False)
        graph_attrs: Optional dictionary of graph-level attributes
        
    Returns:
        Dictionary with graph information and statistics:
        {
            "status": "success" or "error",
            "graph_type": "directed" or "undirected" or "multidigraph" or "multigraph",
            "node_count": number of nodes,
            "edge_count": number of edges,
            "node_types": dictionary of node types and their counts,
            "edge_types": dictionary of edge types and their counts,
            "is_connected": whether the graph is connected,
            "components": number of connected components,
            "diameter": diameter of the graph (if connected),
            "average_degree": average degree of nodes,
            "density": graph density,
            "graph_json": serialized graph in JSON format,
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "graph_type": "",
            "node_count": 0,
            "edge_count": 0,
            "node_types": {},
            "edge_types": {},
            "is_connected": False,
            "components": 0,
            "diameter": 0,
            "average_degree": 0.0,
            "density": 0.0,
            "graph_json": {}
        }
        
        # Create the appropriate graph type
        if directed and multigraph:
            G = nx.MultiDiGraph()
            result["graph_type"] = "multidigraph"
        elif directed and not multigraph:
            G = nx.DiGraph()
            result["graph_type"] = "directed"
        elif not directed and multigraph:
            G = nx.MultiGraph()
            result["graph_type"] = "multigraph"
        else:
            G = nx.Graph()
            result["graph_type"] = "undirected"
        
        # Add graph-level attributes
        if graph_attrs:
            for key, value in graph_attrs.items():
                G.graph[key] = value
        
        # Add nodes with attributes
        for node in nodes:
            if 'id' not in node:
                logger.warning("Skipping node without id")
                continue
            
            node_id = node['id']
            node_attrs = {k: v for k, v in node.items() if k != 'id'}
            G.add_node(node_id, **node_attrs)
            
            # Count node types
            node_type = node.get('type', 'unknown')
            result["node_types"][node_type] = result["node_types"].get(node_type, 0) + 1
        
        # Add edges with attributes
        for edge in edges:
            if 'source' not in edge or 'target' not in edge:
                logger.warning("Skipping edge without source or target")
                continue
            
            source = edge['source']
            target = edge['target']
            edge_attrs = {k: v for k, v in edge.items() if k not in ['source', 'target']}
            
            if source in G and target in G:
                G.add_edge(source, target, **edge_attrs)
                
                # Count edge types
                edge_type = edge.get('type', 'unknown')
                result["edge_types"][edge_type] = result["edge_types"].get(edge_type, 0) + 1
            else:
                logger.warning(f"Skipping edge ({source}, {target}) because one or both nodes do not exist")
        
        # Calculate graph statistics
        result["node_count"] = G.number_of_nodes()
        result["edge_count"] = G.number_of_edges()
        
        # Handle empty graph case
        if result["node_count"] == 0:
            return {
                "status": "error",
                "error": "Empty graph: no nodes were added"
            }
        
        # Convert to undirected for some metrics
        if directed:
            G_undirected = G.to_undirected()
        else:
            G_undirected = G
        
        # Calculate connected components
        components = list(connected_components(G_undirected))
        result["components"] = len(components)
        result["is_connected"] = (result["components"] == 1)
        
        # Calculate diameter (only for connected graphs)
        if result["is_connected"]:
            try:
                result["diameter"] = nx.diameter(G_undirected)
            except nx.NetworkXError:
                result["diameter"] = 0
        
        # Calculate average degree
        degrees = [d for _, d in G.degree()]
        result["average_degree"] = sum(degrees) / len(degrees) if degrees else 0
        
        # Calculate density
        result["density"] = nx.density(G)
        
        # Serialize graph to JSON
        node_data = {n: {**G.nodes[n]} for n in G.nodes()}
        
        if multigraph:
            edge_data = {f"{u}_{v}_{k}": {**G.edges[u, v, k]} for u, v, k in G.edges}
        else:
            edge_data = {f"{u}_{v}": {**G.edges[u, v]} for u, v in G.edges}
        
        result["graph_json"] = {
            "directed": directed,
            "multigraph": multigraph,
            "graph": G.graph,
            "nodes": node_data,
            "edges": edge_data
        }
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error creating network graph: {str(e)}"
        }


@tool
def analyze_network_graph(
    graph_json: Dict[str, Any],
    analysis_types: List[str] = ["basic", "centrality", "communities", "paths"],
    node_filters: Optional[Dict[str, Any]] = None,
    edge_filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyze a NetworkX graph representing AWS network topology.
    
    This tool performs various analyses on a graph representing AWS network resources,
    including basic statistics, centrality measures, community detection, and path analysis.
    
    Args:
        graph_json: Serialized graph in JSON format (as returned by create_network_graph)
        analysis_types: List of analysis types to perform (default: ["basic", "centrality", "communities", "paths"])
                        - "basic": Basic graph statistics
                        - "centrality": Node centrality measures
                        - "communities": Community detection
                        - "paths": Path analysis between key nodes
        node_filters: Optional filters to apply to nodes before analysis
        edge_filters: Optional filters to apply to edges before analysis
        
    Returns:
        Dictionary with analysis results:
        {
            "status": "success" or "error",
            "graph_info": basic graph information,
            "basic_stats": basic graph statistics (if requested),
            "centrality": centrality measures (if requested),
            "communities": community detection results (if requested),
            "paths": path analysis results (if requested),
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "graph_info": {
                "node_count": 0,
                "edge_count": 0,
                "directed": False,
                "multigraph": False
            }
        }
        
        # Deserialize graph from JSON
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
            # Apply node filters if provided
            if node_filters:
                skip = False
                for key, value in node_filters.items():
                    if key in attrs and attrs[key] != value:
                        skip = True
                        break
                if skip:
                    continue
            
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
            else:
                try:
                    source, target = edge_id.split('_')
                except ValueError:
                    logger.warning(f"Invalid edge ID format: {edge_id}")
                    continue
            
            # Apply edge filters if provided
            if edge_filters:
                skip = False
                for key, value in edge_filters.items():
                    if key in attrs and attrs[key] != value:
                        skip = True
                        break
                if skip:
                    continue
            
            # Add edge
            if multigraph:
                G.add_edge(source, target, key=key, **attrs)
            else:
                G.add_edge(source, target, **attrs)
        
        # Update graph info
        result["graph_info"] = {
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "directed": directed,
            "multigraph": multigraph
        }
        
        # Handle empty graph case
        if G.number_of_nodes() == 0:
            return {
                "status": "error",
                "error": "Empty graph: no nodes were added after filtering"
            }
        
        # Convert to undirected for some metrics
        if directed:
            G_undirected = G.to_undirected()
        else:
            G_undirected = G
        
        # Perform requested analyses
        if "basic" in analysis_types:
            # Basic graph statistics
            components = list(connected_components(G_undirected))
            
            result["basic_stats"] = {
                "components": len(components),
                "is_connected": (len(components) == 1),
                "largest_component_size": len(max(components, key=len)) if components else 0,
                "average_degree": sum(dict(G.degree()).values()) / G.number_of_nodes(),
                "density": nx.density(G),
                "node_type_counts": {},
                "edge_type_counts": {}
            }
            
            # Count node types
            for node, attrs in G.nodes(data=True):
                node_type = attrs.get('type', 'unknown')
                result["basic_stats"]["node_type_counts"][node_type] = result["basic_stats"]["node_type_counts"].get(node_type, 0) + 1
            
            # Count edge types
            for u, v, attrs in G.edges(data=True):
                edge_type = attrs.get('type', 'unknown')
                result["basic_stats"]["edge_type_counts"][edge_type] = result["basic_stats"]["edge_type_counts"].get(edge_type, 0) + 1
        
        if "centrality" in analysis_types:
            # Centrality measures
            result["centrality"] = {
                "degree": {},
                "betweenness": {},
                "closeness": {},
                "eigenvector": {}
            }
            
            # Degree centrality
            degree_centrality = nx.degree_centrality(G)
            result["centrality"]["degree"] = {str(node): value for node, value in sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:10]}
            
            # Betweenness centrality
            try:
                betweenness_centrality = nx.betweenness_centrality(G)
                result["centrality"]["betweenness"] = {str(node): value for node, value in sorted(betweenness_centrality.items(), key=lambda x: x[1], reverse=True)[:10]}
            except Exception as e:
                logger.warning(f"Failed to calculate betweenness centrality: {str(e)}")
            
            # Closeness centrality
            try:
                closeness_centrality = nx.closeness_centrality(G)
                result["centrality"]["closeness"] = {str(node): value for node, value in sorted(closeness_centrality.items(), key=lambda x: x[1], reverse=True)[:10]}
            except Exception as e:
                logger.warning(f"Failed to calculate closeness centrality: {str(e)}")
            
            # Eigenvector centrality
            try:
                eigenvector_centrality = nx.eigenvector_centrality(G, max_iter=1000)
                result["centrality"]["eigenvector"] = {str(node): value for node, value in sorted(eigenvector_centrality.items(), key=lambda x: x[1], reverse=True)[:10]}
            except Exception as e:
                logger.warning(f"Failed to calculate eigenvector centrality: {str(e)}")
        
        if "communities" in analysis_types:
            # Community detection
            result["communities"] = {
                "louvain": [],
                "label_propagation": []
            }
            
            # Louvain method
            try:
                louvain_communities = community.louvain_communities(G_undirected)
                result["communities"]["louvain"] = [list(comm) for comm in louvain_communities]
            except Exception as e:
                logger.warning(f"Failed to detect Louvain communities: {str(e)}")
            
            # Label propagation
            try:
                label_propagation_communities = community.label_propagation_communities(G_undirected)
                result["communities"]["label_propagation"] = [list(comm) for comm in label_propagation_communities]
            except Exception as e:
                logger.warning(f"Failed to detect label propagation communities: {str(e)}")
        
        if "paths" in analysis_types:
            # Path analysis
            result["paths"] = {
                "critical_nodes": [],
                "critical_edges": [],
                "cross_region_paths": [],
                "cross_account_paths": []
            }
            
            # Find critical nodes (articulation points)
            try:
                critical_nodes = list(nx.articulation_points(G_undirected))
                result["paths"]["critical_nodes"] = critical_nodes
            except Exception as e:
                logger.warning(f"Failed to find articulation points: {str(e)}")
            
            # Find critical edges (bridges)
            try:
                critical_edges = list(nx.bridges(G_undirected))
                result["paths"]["critical_edges"] = [{"source": u, "target": v} for u, v in critical_edges]
            except Exception as e:
                logger.warning(f"Failed to find bridges: {str(e)}")
            
            # Find cross-region paths
            try:
                nodes_by_region = {}
                for node, attrs in G.nodes(data=True):
                    region = attrs.get('region')
                    if region:
                        if region not in nodes_by_region:
                            nodes_by_region[region] = []
                        nodes_by_region[region].append(node)
                
                cross_region_paths = []
                regions = list(nodes_by_region.keys())
                for i in range(len(regions)):
                    for j in range(i + 1, len(regions)):
                        region1 = regions[i]
                        region2 = regions[j]
                        
                        # Sample nodes from each region
                        source_nodes = nodes_by_region[region1][:min(3, len(nodes_by_region[region1]))]
                        target_nodes = nodes_by_region[region2][:min(3, len(nodes_by_region[region2]))]
                        
                        for source in source_nodes:
                            for target in target_nodes:
                                try:
                                    path = shortest_path(G_undirected, source, target)
                                    if len(path) > 1:
                                        cross_region_paths.append({
                                            "source": source,
                                            "source_region": region1,
                                            "target": target,
                                            "target_region": region2,
                                            "path": path,
                                            "path_length": len(path) - 1
                                        })
                                except nx.NetworkXNoPath:
                                    pass
                
                result["paths"]["cross_region_paths"] = cross_region_paths[:10]  # Limit to 10 paths
            except Exception as e:
                logger.warning(f"Failed to find cross-region paths: {str(e)}")
            
            # Find cross-account paths
            try:
                nodes_by_account = {}
                for node, attrs in G.nodes(data=True):
                    account_id = attrs.get('account_id')
                    if account_id:
                        if account_id not in nodes_by_account:
                            nodes_by_account[account_id] = []
                        nodes_by_account[account_id].append(node)
                
                cross_account_paths = []
                accounts = list(nodes_by_account.keys())
                for i in range(len(accounts)):
                    for j in range(i + 1, len(accounts)):
                        account1 = accounts[i]
                        account2 = accounts[j]
                        
                        # Sample nodes from each account
                        source_nodes = nodes_by_account[account1][:min(3, len(nodes_by_account[account1]))]
                        target_nodes = nodes_by_account[account2][:min(3, len(nodes_by_account[account2]))]
                        
                        for source in source_nodes:
                            for target in target_nodes:
                                try:
                                    path = shortest_path(G_undirected, source, target)
                                    if len(path) > 1:
                                        cross_account_paths.append({
                                            "source": source,
                                            "source_account": account1,
                                            "target": target,
                                            "target_account": account2,
                                            "path": path,
                                            "path_length": len(path) - 1
                                        })
                                except nx.NetworkXNoPath:
                                    pass
                
                result["paths"]["cross_account_paths"] = cross_account_paths[:10]  # Limit to 10 paths
            except Exception as e:
                logger.warning(f"Failed to find cross-account paths: {str(e)}")
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error analyzing network graph: {str(e)}"
        }


@tool
def identify_network_boundaries(
    graph_json: Dict[str, Any],
    boundary_types: List[str] = ["account", "region", "vpc", "security"],
    include_nodes: bool = True,
    include_edges: bool = True
) -> Dict[str, Any]:
    """
    Identify and highlight network boundaries in an AWS network topology graph.
    
    This tool identifies different types of network boundaries in an AWS network topology,
    such as account boundaries, region boundaries, VPC boundaries, and security boundaries.
    
    Args:
        graph_json: Serialized graph in JSON format (as returned by create_network_graph)
        boundary_types: List of boundary types to identify (default: ["account", "region", "vpc", "security"])
        include_nodes: Whether to include nodes in the boundary definitions (default: True)
        include_edges: Whether to include edges in the boundary definitions (default: True)
        
    Returns:
        Dictionary with boundary identification results:
        {
            "status": "success" or "error",
            "boundaries": {
                "account": list of account boundaries,
                "region": list of region boundaries,
                "vpc": list of VPC boundaries,
                "security": list of security boundaries
            },
            "boundary_crossings": {
                "account": list of account boundary crossings,
                "region": list of region boundary crossings,
                "vpc": list of VPC boundary crossings,
                "security": list of security boundary crossings
            },
            "boundary_stats": statistics about boundaries and crossings,
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "boundaries": {},
            "boundary_crossings": {},
            "boundary_stats": {}
        }
        
        # Deserialize graph from JSON
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
        
        # Initialize boundary containers
        for boundary_type in boundary_types:
            result["boundaries"][boundary_type] = []
            result["boundary_crossings"][boundary_type] = []
        
        # Identify account boundaries
        if "account" in boundary_types:
            account_nodes = {}
            for node, attrs in G.nodes(data=True):
                account_id = attrs.get('account_id')
                if account_id:
                    if account_id not in account_nodes:
                        account_nodes[account_id] = []
                    account_nodes[account_id].append(node)
            
            # Create account boundaries
            for account_id, nodes in account_nodes.items():
                boundary = {
                    "type": "account",
                    "id": account_id,
                    "name": account_id,  # Could be enhanced with account alias if available
                }
                
                if include_nodes:
                    boundary["nodes"] = nodes
                
                if include_edges:
                    # Find edges within this account
                    internal_edges = []
                    for u, v, attrs in G.edges(data=True):
                        if u in nodes and v in nodes:
                            if multigraph:
                                for k in G[u][v]:
                                    internal_edges.append((u, v, k))
                            else:
                                internal_edges.append((u, v))
                    boundary["edges"] = internal_edges
                
                result["boundaries"]["account"].append(boundary)
            
            # Identify account boundary crossings
            account_crossings = []
            for u, v, attrs in G.edges(data=True):
                u_account = G.nodes[u].get('account_id')
                v_account = G.nodes[v].get('account_id')
                
                if u_account and v_account and u_account != v_account:
                    crossing = {
                        "type": "account",
                        "source": u,
                        "target": v,
                        "source_account": u_account,
                        "target_account": v_account,
                        "connection_type": attrs.get('type', 'unknown')
                    }
                    account_crossings.append(crossing)
            
            result["boundary_crossings"]["account"] = account_crossings
        
        # Identify region boundaries
        if "region" in boundary_types:
            region_nodes = {}
            for node, attrs in G.nodes(data=True):
                region = attrs.get('region')
                if region:
                    if region not in region_nodes:
                        region_nodes[region] = []
                    region_nodes[region].append(node)
            
            # Create region boundaries
            for region, nodes in region_nodes.items():
                boundary = {
                    "type": "region",
                    "id": region,
                    "name": region,
                }
                
                if include_nodes:
                    boundary["nodes"] = nodes
                
                if include_edges:
                    # Find edges within this region
                    internal_edges = []
                    for u, v, attrs in G.edges(data=True):
                        if u in nodes and v in nodes:
                            if multigraph:
                                for k in G[u][v]:
                                    internal_edges.append((u, v, k))
                            else:
                                internal_edges.append((u, v))
                    boundary["edges"] = internal_edges
                
                result["boundaries"]["region"].append(boundary)
            
            # Identify region boundary crossings
            region_crossings = []
            for u, v, attrs in G.edges(data=True):
                u_region = G.nodes[u].get('region')
                v_region = G.nodes[v].get('region')
                
                if u_region and v_region and u_region != v_region:
                    crossing = {
                        "type": "region",
                        "source": u,
                        "target": v,
                        "source_region": u_region,
                        "target_region": v_region,
                        "connection_type": attrs.get('type', 'unknown')
                    }
                    region_crossings.append(crossing)
            
            result["boundary_crossings"]["region"] = region_crossings
        
        # Identify VPC boundaries
        if "vpc" in boundary_types:
            vpc_nodes = {}
            for node, attrs in G.nodes(data=True):
                vpc_id = attrs.get('vpc_id')
                if vpc_id:
                    if vpc_id not in vpc_nodes:
                        vpc_nodes[vpc_id] = []
                    vpc_nodes[vpc_id].append(node)
            
            # Create VPC boundaries
            for vpc_id, nodes in vpc_nodes.items():
                boundary = {
                    "type": "vpc",
                    "id": vpc_id,
                    "name": vpc_id,  # Could be enhanced with VPC name from tags if available
                }
                
                if include_nodes:
                    boundary["nodes"] = nodes
                
                if include_edges:
                    # Find edges within this VPC
                    internal_edges = []
                    for u, v, attrs in G.edges(data=True):
                        if u in nodes and v in nodes:
                            if multigraph:
                                for k in G[u][v]:
                                    internal_edges.append((u, v, k))
                            else:
                                internal_edges.append((u, v))
                    boundary["edges"] = internal_edges
                
                result["boundaries"]["vpc"].append(boundary)
            
            # Identify VPC boundary crossings
            vpc_crossings = []
            for u, v, attrs in G.edges(data=True):
                u_vpc = G.nodes[u].get('vpc_id')
                v_vpc = G.nodes[v].get('vpc_id')
                
                if u_vpc and v_vpc and u_vpc != v_vpc:
                    crossing = {
                        "type": "vpc",
                        "source": u,
                        "target": v,
                        "source_vpc": u_vpc,
                        "target_vpc": v_vpc,
                        "connection_type": attrs.get('type', 'unknown')
                    }
                    vpc_crossings.append(crossing)
            
            result["boundary_crossings"]["vpc"] = vpc_crossings
        
        # Identify security boundaries
        if "security" in boundary_types:
            # Security boundaries based on security groups and network ACLs
            security_boundaries = []
            security_crossings = []
            
            # Find nodes with security groups
            sg_nodes = {}
            for node, attrs in G.nodes(data=True):
                security_groups = attrs.get('security_groups', [])
                if security_groups:
                    for sg in security_groups:
                        if sg not in sg_nodes:
                            sg_nodes[sg] = []
                        sg_nodes[sg].append(node)
            
            # Create security group boundaries
            for sg_id, nodes in sg_nodes.items():
                boundary = {
                    "type": "security",
                    "subtype": "security_group",
                    "id": sg_id,
                    "name": sg_id,  # Could be enhanced with security group name if available
                }
                
                if include_nodes:
                    boundary["nodes"] = nodes
                
                if include_edges:
                    # Find edges within this security group
                    internal_edges = []
                    for u, v, attrs in G.edges(data=True):
                        if u in nodes and v in nodes:
                            if multigraph:
                                for k in G[u][v]:
                                    internal_edges.append((u, v, k))
                            else:
                                internal_edges.append((u, v))
                    boundary["edges"] = internal_edges
                
                security_boundaries.append(boundary)
            
            # Find network firewall boundaries
            firewall_edges = []
            for u, v, attrs in G.edges(data=True):
                if attrs.get('type') == 'network_firewall':
                    firewall_edges.append((u, v))
                    
                    # Add to security crossings
                    crossing = {
                        "type": "security",
                        "subtype": "network_firewall",
                        "source": u,
                        "target": v,
                        "firewall_id": attrs.get('firewall_id', 'unknown')
                    }
                    security_crossings.append(crossing)
            
            # Add network firewall boundaries
            if firewall_edges:
                boundary = {
                    "type": "security",
                    "subtype": "network_firewall",
                    "id": "network_firewalls",
                    "name": "Network Firewalls",
                }
                
                if include_edges:
                    boundary["edges"] = firewall_edges
                
                security_boundaries.append(boundary)
            
            result["boundaries"]["security"] = security_boundaries
            result["boundary_crossings"]["security"] = security_crossings
        
        # Calculate boundary statistics
        boundary_stats = {}
        for boundary_type in boundary_types:
            boundary_stats[boundary_type] = {
                "count": len(result["boundaries"].get(boundary_type, [])),
                "crossing_count": len(result["boundary_crossings"].get(boundary_type, [])),
                "avg_nodes_per_boundary": 0,
                "avg_edges_per_boundary": 0
            }
            
            # Calculate average nodes and edges per boundary
            if boundary_stats[boundary_type]["count"] > 0:
                total_nodes = sum(len(b.get("nodes", [])) for b in result["boundaries"].get(boundary_type, []))
                total_edges = sum(len(b.get("edges", [])) for b in result["boundaries"].get(boundary_type, []))
                
                boundary_stats[boundary_type]["avg_nodes_per_boundary"] = total_nodes / boundary_stats[boundary_type]["count"]
                boundary_stats[boundary_type]["avg_edges_per_boundary"] = total_edges / boundary_stats[boundary_type]["count"]
        
        result["boundary_stats"] = boundary_stats
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error identifying network boundaries: {str(e)}"
        }


@tool
def find_network_paths(
    graph_json: Dict[str, Any],
    source_filters: Dict[str, Any],
    target_filters: Dict[str, Any],
    path_type: str = "shortest",
    max_paths: int = 5,
    max_path_length: Optional[int] = None,
    include_node_details: bool = True
) -> Dict[str, Any]:
    """
    Find network paths between source and target nodes in an AWS network topology.
    
    This tool finds paths between source and target nodes matching specified filters,
    which is useful for analyzing connectivity and identifying potential security issues.
    
    Args:
        graph_json: Serialized graph in JSON format (as returned by create_network_graph)
        source_filters: Filters to identify source nodes (e.g., {"type": "internet_gateway"})
        target_filters: Filters to identify target nodes (e.g., {"type": "rds_instance"})
        path_type: Type of path to find (default: "shortest")
                   - "shortest": Find shortest paths
                   - "all": Find all simple paths
                   - "disjoint": Find edge-disjoint paths
        max_paths: Maximum number of paths to return (default: 5)
        max_path_length: Maximum path length to consider (default: None, no limit)
        include_node_details: Whether to include node details in the results (default: True)
        
    Returns:
        Dictionary with path finding results:
        {
            "status": "success" or "error",
            "source_nodes": list of source nodes matching filters,
            "target_nodes": list of target nodes matching filters,
            "paths": list of found paths,
            "path_count": number of paths found,
            "path_stats": statistics about the found paths,
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "source_nodes": [],
            "target_nodes": [],
            "paths": [],
            "path_count": 0,
            "path_stats": {}
        }
        
        # Deserialize graph from JSON
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
        
        # Find source nodes matching filters
        source_nodes = []
        for node, attrs in G.nodes(data=True):
            match = True
            for key, value in source_filters.items():
                if key not in attrs or attrs[key] != value:
                    match = False
                    break
            if match:
                source_nodes.append(node)
        
        # Find target nodes matching filters
        target_nodes = []
        for node, attrs in G.nodes(data=True):
            match = True
            for key, value in target_filters.items():
                if key not in attrs or attrs[key] != value:
                    match = False
                    break
            if match:
                target_nodes.append(node)
        
        result["source_nodes"] = source_nodes
        result["target_nodes"] = target_nodes
        
        # Check if we found any source and target nodes
        if not source_nodes:
            return {
                "status": "error",
                "error": "No source nodes found matching the specified filters"
            }
        
        if not target_nodes:
            return {
                "status": "error",
                "error": "No target nodes found matching the specified filters"
            }
        
        # Find paths between source and target nodes
        paths = []
        path_lengths = []
        
        # For undirected graphs, we need to convert to undirected for some algorithms
        if directed and path_type in ["all", "disjoint"]:
            G_undirected = G.to_undirected()
        else:
            G_undirected = G
        
        # Limit the number of source-target pairs to avoid excessive computation
        source_sample = source_nodes[:min(5, len(source_nodes))]
        target_sample = target_nodes[:min(5, len(target_nodes))]
        
        for source in source_sample:
            for target in target_sample:
                if source == target:
                    continue
                
                try:
                    if path_type == "shortest":
                        # Find shortest path
                        path = nx.shortest_path(G, source, target)
                        if max_path_length is None or len(path) - 1 <= max_path_length:
                            path_data = {
                                "source": source,
                                "target": target,
                                "nodes": path,
                                "length": len(path) - 1,
                                "edges": [(path[i], path[i+1]) for i in range(len(path)-1)]
                            }
                            
                            if include_node_details:
                                path_data["node_details"] = {node: G.nodes[node] for node in path}
                                path_data["edge_details"] = {f"{u}_{v}": G.edges[u, v] for u, v in path_data["edges"]}
                            
                            paths.append(path_data)
                            path_lengths.append(len(path) - 1)
                    
                    elif path_type == "all":
                        # Find all simple paths
                        cutoff = max_path_length if max_path_length is not None else None
                        all_paths = list(nx.all_simple_paths(G, source, target, cutoff=cutoff))
                        
                        for path in all_paths[:max_paths]:
                            path_data = {
                                "source": source,
                                "target": target,
                                "nodes": path,
                                "length": len(path) - 1,
                                "edges": [(path[i], path[i+1]) for i in range(len(path)-1)]
                            }
                            
                            if include_node_details:
                                path_data["node_details"] = {node: G.nodes[node] for node in path}
                                path_data["edge_details"] = {f"{u}_{v}": G.edges[u, v] for u, v in path_data["edges"]}
                            
                            paths.append(path_data)
                            path_lengths.append(len(path) - 1)
                    
                    elif path_type == "disjoint":
                        # Find edge-disjoint paths
                        try:
                            disjoint_paths = list(nx.edge_disjoint_paths(G_undirected, source, target))
                            
                            for path in disjoint_paths[:max_paths]:
                                if max_path_length is None or len(path) - 1 <= max_path_length:
                                    path_data = {
                                        "source": source,
                                        "target": target,
                                        "nodes": path,
                                        "length": len(path) - 1,
                                        "edges": [(path[i], path[i+1]) for i in range(len(path)-1)]
                                    }
                                    
                                    if include_node_details:
                                        path_data["node_details"] = {node: G.nodes[node] for node in path}
                                        path_data["edge_details"] = {f"{u}_{v}": G.edges[u, v] for u, v in path_data["edges"]}
                                    
                                    paths.append(path_data)
                                    path_lengths.append(len(path) - 1)
                        except nx.NetworkXError:
                            # Some algorithms may not work with certain graph types
                            logger.warning(f"Could not find disjoint paths between {source} and {target}")
                
                except nx.NetworkXNoPath:
                    # No path exists between these nodes
                    continue
                
                # Limit the total number of paths
                if len(paths) >= max_paths:
                    break
            
            if len(paths) >= max_paths:
                break
        
        # Sort paths by length
        paths.sort(key=lambda x: x["length"])
        
        # Limit to max_paths
        paths = paths[:max_paths]
        
        result["paths"] = paths
        result["path_count"] = len(paths)
        
        # Calculate path statistics
        if path_lengths:
            result["path_stats"] = {
                "min_length": min(path_lengths),
                "max_length": max(path_lengths),
                "avg_length": sum(path_lengths) / len(path_lengths),
                "total_unique_nodes": len(set(node for path in paths for node in path["nodes"])),
                "total_unique_edges": len(set((u, v) for path in paths for u, v in path["edges"]))
            }
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error finding network paths: {str(e)}"
        }