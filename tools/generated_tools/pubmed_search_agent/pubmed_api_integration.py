#!/usr/bin/env python3
"""
PubMed API Integration Tool

This tool provides integration with the PubMed/NCBI E-utilities API for searching medical literature,
retrieving article metadata, and extracting abstracts. It handles API rate limits, pagination,
and implements caching to minimize API calls.
"""

import json
import time
import hashlib
import requests
import logging
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode
from functools import lru_cache
from strands import tool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pubmed_api_tool")

# NCBI E-utilities base URLs
EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ESEARCH_URL = f"{EUTILS_BASE_URL}/esearch.fcgi"
EFETCH_URL = f"{EUTILS_BASE_URL}/efetch.fcgi"
ESUMMARY_URL = f"{EUTILS_BASE_URL}/esummary.fcgi"
ELINK_URL = f"{EUTILS_BASE_URL}/elink.fcgi"

# API rate limits
# NCBI recommends no more than 3 requests per second
REQUEST_DELAY = 0.34  # ~3 requests per second
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# In-memory cache for API responses
CACHE = {}
CACHE_EXPIRY = 3600  # 1 hour in seconds


def _generate_cache_key(url: str, params: Dict[str, Any]) -> str:
    """Generate a unique cache key based on URL and parameters."""
    param_str = json.dumps(params, sort_keys=True)
    key_str = f"{url}:{param_str}"
    return hashlib.md5(key_str.encode()).hexdigest()


def _get_cached_response(cache_key: str) -> Optional[Dict[str, Any]]:
    """Retrieve a cached response if it exists and is not expired."""
    if cache_key in CACHE:
        timestamp, data = CACHE[cache_key]
        if time.time() - timestamp < CACHE_EXPIRY:
            return data
    return None


def _cache_response(cache_key: str, data: Dict[str, Any]) -> None:
    """Cache an API response with the current timestamp."""
    CACHE[cache_key] = (time.time(), data)


