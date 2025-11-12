"""
AWS Network Topology Visualizer - File Manager Tool

This module provides tools for managing file input/output operations,
including saving and loading network topology graphs and related data.
"""

from typing import Dict, List, Optional, Any, Tuple, Set, Union, BinaryIO
import os
import json
import logging
import tempfile
import base64
import pickle
import csv
import yaml
import time
from datetime import datetime
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
def save_network_graph(
    graph_json: Dict[str, Any],
    file_path: Optional[str] = None,
    file_format: str = "json",
    include_metadata: bool = True,
    pretty_print: bool = True,
    compress: bool = False
) -> Dict[str, Any]:
    """
    Save a network graph to a file in various formats.
    
    This tool saves a network graph to a file in JSON, YAML, or pickle format,
    with options to include metadata, pretty-print, and compress the output.
    
    Args:
        graph_json: Serialized graph in JSON format (as returned by create_network_graph)
        file_path: Path to save the file. If None, a default path in the cache directory is used.
        file_format: Format to save the file in (json, yaml, pickle) (default: "json")
        include_metadata: Whether to include metadata like timestamp and version (default: True)
        pretty_print: Whether to pretty-print JSON and YAML output (default: True)
        compress: Whether to compress the output file (default: False)
        
    Returns:
        Dictionary with save results:
        {
            "status": "success" or "error",
            "file_path": path to the saved file,
            "file_format": format of the saved file,
            "file_size": size of the saved file in bytes,
            "metadata": metadata included in the file (if any),
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "file_format": file_format
        }
        
        # Validate file format
        valid_formats = ["json", "yaml", "pickle"]
        if file_format not in valid_formats:
            return {
                "status": "error",
                "error": f"Invalid file format: {file_format}. Valid formats are: {', '.join(valid_formats)}"
            }
        
        # Generate default file path if not provided
        if not file_path:
            timestamp = int(time.time())
            file_path = os.path.join(CACHE_DIR, f"network_graph_{timestamp}.{file_format}")
            if compress:
                file_path += ".gz"
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # Add metadata if requested
        data_to_save = graph_json.copy()
        metadata = {}
        
        if include_metadata:
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "version": "1.0",
                "node_count": len(graph_json.get("nodes", {})),
                "edge_count": len(graph_json.get("edges", {})),
                "directed": graph_json.get("directed", False),
                "multigraph": graph_json.get("multigraph", False)
            }
            data_to_save["metadata"] = metadata
        
        # Save the file in the requested format
        if compress:
            import gzip
            
            if file_format == "json":
                with gzip.open(file_path, 'wt', encoding='utf-8') as f:
                    if pretty_print:
                        json.dump(data_to_save, f, indent=2, sort_keys=True)
                    else:
                        json.dump(data_to_save, f)
            
            elif file_format == "yaml":
                with gzip.open(file_path, 'wt', encoding='utf-8') as f:
                    yaml.dump(data_to_save, f, default_flow_style=not pretty_print)
            
            elif file_format == "pickle":
                with gzip.open(file_path, 'wb') as f:
                    pickle.dump(data_to_save, f)
        
        else:
            if file_format == "json":
                with open(file_path, 'w', encoding='utf-8') as f:
                    if pretty_print:
                        json.dump(data_to_save, f, indent=2, sort_keys=True)
                    else:
                        json.dump(data_to_save, f)
            
            elif file_format == "yaml":
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(data_to_save, f, default_flow_style=not pretty_print)
            
            elif file_format == "pickle":
                with open(file_path, 'wb') as f:
                    pickle.dump(data_to_save, f)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Update result
        result.update({
            "file_path": file_path,
            "file_size": file_size,
            "metadata": metadata
        })
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error saving network graph: {str(e)}"
        }


@tool
def load_network_graph(
    file_path: str,
    file_format: Optional[str] = None,
    validate: bool = True
) -> Dict[str, Any]:
    """
    Load a network graph from a file.
    
    This tool loads a network graph from a file in JSON, YAML, or pickle format,
    with options to automatically detect the format and validate the loaded data.
    
    Args:
        file_path: Path to the file to load
        file_format: Format of the file (json, yaml, pickle). If None, will try to detect from extension.
        validate: Whether to validate the loaded data (default: True)
        
    Returns:
        Dictionary with load results:
        {
            "status": "success" or "error",
            "graph_json": loaded graph data,
            "file_format": detected file format,
            "file_size": size of the loaded file in bytes,
            "metadata": metadata from the file (if any),
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success"
        }
        
        # Check if file exists
        if not os.path.isfile(file_path):
            return {
                "status": "error",
                "error": f"File not found: {file_path}"
            }
        
        # Get file size
        file_size = os.path.getsize(file_path)
        result["file_size"] = file_size
        
        # Detect file format if not provided
        if not file_format:
            if file_path.endswith(".json") or file_path.endswith(".json.gz"):
                file_format = "json"
            elif file_path.endswith(".yaml") or file_path.endswith(".yml") or file_path.endswith(".yaml.gz") or file_path.endswith(".yml.gz"):
                file_format = "yaml"
            elif file_path.endswith(".pickle") or file_path.endswith(".pkl") or file_path.endswith(".pickle.gz") or file_path.endswith(".pkl.gz"):
                file_format = "pickle"
            else:
                return {
                    "status": "error",
                    "error": f"Could not detect file format from extension. Please specify file_format."
                }
        
        result["file_format"] = file_format
        
        # Check if file is compressed
        is_compressed = file_path.endswith(".gz")
        
        # Load the file in the detected format
        if is_compressed:
            import gzip
            
            if file_format == "json":
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            
            elif file_format == "yaml":
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
            
            elif file_format == "pickle":
                with gzip.open(file_path, 'rb') as f:
                    data = pickle.load(f)
            
            else:
                return {
                    "status": "error",
                    "error": f"Invalid file format: {file_format}. Valid formats are: json, yaml, pickle"
                }
        
        else:
            if file_format == "json":
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            elif file_format == "yaml":
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
            
            elif file_format == "pickle":
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)
            
            else:
                return {
                    "status": "error",
                    "error": f"Invalid file format: {file_format}. Valid formats are: json, yaml, pickle"
                }
        
        # Extract metadata if present
        metadata = data.pop("metadata", {}) if isinstance(data, dict) else {}
        result["metadata"] = metadata
        
        # Validate the loaded data if requested
        if validate:
            # Check if the data has the expected structure
            if not isinstance(data, dict):
                return {
                    "status": "error",
                    "error": "Invalid graph data: not a dictionary"
                }
            
            # Check for required keys
            required_keys = ["nodes", "edges"]
            missing_keys = [key for key in required_keys if key not in data]
            
            if missing_keys:
                return {
                    "status": "error",
                    "error": f"Invalid graph data: missing required keys: {', '.join(missing_keys)}"
                }
            
            # Check if nodes and edges are dictionaries
            if not isinstance(data["nodes"], dict) or not isinstance(data["edges"], dict):
                return {
                    "status": "error",
                    "error": "Invalid graph data: 'nodes' and 'edges' must be dictionaries"
                }
        
        # Update result
        result["graph_json"] = data
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error loading network graph: {str(e)}"
        }


