#!/usr/bin/env python3
"""
Knowledge Graph Query Tools Collection
Provides various query functions based on Neo4j knowledge graph
Strands Tools List for querying the knowledge graph:
- "tools/generated_tools/tooluniverse/neo4j/knowledge_graph_queries/get_tools_by_parameter"
- "tools/generated_tools/tooluniverse/neo4j/knowledge_graph_queries/get_parameters_by_tool"
- "tools/generated_tools/tooluniverse/neo4j/knowledge_graph_queries/get_parameter_path"
- "tools/generated_tools/tooluniverse/neo4j/knowledge_graph_queries/get_tools_by_genre"
- "tools/generated_tools/tooluniverse/neo4j/knowledge_graph_queries/get_all_genres"
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.generated_tools.tooluniverse.neo4j.create_knowledge_graph import Neo4jKnowledgeGraph
import logging
from typing import List, Dict, Any, Optional
from strands import tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global configuration
DEFAULT_CONFIG_FILE = "tools/generated_tools/tooluniverse/neo4j/neo4j_config.yaml"

def _get_neo4j_kg(config_file: str = DEFAULT_CONFIG_FILE) -> Neo4jKnowledgeGraph:
    """Get Neo4jKnowledgeGraph instance"""
    return Neo4jKnowledgeGraph(config_file)


@tool(description="""
    Returns a list of tools that can use the given parameter name.
    
    This tool helps users understand which tools use a specific parameter,
    including parameter usage frequency, requirement status, and other information.
""")
def get_tools_by_parameter(parameter_name: str) -> List[Dict[str, Any]]:
    """
    Find all tools that use the specified parameter
    
    Args:
        parameter_name (str): Parameter name
        
    Returns:
        List[Dict]: List containing tool information, each dictionary contains:
            - tool_name (str): Tool name
            - tool_description (str): Tool description
            - parameter_required (bool): Whether this parameter is required in this tool
            - parameter_type (str): Parameter type
            - parameter_default (Any): Parameter default value
    """
    neo4j_kg = _get_neo4j_kg()
    try:
        with neo4j_kg.driver.session() as session:
            result = session.run("""
                MATCH (t:Tool)-[:HAS_PARAMETER]->(p:Parameter)
                WHERE p.name = $param_name
                RETURN t.name as tool_name, 
                       t.description as tool_description,
                       p.required as parameter_required,
                       p.type as parameter_type,
                       p.default_value as parameter_default
                ORDER BY t.name
            """, param_name=parameter_name)
            
            tools = []
            for record in result:
                tools.append({
                    'tool_name': record['tool_name'],
                    'tool_description': record['tool_description'],
                    'parameter_required': record['parameter_required'],
                    'parameter_type': record['parameter_type'],
                    'parameter_default': record['parameter_default']
                })
            
            logger.info(f"Found {len(tools)} tools using parameter '{parameter_name}'")
            return tools
            
    except Exception as e:
        logger.error(f"Failed to query tools for parameter '{parameter_name}': {e}")
        return []
    finally:
        neo4j_kg.close()


@tool(description="""
    Returns all parameter information required by the given tool name.
    
    This tool helps users understand what parameters a tool requires,
    including parameter requirements, types, default values, and descriptions.
