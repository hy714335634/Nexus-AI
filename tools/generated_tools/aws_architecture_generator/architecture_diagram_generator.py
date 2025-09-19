"""Architecture Diagram Generator Tool.

This tool generates visual architecture diagrams in various formats like drawio, mermaid, etc.
based on AWS architecture descriptions.
"""

from typing import Dict, List, Optional, Any, Union, Tuple
import json
import re
import base64
import boto3
import hashlib
from datetime import datetime
from strands import tool


@tool
def generate_architecture_diagram(
    architecture_description: Dict[str, Any],
    diagram_format: str = "mermaid",
    include_icons: bool = True,
    layout_style: str = "top-down"
) -> str:
    """Generate a visual architecture diagram from an architecture description.

    Args:
        architecture_description (Dict[str, Any]): A structured description of the architecture.
            Must include:
            - "components": List of AWS services/components
            - "connections": List of connections between components
            - Optional: "groups" for logical grouping (e.g., VPCs, subnets)
        diagram_format (str): The output format of the diagram. Options:
            - "mermaid": Mermaid diagram code (default)
            - "drawio": Draw.io compatible XML
            - "ascii": ASCII art diagram
        include_icons (bool): Whether to include AWS service icons (default: True)
        layout_style (str): The layout style of the diagram. Options:
            - "top-down": Components flow from top to bottom (default)
            - "left-right": Components flow from left to right
            - "circular": Components arranged in a circular pattern

    Returns:
        str: JSON formatted result containing the diagram in the requested format
    """
    try:
        # Validate input
        _validate_architecture_description(architecture_description)
        
        # Generate the diagram based on the requested format
        if diagram_format.lower() == "mermaid":
            diagram = _generate_mermaid_diagram(architecture_description, include_icons, layout_style)
        elif diagram_format.lower() == "drawio":
            diagram = _generate_drawio_diagram(architecture_description, include_icons, layout_style)
        elif diagram_format.lower() == "ascii":
            diagram = _generate_ascii_diagram(architecture_description, layout_style)
        else:
            raise ValueError(f"Unsupported diagram format: {diagram_format}")
        
        # Create the result
        result = {
            "format": diagram_format,
            "diagram": diagram,
            "timestamp": datetime.utcnow().isoformat(),
            "component_count": len(architecture_description.get("components", [])),
            "connection_count": len(architecture_description.get("connections", [])),
            "include_icons": include_icons,
            "layout_style": layout_style
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"Failed to generate architecture diagram: {str(e)}",
            "format": diagram_format
        }, indent=2)


@tool
def convert_diagram_format(
    diagram_content: str,
    source_format: str,
    target_format: str,
    include_icons: bool = True
) -> str:
    """Convert a diagram from one format to another.

    Args:
        diagram_content (str): The content of the diagram to convert
        source_format (str): The current format of the diagram. Options:
            - "mermaid": Mermaid diagram code
            - "drawio": Draw.io compatible XML
            - "json": JSON architecture description
        target_format (str): The desired output format. Options:
            - "mermaid": Mermaid diagram code
            - "drawio": Draw.io compatible XML
            - "ascii": ASCII art diagram
            - "json": JSON architecture description
        include_icons (bool): Whether to include AWS service icons in the output (default: True)

    Returns:
        str: JSON formatted result containing the converted diagram
    """
    try:
        # First convert to our internal architecture description format if needed
        arch_description = {}
        
        if source_format.lower() == "json":
            # Already in our format, just parse it
            try:
                arch_description = json.loads(diagram_content)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON architecture description")
                
        elif source_format.lower() == "mermaid":
            # Parse Mermaid diagram to our architecture description format
            arch_description = _parse_mermaid_to_architecture(diagram_content)
            
        elif source_format.lower() == "drawio":
            # Parse Draw.io XML to our architecture description format
            arch_description = _parse_drawio_to_architecture(diagram_content)
            
        else:
            raise ValueError(f"Unsupported source format: {source_format}")
        
        # Now generate the target format
        if target_format.lower() == "json":
            # Just return the architecture description
            return json.dumps(arch_description, indent=2)
            
        elif target_format.lower() == "mermaid":
            # Generate Mermaid diagram
            diagram = _generate_mermaid_diagram(arch_description, include_icons, "top-down")
            
        elif target_format.lower() == "drawio":
            # Generate Draw.io XML
            diagram = _generate_drawio_diagram(arch_description, include_icons, "top-down")
            
        elif target_format.lower() == "ascii":
            # Generate ASCII art diagram
            diagram = _generate_ascii_diagram(arch_description, "top-down")
            
        else:
            raise ValueError(f"Unsupported target format: {target_format}")
        
        # Create the result
        result = {
            "source_format": source_format,
            "target_format": target_format,
            "diagram": diagram,
            "timestamp": datetime.utcnow().isoformat(),
            "component_count": len(arch_description.get("components", [])),
            "connection_count": len(arch_description.get("connections", []))
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"Failed to convert diagram format: {str(e)}",
            "source_format": source_format,
            "target_format": target_format
        }, indent=2)


