#!/usr/bin/env python3
"""
PubMed API Tool Development Documentation

This file documents the development of the PubMed API integration tools for the pubmed_search_agent project.
"""

import json
from strands import tool

@tool
def get_pubmed_tools_documentation() -> str:
    """
    Get documentation for the PubMed API integration tools.
    
    Returns:
        str: JSON string containing documentation for the PubMed API integration tools
    """
    documentation = {
        "tool_development": {
            "development_overview": {
                "project_name": "pubmed_search_agent",
                "version": "1.0",
                "date": "2023-09-18",
                "development_scope": "PubMed API integration tool for searching and retrieving scientific articles",
                "design_principles": [
                    "Comprehensive PubMed API coverage",
                    "Robust error handling and rate limiting",
                    "Efficient caching to minimize API calls",
                    "Clean, well-documented code structure",
                    "Type-safe implementation with complete annotations",
                    "User-friendly JSON response format"
                ],
                "key_decisions": [
                    "Implemented caching system to reduce API calls and improve performance",
                    "Added rate limiting to comply with NCBI E-utilities API guidelines",
                    "Created multiple specialized tools for different PubMed interaction needs",
                    "Implemented article ranking based on multiple relevance factors",
                    "Used XML parsing for handling PubMed's response format",
                    "Added support for API key to increase rate limits"
                ]
            },
            "tools": [
                {
                    "tool_name": "pubmed_search",
                    "description": "Search PubMed for scientific articles matching a query",
                    "function_signature": "pubmed_search(query: str, max_results: int = 20, sort_by: str = \"relevance\", min_date: Optional[str] = None, max_date: Optional[str] = None, optimize_query: bool = True) -> str",
                    "parameters": [
                        {
                            "name": "query",
                            "type": "str",
                            "description": "Search query for PubMed articles",
                            "required": True
                        },
                        {
                            "name": "max_results",
                            "type": "int",
                            "description": "Maximum number of results to return (default: 20, max: 100)",
                            "required": False
                        },
                        {
                            "name": "sort_by",
                            "type": "str",
                            "description": "Sort order - \"relevance\", \"pub_date\", \"first_author\", or \"journal\"",
                            "required": False
                        },
                        {
                            "name": "min_date",
                            "type": "Optional[str]",
                            "description": "Minimum publication date in format YYYY/MM/DD or YYYY",
                            "required": False
                        },
                        {
                            "name": "max_date",
                            "type": "Optional[str]",
                            "description": "Maximum publication date in format YYYY/MM/DD or YYYY",
                            "required": False
                        },
                        {
                            "name": "optimize_query",
                            "type": "bool",
                            "description": "Whether to optimize the query for PubMed syntax",
                            "required": False
                        }
                    ],
                    "return_type": "str",
                    "return_description": "JSON string containing search results with article metadata",
                    "dependencies": ["requests", "xml.etree.ElementTree", "json", "os", "logging"],
                    "implementation_notes": [
                        "Uses NCBI E-utilities esearch.fcgi endpoint for searching",
                        "Optimizes query with PubMed syntax when optimize_query=True",
                        "Handles rate limiting according to NCBI guidelines",
                        "Implements caching to reduce duplicate API calls"
                    ],
                    "error_handling": [
                        "Catches and reports API request failures",
                        "Handles XML parsing errors",
                        "Returns structured JSON with error information when failures occur"
                    ],
                    "usage_examples": [
                        "pubmed_search(\"cancer immunotherapy\")",
                        "pubmed_search(\"diabetes\", max_results=50, sort_by=\"pub_date\", min_date=\"2020\")"
                    ]
                },
                {
                    "tool_name": "pubmed_fetch_abstract",
                    "description": "Fetch the abstract for a specific PubMed article by its PMID",
                    "function_signature": "pubmed_fetch_abstract(pmid: str) -> str",
                    "parameters": [
                        {
                            "name": "pmid",
                            "type": "str",
                            "description": "PubMed ID of the article",
                            "required": True
                        }
                    ],
                    "return_type": "str",
                    "return_description": "JSON string containing the article abstract and metadata",
                    "dependencies": ["requests", "xml.etree.ElementTree", "json", "os", "logging"],
                    "implementation_notes": [
                        "Uses NCBI E-utilities efetch.fcgi endpoint to retrieve full article data",
                        "Parses XML response to extract abstract and metadata",
                        "Implements caching to avoid redundant API calls"
                    ],
                    "error_handling": [
                        "Handles missing abstract data gracefully",
                        "Catches XML parsing errors",
                        "Returns structured error information in JSON format"
                    ],
                    "usage_examples": [
                        "pubmed_fetch_abstract(\"34617038\")"
                    ]
                },
                {
                    "tool_name": "pubmed_advanced_search",
                    "description": "Perform an advanced search on PubMed with structured query terms and filters",
                    "function_signature": "pubmed_advanced_search(query_terms: Dict[str, str], filters: Optional[Dict[str, Any]] = None, max_results: int = 20, sort_by: str = \"relevance\") -> str",
                    "parameters": [
                        {
                            "name": "query_terms",
                            "type": "Dict[str, str]",
                            "description": "Dictionary of search fields and terms (e.g., {\"title\": \"cancer\", \"author\": \"Smith J\"})",
                            "required": True
                        },
                        {
                            "name": "filters",
                            "type": "Optional[Dict[str, Any]]",
                            "description": "Additional filters like publication types, languages, species, etc.",
                            "required": False
                        },
                        {
                            "name": "max_results",
                            "type": "int",
                            "description": "Maximum number of results to return (default: 20, max: 100)",
                            "required": False
                        },
                        {
                            "name": "sort_by",
                            "type": "str",
                            "description": "Sort order - \"relevance\", \"pub_date\", \"first_author\", or \"journal\"",
                            "required": False
                        }
                    ],
                    "return_type": "str",
                    "return_description": "JSON string containing search results with article metadata",
                    "dependencies": ["requests", "xml.etree.ElementTree", "json", "os", "logging"],
                    "implementation_notes": [
                        "Builds structured PubMed query with field tags",
                        "Supports multiple filter types including publication types, languages, and date ranges",
                        "Maps common field names to PubMed field tags"
                    ],
                    "error_handling": [
                        "Validates input parameters",
                        "Handles API errors and parsing failures",
                        "Returns structured error information"
                    ],
                    "usage_examples": [
                        "pubmed_advanced_search({\"title\": \"cancer\", \"author\": \"Smith J\"})",
                        "pubmed_advanced_search({\"journal\": \"Nature\"}, {\"publication_types\": [\"Review\"], \"date_range\": {\"min_date\": \"2020\"}})"
                    ]
                },
                {
                    "tool_name": "pubmed_fetch_citations",
                    "description": "Fetch citations for a specific PubMed article by its PMID",
                    "function_signature": "pubmed_fetch_citations(pmid: str, max_results: int = 20) -> str",
                    "parameters": [
                        {
                            "name": "pmid",
                            "type": "str",
                            "description": "PubMed ID of the article",
                            "required": True
                        },
                        {
                            "name": "max_results",
                            "type": "int",
                            "description": "Maximum number of citations to return (default: 20, max: 100)",
                            "required": False
                        }
                    ],
                    "return_type": "str",
                    "return_description": "JSON string containing the citing articles",
                    "dependencies": ["requests", "xml.etree.ElementTree", "json", "os", "logging"],
                    "implementation_notes": [
                        "Uses NCBI E-utilities elink.fcgi endpoint with citation command",
                        "Fetches summaries for citing articles after getting citation PMIDs",
                        "Limits results to the specified maximum"
                    ],
                    "error_handling": [
                        "Handles case when no citations are found",
                        "Catches XML parsing errors",
                        "Returns structured error information"
                    ],
                    "usage_examples": [
                        "pubmed_fetch_citations(\"34617038\")",
                        "pubmed_fetch_citations(\"33306283\", max_results=50)"
                    ]
                },
                {
                    "tool_name": "pubmed_fetch_related",
                    "description": "Fetch articles related to a specific PubMed article by its PMID",
                    "function_signature": "pubmed_fetch_related(pmid: str, max_results: int = 20) -> str",
                    "parameters": [
                        {
                            "name": "pmid",
                            "type": "str",
                            "description": "PubMed ID of the article",
                            "required": True
                        },
                        {
                            "name": "max_results",
                            "type": "int",
                            "description": "Maximum number of related articles to return (default: 20, max: 100)",
                            "required": False
                        }
                    ],
                    "return_type": "str",
                    "return_description": "JSON string containing the related articles",
                    "dependencies": ["requests", "xml.etree.ElementTree", "json", "os", "logging"],
                    "implementation_notes": [
                        "Uses NCBI E-utilities elink.fcgi endpoint with neighbor command",
                        "Excludes the original article from the results",
                        "Fetches summaries for related articles after getting related PMIDs"
                    ],
                    "error_handling": [
                        "Handles case when no related articles are found",
                        "Catches XML parsing errors",
                        "Returns structured error information"
                    ],
                    "usage_examples": [
                        "pubmed_fetch_related(\"34617038\")",
                        "pubmed_fetch_related(\"33306283\", max_results=30)"
                    ]
                },
                {
                    "tool_name": "pubmed_get_trending_articles",
                    "description": "Get trending or recent articles from PubMed, optionally filtered by topic",
                    "function_signature": "pubmed_get_trending_articles(topic: str = \"\", days: int = 30, max_results: int = 20) -> str",
                    "parameters": [
                        {
                            "name": "topic",
                            "type": "str",
                            "description": "Optional topic to filter articles",
                            "required": False
                        },
                        {
                            "name": "days",
                            "type": "int",
                            "description": "Number of days to look back (default: 30)",
                            "required": False
                        },
                        {
                            "name": "max_results",
                            "type": "int",
                            "description": "Maximum number of articles to return (default: 20, max: 100)",
                            "required": False
                        }
                    ],
                    "return_type": "str",
                    "return_description": "JSON string containing trending articles",
                    "dependencies": ["requests", "xml.etree.ElementTree", "json", "os", "logging", "datetime"],
                    "implementation_notes": [
                        "Calculates date range based on specified number of days",
                        "Builds query with optional topic and date range filter",
                        "Sorts results by publication date (newest first)"
                    ],
                    "error_handling": [
                        "Validates input parameters",
                        "Handles API errors",
                        "Returns structured error information"
                    ],
                    "usage_examples": [
                        "pubmed_get_trending_articles()",
                        "pubmed_get_trending_articles(\"COVID-19\", days=7)"
                    ]
                },
                {
                    "tool_name": "pubmed_rank_articles",
                    "description": "Rank a list of PubMed articles based on multiple factors",
                    "function_signature": "pubmed_rank_articles(pmids: List[str], ranking_factors: Dict[str, float] = None) -> str",
                    "parameters": [
                        {
                            "name": "pmids",
                            "type": "List[str]",
                            "description": "List of PubMed IDs to rank",
                            "required": True
                        },
                        {
                            "name": "ranking_factors",
                            "type": "Dict[str, float]",
                            "description": "Weighting factors for ranking (recency, journal_impact, citation_count, relevance)",
                            "required": False
                        }
                    ],
                    "return_type": "str",
                    "return_description": "JSON string containing ranked articles with scores",
                    "dependencies": ["requests", "xml.etree.ElementTree", "json", "os", "logging", "datetime", "re"],
                    "implementation_notes": [
                        "Calculates scores based on multiple factors: recency, journal impact, citation count, and relevance",
                        "Fetches citation counts for each article",
                        "Uses simplified journal impact approximation",
                        "Normalizes scores to 0-100 scale"
                    ],
                    "error_handling": [
                        "Handles empty PMID list",
                        "Catches errors when fetching citation counts",
                        "Returns structured error information"
                    ],
                    "usage_examples": [
                        "pubmed_rank_articles([\"34617038\", \"33306283\", \"32887982\"])",
                        "pubmed_rank_articles([\"34617038\", \"33306283\"], {\"recency\": 2.0, \"citation_count\": 1.5})"
                    ]
                },
                {
                    "tool_name": "pubmed_get_author_publications",
                    "description": "Get publications by a specific author from PubMed",
                    "function_signature": "pubmed_get_author_publications(author_name: str, max_results: int = 20) -> str",
                    "parameters": [
                        {
                            "name": "author_name",
                            "type": "str",
                            "description": "Author name to search for (format: \"Last FM\" or \"Last F\")",
                            "required": True
                        },
                        {
                            "name": "max_results",
                            "type": "int",
                            "description": "Maximum number of publications to return (default: 20, max: 100)",
                            "required": False
                        }
                    ],
                    "return_type": "str",
                    "return_description": "JSON string containing the author's publications",
                    "dependencies": ["requests", "xml.etree.ElementTree", "json", "os", "logging"],
                    "implementation_notes": [
                        "Formats author name with [Author] field tag if not already present",
                        "Sorts results by publication date (newest first)",
                        "Returns complete publication metadata"
                    ],
                    "error_handling": [
                        "Validates author name format",
                        "Handles case when no publications are found",
                        "Returns structured error information"
                    ],
                    "usage_examples": [
                        "pubmed_get_author_publications(\"Smith JD\")",
                        "pubmed_get_author_publications(\"Fauci A\", max_results=50)"
                    ]
                }
            ],
            "code_quality": {
                "code_standards": [
                    "PEP 8 compliant code style",
                    "Comprehensive type annotations",
                    "Detailed docstrings for all functions and classes",
                    "Consistent error handling patterns",
                    "Proper logging for debugging and monitoring"
                ],
                "testing_strategy": [
                    "Unit tests for each tool function",
                    "Mock API responses for testing without actual API calls",
                    "Edge case testing for error handling",
                    "Integration tests for end-to-end functionality"
                ],
                "performance_considerations": [
                    "Caching system to minimize redundant API calls",
                    "Rate limiting to comply with NCBI guidelines",
                    "Efficient XML parsing",
                    "Optimized memory usage for large result sets"
                ],
                "security_measures": [
                    "Input validation to prevent injection attacks",
                    "Secure API key handling via environment variables",
                    "Protection against XML parsing vulnerabilities",
                    "Cache file security with proper permissions"
                ]
            },
            "integration_details": {
                "aws_services": [],
                "external_libraries": [
                    "requests - For HTTP API calls",
                    "xml.etree.ElementTree - For XML parsing"
                ],
                "api_endpoints": [
                    "NCBI E-utilities esearch.fcgi - For searching articles",
                    "NCBI E-utilities esummary.fcgi - For retrieving article summaries",
                    "NCBI E-utilities efetch.fcgi - For fetching full article data",
                    "NCBI E-utilities elink.fcgi - For citations and related articles"
                ],
                "data_formats": [
                    "XML - PubMed API response format",
                    "JSON - Tool output format"
                ]
            },
            "development_notes": "The PubMed API integration tool was developed to provide comprehensive access to the PubMed database through the NCBI E-utilities API. Key considerations included adherence to NCBI's rate limiting guidelines, efficient caching to minimize API calls, and robust error handling. The tool set provides a complete solution for searching articles, retrieving abstracts, finding related articles, tracking citations, and ranking articles based on multiple relevance factors. The implementation follows best practices for Python development with complete type annotations, comprehensive documentation, and structured error handling."
        }
    }
    
    return json.dumps(documentation, indent=2)