@tool
def save_network_visualization(
    image_data: Union[str, bytes],
    file_path: Optional[str] = None,
    file_format: str = "png",
    is_base64: bool = True,
    include_metadata: bool = True,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Save a network visualization image to a file.
    
    This tool saves a network visualization image (from graphviz_renderer or matplotlib_plotter)
    to a file, with options to include metadata.
    
    Args:
        image_data: Image data as a base64-encoded string or raw bytes
        file_path: Path to save the file. If None, a default path in the cache directory is used.
        file_format: Format of the image (png, jpg, svg, pdf) (default: "png")
        is_base64: Whether the image_data is base64-encoded (default: True)
        include_metadata: Whether to include metadata in a sidecar file (default: True)
        metadata: Optional dictionary of metadata to include
        
    Returns:
        Dictionary with save results:
        {
            "status": "success" or "error",
            "file_path": path to the saved image file,
            "metadata_path": path to the metadata file (if include_metadata is True),
            "file_format": format of the saved image,
            "file_size": size of the saved image in bytes,
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "file_format": file_format
        }
        
        # Validate file format
        valid_formats = ["png", "jpg", "jpeg", "svg", "pdf"]
        if file_format not in valid_formats:
            return {
                "status": "error",
                "error": f"Invalid file format: {file_format}. Valid formats are: {', '.join(valid_formats)}"
            }
        
        # Normalize jpg to jpeg
        if file_format == "jpg":
            file_format = "jpeg"
        
        # Generate default file path if not provided
        if not file_path:
            timestamp = int(time.time())
            file_path = os.path.join(CACHE_DIR, f"network_visualization_{timestamp}.{file_format}")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # Decode base64 data if needed
        if is_base64 and isinstance(image_data, str):
            try:
                image_data = base64.b64decode(image_data)
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Error decoding base64 data: {str(e)}"
                }
        
        # Save the image
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Save metadata if requested
        if include_metadata:
            metadata_path = f"{file_path}.metadata.json"
            
            # Prepare metadata
            metadata_dict = metadata or {}
            metadata_dict.update({
                "timestamp": datetime.now().isoformat(),
                "file_format": file_format,
                "file_size": file_size,
                "file_path": file_path
            })
            
            # Save metadata
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_dict, f, indent=2)
            
            result["metadata_path"] = metadata_path
        
        # Update result
        result.update({
            "file_path": file_path,
            "file_size": file_size
        })
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error saving network visualization: {str(e)}"
        }