@tool
def create_architecture_description(
    components: List[Dict[str, Any]],
    connections: List[Dict[str, Any]],
    groups: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Create a structured architecture description from components and connections.

    Args:
        components (List[Dict[str, Any]]): List of architecture components. Each component should have:
            - "id": Unique identifier
            - "type": AWS service type (e.g., "EC2", "S3")
            - "name": Display name
            - Optional: "properties" for additional attributes
        connections (List[Dict[str, Any]]): List of connections between components. Each connection should have:
            - "source": ID of source component
            - "target": ID of target component
            - "type": Connection type (e.g., "network", "data", "dependency")
            - Optional: "label" for connection description
        groups (List[Dict[str, Any]], optional): List of logical groups (e.g., VPCs, subnets). Each group should have:
            - "id": Unique identifier
            - "name": Display name
            - "type": Group type (e.g., "VPC", "Subnet", "AvailabilityZone")
            - "components": List of component IDs in this group
        metadata (Dict[str, Any], optional): Additional metadata about the architecture

    Returns:
        str: JSON formatted architecture description
    """
    try:
        # Validate components
        if not components:
            raise ValueError("Components list cannot be empty")
        
        # Check for duplicate component IDs
        component_ids = [c.get("id") for c in components if "id" in c]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("Duplicate component IDs found")
        
        # Validate connections
        for connection in connections:
            if "source" not in connection or "target" not in connection:
                raise ValueError("Connections must have source and target")
            
            # Check that source and target exist in components
            if connection["source"] not in component_ids:
                raise ValueError(f"Connection source '{connection['source']}' not found in components")
            if connection["target"] not in component_ids:
                raise ValueError(f"Connection target '{connection['target']}' not found in components")
        
        # Validate groups if provided
        if groups:
            group_ids = [g.get("id") for g in groups if "id" in g]
            if len(group_ids) != len(set(group_ids)):
                raise ValueError("Duplicate group IDs found")
            
            # Check that all components in groups exist
            for group in groups:
                if "components" in group:
                    for component_id in group["components"]:
                        if component_id not in component_ids:
                            raise ValueError(f"Component '{component_id}' in group '{group.get('id')}' not found")
        
        # Create the architecture description
        architecture_description = {
            "components": components,
            "connections": connections
        }
        
        if groups:
            architecture_description["groups"] = groups
            
        if metadata:
            architecture_description["metadata"] = metadata
        else:
            architecture_description["metadata"] = {
                "created": datetime.utcnow().isoformat(),
                "version": "1.0"
            }
        
        return json.dumps(architecture_description, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"Failed to create architecture description: {str(e)}"
        }, indent=2)


@tool
def extract_architecture_from_text(
    text_description: str,
    extract_connections: bool = True,
    identify_groups: bool = True
) -> str:
    """Extract architecture components and connections from a natural language description.

    Args:
        text_description (str): Natural language description of the architecture
        extract_connections (bool): Whether to extract connections between components (default: True)
        identify_groups (bool): Whether to identify logical groups like VPCs and subnets (default: True)

    Returns:
        str: JSON formatted architecture description extracted from the text
    """
    try:
        # This would ideally use more sophisticated NLP techniques
        # For now, we'll implement a basic keyword-based extraction
        
        # Extract AWS service mentions
        components = _extract_components_from_text(text_description)
        
        # Extract connections if requested
        connections = []
        if extract_connections:
            connections = _extract_connections_from_text(text_description, components)
        
        # Identify logical groups if requested
        groups = []
        if identify_groups:
            groups = _extract_groups_from_text(text_description, components)
        
        # Create the architecture description
        architecture_description = {
            "components": components,
            "connections": connections
        }
        
        if groups:
            architecture_description["groups"] = groups
            
        architecture_description["metadata"] = {
            "source": "text_extraction",
            "created": datetime.utcnow().isoformat(),
            "text_summary": text_description[:100] + "..." if len(text_description) > 100 else text_description
        }
        
        # Add confidence scores
        architecture_description["extraction_confidence"] = {
            "components": 0.8 if len(components) > 0 else 0.0,
            "connections": 0.6 if len(connections) > 0 else 0.0,
            "groups": 0.7 if len(groups) > 0 else 0.0,
            "overall": 0.7 if len(components) > 0 else 0.0
        }
        
        return json.dumps(architecture_description, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"Failed to extract architecture from text: {str(e)}"
        }, indent=2)


@tool
def get_aws_service_icons(
    service_types: List[str],
    icon_format: str = "url"
) -> str:
    """Get AWS service icons for use in architecture diagrams.

    Args:
        service_types (List[str]): List of AWS service types (e.g., ["EC2", "S3", "RDS"])
        icon_format (str): Format of the icons to return. Options:
            - "url": URLs to the official AWS icons (default)
            - "base64": Base64 encoded icon data
            - "markdown": Markdown image references

    Returns:
        str: JSON formatted mapping of service types to their icons
    """
    try:
        # Get icons for the requested services
        icons = {}
        
        for service_type in service_types:
            icon = _get_aws_service_icon(service_type, icon_format)
            if icon:
                icons[service_type] = icon
        
        result = {
            "format": icon_format,
            "icons": icons,
            "count": len(icons),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"Failed to get AWS service icons: {str(e)}",
            "format": icon_format
        }, indent=2)


# Helper functions

def _validate_architecture_description(architecture_description: Dict[str, Any]) -> None:
    """Validate the architecture description."""
    if not isinstance(architecture_description, dict):
        raise ValueError("Architecture description must be a dictionary")
    
    if "components" not in architecture_description:
        raise ValueError("Architecture description must include 'components'")
    
    if not isinstance(architecture_description["components"], list):
        raise ValueError("Components must be a list")
    
    if len(architecture_description["components"]) == 0:
        raise ValueError("Components list cannot be empty")
    
    # Check that each component has the required fields
    for component in architecture_description["components"]:
        if not isinstance(component, dict):
            raise ValueError("Each component must be a dictionary")
        
        if "id" not in component:
            raise ValueError("Each component must have an 'id'")
        
        if "type" not in component:
            raise ValueError("Each component must have a 'type'")
    
    # Validate connections if present
    if "connections" in architecture_description:
        if not isinstance(architecture_description["connections"], list):
            raise ValueError("Connections must be a list")
        
        # Check that each connection has the required fields
        for connection in architecture_description["connections"]:
            if not isinstance(connection, dict):
                raise ValueError("Each connection must be a dictionary")
            
            if "source" not in connection:
                raise ValueError("Each connection must have a 'source'")
            
            if "target" not in connection:
                raise ValueError("Each connection must have a 'target'")
            
            # Check that source and target exist in components
            component_ids = [c["id"] for c in architecture_description["components"]]
            if connection["source"] not in component_ids:
                raise ValueError(f"Connection source '{connection['source']}' not found in components")
            
            if connection["target"] not in component_ids:
                raise ValueError(f"Connection target '{connection['target']}' not found in components")


def _generate_mermaid_diagram(
    architecture_description: Dict[str, Any],
    include_icons: bool,
    layout_style: str
) -> str:
    """Generate a Mermaid diagram from an architecture description."""
    # Start with the diagram type
    if layout_style.lower() == "top-down":
        mermaid = "graph TD\n"
    elif layout_style.lower() == "left-right":
        mermaid = "graph LR\n"
    else:  # Default to top-down
        mermaid = "graph TD\n"
    
    # Define node styles based on AWS service types
    mermaid += "    %% Node styles\n"
    mermaid += "    classDef ec2 fill:#F58536,stroke:#333,stroke-width:1px;\n"
    mermaid += "    classDef s3 fill:#E05243,stroke:#333,stroke-width:1px;\n"
    mermaid += "    classDef rds fill:#3B48CC,stroke:#333,stroke-width:1px;\n"
    mermaid += "    classDef lambda fill:#FF9900,stroke:#333,stroke-width:1px;\n"
    mermaid += "    classDef dynamodb fill:#4053D6,stroke:#333,stroke-width:1px;\n"
    mermaid += "    classDef vpc fill:#F58536,stroke:#333,stroke-width:1px,stroke-dasharray: 5 5;\n"
    mermaid += "    classDef subnet fill:#F58536,stroke:#333,stroke-width:1px,stroke-dasharray: 5 5;\n"
    mermaid += "    classDef default fill:#fff,stroke:#333,stroke-width:1px;\n"
    
    # Add subgraphs for groups if present
    if "groups" in architecture_description:
        # Sort groups to ensure parent groups come before their children
        groups = sorted(architecture_description["groups"], key=lambda g: len(g.get("components", [])), reverse=True)
        
        for group in groups:
            group_id = group["id"]
            group_name = group.get("name", group_id)
            group_type = group.get("type", "").lower()
            
            mermaid += f"    subgraph {group_id}[{group_name}]\n"
            
            # Add components in this group
            if "components" in group:
                for component_id in group["components"]:
                    # Find the component
                    component = next((c for c in architecture_description["components"] if c["id"] == component_id), None)
                    if component:
                        component_name = component.get("name", component["id"])
                        mermaid += f"        {component_id}[{component_name}]\n"
            
            mermaid += "    end\n"
            
            # Apply style to the group
            if group_type == "vpc":
                mermaid += f"    class {group_id} vpc;\n"
            elif group_type == "subnet":
                mermaid += f"    class {group_id} subnet;\n"
    
    # Add nodes for components not in any group
    group_components = []
    if "groups" in architecture_description:
        for group in architecture_description["groups"]:
            if "components" in group:
                group_components.extend(group["components"])
    
    for component in architecture_description["components"]:
        if "groups" not in architecture_description or component["id"] not in group_components:
            component_id = component["id"]
            component_name = component.get("name", component_id)
            
            # Add icon if requested
            if include_icons:
                icon = _get_aws_service_icon_unicode(component["type"])
                if icon:
                    mermaid += f"    {component_id}[{icon} {component_name}]\n"
                else:
                    mermaid += f"    {component_id}[{component_name}]\n"
            else:
                mermaid += f"    {component_id}[{component_name}]\n"
            
            # Apply style based on component type
            component_type = component["type"].lower()
            if component_type in ["ec2", "s3", "rds", "lambda", "dynamodb"]:
                mermaid += f"    class {component_id} {component_type};\n"
    
    # Add connections
    if "connections" in architecture_description:
        mermaid += "    %% Connections\n"
        for connection in architecture_description["connections"]:
            source = connection["source"]
            target = connection["target"]
            label = connection.get("label", "")
            connection_type = connection.get("type", "").lower()
            
            # Determine arrow style based on connection type
            if connection_type == "network":
                arrow = "-->"
            elif connection_type == "dependency":
                arrow = "-..->"
            elif connection_type == "data":
                arrow = "==>"
            else:
                arrow = "-->"
            
            if label:
                mermaid += f"    {source} {arrow}|{label}| {target}\n"
            else:
                mermaid += f"    {source} {arrow} {target}\n"
    
    return mermaid


def _generate_drawio_diagram(
    architecture_description: Dict[str, Any],
    include_icons: bool,
    layout_style: str
) -> str:
    """Generate a Draw.io compatible XML diagram from an architecture description."""
    # This is a simplified implementation that creates a basic Draw.io diagram
    # A real implementation would use the Draw.io XML format to create a more sophisticated diagram
    
    # Start with the XML header
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<mxfile host="app.diagrams.net" modified="2025-09-19T00:00:00.000Z" agent="AWS Architecture Generator" version="15.8.6" type="device">\n'
    xml += '  <diagram id="architecture" name="AWS Architecture">\n'
    xml += '    <mxGraphModel dx="1422" dy="798" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="1100" math="0" shadow="0">\n'
    xml += '      <root>\n'
    xml += '        <mxCell id="0" />\n'
    xml += '        <mxCell id="1" parent="0" />\n'
    
    # Calculate positions based on layout style
    positions = _calculate_diagram_positions(architecture_description, layout_style)
    
    # Add groups first (if any)
    group_cell_id = 2  # Start cell IDs from 2 (0 and 1 are reserved)
    group_cells = {}
    
    if "groups" in architecture_description:
        for group in architecture_description["groups"]:
            group_id = group["id"]
            group_name = group.get("name", group_id)
            group_type = group.get("type", "").lower()
            
            # Get position and size
            if group_id in positions:
                x, y = positions[group_id]["position"]
                width = positions[group_id].get("width", 200)
                height = positions[group_id].get("height", 200)
            else:
                x, y = 100, 100
                width, height = 200, 200
            
            # Set style based on group type
            style = "rounded=1;whiteSpace=wrap;html=1;dashed=1;fillColor=#f5f5f5;strokeColor=#666666;"
            if group_type == "vpc":
                style = "rounded=1;whiteSpace=wrap;html=1;dashed=1;fillColor=#f8cecc;strokeColor=#b85450;"
            elif group_type == "subnet":
                style = "rounded=1;whiteSpace=wrap;html=1;dashed=1;fillColor=#dae8fc;strokeColor=#6c8ebf;"
            elif group_type == "availabilityzone":
                style = "rounded=1;whiteSpace=wrap;html=1;dashed=1;fillColor=#d5e8d4;strokeColor=#82b366;"
            
            # Add the group cell
            xml += f'        <mxCell id="{group_cell_id}" value="{group_name}" style="{style}" vertex="1" parent="1">\n'
            xml += f'          <mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry" />\n'
            xml += '        </mxCell>\n'
            
            # Store the cell ID for this group
            group_cells[group_id] = group_cell_id
            group_cell_id += 1
    
    # Add components
    component_cell_id = group_cell_id
    component_cells = {}
    
    for component in architecture_description["components"]:
        component_id = component["id"]
        component_name = component.get("name", component_id)
        component_type = component["type"].lower()
        
        # Get position
        if component_id in positions:
            x, y = positions[component_id]["position"]
        else:
            x, y = 100, 100
        
        # Determine parent cell (group or root)
        parent_cell = "1"  # Default to root
        if "groups" in architecture_description:
            for group in architecture_description["groups"]:
                if "components" in group and component_id in group["components"]:
                    parent_cell = str(group_cells[group["id"]])
                    break
        
        # Set style based on component type
        style = "rounded=1;whiteSpace=wrap;html=1;"
        if component_type == "ec2":
            style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;"
        elif component_type == "s3":
            style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;"
        elif component_type == "rds":
            style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;"
        elif component_type == "lambda":
            style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;"
        elif component_type == "dynamodb":
            style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;"
        
        # Add icon if requested
        value = component_name
        if include_icons:
            # In a real implementation, we would add the actual AWS service icon
            # For now, we'll just add the service type as a prefix
            value = f"{component_type.upper()}: {component_name}"
        
        # Add the component cell
        xml += f'        <mxCell id="{component_cell_id}" value="{value}" style="{style}" vertex="1" parent="{parent_cell}">\n'
        xml += f'          <mxGeometry x="{x}" y="{y}" width="120" height="60" as="geometry" />\n'
        xml += '        </mxCell>\n'
        
        # Store the cell ID for this component
        component_cells[component_id] = component_cell_id
        component_cell_id += 1
    
    # Add connections
    if "connections" in architecture_description:
        for connection in architecture_description["connections"]:
            source = connection["source"]
            target = connection["target"]
            label = connection.get("label", "")
            connection_type = connection.get("type", "").lower()
            
            # Determine edge style based on connection type
            style = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;"
            if connection_type == "network":
                style += "strokeColor=#000000;"
            elif connection_type == "dependency":
                style += "strokeColor=#000000;dashed=1;"
            elif connection_type == "data":
                style += "strokeColor=#0000FF;"
            
            # Add the connection edge
            xml += f'        <mxCell id="{component_cell_id}" value="{label}" style="{style}" edge="1" parent="1" source="{component_cells[source]}" target="{component_cells[target]}">\n'
            xml += '          <mxGeometry relative="1" as="geometry" />\n'
            xml += '        </mxCell>\n'
            
            component_cell_id += 1
    
    # Close the XML
    xml += '      </root>\n'
    xml += '    </mxGraphModel>\n'
    xml += '  </diagram>\n'
    xml += '</mxfile>'
    
    return xml


def _generate_ascii_diagram(
    architecture_description: Dict[str, Any],
    layout_style: str
) -> str:
    """Generate an ASCII art diagram from an architecture description."""
    # This is a simplified ASCII art diagram
    # A real implementation would use a more sophisticated algorithm to create a better layout
    
    # Start with a header
    ascii_diagram = "AWS Architecture Diagram (ASCII)\n"
    ascii_diagram += "==============================\n\n"
    
    # Add components
    ascii_diagram += "Components:\n"
    for component in architecture_description["components"]:
        component_id = component["id"]
        component_name = component.get("name", component_id)
        component_type = component["type"].upper()
        
        ascii_diagram += f"  [{component_type}] {component_name} ({component_id})\n"
    
    ascii_diagram += "\n"
    
    # Add connections
    if "connections" in architecture_description:
        ascii_diagram += "Connections:\n"
        for connection in architecture_description["connections"]:
            source = connection["source"]
            target = connection["target"]
            label = connection.get("label", "")
            
            # Find source and target component names
            source_name = next((c.get("name", c["id"]) for c in architecture_description["components"] if c["id"] == source), source)
            target_name = next((c.get("name", c["id"]) for c in architecture_description["components"] if c["id"] == target), target)
            
            if label:
                ascii_diagram += f"  {source_name} --({label})--> {target_name}\n"
            else:
                ascii_diagram += f"  {source_name} --> {target_name}\n"
    
    ascii_diagram += "\n"
    
    # Add groups if present
    if "groups" in architecture_description:
        ascii_diagram += "Groups:\n"
        for group in architecture_description["groups"]:
            group_id = group["id"]
            group_name = group.get("name", group_id)
            group_type = group.get("type", "").upper()
            
            ascii_diagram += f"  [{group_type}] {group_name} ({group_id})\n"
            
            # List components in this group
            if "components" in group:
                for component_id in group["components"]:
                    # Find the component
                    component = next((c for c in architecture_description["components"] if c["id"] == component_id), None)
                    if component:
                        component_name = component.get("name", component["id"])
                        ascii_diagram += f"    - {component_name} ({component_id})\n"
    
    # Add a simple visual representation
    ascii_diagram += "\nSimple Visual Representation:\n"
    ascii_diagram += "-----------------------------\n"
    
    # Create a simple visual representation based on the layout style
    if layout_style.lower() == "top-down":
        ascii_diagram += _generate_top_down_ascii(architecture_description)
    elif layout_style.lower() == "left-right":
        ascii_diagram += _generate_left_right_ascii(architecture_description)
    else:
        ascii_diagram += _generate_top_down_ascii(architecture_description)
    
    return ascii_diagram


def _generate_top_down_ascii(architecture_description: Dict[str, Any]) -> str:
    """Generate a top-down ASCII art representation."""
    ascii_art = ""
    
    # Create a simplified representation of the architecture
    components = architecture_description["components"]
    connections = architecture_description.get("connections", [])
    
    # Create a directed graph
    graph = {}
    for component in components:
        graph[component["id"]] = {"outgoing": [], "incoming": []}
    
    for connection in connections:
        source = connection["source"]
        target = connection["target"]
        graph[source]["outgoing"].append(target)
        graph[target]["incoming"].append(source)
    
    # Find root nodes (no incoming connections)
    roots = [component["id"] for component in components if not graph[component["id"]]["incoming"]]
    if not roots:
        # If no roots, use the first component
        roots = [components[0]["id"]]
    
    # Generate a simple tree representation
    visited = set()
    
    def print_node(node_id, indent=0):
        nonlocal ascii_art
        if node_id in visited:
            return
        
        visited.add(node_id)
        
        # Find the component
        component = next((c for c in components if c["id"] == node_id), None)
        if not component:
            return
        
        component_name = component.get("name", component["id"])
        component_type = component["type"].upper()
        
        # Print the node
        ascii_art += " " * indent + f"+-- [{component_type}] {component_name}\n"
        
        # Print outgoing connections
        for target in graph[node_id]["outgoing"]:
            print_node(target, indent + 4)
    
    # Print the tree starting from root nodes
    for root in roots:
        print_node(root)
    
    return ascii_art


def _generate_left_right_ascii(architecture_description: Dict[str, Any]) -> str:
    """Generate a left-right ASCII art representation."""
    # Similar to top-down but with different formatting
    # In a real implementation, this would be more sophisticated
    return _generate_top_down_ascii(architecture_description)


def _calculate_diagram_positions(
    architecture_description: Dict[str, Any],
    layout_style: str
) -> Dict[str, Dict[str, Any]]:
    """Calculate positions for components and groups in the diagram."""
    # This is a simplified positioning algorithm
    # A real implementation would use a more sophisticated algorithm for better layouts
    
    positions = {}
    
    # Get components and connections
    components = architecture_description["components"]
    connections = architecture_description.get("connections", [])
    
    # Create a directed graph
    graph = {}
    for component in components:
        graph[component["id"]] = {"outgoing": [], "incoming": []}
    
    for connection in connections:
        source = connection["source"]
        target = connection["target"]
        graph[source]["outgoing"].append(target)
        graph[target]["incoming"].append(source)
    
    # Calculate levels (distance from root)
    levels = {}
    
    # Find root nodes (no incoming connections)
    roots = [component["id"] for component in components if not graph[component["id"]]["incoming"]]
    if not roots:
        # If no roots, use the first component
        roots = [components[0]["id"]]
    
    # Assign levels using BFS
    queue = [(root, 0) for root in roots]
    visited = set()
    
    while queue:
        node_id, level = queue.pop(0)
        
        if node_id in visited:
            continue
        
        visited.add(node_id)
        levels[node_id] = level
        
        for target in graph[node_id]["outgoing"]:
            queue.append((target, level + 1))
    
    # Assign positions based on levels
    max_level = max(levels.values()) if levels else 0
    level_counts = [0] * (max_level + 1)
    
    # Count components at each level
    for level in levels.values():
        level_counts[level] += 1
    
    # Calculate positions
    level_positions = [0] * (max_level + 1)
    
    for component in components:
        component_id = component["id"]
        
        # If not in levels (isolated node), assign to level 0
        level = levels.get(component_id, 0)
        
        # Calculate position based on layout style
        if layout_style.lower() == "top-down":
            x = 100 + 200 * level_positions[level]
            y = 100 + 150 * level
        elif layout_style.lower() == "left-right":
            x = 100 + 200 * level
            y = 100 + 150 * level_positions[level]
        else:  # Default to top-down
            x = 100 + 200 * level_positions[level]
            y = 100 + 150 * level
        
        positions[component_id] = {"position": (x, y)}
        level_positions[level] += 1
    
    # Calculate positions for groups if present
    if "groups" in architecture_description:
        for group in architecture_description["groups"]:
            group_id = group["id"]
            
            # Get components in this group
            group_components = group.get("components", [])
            
            # Calculate bounding box
            if group_components:
                min_x = min(positions[c]["position"][0] for c in group_components if c in positions)
                max_x = max(positions[c]["position"][0] for c in group_components if c in positions)
                min_y = min(positions[c]["position"][1] for c in group_components if c in positions)
                max_y = max(positions[c]["position"][1] for c in group_components if c in positions)
                
                # Add padding
                padding = 50
                min_x -= padding
                max_x += padding + 120  # Add component width
                min_y -= padding
                max_y += padding + 60   # Add component height
                
                width = max_x - min_x
                height = max_y - min_y
                
                positions[group_id] = {
                    "position": (min_x, min_y),
                    "width": width,
                    "height": height
                }
            else:
                # Default position and size for empty groups
                positions[group_id] = {
                    "position": (100, 100),
                    "width": 200,
                    "height": 200
                }
    
    return positions


def _parse_mermaid_to_architecture(mermaid_content: str) -> Dict[str, Any]:
    """Parse a Mermaid diagram to our architecture description format."""
    # This is a simplified parser for Mermaid diagrams
    # A real implementation would use a more sophisticated parser
    
    components = []
    connections = []
    
    # Extract nodes
    node_pattern = r'(\w+)\[(.*?)\]'
    for match in re.finditer(node_pattern, mermaid_content):
        node_id = match.group(1)
        node_label = match.group(2).strip()
        
        # Try to extract service type from the label
        service_type = "generic"
        if ":" in node_label:
            parts = node_label.split(":", 1)
            service_type = parts[0].strip()
            node_label = parts[1].strip()
        
        components.append({
            "id": node_id,
            "name": node_label,
            "type": service_type
        })
    
    # Extract connections
    connection_pattern = r'(\w+)\s+(--?>|==?>|-.\.->)\s+(\w+)'
    for match in re.finditer(connection_pattern, mermaid_content):
        source = match.group(1)
        arrow = match.group(2)
        target = match.group(3)
        
        # Determine connection type based on arrow
        connection_type = "network"
        if arrow == "==&gt;":
            connection_type = "data"
        elif arrow == "-...-&gt;":
            connection_type = "dependency"
        
        connections.append({
            "source": source,
            "target": target,
            "type": connection_type
        })
    
    # Extract connection labels
    label_pattern = r'(\w+)\s+(--?>|==?>|-.\.->)\|(.+?)\|\s+(\w+)'
    for match in re.finditer(label_pattern, mermaid_content):
        source = match.group(1)
        target = match.group(4)
        label = match.group(3).strip()
        
        # Find the connection and add the label
        for connection in connections:
            if connection["source"] == source and connection["target"] == target:
                connection["label"] = label
                break
    
    # Extract subgraphs (groups)
    groups = []
    subgraph_pattern = r'subgraph\s+(\w+)\[(.*?)\](.*?)end'
    for match in re.finditer(subgraph_pattern, mermaid_content, re.DOTALL):
        group_id = match.group(1)
        group_name = match.group(2).strip()
        group_content = match.group(3)
        
        # Extract components in this group
        group_components = []
        for component_match in re.finditer(node_pattern, group_content):
            group_components.append(component_match.group(1))
        
        # Determine group type
        group_type = "generic"
        if "vpc" in group_name.lower():
            group_type = "vpc"
        elif "subnet" in group_name.lower():
            group_type = "subnet"
        elif "zone" in group_name.lower() or "az" in group_name.lower():
            group_type = "availabilityzone"
        
        groups.append({
            "id": group_id,
            "name": group_name,
            "type": group_type,
            "components": group_components
        })
    
    return {
        "components": components,
        "connections": connections,
        "groups": groups if groups else None
    }


def _parse_drawio_to_architecture(drawio_content: str) -> Dict[str, Any]:
    """Parse a Draw.io XML diagram to our architecture description format."""
    # This is a simplified parser for Draw.io diagrams
    # A real implementation would use a proper XML parser
    
    # For now, return a placeholder architecture
    return {
        "components": [
            {
                "id": "component1",
                "name": "Parsed from Draw.io",
                "type": "generic"
            }
        ],
        "connections": [],
        "metadata": {
            "source": "drawio_import",
            "note": "Draw.io parsing not fully implemented"
        }
    }


def _extract_components_from_text(text_description: str) -> List[Dict[str, Any]]:
    """Extract AWS service components from text description."""
    # This is a simplified extraction using regex
    # A real implementation would use NLP techniques
    
    components = []
    component_id_counter = 1
    
    # Define patterns for common AWS services
    service_patterns = [
        (r'\b(EC2|Amazon EC2|EC2 instances?)\b', 'EC2'),
        (r'\b(S3|Amazon S3|S3 buckets?)\b', 'S3'),
        (r'\b(RDS|Amazon RDS|RDS instances?|MySQL|PostgreSQL|Aurora)\b', 'RDS'),
        (r'\b(DynamoDB|Amazon DynamoDB|DynamoDB tables?)\b', 'DynamoDB'),
        (r'\b(Lambda|AWS Lambda|Lambda functions?)\b', 'Lambda'),
        (r'\b(API Gateway|Amazon API Gateway)\b', 'API Gateway'),
        (r'\b(CloudFront|Amazon CloudFront)\b', 'CloudFront'),
        (r'\b(ELB|Elastic Load Balancer|Load Balancer|ALB|NLB)\b', 'ELB'),
        (r'\b(VPC|Amazon VPC|Virtual Private Cloud)\b', 'VPC'),
        (r'\b(IAM|AWS IAM|Identity and Access Management)\b', 'IAM'),
        (r'\b(CloudWatch|Amazon CloudWatch)\b', 'CloudWatch'),
        (r'\b(SNS|Amazon SNS|Simple Notification Service)\b', 'SNS'),
        (r'\b(SQS|Amazon SQS|Simple Queue Service)\b', 'SQS'),
        (r'\b(ECS|Amazon ECS|Elastic Container Service)\b', 'ECS'),
        (r'\b(EKS|Amazon EKS|Kubernetes Service)\b', 'EKS'),
        (r'\b(Fargate|AWS Fargate)\b', 'Fargate'),
        (r'\b(ElastiCache|Amazon ElastiCache|Redis|Memcached)\b', 'ElastiCache'),
        (r'\b(Route 53|Amazon Route 53|DNS)\b', 'Route 53'),
        (r'\b(CloudFormation|AWS CloudFormation)\b', 'CloudFormation'),
        (r'\b(Step Functions|AWS Step Functions)\b', 'Step Functions')
    ]
    
    # Track which services we've already added
    added_services = set()
    
    for pattern, service_type in service_patterns:
        matches = re.finditer(pattern, text_description, re.IGNORECASE)
        for match in matches:
            service_mention = match.group(0)
            
            # Skip if we've already added this service type
            if service_type in added_services:
                continue
                
            added_services.add(service_type)
            
            # Create a component for this service
            component_id = f"{service_type.lower().replace(' ', '_')}{component_id_counter}"
            component_name = service_type
            
            components.append({
                "id": component_id,
                "name": component_name,
                "type": service_type,
                "properties": {
                    "mentioned_as": service_mention,
                    "extracted_from": "text"
                }
            })
            
            component_id_counter += 1
    
    return components


def _extract_connections_from_text(
    text_description: str,
    components: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Extract connections between components from text description."""
    # This is a simplified extraction
    # A real implementation would use NLP techniques
    
    connections = []
    
    # Skip if we have fewer than 2 components
    if len(components) < 2:
        return connections
    
    # Define patterns for common connection phrases
    connection_patterns = [
        (r'(\w+)\s+connects?\s+to\s+(\w+)', 'network'),
        (r'(\w+)\s+communicates?\s+with\s+(\w+)', 'network'),
        (r'(\w+)\s+sends?\s+data\s+to\s+(\w+)', 'data'),
        (r'(\w+)\s+stores?\s+data\s+in\s+(\w+)', 'data'),
        (r'(\w+)\s+depends?\s+on\s+(\w+)', 'dependency'),
        (r'(\w+)\s+uses?\s+(\w+)', 'dependency'),
        (r'(\w+)\s+calls?\s+(\w+)', 'dependency'),
        (r'(\w+)\s+triggers?\s+(\w+)', 'dependency'),
        (r'(\w+)\s+to\s+(\w+)', 'network')
    ]
    
    # Map of service types to component IDs
    service_map = {}
    for component in components:
        service_type = component["type"].lower()
        service_map[service_type] = component["id"]
    
    # Look for connection phrases
    for pattern, connection_type in connection_patterns:
        matches = re.finditer(pattern, text_description, re.IGNORECASE)
        for match in matches:
            source_mention = match.group(1).lower()
            target_mention = match.group(2).lower()
            
            # Try to map mentions to component IDs
            source_id = None
            target_id = None
            
            for service_type, component_id in service_map.items():
                if service_type in source_mention:
                    source_id = component_id
                if service_type in target_mention:
                    target_id = component_id
            
            # If we found both source and target, add the connection
            if source_id and target_id and source_id != target_id:
                # Check if this connection already exists
                if not any(c["source"] == source_id and c["target"] == target_id for c in connections):
                    connections.append({
                        "source": source_id,
                        "target": target_id,
                        "type": connection_type,
                        "properties": {
                            "extracted_from": "text"
                        }
                    })
    
    # If we didn't find any connections but have components, try to infer some basic connections
    if not connections and len(components) >= 2:
        # Create some basic connections based on common architecture patterns
        component_types = [c["type"].lower() for c in components]
        
        # Web tier -> App tier -> Data tier pattern
        if "elb" in component_types and "ec2" in component_types:
            connections.append({
                "source": service_map["elb"],
                "target": service_map["ec2"],
                "type": "network",
                "properties": {
                    "inferred": True
                }
            })
        
        if "ec2" in component_types and "rds" in component_types:
            connections.append({
                "source": service_map["ec2"],
                "target": service_map["rds"],
                "type": "data",
                "properties": {
                    "inferred": True
                }
            })
        
        if "ec2" in component_types and "s3" in component_types:
            connections.append({
                "source": service_map["ec2"],
                "target": service_map["s3"],
                "type": "data",
                "properties": {
                    "inferred": True
                }
            })
        
        if "lambda" in component_types and "dynamodb" in component_types:
            connections.append({
                "source": service_map["lambda"],
                "target": service_map["dynamodb"],
                "type": "data",
                "properties": {
                    "inferred": True
                }
            })
    
    return connections


def _extract_groups_from_text(
    text_description: str,
    components: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Extract logical groups from text description."""
    # This is a simplified extraction
    # A real implementation would use NLP techniques
    
    groups = []
    group_id_counter = 1
    
    # Skip if we have no components
    if not components:
        return groups
    
    # Define patterns for common group types
    group_patterns = [
        (r'\b(VPC|Virtual Private Cloud)\b', 'vpc'),
        (r'\b(Subnet|Public Subnet|Private Subnet)\b', 'subnet'),
        (r'\b(Availability Zone|AZ)\b', 'availabilityzone'),
        (r'\b(Region|AWS Region)\b', 'region')
    ]
    
    # Look for group mentions
    for pattern, group_type in group_patterns:
        matches = re.finditer(pattern, text_description, re.IGNORECASE)
        for match in matches:
            group_mention = match.group(0)
            
            # Create a group
            group_id = f"{group_type}{group_id_counter}"
            group_name = f"{group_mention}"
            
            # For simplicity, assign components based on common patterns
            group_components = []
            
            if group_type == "vpc":
                # In a VPC, include all components except global services
                for component in components:
                    if component["type"].lower() not in ["cloudfront", "route 53", "iam", "s3"]:
                        group_components.append(component["id"])
            
            elif group_type == "subnet":
                # In a subnet, include compute and database components
                for component in components:
                    if component["type"].lower() in ["ec2", "rds", "elasticache", "lambda"]:
                        group_components.append(component["id"])
            
            # Only add the group if it has components
            if group_components:
                groups.append({
                    "id": group_id,
                    "name": group_name,
                    "type": group_type,
                    "components": group_components,
                    "properties": {
                        "extracted_from": "text"
                    }
                })
                
                group_id_counter += 1
    
    return groups


def _get_aws_service_icon(service_type: str, icon_format: str) -> str:
    """Get the AWS service icon in the requested format."""
    # This is a simplified implementation
    # A real implementation would use the official AWS Architecture Icons
    
    # Normalize service type
    service_type = service_type.lower().strip()
    
    # Map of service types to icon URLs
    # In a real implementation, this would be a comprehensive mapping to official AWS icons
    icon_urls = {
        "ec2": "https://d1.awsstatic.com/icons/aws-icons/AWS-EC2_icon.png",
        "s3": "https://d1.awsstatic.com/icons/aws-icons/AWS-S3_icon.png",
        "rds": "https://d1.awsstatic.com/icons/aws-icons/AWS-RDS_icon.png",
        "lambda": "https://d1.awsstatic.com/icons/aws-icons/AWS-Lambda_icon.png",
        "dynamodb": "https://d1.awsstatic.com/icons/aws-icons/AWS-DynamoDB_icon.png",
        "api gateway": "https://d1.awsstatic.com/icons/aws-icons/AWS-API-Gateway_icon.png",
        "cloudfront": "https://d1.awsstatic.com/icons/aws-icons/AWS-CloudFront_icon.png",
        "elb": "https://d1.awsstatic.com/icons/aws-icons/AWS-ELB_icon.png",
        "vpc": "https://d1.awsstatic.com/icons/aws-icons/AWS-VPC_icon.png",
        "iam": "https://d1.awsstatic.com/icons/aws-icons/AWS-IAM_icon.png",
        "cloudwatch": "https://d1.awsstatic.com/icons/aws-icons/AWS-CloudWatch_icon.png",
        "sns": "https://d1.awsstatic.com/icons/aws-icons/AWS-SNS_icon.png",
        "sqs": "https://d1.awsstatic.com/icons/aws-icons/AWS-SQS_icon.png"
    }
    
    # If we don't have an icon for this service, return None
    if service_type not in icon_urls:
        return None
    
    # Get the icon URL
    icon_url = icon_urls[service_type]
    
    # Return the icon in the requested format
    if icon_format.lower() == "url":
        return icon_url
    
    elif icon_format.lower() == "markdown":
        service_name = service_type.upper()
        return f"![{service_name}]({icon_url})"
    
    elif icon_format.lower() == "base64":
        # In a real implementation, this would download the icon and convert to base64
        # For now, return a placeholder
        return f"base64_encoded_icon_for_{service_type}"
    
    else:
        return None


def _get_aws_service_icon_unicode(service_type: str) -> str:
    """Get a Unicode character to represent the AWS service in text diagrams."""
    # This is a simplified implementation using emoji or symbols to represent services
    # A real implementation might use more specific icons or ASCII art
    
    # Normalize service type
    service_type = service_type.lower().strip()
    
    # Map of service types to Unicode characters
    icon_map = {
        "ec2": "💻",
        "s3": "🗄️",
        "rds": "🛢️",
        "lambda": "λ",
        "dynamodb": "📊",
        "api gateway": "🔌",
        "cloudfront": "🌐",
        "elb": "⚖️",
        "vpc": "🔒",
        "iam": "🔑",
        "cloudwatch": "📈",
        "sns": "📨",
        "sqs": "📬",
        "ecs": "🐳",
        "eks": "☸️",
        "route 53": "🧭",
        "cloudformation": "📝",
        "step functions": "🔄",
        "elasticache": "⚡",
        "fargate": "🚢"
    }
    
    # Return the icon if we have one, otherwise return a generic icon
    return icon_map.get(service_type, "📦")