""")
def get_parameters_by_tool(tool_name: str) -> Dict[str, Any]:
    """
    Get all parameter information for the specified tool
    
    Args:
        tool_name (str): Tool name
        
    Returns:
        Dict: Dictionary containing tool information and parameter list:
            - tool_name (str): Tool name
            - tool_description (str): Tool description
            - genre (str): Tool type
            - parameters (List[Dict]): Parameter list, each parameter contains:
                - name (str): Parameter name
                - description (str): Parameter description
                - type (str): Parameter type
                - required (bool): Whether required
                - default_value (Any): Default value
    """
    neo4j_kg = _get_neo4j_kg()
    try:
        with neo4j_kg.driver.session() as session:
            # Get tool basic information
            tool_result = session.run("""
                MATCH (t:Tool)-[:BELONGS_TO_GENRE]->(g:Genre)
                WHERE t.name = $tool_name
                RETURN t.name as tool_name,
                       t.description as tool_description,
                       g.name as genre
            """, tool_name=tool_name)
            
            tool_record = tool_result.single()
            if not tool_record:
                logger.warning(f"Tool '{tool_name}' not found")
                return {}
            
            # Get all parameters for the tool
            params_result = session.run("""
                MATCH (t:Tool)-[:HAS_PARAMETER]->(p:Parameter)
                WHERE t.name = $tool_name
                RETURN p.name as name,
                       p.description as description,
                       p.type as type,
                       p.required as required,
                       p.default_value as default_value
                ORDER BY p.required DESC, p.name
            """, tool_name=tool_name)
            
            parameters = []
            for record in params_result:
                parameters.append({
                    'name': record['name'],
                    'description': record['description'],
                    'type': record['type'],
                    'required': record['required'],
                    'default_value': record['default_value']
                })
            
            result = {
                'tool_name': tool_record['tool_name'],
                'tool_description': tool_record['tool_description'],
                'genre': tool_record['genre'],
                'parameters': parameters
            }
            
            logger.info(f"Found {len(parameters)} parameters for tool '{tool_name}'")
            return result
            
    except Exception as e:
        logger.error(f"Failed to query parameters for tool '{tool_name}': {e}")
        return {}
    finally:
        neo4j_kg.close()


@tool(description="""
    Returns path relationships between given parameters, including tool names that need to be executed.
    
    This tool helps users understand how to connect different parameters through a combination of tools,
    enabling data flow transformation from input parameters to target parameters.
