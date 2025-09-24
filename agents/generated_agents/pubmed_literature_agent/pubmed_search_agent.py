#!/usr/bin/env python3
"""
PubMed Literature Search Agent

This agent retrieves, analyzes, and presents relevant medical literature from PubMed
based on user queries. It processes natural language medical queries, searches PubMed
for relevant scientific articles, extracts key content, generates concise summaries,
and presents results ranked by relevance.

Key capabilities:
1. Query processing and optimization
2. Literature retrieval from PubMed
3. Content extraction and analysis
4. Summary generation
5. Relevance ranking
6. Structured results presentation

The agent uses specialized PubMed API tools to interact with the PubMed/NCBI E-utilities API.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up telemetry
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# Create agent parameters
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "us.anthropic.claude-opus-4-20250514-v1:0"  # Using Claude Opus for advanced medical comprehension
}

# Create the PubMed Literature Search Agent
pubmed_search_agent = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/pubmed_literature_agent/pubmed_search_agent", 
    **agent_params
)

def search_pubmed_literature(query: str, 
                           max_results: int = 20,
                           sort_by: str = "relevance",
                           date_range: Optional[Dict[str, str]] = None,
                           article_types: Optional[List[str]] = None) -> str:
    """
    Search PubMed for medical literature based on a query and parameters.
    
    Args:
        query (str): The natural language query or research question
        max_results (int): Maximum number of results to return (default: 20)
        sort_by (str): Sort order - "relevance", "pub_date", "first_author", or "journal" (default: "relevance")
        date_range (Dict[str, str], optional): Date range for filtering results, e.g. {"min_date": "2020", "max_date": "2023"}
        article_types (List[str], optional): Specific article types to filter by, e.g. ["Clinical Trial", "Review"]
        
    Returns:
        str: Formatted response with search results, summaries, and analysis
    """
    # Construct input with parameters
    input_text = f"{query}\n\n"
    
    # Add search parameters if provided
    params = []
    if max_results != 20:
        params.append(f"Max results: {max_results}")
    if sort_by != "relevance":
        params.append(f"Sort by: {sort_by}")
    if date_range:
        date_str = f"Date range: {date_range.get('min_date', '')} to {date_range.get('max_date', '')}"
        params.append(date_str)
    if article_types:
        types_str = f"Article types: {', '.join(article_types)}"
        params.append(types_str)
    
    if params:
        input_text += "Search parameters:\n" + "\n".join(f"- {param}" for param in params) + "\n\n"
    
    # Process the query through the agent
    try:
        result = pubmed_search_agent(input_text)
        return result
    except Exception as e:
        logger.error(f"Error processing PubMed search: {e}")
        return f"Error processing PubMed search: {str(e)}"

if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='PubMed Literature Search Agent')
    parser.add_argument('-q', '--query', type=str, required=True,
                       help='Research question or medical query')
    parser.add_argument('-n', '--max_results', type=int, default=20,
                       help='Maximum number of results to return (default: 20)')
    parser.add_argument('-s', '--sort_by', type=str, default="relevance",
                       choices=["relevance", "pub_date", "first_author", "journal"],
                       help='Sort order for results (default: relevance)')
    parser.add_argument('--min_date', type=str, default=None,
                       help='Minimum publication date (YYYY/MM/DD or YYYY)')
    parser.add_argument('--max_date', type=str, default=None,
                       help='Maximum publication date (YYYY/MM/DD or YYYY)')
    parser.add_argument('--article_types', type=str, default=None,
                       help='Comma-separated list of article types to filter by')
    
    args = parser.parse_args()
    
    # Process date range and article types
    date_range = None
    if args.min_date or args.max_date:
        date_range = {
            "min_date": args.min_date,
            "max_date": args.max_date
        }
    
    article_types = None
    if args.article_types:
        article_types = [t.strip() for t in args.article_types.split(',')]
    
    print(f"✅ PubMed Literature Search Agent initialized")
    print(f"🔍 Searching for: {args.query}")
    
    # Execute search
    result = search_pubmed_literature(
        query=args.query,
        max_results=args.max_results,
        sort_by=args.sort_by,
        date_range=date_range,
        article_types=article_types
    )
    
    print("\n📋 Search Results:\n")
    print(result)