def _make_api_request(url: str, params: Dict[str, Any], use_cache: bool = True) -> Dict[str, Any]:
    """Make a request to the NCBI E-utilities API with rate limiting and caching."""
    # Add common parameters
    params.update({
        "retmode": "json",
        "tool": "pubmed_search_agent",
        "email": "agent@example.com"  # Should be replaced with a valid email in production
    })
    
    # Check cache first if enabled
    if use_cache:
        cache_key = _generate_cache_key(url, params)
        cached_data = _get_cached_response(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for {url}")
            return cached_data
    
    # Implement rate limiting
    time.sleep(REQUEST_DELAY)
    
    # Make the request with retries
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse the response
            try:
                data = response.json()
            except ValueError:
                # Some NCBI endpoints return XML by default
                data = {"raw_content": response.text}
            
            # Cache the successful response
            if use_cache:
                cache_key = _generate_cache_key(url, params)
                _cache_response(cache_key, data)
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
            else:
                raise Exception(f"API request failed after {MAX_RETRIES} attempts: {str(e)}")


def _optimize_search_query(query: str) -> str:
    """
    Optimize a search query for PubMed by adding MeSH terms and other enhancements.
    
    Args:
        query: The original search query
        
    Returns:
        An optimized search query
    """
    # This is a simplified implementation
    # In a production system, this could be expanded with:
    # - MeSH term mapping
    # - Field tags
    # - Boolean operators
    
    # Add field tags if not present
    if "[" not in query:
        # Try to identify if this is an author search
        if re.search(r'\b[A-Z][a-z]+ [A-Z]\b', query) or re.search(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', query):
            query += "[Author]"
        # If it contains year references
        elif re.search(r'\b(19|20)\d{2}\b', query):
            # Extract the year and format properly
            year_match = re.search(r'\b(19|20)\d{2}\b', query)
            if year_match:
                year = year_match.group(0)
                # Remove the year from the original query
                query = query.replace(year, "")
                query = query.strip() + f" AND {year}[Publication Date]"
    
    return query


def _extract_article_metadata(article_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and format article metadata from PubMed API response.
    
    Args:
        article_data: Raw article data from PubMed API
        
    Returns:
        Formatted article metadata
    """
    metadata = {}
    
    # Extract PubMed ID
    metadata["pmid"] = article_data.get("uid", "")
    
    # Extract basic metadata
    if "title" in article_data:
        metadata["title"] = article_data["title"]
    
    # Extract authors
    authors = []
    if "authors" in article_data:
        for author in article_data["authors"]:
            if "name" in author:
                authors.append(author["name"])
    metadata["authors"] = authors
    
    # Extract journal information
    if "fulljournalname" in article_data:
        metadata["journal"] = article_data["fulljournalname"]
    elif "source" in article_data:
        metadata["journal"] = article_data["source"]
    
    # Extract publication date
    if "pubdate" in article_data:
        metadata["publication_date"] = article_data["pubdate"]
    
    # Extract DOI
    if "elocationid" in article_data and article_data["elocationid"].startswith("doi:"):
        metadata["doi"] = article_data["elocationid"].replace("doi:", "")
    elif "articleids" in article_data:
        for id_obj in article_data["articleids"]:
            if id_obj.get("idtype") == "doi":
                metadata["doi"] = id_obj.get("value", "")
    
    # Extract volume, issue, pages
    if "volume" in article_data:
        metadata["volume"] = article_data["volume"]
    if "issue" in article_data:
        metadata["issue"] = article_data["issue"]
    if "pages" in article_data:
        metadata["pages"] = article_data["pages"]
    
    return metadata


def _extract_abstract(article_data: Dict[str, Any]) -> str:
    """
    Extract the abstract from article data.
    
    Args:
        article_data: Article data from PubMed API
        
    Returns:
        The article abstract or empty string if not available
    """
    # Check different possible locations of the abstract
    if "abstracttext" in article_data:
        return article_data["abstracttext"]
    elif "abstract" in article_data:
        if isinstance(article_data["abstract"], str):
            return article_data["abstract"]
        elif isinstance(article_data["abstract"], list):
            return " ".join(article_data["abstract"])
        elif isinstance(article_data["abstract"], dict) and "abstracttext" in article_data["abstract"]:
            abstract_text = article_data["abstract"]["abstracttext"]
            if isinstance(abstract_text, list):
                return " ".join([item.get("content", "") for item in abstract_text if "content" in item])
            return abstract_text
    
    # For XML responses that were converted to text
    if "raw_content" in article_data:
        # Simple regex-based extraction (not ideal but works as fallback)
        abstract_match = re.search(r'<Abstract>(.*?)</Abstract>', article_data["raw_content"], re.DOTALL)
        if abstract_match:
            # Remove XML tags
            abstract = re.sub(r'<[^>]+>', ' ', abstract_match.group(1))
            # Clean up whitespace
            abstract = re.sub(r'\s+', ' ', abstract).strip()
            return abstract
    
    return ""


@tool
def pubmed_search(query: str, max_results: int = 10, sort_by: str = "relevance", 
                  publication_date_range: str = None, use_cache: bool = True) -> str:
    """
    Search PubMed database for medical literature.
    
    Args:
        query: Search query (can include MeSH terms, author names, keywords)
        max_results: Maximum number of results to return (default: 10)
        sort_by: Sort order - "relevance", "date" (default: "relevance")
        publication_date_range: Date range filter (e.g., "2020:2023", "2023/01/01:2023/12/31")
        use_cache: Whether to use cached results if available (default: True)
        
    Returns:
        JSON string containing search results with article metadata
    """
    try:
        # Optimize the search query
        optimized_query = _optimize_search_query(query)
        
        # Prepare search parameters
        search_params = {
            "db": "pubmed",
            "term": optimized_query,
            "retmax": max_results,
            "usehistory": "y"
        }
        
        # Add date range if provided
        if publication_date_range:
            search_params["datetype"] = "pdat"
            search_params["date"] = publication_date_range
        
        # Add sort parameter
        if sort_by == "date":
            search_params["sort"] = "date"
        
        # Execute the search
        search_result = _make_api_request(ESEARCH_URL, search_params, use_cache)
        
        # Check if we have results
        if "esearchresult" not in search_result:
            return json.dumps({"error": "Invalid response from PubMed API", "results": []})
        
        esearch_result = search_result["esearchresult"]
        total_results = int(esearch_result.get("count", 0))
        
        if total_results == 0:
            return json.dumps({
                "query": query,
                "optimized_query": optimized_query,
                "total_results": 0,
                "results": []
            })
        
        # Get the list of IDs
        id_list = esearch_result.get("idlist", [])
        
        # Get WebEnv and QueryKey for retrieving full records
        web_env = esearch_result.get("webenv", "")
        query_key = esearch_result.get("querykey", "")
        
        # Fetch summaries for the IDs
        summary_params = {
            "db": "pubmed",
            "id": ",".join(id_list) if id_list else "",
            "WebEnv": web_env,
            "query_key": query_key
        }
        
        summary_result = _make_api_request(ESUMMARY_URL, summary_params, use_cache)
        
        # Process results
        results = []
        if "result" in summary_result:
            for pmid, article_data in summary_result["result"].items():
                if pmid == "uids":
                    continue
                
                # Extract metadata
                metadata = _extract_article_metadata(article_data)
                
                # Add abstract (requires a separate API call)
                abstract = ""
                try:
                    efetch_params = {
                        "db": "pubmed",
                        "id": pmid,
                        "rettype": "abstract",
                        "retmode": "xml"  # XML format often contains more complete data
                    }
                    abstract_result = _make_api_request(EFETCH_URL, efetch_params, use_cache)
                    abstract = _extract_abstract(abstract_result)
                    metadata["abstract"] = abstract
                except Exception as e:
                    logger.warning(f"Failed to fetch abstract for PMID {pmid}: {str(e)}")
                    metadata["abstract"] = ""
                
                results.append(metadata)
        
        # Return the formatted results
        return json.dumps({
            "query": query,
            "optimized_query": optimized_query,
            "total_results": total_results,
            "displayed_results": len(results),
            "results": results
        }, indent=2)
        
    except Exception as e:
        logger.error(f"PubMed search error: {str(e)}")
        return json.dumps({
            "error": f"Search failed: {str(e)}",
            "query": query,
            "results": []
        })


@tool
def pubmed_get_article(pmid: str, include_references: bool = False, 
                       include_citations: bool = False, use_cache: bool = True) -> str:
    """
    Retrieve detailed information about a specific PubMed article.
    
    Args:
        pmid: PubMed ID of the article
        include_references: Whether to include the article's references (default: False)
        include_citations: Whether to include articles that cite this one (default: False)
        use_cache: Whether to use cached results if available (default: True)
        
    Returns:
        JSON string containing detailed article information
    """
    try:
        # Fetch the article data
        fetch_params = {
            "db": "pubmed",
            "id": pmid,
            "rettype": "full",
            "retmode": "xml"  # XML format often contains more complete data
        }
        
        article_result = _make_api_request(EFETCH_URL, fetch_params, use_cache)
        
        # Convert XML to structured data if needed
        if isinstance(article_result, dict) and "raw_content" in article_result:
            # This is a simplified approach - in production, use a proper XML parser
            xml_content = article_result["raw_content"]
            
            # Extract basic metadata using regex (simplified)
            title_match = re.search(r'<ArticleTitle>(.*?)</ArticleTitle>', xml_content, re.DOTALL)
            title = title_match.group(1) if title_match else ""
            
            # Extract authors
            authors = []
            author_matches = re.finditer(r'<Author[^>]*>(.*?)</Author>', xml_content, re.DOTALL)
            for author_match in author_matches:
                author_content = author_match.group(1)
                last_name_match = re.search(r'<LastName>(.*?)</LastName>', author_content)
                fore_name_match = re.search(r'<ForeName>(.*?)</ForeName>', author_content)
                if last_name_match:
                    author_name = last_name_match.group(1)
                    if fore_name_match:
                        author_name = f"{fore_name_match.group(1)} {author_name}"
                    authors.append(author_name)
            
            # Extract journal info
            journal_match = re.search(r'<Journal>(.*?)</Journal>', xml_content, re.DOTALL)
            journal_title = ""
            if journal_match:
                journal_content = journal_match.group(1)
                journal_title_match = re.search(r'<Title>(.*?)</Title>', journal_content)
                journal_title = journal_title_match.group(1) if journal_title_match else ""
            
            # Extract abstract
            abstract = _extract_abstract({"raw_content": xml_content})
            
            # Create structured article data
            article_data = {
                "pmid": pmid,
                "title": title,
                "authors": authors,
                "journal": journal_title,
                "abstract": abstract
            }
        else:
            # If we got JSON data directly
            article_data = _extract_article_metadata(article_result.get("result", {}).get(pmid, {}))
            article_data["abstract"] = _extract_abstract(article_result.get("result", {}).get(pmid, {}))
        
        # Fetch references if requested
        if include_references:
            try:
                ref_params = {
                    "dbfrom": "pubmed",
                    "db": "pubmed",
                    "id": pmid,
                    "linkname": "pubmed_pubmed_refs"
                }
                ref_result = _make_api_request(ELINK_URL, ref_params, use_cache)
                
                # Extract reference IDs
                reference_ids = []
                if "linksets" in ref_result:
                    for linkset in ref_result["linksets"]:
                        if "linksetdbs" in linkset:
                            for linksetdb in linkset["linksetdbs"]:
                                if linksetdb.get("linkname") == "pubmed_pubmed_refs":
                                    reference_ids.extend(linksetdb.get("links", []))
                
                # Get basic info for each reference
                references = []
                if reference_ids:
                    # Batch the references to avoid large requests
                    batch_size = 20
                    for i in range(0, len(reference_ids), batch_size):
                        batch_ids = reference_ids[i:i+batch_size]
                        summary_params = {
                            "db": "pubmed",
                            "id": ",".join(map(str, batch_ids))
                        }
                        summary_result = _make_api_request(ESUMMARY_URL, summary_params, use_cache)
                        
                        if "result" in summary_result:
                            for ref_id, ref_data in summary_result["result"].items():
                                if ref_id == "uids":
                                    continue
                                ref_metadata = _extract_article_metadata(ref_data)
                                references.append(ref_metadata)
                
                article_data["references"] = references
                article_data["reference_count"] = len(references)
            except Exception as e:
                logger.warning(f"Failed to fetch references for PMID {pmid}: {str(e)}")
                article_data["references"] = []
                article_data["reference_count"] = 0
        
        # Fetch citations if requested
        if include_citations:
            try:
                cite_params = {
                    "dbfrom": "pubmed",
                    "db": "pubmed",
                    "id": pmid,
                    "linkname": "pubmed_pubmed_citedin"
                }
                cite_result = _make_api_request(ELINK_URL, cite_params, use_cache)
                
                # Extract citation IDs
                citation_ids = []
                if "linksets" in cite_result:
                    for linkset in cite_result["linksets"]:
                        if "linksetdbs" in linkset:
                            for linksetdb in linkset["linksetdbs"]:
                                if linksetdb.get("linkname") == "pubmed_pubmed_citedin":
                                    citation_ids.extend(linksetdb.get("links", []))
                
                # Get basic info for each citation
                citations = []
                if citation_ids:
                    # Batch the citations to avoid large requests
                    batch_size = 20
                    for i in range(0, len(citation_ids), batch_size):
                        batch_ids = citation_ids[i:i+batch_size]
                        summary_params = {
                            "db": "pubmed",
                            "id": ",".join(map(str, batch_ids))
                        }
                        summary_result = _make_api_request(ESUMMARY_URL, summary_params, use_cache)
                        
                        if "result" in summary_result:
                            for cite_id, cite_data in summary_result["result"].items():
                                if cite_id == "uids":
                                    continue
                                cite_metadata = _extract_article_metadata(cite_data)
                                citations.append(cite_metadata)
                
                article_data["citations"] = citations
                article_data["citation_count"] = len(citations)
            except Exception as e:
                logger.warning(f"Failed to fetch citations for PMID {pmid}: {str(e)}")
                article_data["citations"] = []
                article_data["citation_count"] = 0
        
        return json.dumps(article_data, indent=2)
        
    except Exception as e:
        logger.error(f"Error retrieving article {pmid}: {str(e)}")
        return json.dumps({
            "error": f"Failed to retrieve article: {str(e)}",
            "pmid": pmid
        })


@tool
def pubmed_advanced_search(
    keywords: str = None,
    authors: str = None,
    journal: str = None,
    publication_date_range: str = None,
    article_types: List[str] = None,
    mesh_terms: List[str] = None,
    max_results: int = 20,
    page: int = 1,
    use_cache: bool = True
) -> str:
    """
    Perform an advanced search on PubMed with multiple filters.
    
    Args:
        keywords: Search terms for article content
        authors: Author names (comma-separated)
        journal: Journal name or abbreviation
        publication_date_range: Date range (e.g., "2020:2023", "2023/01/01:2023/12/31")
        article_types: List of article types (e.g., ["Review", "Clinical Trial"])
        mesh_terms: List of MeSH terms to include
        max_results: Maximum number of results per page (default: 20)
        page: Page number for pagination (default: 1)
        use_cache: Whether to use cached results if available (default: True)
        
    Returns:
        JSON string containing search results with pagination info
    """
    try:
        # Build the query
        query_parts = []
        
        if keywords:
            query_parts.append(f"({keywords})")
        
        if authors:
            author_list = [f"{author.strip()}[Author]" for author in authors.split(",")]
            query_parts.append(f"({' OR '.join(author_list)})")
        
        if journal:
            query_parts.append(f"({journal}[Journal])")
        
        if article_types:
            article_type_parts = [f"{art_type}[Publication Type]" for art_type in article_types]
            query_parts.append(f"({' OR '.join(article_type_parts)})")
        
        if mesh_terms:
            mesh_parts = [f"{term}[MeSH Terms]" for term in mesh_terms]
            query_parts.append(f"({' OR '.join(mesh_parts)})")
        
        # Combine all parts with AND
        if query_parts:
            full_query = " AND ".join(query_parts)
        else:
            return json.dumps({
                "error": "No search criteria provided",
                "results": []
            })
        
        # Calculate offsets for pagination
        offset = (page - 1) * max_results
        
        # Prepare search parameters
        search_params = {
            "db": "pubmed",
            "term": full_query,
            "retmax": max_results,
            "retstart": offset,
            "usehistory": "y"
        }
        
        # Add date range if provided
        if publication_date_range:
            search_params["datetype"] = "pdat"
            search_params["date"] = publication_date_range
        
        # Execute the search
        search_result = _make_api_request(ESEARCH_URL, search_params, use_cache)
        
        # Check if we have results
        if "esearchresult" not in search_result:
            return json.dumps({"error": "Invalid response from PubMed API", "results": []})
        
        esearch_result = search_result["esearchresult"]
        total_results = int(esearch_result.get("count", 0))
        
        if total_results == 0:
            return json.dumps({
                "query": full_query,
                "total_results": 0,
                "page": page,
                "max_results": max_results,
                "total_pages": 0,
                "results": []
            })
        
        # Calculate pagination info
        total_pages = (total_results + max_results - 1) // max_results
        
        # Get the list of IDs
        id_list = esearch_result.get("idlist", [])
        
        # Fetch summaries for the IDs
        summary_params = {
            "db": "pubmed",
            "id": ",".join(id_list)
        }
        
        summary_result = _make_api_request(ESUMMARY_URL, summary_params, use_cache)
        
        # Process results
        results = []
        if "result" in summary_result:
            for pmid, article_data in summary_result["result"].items():
                if pmid == "uids":
                    continue
                
                # Extract metadata
                metadata = _extract_article_metadata(article_data)
                
                # Add abstract (requires a separate API call)
                try:
                    efetch_params = {
                        "db": "pubmed",
                        "id": pmid,
                        "rettype": "abstract",
                        "retmode": "xml"
                    }
                    abstract_result = _make_api_request(EFETCH_URL, efetch_params, use_cache)
                    abstract = _extract_abstract(abstract_result)
                    metadata["abstract"] = abstract
                except Exception as e:
                    logger.warning(f"Failed to fetch abstract for PMID {pmid}: {str(e)}")
                    metadata["abstract"] = ""
                
                results.append(metadata)
        
        # Return the formatted results with pagination info
        return json.dumps({
            "query": full_query,
            "total_results": total_results,
            "page": page,
            "max_results": max_results,
            "total_pages": total_pages,
            "has_next_page": page < total_pages,
            "has_prev_page": page > 1,
            "results": results
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Advanced search error: {str(e)}")
        return json.dumps({
            "error": f"Search failed: {str(e)}",
            "results": []
        })


@tool
def pubmed_rank_articles(pmids: List[str], ranking_factors: Dict[str, float] = None, 
                         use_cache: bool = True) -> str:
    """
    Rank PubMed articles based on multiple factors.
    
    Args:
        pmids: List of PubMed IDs to rank
        ranking_factors: Dictionary of factors and their weights (e.g., {"recency": 0.5, "citation_count": 0.3, "journal_impact": 0.2})
        use_cache: Whether to use cached results if available (default: True)
        
    Returns:
        JSON string containing ranked articles with scores
    """
    try:
        if not pmids:
            return json.dumps({
                "error": "No PMIDs provided",
                "ranked_articles": []
            })
        
        # Default ranking factors if not provided
        if not ranking_factors:
            ranking_factors = {
                "recency": 0.5,        # More recent articles score higher
                "citation_count": 0.3,  # More cited articles score higher
                "relevance": 0.2       # Based on original search relevance
            }
        
        # Normalize weights to sum to 1
        total_weight = sum(ranking_factors.values())
        if total_weight > 0:
            for factor in ranking_factors:
                ranking_factors[factor] /= total_weight
        
        # Fetch data for all articles
        articles = []
        for i, pmid in enumerate(pmids):
            # Fetch article data
            summary_params = {
                "db": "pubmed",
                "id": pmid
            }
            
            summary_result = _make_api_request(ESUMMARY_URL, summary_params, use_cache)
            
            if "result" not in summary_result or pmid not in summary_result["result"]:
                logger.warning(f"Could not fetch data for PMID {pmid}")
                continue
            
            article_data = summary_result["result"][pmid]
            
            # Extract metadata
            metadata = _extract_article_metadata(article_data)
            
            # Add original position for relevance scoring
            metadata["original_position"] = i
            
            # Get publication year for recency calculation
            pub_year = datetime.now().year  # Default to current year
            if "pubdate" in article_data:
                pub_date_str = article_data["pubdate"]
                year_match = re.search(r'\b(19|20)\d{2}\b', pub_date_str)
                if year_match:
                    pub_year = int(year_match.group(0))
            metadata["publication_year"] = pub_year
            
            # Get citation count if needed
            if "citation_count" in ranking_factors and ranking_factors["citation_count"] > 0:
                try:
                    cite_params = {
                        "dbfrom": "pubmed",
                        "db": "pubmed",
                        "id": pmid,
                        "linkname": "pubmed_pubmed_citedin"
                    }
                    cite_result = _make_api_request(ELINK_URL, cite_params, use_cache)
                    
                    citation_count = 0
                    if "linksets" in cite_result:
                        for linkset in cite_result["linksets"]:
                            if "linksetdbs" in linkset:
                                for linksetdb in linkset["linksetdbs"]:
                                    if linksetdb.get("linkname") == "pubmed_pubmed_citedin":
                                        citation_count = len(linksetdb.get("links", []))
                    
                    metadata["citation_count"] = citation_count
                except Exception as e:
                    logger.warning(f"Failed to fetch citation count for PMID {pmid}: {str(e)}")
                    metadata["citation_count"] = 0
            else:
                metadata["citation_count"] = 0
            
            articles.append(metadata)
        
        # Calculate scores for each article
        current_year = datetime.now().year
        max_citations = max([a.get("citation_count", 0) for a in articles]) if articles else 1
        
        for article in articles:
            score = 0
            
            # Recency score (0-1)
            if "recency" in ranking_factors and ranking_factors["recency"] > 0:
                years_old = current_year - article.get("publication_year", current_year)
                recency_score = max(0, 1 - (years_old / 10))  # Linear decay over 10 years
                score += recency_score * ranking_factors["recency"]
            
            # Citation count score (0-1)
            if "citation_count" in ranking_factors and ranking_factors["citation_count"] > 0:
                citation_score = article.get("citation_count", 0) / max(1, max_citations)
                score += citation_score * ranking_factors["citation_count"]
            
            # Relevance score based on original position (0-1)
            if "relevance" in ranking_factors and ranking_factors["relevance"] > 0:
                total_articles = len(pmids)
                position = article.get("original_position", 0)
                relevance_score = 1 - (position / total_articles) if total_articles > 0 else 0
                score += relevance_score * ranking_factors["relevance"]
            
            article["score"] = round(score, 3)
        
        # Sort articles by score (descending)
        ranked_articles = sorted(articles, key=lambda x: x.get("score", 0), reverse=True)
        
        # Remove temporary fields used for scoring
        for article in ranked_articles:
            article.pop("original_position", None)
        
        return json.dumps({
            "ranking_factors": ranking_factors,
            "ranked_articles": ranked_articles
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Article ranking error: {str(e)}")
        return json.dumps({
            "error": f"Ranking failed: {str(e)}",
            "ranked_articles": []
        })


@tool
def pubmed_clear_cache() -> str:
    """
    Clear the PubMed API response cache.
    
    Returns:
        JSON string with cache clearing result
    """
    try:
        cache_size = len(CACHE)
        CACHE.clear()
        
        return json.dumps({
            "success": True,
            "message": f"Cache cleared successfully. {cache_size} entries removed.",
            "cache_size_before": cache_size,
            "cache_size_after": 0
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to clear cache: {str(e)}"
        })


@tool
def pubmed_get_mesh_terms(query: str, max_terms: int = 10, use_cache: bool = True) -> str:
    """
    Get relevant MeSH (Medical Subject Headings) terms for a search query.
    
    Args:
        query: Search query to find relevant MeSH terms
        max_terms: Maximum number of MeSH terms to return (default: 10)
        use_cache: Whether to use cached results if available (default: True)
        
    Returns:
        JSON string containing relevant MeSH terms
    """
    try:
        # First search for articles matching the query
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": 20,  # Get a reasonable sample of articles
            "usehistory": "y"
        }
        
        search_result = _make_api_request(ESEARCH_URL, search_params, use_cache)
        
        if "esearchresult" not in search_result:
            return json.dumps({"error": "Invalid response from PubMed API", "mesh_terms": []})
        
        esearch_result = search_result["esearchresult"]
        id_list = esearch_result.get("idlist", [])
        
        if not id_list:
            return json.dumps({
                "query": query,
                "mesh_terms": []
            })
        
        # Collect MeSH terms from these articles
        mesh_terms = {}
        for pmid in id_list:
            try:
                # Fetch full article data to get MeSH terms
                efetch_params = {
                    "db": "pubmed",
                    "id": pmid,
                    "rettype": "full",
                    "retmode": "xml"
                }
                
                article_result = _make_api_request(EFETCH_URL, efetch_params, use_cache)
                
                # Extract MeSH terms from XML
                if "raw_content" in article_result:
                    xml_content = article_result["raw_content"]
                    mesh_heading_matches = re.finditer(r'<MeshHeading>(.*?)</MeshHeading>', xml_content, re.DOTALL)
                    
                    for mesh_heading_match in mesh_heading_matches:
                        mesh_heading = mesh_heading_match.group(1)
                        descriptor_match = re.search(r'<DescriptorName[^>]*>(.*?)</DescriptorName>', mesh_heading)
                        
                        if descriptor_match:
                            term = descriptor_match.group(1).strip()
                            if term:
                                mesh_terms[term] = mesh_terms.get(term, 0) + 1
            except Exception as e:
                logger.warning(f"Failed to extract MeSH terms from PMID {pmid}: {str(e)}")
        
        # Sort MeSH terms by frequency
        sorted_terms = sorted(mesh_terms.items(), key=lambda x: x[1], reverse=True)
        
        # Format the results
        result_terms = []
        for term, frequency in sorted_terms[:max_terms]:
            result_terms.append({
                "term": term,
                "frequency": frequency
            })
        
        return json.dumps({
            "query": query,
            "mesh_terms": result_terms
        }, indent=2)
        
    except Exception as e:
        logger.error(f"MeSH terms error: {str(e)}")
        return json.dumps({
            "error": f"Failed to retrieve MeSH terms: {str(e)}",
            "query": query,
            "mesh_terms": []
        })