""")
def get_parameter_path(source_parameters: List[str], target_parameters: List[str], max_depth: int = 3) -> List[Dict[str, Any]]:
    """
    Find path relationships connecting multiple parameters
    
    Args:
        source_parameters (List[str]): List of source parameter names
        target_parameters (List[str]): List of target parameter names
        max_depth (int): Maximum path depth, default 3
        
    Returns:
        List[Dict]: List of paths, each path contains:
            - path_length (int): Path length
            - tools_in_path (List[str]): Tool names in the path
            - path_description (str): Path description
    """
    neo4j_kg = _get_neo4j_kg()
    try:
        with neo4j_kg.driver.session() as session:
            # Build parameter matching conditions
            source_params_str = "', '".join(source_parameters)
            target_params_str = "', '".join(target_parameters)
            
            # Find connecting paths
            result = session.run(f"""
                MATCH path = (source:Parameter)-[:HAS_PARAMETER*1..{max_depth}]-(target:Parameter)
                WHERE source.name IN ['{source_params_str}']
                  AND target.name IN ['{target_params_str}']
                  AND source <> target
                WITH path, 
                     [node IN nodes(path) WHERE node:Tool | node.name] as tools,
                     length(path) as path_length
                RETURN DISTINCT path_length,
                       tools,
                       [node IN nodes(path) | 
                        CASE 
                            WHEN node:Tool THEN 'Tool: ' + node.name
                            WHEN node:Parameter THEN 'Parameter: ' + node.name
                            ELSE 'Unknown: ' + node.name
                        END] as path_nodes
                ORDER BY path_length, size(tools)
                LIMIT 20
            """)
            
            paths = []
            for record in result:
                # Filter out paths containing only parameter nodes (no tools)
                if record['tools']:
                    paths.append({
                        'path_length': record['path_length'],
                        'tools_in_path': record['tools'],
                        'path_description': ' -> '.join(record['path_nodes'])
                    })
            
            logger.info(f"Found {len(paths)} paths connecting parameters {source_parameters} to {target_parameters}")
            return paths
            
    except Exception as e:
        logger.error(f"Failed to find parameter paths: {e}")
        return []
    finally:
        neo4j_kg.close()


def _find_similar_genres(query: str, all_genres: List[str]) -> List[str]:
    """Find similar genre names using fuzzy matching"""
    import difflib
    query_lower = query.lower()
    
    # Mapping of common incorrect terms to correct genres
    genre_mapping = {
        'medical': ['MedlinePlusRESTTool', 'FDADrugLabel', 'ClinicalTrialsDetailsTool'],
        'health': ['MedlinePlusRESTTool', 'HPAGetGenePageDetailsTool'],
        'research': ['OpenAlexTool', 'SemanticScholarTool', 'PubTatorTool'],
        'pharmacology': ['FDADrugLabel', 'PubChemRESTTool', 'OpenTarget'],
        'medicine': ['MedlinePlusRESTTool', 'FDADrugLabel', 'OpenTarget'],
        'clinical': ['ClinicalTrialsDetailsTool', 'ClinicalTrialsSearchTool'],
        'healthcare': ['MedlinePlusRESTTool', 'ClinicalTrialsDetailsTool'],
        'pharmacy': ['FDADrugLabel', 'PubChemRESTTool'],
        'drug': ['FDADrugLabel', 'FDADrugAdverseEventTool', 'PubChemRESTTool', 'OpenTarget'],
        'search': ['OpenAlexTool', 'SemanticScholarTool', 'ClinicalTrialsSearchTool'],
        'product': ['PackageTool'],
        'web': ['URLHTMLTagTool', 'URLToPDFTextTool'],
    }
    
    # Check if there's a direct mapping
    if query_lower in genre_mapping:
        return genre_mapping[query_lower]
    
    # Use difflib to find close matches
    close_matches = difflib.get_close_matches(query, all_genres, n=5, cutoff=0.3)
    if close_matches:
        return close_matches
    
    # Partial matching - find genres containing the query
    partial_matches = [g for g in all_genres if query_lower in g.lower()]
    if partial_matches:
        return partial_matches[:5]
    
    return []


@tool(description="""
    Returns all tool names under the given Genre name.
    
    ⚠️ CRITICAL: You MUST use exact Genre names from the available list. 
    Common invalid genre names that will return 0 results:
    - ❌ "Medical", "Health", "Research", "Pharmacology", "Medicine", "Clinical", "Healthcare"
    
    Valid genre examples:
    - ✅ "FDADrugLabel", "OpenTarget", "ClinicalTrialsDetailsTool", "MedlinePlusRESTTool"
    - ✅ "AgenticTool", "PackageTool", "PubChemRESTTool", "UniProtRESTTool"
    
    If you get 0 results, your genre name is incorrect. Use get_all_genres() first to see valid names.
    
    This tool helps users understand the collection of tools of a specific type,
    facilitating browsing and selecting tools by function category.