@tool
def export_network_data(
    graph_json: Dict[str, Any],
    export_type: str = "nodes",
    file_path: Optional[str] = None,
    file_format: str = "csv",
    include_headers: bool = True,
    filter_criteria: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Export network data to various formats for further analysis.
    
    This tool exports node or edge data from a network graph to CSV, JSON, or YAML format,
    with options to filter the data and include headers.
    
    Args:
        graph_json: Serialized graph in JSON format (as returned by create_network_graph)
        export_type: Type of data to export (nodes, edges, both) (default: "nodes")
        file_path: Path to save the file. If None, a default path in the cache directory is used.
        file_format: Format to export the data in (csv, json, yaml) (default: "csv")
        include_headers: Whether to include headers in CSV output (default: True)
        filter_criteria: Optional dictionary of criteria to filter the data
        
    Returns:
        Dictionary with export results:
        {
            "status": "success" or "error",
            "file_path": path to the exported file,
            "export_type": type of data exported,
            "file_format": format of the exported file,
            "record_count": number of records exported,
            "filtered_count": number of records filtered out (if filter_criteria is provided),
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "export_type": export_type,
            "file_format": file_format
        }
        
        # Validate export type
        valid_export_types = ["nodes", "edges", "both"]
        if export_type not in valid_export_types:
            return {
                "status": "error",
                "error": f"Invalid export type: {export_type}. Valid types are: {', '.join(valid_export_types)}"
            }
        
        # Validate file format
        valid_formats = ["csv", "json", "yaml"]
        if file_format not in valid_formats:
            return {
                "status": "error",
                "error": f"Invalid file format: {file_format}. Valid formats are: {', '.join(valid_formats)}"
            }
        
        # Generate default file path if not provided
        if not file_path:
            timestamp = int(time.time())
            file_path = os.path.join(CACHE_DIR, f"network_{export_type}_{timestamp}.{file_format}")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # Prepare data to export
        export_data = {}
        filtered_count = 0
        
        if export_type == "nodes" or export_type == "both":
            nodes_data = []
            for node_id, attrs in graph_json.get("nodes", {}).items():
                # Create node record with ID
                node_record = {"id": node_id}
                node_record.update(attrs)
                
                # Apply filter if provided
                if filter_criteria and not _matches_filter(node_record, filter_criteria):
                    filtered_count += 1
                    continue
                
                nodes_data.append(node_record)
            
            if export_type == "nodes":
                export_data = nodes_data
            else:
                export_data["nodes"] = nodes_data
        
        if export_type == "edges" or export_type == "both":
            edges_data = []
            for edge_id, attrs in graph_json.get("edges", {}).items():
                # Parse edge ID to get source and target
                if graph_json.get("multigraph", False):
                    try:
                        source, target, key = edge_id.split('_')
                    except ValueError:
                        logger.warning(f"Invalid edge ID format for multigraph: {edge_id}")
                        continue
                    
                    # Create edge record
                    edge_record = {"source": source, "target": target, "key": key}
                    edge_record.update(attrs)
                else:
                    try:
                        source, target = edge_id.split('_')
                    except ValueError:
                        logger.warning(f"Invalid edge ID format: {edge_id}")
                        continue
                    
                    # Create edge record
                    edge_record = {"source": source, "target": target}
                    edge_record.update(attrs)
                
                # Apply filter if provided
                if filter_criteria and not _matches_filter(edge_record, filter_criteria):
                    filtered_count += 1
                    continue
                
                edges_data.append(edge_record)
            
            if export_type == "edges":
                export_data = edges_data
            else:
                export_data["edges"] = edges_data
        
        # Export the data in the requested format
        if file_format == "csv":
            if export_type == "both":
                # For "both", we need to create separate files for nodes and edges
                nodes_path = file_path.replace(".", "_nodes.")
                edges_path = file_path.replace(".", "_edges.")
                
                # Export nodes
                if export_data.get("nodes"):
                    with open(nodes_path, 'w', newline='', encoding='utf-8') as f:
                        if export_data["nodes"]:
                            fieldnames = export_data["nodes"][0].keys()
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            
                            if include_headers:
                                writer.writeheader()
                            
                            writer.writerows(export_data["nodes"])
                
                # Export edges
                if export_data.get("edges"):
                    with open(edges_path, 'w', newline='', encoding='utf-8') as f:
                        if export_data["edges"]:
                            fieldnames = export_data["edges"][0].keys()
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            
                            if include_headers:
                                writer.writeheader()
                            
                            writer.writerows(export_data["edges"])
                
                # Update result
                result["file_path"] = {"nodes": nodes_path, "edges": edges_path}
                result["record_count"] = {
                    "nodes": len(export_data.get("nodes", [])),
                    "edges": len(export_data.get("edges", []))
                }
            
            else:
                # For "nodes" or "edges", we create a single CSV file
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    if export_data:
                        fieldnames = export_data[0].keys()
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        
                        if include_headers:
                            writer.writeheader()
                        
                        writer.writerows(export_data)
                
                # Update result
                result["file_path"] = file_path
                result["record_count"] = len(export_data)
        
        elif file_format == "json":
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
            
            # Update result
            result["file_path"] = file_path
            if export_type == "both":
                result["record_count"] = {
                    "nodes": len(export_data.get("nodes", [])),
                    "edges": len(export_data.get("edges", []))
                }
            else:
                result["record_count"] = len(export_data)
        
        elif file_format == "yaml":
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(export_data, f, default_flow_style=False)
            
            # Update result
            result["file_path"] = file_path
            if export_type == "both":
                result["record_count"] = {
                    "nodes": len(export_data.get("nodes", [])),
                    "edges": len(export_data.get("edges", []))
                }
            else:
                result["record_count"] = len(export_data)
        
        # Add filtered count if filtering was applied
        if filter_criteria:
            result["filtered_count"] = filtered_count
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error exporting network data: {str(e)}"
        }