""")
def get_tools_by_genre(genre_name: str) -> List[Dict[str, Any]]:
    """
    Get all tools under the specified Genre
    
    Args:
        genre_name (str): Genre name (must be exact match from available genres)
        
    Returns:
        List[Dict]: List of tools, each dictionary contains:
            - tool_name (str): Tool name
            - tool_description (str): Tool description
            - parameter_count (int): Parameter count
            - required_parameter_count (int): Required parameter count
            - suggestion (str, optional): Suggested genre names if input is invalid
    """
    neo4j_kg = _get_neo4j_kg()
    try:
        with neo4j_kg.driver.session() as session:
            result = session.run("""
                MATCH (g:Genre)<-[:BELONGS_TO_GENRE]-(t:Tool)
                WHERE g.name = $genre_name
                OPTIONAL MATCH (t)-[:HAS_PARAMETER]->(p:Parameter)
                OPTIONAL MATCH (t)-[:HAS_PARAMETER]->(req_p:Parameter)
                WHERE req_p.required = true
                RETURN t.name as tool_name,
                       t.description as tool_description,
                       count(DISTINCT p) as parameter_count,
                       count(DISTINCT req_p) as required_parameter_count
                ORDER BY t.name
            """, genre_name=genre_name)
            
            tools = []
            for record in result:
                tools.append({
                    'tool_name': record['tool_name'],
                    'tool_description': record['tool_description'],
                    'parameter_count': record['parameter_count'],
                    'required_parameter_count': record['required_parameter_count']
                })
            
            # If no tools found, provide helpful suggestions
            if len(tools) == 0:
                all_genres = get_all_genres()
                suggestions = _find_similar_genres(genre_name, all_genres)
                
                error_msg = f"❌ Genre '{genre_name}' not found (0 tools). "
                if suggestions:
                    error_msg += f"Did you mean one of these? {', '.join(suggestions[:5])}"
                else:
                    error_msg += f"Please use get_all_genres() to see all {len(all_genres)} available genre names."
                
                logger.warning(error_msg)
                return [{
                    'error': f"Genre '{genre_name}' not found",
                    'suggestion': error_msg,
                    'available_genres_count': len(all_genres),
                    'similar_genres': suggestions[:5] if suggestions else []
                }]
            
            logger.info(f"Found {len(tools)} tools under Genre '{genre_name}'")
            return tools
            
    except Exception as e:
        logger.error(f"Failed to query tools for Genre '{genre_name}': {e}")
        return []
    finally:
        neo4j_kg.close()


@tool(description="""
    Returns all available Genre names in the knowledge graph.
    
    This tool helps users discover all available tool categories (Genres) 
    in the system. Use this tool when you need to browse available genres
    or verify the exact spelling of a genre name before using get_tools_by_genre().
    
    Returns a list of all genre names sorted alphabetically.