@tool
def import_network_data(
    file_path: str,
    import_type: str = "nodes",
    file_format: Optional[str] = None,
    id_field: str = "id",
    source_field: str = "source",
    target_field: str = "target",
    merge_with: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Import network data from various formats.
    
    This tool imports node or edge data from CSV, JSON, or YAML format,
    with options to specify field names and merge with existing data.
    
    Args:
        file_path: Path to the file to import
        import_type: Type of data to import (nodes, edges, both) (default: "nodes")
        file_format: Format of the file (csv, json, yaml). If None, will try to detect from extension.
        id_field: Field name for node IDs (default: "id")
        source_field: Field name for edge source (default: "source")
        target_field: Field name for edge target (default: "target")
        merge_with: Optional existing graph data to merge with
        
    Returns:
        Dictionary with import results:
        {
            "status": "success" or "error",
            "graph_json": imported graph data,
            "import_type": type of data imported,
            "file_format": detected file format,
            "record_count": number of records imported,
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "import_type": import_type
        }
        
        # Check if file exists
        if not os.path.isfile(file_path):
            return {
                "status": "error",
                "error": f"File not found: {file_path}"
            }
        
        # Validate import type
        valid_import_types = ["nodes", "edges", "both"]
        if import_type not in valid_import_types:
            return {
                "status": "error",
                "error": f"Invalid import type: {import_type}. Valid types are: {', '.join(valid_import_types)}"
            }
        
        # Detect file format if not provided
        if not file_format:
            if file_path.endswith(".csv"):
                file_format = "csv"
            elif file_path.endswith(".json"):
                file_format = "json"
            elif file_path.endswith(".yaml") or file_path.endswith(".yml"):
                file_format = "yaml"
            else:
                return {
                    "status": "error",
                    "error": f"Could not detect file format from extension. Please specify file_format."
                }
        
        result["file_format"] = file_format
        
        # Initialize graph data
        graph_data = merge_with.copy() if merge_with else {"nodes": {}, "edges": {}, "directed": False, "multigraph": False}
        
        # Ensure nodes and edges dictionaries exist
        if "nodes" not in graph_data:
            graph_data["nodes"] = {}
        if "edges" not in graph_data:
            graph_data["edges"] = {}
        
        # Import the data based on format
        if file_format == "csv":
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                records = list(reader)
            
            if import_type == "nodes" or import_type == "both":
                for record in records:
                    # Skip records without ID
                    if id_field not in record:
                        continue
                    
                    node_id = record[id_field]
                    
                    # Remove ID field from attributes
                    node_attrs = {k: v for k, v in record.items() if k != id_field}
                    
                    # Add node to graph
                    graph_data["nodes"][node_id] = node_attrs
            
            if import_type == "edges" or import_type == "both":
                for record in records:
                    # Skip records without source or target
                    if source_field not in record or target_field not in record:
                        continue
                    
                    source = record[source_field]
                    target = record[target_field]
                    
                    # Remove source and target fields from attributes
                    edge_attrs = {k: v for k, v in record.items() if k not in [source_field, target_field]}
                    
                    # Create edge ID
                    edge_id = f"{source}_{target}"
                    
                    # Add edge to graph
                    graph_data["edges"][edge_id] = edge_attrs
        
        elif file_format == "json":
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if import_type == "both" and isinstance(data, dict):
                # Import nodes
                if "nodes" in data and isinstance(data["nodes"], list):
                    for node in data["nodes"]:
                        if id_field in node:
                            node_id = node[id_field]
                            node_attrs = {k: v for k, v in node.items() if k != id_field}
                            graph_data["nodes"][node_id] = node_attrs
                
                # Import edges
                if "edges" in data and isinstance(data["edges"], list):
                    for edge in data["edges"]:
                        if source_field in edge and target_field in edge:
                            source = edge[source_field]
                            target = edge[target_field]
                            edge_attrs = {k: v for k, v in edge.items() if k not in [source_field, target_field]}
                            edge_id = f"{source}_{target}"
                            graph_data["edges"][edge_id] = edge_attrs
            
            elif import_type == "nodes" and isinstance(data, list):
                for node in data:
                    if id_field in node:
                        node_id = node[id_field]
                        node_attrs = {k: v for k, v in node.items() if k != id_field}
                        graph_data["nodes"][node_id] = node_attrs
            
            elif import_type == "edges" and isinstance(data, list):
                for edge in data:
                    if source_field in edge and target_field in edge:
                        source = edge[source_field]
                        target = edge[target_field]
                        edge_attrs = {k: v for k, v in edge.items() if k not in [source_field, target_field]}
                        edge_id = f"{source}_{target}"
                        graph_data["edges"][edge_id] = edge_attrs
        
        elif file_format == "yaml":
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if import_type == "both" and isinstance(data, dict):
                # Import nodes
                if "nodes" in data and isinstance(data["nodes"], list):
                    for node in data["nodes"]:
                        if id_field in node:
                            node_id = node[id_field]
                            node_attrs = {k: v for k, v in node.items() if k != id_field}
                            graph_data["nodes"][node_id] = node_attrs
                
                # Import edges
                if "edges" in data and isinstance(data["edges"], list):
                    for edge in data["edges"]:
                        if source_field in edge and target_field in edge:
                            source = edge[source_field]
                            target = edge[target_field]
                            edge_attrs = {k: v for k, v in edge.items() if k not in [source_field, target_field]}
                            edge_id = f"{source}_{target}"
                            graph_data["edges"][edge_id] = edge_attrs
            
            elif import_type == "nodes" and isinstance(data, list):
                for node in data:
                    if id_field in node:
                        node_id = node[id_field]
                        node_attrs = {k: v for k, v in node.items() if k != id_field}
                        graph_data["nodes"][node_id] = node_attrs
            
            elif import_type == "edges" and isinstance(data, list):
                for edge in data:
                    if source_field in edge and target_field in edge:
                        source = edge[source_field]
                        target = edge[target_field]
                        edge_attrs = {k: v for k, v in edge.items() if k not in [source_field, target_field]}
                        edge_id = f"{source}_{target}"
                        graph_data["edges"][edge_id] = edge_attrs
        
        # Update result
        result["graph_json"] = graph_data
        
        if import_type == "both":
            result["record_count"] = {
                "nodes": len(graph_data["nodes"]),
                "edges": len(graph_data["edges"])
            }
        elif import_type == "nodes":
            result["record_count"] = len(graph_data["nodes"])
        else:  # edges
            result["record_count"] = len(graph_data["edges"])
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error importing network data: {str(e)}"
        }


def _matches_filter(record: Dict[str, Any], filter_criteria: Dict[str, Any]) -> bool:
    """
    Check if a record matches the filter criteria.
    
    Args:
        record: Record to check
        filter_criteria: Filter criteria to match against
        
    Returns:
        True if the record matches the filter criteria, False otherwise
    """
    for key, value in filter_criteria.items():
        if key not in record:
            return False
        
        if isinstance(value, list):
            if record[key] not in value:
                return False
        elif isinstance(value, dict):
            if "operator" in value and "value" in value:
                operator = value["operator"]
                filter_value = value["value"]
                
                if operator == "eq" and record[key] != filter_value:
                    return False
                elif operator == "neq" and record[key] == filter_value:
                    return False
                elif operator == "gt" and not (record[key] > filter_value):
                    return False
                elif operator == "gte" and not (record[key] >= filter_value):
                    return False
                elif operator == "lt" and not (record[key] < filter_value):
                    return False
                elif operator == "lte" and not (record[key] <= filter_value):
                    return False
                elif operator == "contains" and filter_value not in record[key]:
                    return False
                elif operator == "startswith" and not record[key].startswith(filter_value):
                    return False
                elif operator == "endswith" and not record[key].endswith(filter_value):
                    return False
        elif record[key] != value:
            return False
    
    return True