""")
def get_all_genres() -> List[str]:
    """
    Get all available Genre names
    
    Returns:
        List[str]: List of all genre names sorted alphabetically
    """
    neo4j_kg = _get_neo4j_kg()
    try:
        with neo4j_kg.driver.session() as session:
            result = session.run("""
                MATCH (g:Genre)
                RETURN g.name as genre_name
                ORDER BY g.name
            """)
            
            genres = [record['genre_name'] for record in result]
            logger.info(f"Found {len(genres)} Genres")
            return genres
            
    except Exception as e:
        logger.error(f"Failed to query all Genres: {e}")
        return []
    finally:
        neo4j_kg.close()


def get_all_parameters() -> List[Dict[str, Any]]:
    """Get all parameters and their statistics"""
    neo4j_kg = _get_neo4j_kg()
    try:
        with neo4j_kg.driver.session() as session:
            result = session.run("""
                MATCH (p:Parameter)
                OPTIONAL MATCH (t:Tool)-[:HAS_PARAMETER]->(p)
                RETURN p.name as param_name,
                       p.type as param_type,
                       p.required as required,
                       count(DISTINCT t) as tool_count
                ORDER BY tool_count DESC, p.name
            """)
            
            parameters = []
            for record in result:
                parameters.append({
                    'param_name': record['param_name'],
                    'param_type': record['param_type'],
                    'required': record['required'],
                    'tool_count': record['tool_count']
                })
            
            logger.info(f"Found {len(parameters)} parameters")
            return parameters
            
    except Exception as e:
        logger.error(f"Failed to query all parameters: {e}")
        return []
    finally:
        neo4j_kg.close()


def get_statistics() -> Dict[str, Any]:
    """Get knowledge graph statistics"""
    neo4j_kg = _get_neo4j_kg()
    try:
        with neo4j_kg.driver.session() as session:
            stats = {}
            
            # Node statistics
            result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(n) as count")
            for record in result:
                stats[f"{record['label'].lower()}_count"] = record['count']
            
            # Relationship statistics
            result = session.run("MATCH ()-[r]->() RETURN type(r) as relationship_type, count(r) as count")
            for record in result:
                stats[f"{record['relationship_type'].lower().replace('_', '_')}_count"] = record['count']
            
            # Average parameter count
            result = session.run("""
                MATCH (t:Tool)
                OPTIONAL MATCH (t)-[:HAS_PARAMETER]->(p:Parameter)
                WITH t, count(p) as param_count
                RETURN avg(param_count) as avg_params_per_tool
            """)
            avg_params = result.single()['avg_params_per_tool']
            stats['avg_params_per_tool'] = round(avg_params, 2) if avg_params else 0
            
            logger.info("Statistics retrieval completed")
            return stats
            
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        return {}
    finally:
        neo4j_kg.close()


def main():
    """Main function to demonstrate all query functions"""
    try:
        logger.info("=== Knowledge Graph Query Tools Demo ===\n")
        
        # 1. Display statistics
        logger.info("1. Knowledge Graph Statistics:")
        stats = get_statistics()
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
        # 2. Display all Genres
        logger.info("\n2. All Available Genres:")
        genres = get_all_genres()
        for genre in genres:
            logger.info(f"  - {genre}")
        
        # 3. Display all parameters
        logger.info("\n3. All Parameters and Usage Statistics:")
        parameters = get_all_parameters()
        for param in parameters[:10]:  # Show only first 10
            required_status = "Required" if param['required'] else "Optional"
            logger.info(f"  {param['param_name']}: {param['param_type']} ({required_status}) - Used by {param['tool_count']} tools")
        
        # 4. Demo Tool 1: Find tools by parameter
        logger.info("\n4. Tool 1 Demo - Find Tools by Parameter:")
        if parameters:
            test_param = parameters[0]['param_name']
            tools_by_param = get_tools_by_parameter(test_param)
            logger.info(f"Parameter '{test_param}' is used by the following tools:")
            for tool_info in tools_by_param[:3]:  # Show only first 3
                required_status = "Required" if tool_info['parameter_required'] else "Optional"
                logger.info(f"  - {tool_info['tool_name']} ({required_status})")
        
        # 5. Demo Tool 2: Find parameters by tool
        logger.info("\n5. Tool 2 Demo - Find Parameters by Tool:")
        if tools_by_param:
            test_tool = tools_by_param[0]['tool_name']
            params_by_tool = get_parameters_by_tool(test_tool)
            if params_by_tool:
                logger.info(f"Tool '{test_tool}' parameters:")
                logger.info(f"  Description: {params_by_tool['tool_description']}")
                logger.info(f"  Type: {params_by_tool['genre']}")
                for param in params_by_tool['parameters']:
                    required_status = "Required" if param['required'] else "Optional"
                    logger.info(f"  - {param['name']}: {param['type']} ({required_status})")
        
        # 6. Demo Tool 3: Find parameter paths
        logger.info("\n6. Tool 3 Demo - Find Parameter Paths:")
        if len(parameters) >= 2:
            source_param = parameters[0]['param_name']
            target_param = parameters[1]['param_name']
            paths = get_parameter_path([source_param], [target_param])
            if paths:
                logger.info(f"Paths from parameter '{source_param}' to '{target_param}':")
                for path in paths[:3]:  # Show only first 3 paths
                    logger.info(f"  Path length: {path['path_length']}, Tools: {path['tools_in_path']}")
            else:
                logger.info(f"No paths found from '{source_param}' to '{target_param}'")
        
        # 7. Demo Tool 4: Find tools by Genre
        logger.info("\n7. Tool 4 Demo - Find Tools by Genre:")
        if genres:
            test_genre = genres[0]
            tools_by_genre = get_tools_by_genre(test_genre)
            logger.info(f"Tools under Genre '{test_genre}':")
            for tool_info in tools_by_genre[:3]:  # Show only first 3
                logger.info(f"  - {tool_info['tool_name']} (Parameters: {tool_info['parameter_count']}, Required: {tool_info['required_parameter_count']})")
        
        logger.info("\n=== Demo Completed ===")
        
    except Exception as e:
        logger.error(f"Error during demo: {e}")


if __name__ == "__main__":
    main()
    
    # Additional test examples
    get_tools_by_parameter("limit")
    get_parameters_by_tool("EuropePMC_search_articles")
    get_parameter_path(["limit"], ["skip"])
    get_tools_by_genre("ClinicalTrialsDetailsTool")
