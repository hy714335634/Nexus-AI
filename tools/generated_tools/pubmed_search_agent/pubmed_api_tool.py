#!/usr/bin/env python3
"""
PubMed API Integration Tool

This module provides tools for searching and retrieving scientific articles
from the PubMed/NCBI E-utilities API.
"""

import json
import time
import re
import os
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
import requests
from urllib.parse import urlencode
import logging
from strands import tool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
DEFAULT_RETMAX = 20
MAX_RETMAX = 100
DEFAULT_CACHE_DIR = ".pubmed_cache"
DEFAULT_CACHE_EXPIRY = 24  # hours
API_KEY_ENV_VAR = "PUBMED_API_KEY"
DEFAULT_DELAY = 0.34  # seconds between requests (3 requests per second without API key)
DEFAULT_DELAY_WITH_KEY = 0.1  # seconds between requests with API key (10 requests per second)

# Initialize cache directory
os.makedirs(DEFAULT_CACHE_DIR, exist_ok=True)


class PubMedRateLimiter:
    """Rate limiter for PubMed API requests"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.last_request_time = 0
        self.delay = DEFAULT_DELAY_WITH_KEY if api_key else DEFAULT_DELAY
    
    def wait(self):
        """Wait appropriate time to respect rate limits"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        
        self.last_request_time = time.time()


class PubMedCache:
    """Cache manager for PubMed API responses"""
    
    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR, expiry_hours: int = DEFAULT_CACHE_EXPIRY):
        self.cache_dir = cache_dir
        self.expiry_hours = expiry_hours
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_cache_key(self, url: str, params: Dict[str, Any]) -> str:
        """Generate a cache key from URL and parameters"""
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(f"{url}:{param_str}".encode()).hexdigest()
    
    def get_cache_path(self, cache_key: str) -> str:
        """Get the file path for a cache key"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def get(self, url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached response if it exists and is not expired"""
        cache_key = self.get_cache_key(url, params)
        cache_path = self.get_cache_path(cache_key)
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            # Check if cache is expired
            cached_time = datetime.fromisoformat(cached_data.get('cached_at', ''))
            if datetime.now() - cached_time > timedelta(hours=self.expiry_hours):
                return None
            
            return cached_data
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
    
    def set(self, url: str, params: Dict[str, Any], data: Dict[str, Any]) -> None:
        """Cache response data"""
        cache_key = self.get_cache_key(url, params)
        cache_path = self.get_cache_path(cache_key)
        
        # Add cache metadata
        data['cached_at'] = datetime.now().isoformat()
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write to cache: {e}")


class PubMedClient:
    """Client for interacting with PubMed/NCBI E-utilities API"""
    
    def __init__(self, api_key: Optional[str] = None, use_cache: bool = True):
        self.api_key = api_key
        self.rate_limiter = PubMedRateLimiter(api_key)
        self.use_cache = use_cache
        self.cache = PubMedCache() if use_cache else None
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to the PubMed API with rate limiting and caching"""
        url = f"{BASE_URL}{endpoint}"
        
        # Add API key if available
        if self.api_key:
            params['api_key'] = self.api_key
        
        # Check cache first
        if self.use_cache:
            cached_response = self.cache.get(url, params)
            if cached_response:
                return cached_response
        
        # Respect rate limits
        self.rate_limiter.wait()
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse response based on format
            if endpoint in ['esearch.fcgi', 'esummary.fcgi']:
                result = self._parse_response(response.text, endpoint)
            else:
                result = {'raw_text': response.text}
            
            # Cache the result
            if self.use_cache:
                self.cache.set(url, params, result)
            
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return {"error": str(e)}
    
    def _parse_response(self, response_text: str, endpoint: str) -> Dict[str, Any]:
        """Parse XML response from PubMed API"""
        try:
            root = ET.fromstring(response_text)
            
            if endpoint == 'esearch.fcgi':
                # Parse search results
                count = int(root.find('.//Count').text) if root.find('.//Count') is not None else 0
                pmids = [id_elem.text for id_elem in root.findall('.//Id')]
                
                return {
                    'count': count,
                    'pmids': pmids,
                    'raw_xml': response_text
                }
            
            elif endpoint == 'esummary.fcgi':
                # Parse article summaries
                articles = []
                
                for doc in root.findall('.//DocSum'):
                    article = {'pmid': doc.find('./Id').text if doc.find('./Id') is not None else ''}
                    
                    for item in doc.findall('./Item'):
                        name = item.get('Name')
                        item_type = item.get('Type')
                        
                        if item_type == 'List':
                            article[name] = [subitem.text for subitem in item.findall('./Item')]
                        else:
                            article[name] = item.text
                    
                    articles.append(article)
                
                return {
                    'articles': articles,
                    'raw_xml': response_text
                }
            
            return {'raw_xml': response_text}
        except ET.ParseError:
            logger.warning("Failed to parse XML response")
            return {'raw_text': response_text}
    
    def search(self, query: str, retmax: int = DEFAULT_RETMAX, retstart: int = 0, 
               sort: str = 'relevance', min_date: Optional[str] = None, 
               max_date: Optional[str] = None) -> Dict[str, Any]:
        """Search PubMed for articles matching the query"""
        params = {
            'db': 'pubmed',
            'term': query,
            'retmode': 'xml',
            'retmax': min(retmax, MAX_RETMAX),
            'retstart': retstart,
            'sort': sort
        }
        
        # Add date filters if provided
        if min_date:
            params['mindate'] = min_date
        if max_date:
            params['maxdate'] = max_date
        
        return self._make_request('esearch.fcgi', params)
    
    def fetch_summaries(self, pmids: List[str]) -> Dict[str, Any]:
        """Fetch article summaries for a list of PMIDs"""
        if not pmids:
            return {"error": "No PMIDs provided"}
        
        params = {
            'db': 'pubmed',
            'id': ','.join(pmids),
            'retmode': 'xml'
        }
        
        return self._make_request('esummary.fcgi', params)
    
    def fetch_article(self, pmid: str) -> Dict[str, Any]:
        """Fetch full article data for a PMID"""
        params = {
            'db': 'pubmed',
            'id': pmid,
            'retmode': 'xml',
            'rettype': 'abstract'
        }
        
        return self._make_request('efetch.fcgi', params)
    
    def optimize_query(self, query: str) -> str:
        """Optimize a query for better PubMed search results"""
        # Replace common operators with PubMed syntax
        query = re.sub(r'\bAND\b', ' AND ', query)
        query = re.sub(r'\bOR\b', ' OR ', query)
        query = re.sub(r'\bNOT\b', ' NOT ', query)
        
        # Add quotes around phrases
        query = re.sub(r'([a-zA-Z-]+\s[a-zA-Z-]+\s[a-zA-Z-]+)', r'"\1"', query)
        
        # Add field tags for common search terms
        query = re.sub(r'(author|author):\s*([^,\s]+)', r'\2[Author]', query)
        query = re.sub(r'(title|title):\s*([^,\s]+)', r'\2[Title]', query)
        query = re.sub(r'(journal|journal):\s*([^,\s]+)', r'\2[Journal]', query)
        
        return query


@tool
def pubmed_search(query: str, max_results: int = 20, sort_by: str = "relevance", 
                  min_date: Optional[str] = None, max_date: Optional[str] = None, 
                  optimize_query: bool = True) -> str:
    """
    Search PubMed for scientific articles matching the query.
    
    Args:
        query (str): Search query for PubMed articles
        max_results (int): Maximum number of results to return (default: 20, max: 100)
        sort_by (str): Sort order - "relevance", "pub_date", "first_author", or "journal" (default: "relevance")
        min_date (str, optional): Minimum publication date in format YYYY/MM/DD or YYYY
        max_date (str, optional): Maximum publication date in format YYYY/MM/DD or YYYY
        optimize_query (bool): Whether to optimize the query for PubMed syntax (default: True)
    
    Returns:
        str: JSON string containing search results with article metadata
    """
    try:
        # Initialize client with API key if available
        api_key = os.environ.get(API_KEY_ENV_VAR)
        client = PubMedClient(api_key=api_key)
        
        # Map sort parameter to PubMed sort parameter
        sort_map = {
            "relevance": "relevance",
            "pub_date": "date",
            "first_author": "first+author",
            "journal": "journal"
        }
        sort_param = sort_map.get(sort_by.lower(), "relevance")
        
        # Optimize query if requested
        search_query = client.optimize_query(query) if optimize_query else query
        
        # Perform search
        search_results = client.search(
            search_query, 
            retmax=min(max_results, MAX_RETMAX),
            sort=sort_param,
            min_date=min_date,
            max_date=max_date
        )
        
        if "error" in search_results:
            return json.dumps({
                "success": False,
                "error": search_results["error"],
                "query": query
            }, ensure_ascii=False, indent=2)
        
        # Get PMIDs from search results
        pmids = search_results.get("pmids", [])
        total_count = search_results.get("count", 0)
        
        if not pmids:
            return json.dumps({
                "success": True,
                "query": query,
                "total_count": 0,
                "returned_count": 0,
                "articles": []
            }, ensure_ascii=False, indent=2)
        
        # Fetch article summaries
        summaries = client.fetch_summaries(pmids)
        
        if "error" in summaries:
            return json.dumps({
                "success": False,
                "error": summaries["error"],
                "query": query
            }, ensure_ascii=False, indent=2)
        
        # Format results
        articles = summaries.get("articles", [])
        formatted_articles = []
        
        for article in articles:
            # Extract and format author list
            authors = article.get("AuthorList", [])
            if isinstance(authors, list):
                formatted_authors = authors
            else:
                formatted_authors = []
            
            # Format publication date
            pub_date = article.get("PubDate", "")
            
            # Extract DOI
            doi = ""
            article_ids = article.get("ArticleIds", {})
            if isinstance(article_ids, dict):
                doi = article_ids.get("doi", "")
            elif isinstance(article_ids, list):
                for id_item in article_ids:
                    if isinstance(id_item, dict) and id_item.get("IdType") == "doi":
                        doi = id_item.get("Value", "")
            elif isinstance(article_ids, str):
                # If ArticleIds is a string, try to extract DOI from it
                if "doi:" in article_ids.lower():
                    doi_match = re.search(r'doi:([^\s,]+)', article_ids, re.IGNORECASE)
                    if doi_match:
                        doi = doi_match.group(1)
            
            formatted_article = {
                "pmid": article.get("pmid", ""),
                "title": article.get("Title", ""),
                "authors": formatted_authors,
                "journal": article.get("FullJournalName", article.get("Source", "")),
                "publication_date": pub_date,
                "doi": doi,
                "abstract_available": article.get("HasAbstract", "0") == "1"
            }
            
            formatted_articles.append(formatted_article)
        
        return json.dumps({
            "success": True,
            "query": query,
            "optimized_query": search_query if optimize_query else None,
            "total_count": total_count,
            "returned_count": len(formatted_articles),
            "articles": formatted_articles
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in pubmed_search: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "query": query
        }, ensure_ascii=False, indent=2)


@tool
def pubmed_fetch_abstract(pmid: str) -> str:
    """
    Fetch the abstract for a specific PubMed article by its PMID.
    
    Args:
        pmid (str): PubMed ID of the article
    
    Returns:
        str: JSON string containing the article abstract and metadata
    """
    try:
        # Initialize client with API key if available
        api_key = os.environ.get(API_KEY_ENV_VAR)
        client = PubMedClient(api_key=api_key)
        
        # Fetch article data
        article_data = client.fetch_article(pmid)
        
        if "error" in article_data:
            return json.dumps({
                "success": False,
                "error": article_data["error"],
                "pmid": pmid
            }, ensure_ascii=False, indent=2)
        
        # Parse XML to extract abstract
        raw_xml = article_data.get("raw_text", "")
        
        try:
            root = ET.fromstring(raw_xml)
            
            # Extract article metadata
            article_elem = root.find(".//PubmedArticle/MedlineCitation/Article")
            if article_elem is None:
                return json.dumps({
                    "success": False,
                    "error": "Article data not found",
                    "pmid": pmid
                }, ensure_ascii=False, indent=2)
            
            # Extract title
            title_elem = article_elem.find("./ArticleTitle")
            title = title_elem.text if title_elem is not None and title_elem.text else ""
            
            # Extract abstract
            abstract_elem = article_elem.find("./Abstract/AbstractText")
            abstract = abstract_elem.text if abstract_elem is not None and abstract_elem.text else ""
            
            # Extract authors
            authors = []
            author_list = root.findall(".//AuthorList/Author")
            for author in author_list:
                last_name = author.find("./LastName")
                fore_name = author.find("./ForeName")
                initials = author.find("./Initials")
                
                author_name = ""
                if last_name is not None and last_name.text:
                    author_name = last_name.text
                    if fore_name is not None and fore_name.text:
                        author_name = f"{fore_name.text} {author_name}"
                    elif initials is not None and initials.text:
                        author_name = f"{initials.text} {author_name}"
                
                if author_name:
                    authors.append(author_name)
            
            # Extract journal info
            journal_elem = article_elem.find("./Journal")
            journal = ""
            if journal_elem is not None:
                journal_title = journal_elem.find("./Title")
                if journal_title is not None and journal_title.text:
                    journal = journal_title.text
            
            # Extract publication date
            pub_date = ""
            pub_date_elem = journal_elem.find("./JournalIssue/PubDate") if journal_elem is not None else None
            if pub_date_elem is not None:
                year = pub_date_elem.find("./Year")
                month = pub_date_elem.find("./Month")
                day = pub_date_elem.find("./Day")
                
                date_parts = []
                if year is not None and year.text:
                    date_parts.append(year.text)
                if month is not None and month.text:
                    date_parts.append(month.text)
                if day is not None and day.text:
                    date_parts.append(day.text)
                
                pub_date = "-".join(date_parts)
            
            # Extract DOI
            doi = ""
            article_id_list = root.findall(".//ArticleIdList/ArticleId")
            for article_id in article_id_list:
                if article_id.get("IdType") == "doi":
                    doi = article_id.text
                    break
            
            # Extract keywords
            keywords = []
            keyword_list = root.findall(".//KeywordList/Keyword")
            for keyword in keyword_list:
                if keyword.text:
                    keywords.append(keyword.text)
            
            return json.dumps({
                "success": True,
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "journal": journal,
                "publication_date": pub_date,
                "doi": doi,
                "keywords": keywords
            }, ensure_ascii=False, indent=2)
            
        except ET.ParseError:
            logger.warning(f"Failed to parse XML for PMID {pmid}")
            return json.dumps({
                "success": False,
                "error": "Failed to parse article data",
                "pmid": pmid
            }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in pubmed_fetch_abstract: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "pmid": pmid
        }, ensure_ascii=False, indent=2)


@tool
def pubmed_advanced_search(query_terms: Dict[str, str], 
                           filters: Optional[Dict[str, Any]] = None,
                           max_results: int = 20,
                           sort_by: str = "relevance") -> str:
    """
    Perform an advanced search on PubMed with structured query terms and filters.
    
    Args:
        query_terms (Dict[str, str]): Dictionary of search fields and terms
                                     (e.g., {"title": "cancer", "author": "Smith J"})
        filters (Dict[str, Any], optional): Additional filters like publication types,
                                          languages, species, etc.
        max_results (int): Maximum number of results to return (default: 20, max: 100)
        sort_by (str): Sort order - "relevance", "pub_date", "first_author", or "journal"
    
    Returns:
        str: JSON string containing search results with article metadata
    """
    try:
        # Initialize client with API key if available
        api_key = os.environ.get(API_KEY_ENV_VAR)
        client = PubMedClient(api_key=api_key)
        
        # Build structured query
        query_parts = []
        
        # Process main query terms
        for field, term in query_terms.items():
            if not term:
                continue
                
            # Map common field names to PubMed field tags
            field_map = {
                "title": "Title",
                "abstract": "Abstract",
                "author": "Author",
                "journal": "Journal",
                "affiliation": "Affiliation",
                "mesh": "MeSH Terms",
                "doi": "DOI"
            }
            
            pubmed_field = field_map.get(field.lower(), field)
            query_parts.append(f"{term}[{pubmed_field}]")
        
        # Process filters
        if filters:
            # Publication types
            if "publication_types" in filters and filters["publication_types"]:
                for pub_type in filters["publication_types"]:
                    query_parts.append(f"{pub_type}[Publication Type]")
            
            # Languages
            if "languages" in filters and filters["languages"]:
                for language in filters["languages"]:
                    query_parts.append(f"{language}[Language]")
            
            # Species
            if "species" in filters and filters["species"]:
                for species in filters["species"]:
                    query_parts.append(f"{species}[Organism]")
            
            # Date range
            if "date_range" in filters and filters["date_range"]:
                date_range = filters["date_range"]
                if isinstance(date_range, dict):
                    min_date = date_range.get("min_date")
                    max_date = date_range.get("max_date")
                else:
                    min_date = None
                    max_date = None
            else:
                min_date = None
                max_date = None
        else:
            min_date = None
            max_date = None
        
        # Combine query parts with AND
        combined_query = " AND ".join(query_parts)
        
        # Map sort parameter
        sort_map = {
            "relevance": "relevance",
            "pub_date": "date",
            "first_author": "first+author",
            "journal": "journal"
        }
        sort_param = sort_map.get(sort_by.lower(), "relevance")
        
        # Perform search
        search_results = client.search(
            combined_query,
            retmax=min(max_results, MAX_RETMAX),
            sort=sort_param,
            min_date=min_date,
            max_date=max_date
        )
        
        if "error" in search_results:
            return json.dumps({
                "success": False,
                "error": search_results["error"],
                "query": combined_query
            }, ensure_ascii=False, indent=2)
        
        # Get PMIDs from search results
        pmids = search_results.get("pmids", [])
        total_count = search_results.get("count", 0)
        
        if not pmids:
            return json.dumps({
                "success": True,
                "query": combined_query,
                "total_count": 0,
                "returned_count": 0,
                "articles": []
            }, ensure_ascii=False, indent=2)
        
        # Fetch article summaries
        summaries = client.fetch_summaries(pmids)
        
        if "error" in summaries:
            return json.dumps({
                "success": False,
                "error": summaries["error"],
                "query": combined_query
            }, ensure_ascii=False, indent=2)
        
        # Format results
        articles = summaries.get("articles", [])
        formatted_articles = []
        
        for article in articles:
            # Extract and format author list
            authors = article.get("AuthorList", [])
            if isinstance(authors, list):
                formatted_authors = authors
            else:
                formatted_authors = []
            
            # Format publication date
            pub_date = article.get("PubDate", "")
            
            # Extract DOI
            doi = ""
            article_ids = article.get("ArticleIds", {})
            if isinstance(article_ids, dict):
                doi = article_ids.get("doi", "")
            elif isinstance(article_ids, list):
                for id_item in article_ids:
                    if isinstance(id_item, dict) and id_item.get("IdType") == "doi":
                        doi = id_item.get("Value", "")
            elif isinstance(article_ids, str):
                # If ArticleIds is a string, try to extract DOI from it
                if "doi:" in article_ids.lower():
                    doi_match = re.search(r'doi:([^\s,]+)', article_ids, re.IGNORECASE)
                    if doi_match:
                        doi = doi_match.group(1)
            
            formatted_article = {
                "pmid": article.get("pmid", ""),
                "title": article.get("Title", ""),
                "authors": formatted_authors,
                "journal": article.get("FullJournalName", article.get("Source", "")),
                "publication_date": pub_date,
                "doi": doi,
                "abstract_available": article.get("HasAbstract", "0") == "1"
            }
            
            formatted_articles.append(formatted_article)
        
        return json.dumps({
            "success": True,
            "query": combined_query,
            "total_count": total_count,
            "returned_count": len(formatted_articles),
            "articles": formatted_articles
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in pubmed_advanced_search: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "query_terms": query_terms
        }, ensure_ascii=False, indent=2)


@tool
def pubmed_fetch_citations(pmid: str, max_results: int = 20) -> str:
    """
    Fetch citations for a specific PubMed article by its PMID.
    
    Args:
        pmid (str): PubMed ID of the article
        max_results (int): Maximum number of citations to return (default: 20, max: 100)
    
    Returns:
        str: JSON string containing the citing articles
    """
    try:
        # Initialize client with API key if available
        api_key = os.environ.get(API_KEY_ENV_VAR)
        client = PubMedClient(api_key=api_key)
        
        # Use ELink to find citations
        params = {
            'dbfrom': 'pubmed',
            'db': 'pubmed',
            'id': pmid,
            'cmd': 'citation',
            'retmode': 'xml'
        }
        
        url = f"{BASE_URL}elink.fcgi"
        
        # Respect rate limits
        client.rate_limiter.wait()
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        try:
            root = ET.fromstring(response.text)
            
            # Extract citation PMIDs
            citation_pmids = []
            for id_elem in root.findall('.//LinkSetDb/Link/Id'):
                if id_elem.text:
                    citation_pmids.append(id_elem.text)
            
            if not citation_pmids:
                return json.dumps({
                    "success": True,
                    "pmid": pmid,
                    "total_citations": 0,
                    "returned_citations": 0,
                    "citing_articles": []
                }, ensure_ascii=False, indent=2)
            
            # Limit the number of citations to fetch
            citation_pmids = citation_pmids[:min(max_results, MAX_RETMAX)]
            
            # Fetch summaries for citing articles
            summaries = client.fetch_summaries(citation_pmids)
            
            if "error" in summaries:
                return json.dumps({
                    "success": False,
                    "error": summaries["error"],
                    "pmid": pmid
                }, ensure_ascii=False, indent=2)
            
            # Format results
            articles = summaries.get("articles", [])
            formatted_articles = []
            
            for article in articles:
                # Extract and format author list
                authors = article.get("AuthorList", [])
                if isinstance(authors, list):
                    formatted_authors = authors
                else:
                    formatted_authors = []
                
                # Format publication date
                pub_date = article.get("PubDate", "")
                
                formatted_article = {
                    "pmid": article.get("pmid", ""),
                    "title": article.get("Title", ""),
                    "authors": formatted_authors,
                    "journal": article.get("FullJournalName", article.get("Source", "")),
                    "publication_date": pub_date
                }
                
                formatted_articles.append(formatted_article)
            
            return json.dumps({
                "success": True,
                "pmid": pmid,
                "total_citations": len(citation_pmids),
                "returned_citations": len(formatted_articles),
                "citing_articles": formatted_articles
            }, ensure_ascii=False, indent=2)
            
        except ET.ParseError:
            logger.warning(f"Failed to parse XML for citations of PMID {pmid}")
            return json.dumps({
                "success": False,
                "error": "Failed to parse citation data",
                "pmid": pmid
            }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in pubmed_fetch_citations: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "pmid": pmid
        }, ensure_ascii=False, indent=2)


@tool
def pubmed_fetch_related(pmid: str, max_results: int = 20) -> str:
    """
    Fetch articles related to a specific PubMed article by its PMID.
    
    Args:
        pmid (str): PubMed ID of the article
        max_results (int): Maximum number of related articles to return (default: 20, max: 100)
    
    Returns:
        str: JSON string containing the related articles
    """
    try:
        # Initialize client with API key if available
        api_key = os.environ.get(API_KEY_ENV_VAR)
        client = PubMedClient(api_key=api_key)
        
        # Use ELink to find related articles
        params = {
            'dbfrom': 'pubmed',
            'db': 'pubmed',
            'id': pmid,
            'cmd': 'neighbor',
            'linkname': 'pubmed_pubmed',
            'retmode': 'xml'
        }
        
        url = f"{BASE_URL}elink.fcgi"
        
        # Respect rate limits
        client.rate_limiter.wait()
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        try:
            root = ET.fromstring(response.text)
            
            # Extract related PMIDs
            related_pmids = []
            for id_elem in root.findall('.//LinkSetDb/Link/Id'):
                if id_elem.text and id_elem.text != pmid:  # Exclude the original article
                    related_pmids.append(id_elem.text)
            
            if not related_pmids:
                return json.dumps({
                    "success": True,
                    "pmid": pmid,
                    "total_related": 0,
                    "returned_related": 0,
                    "related_articles": []
                }, ensure_ascii=False, indent=2)
            
            # Limit the number of related articles to fetch
            related_pmids = related_pmids[:min(max_results, MAX_RETMAX)]
            
            # Fetch summaries for related articles
            summaries = client.fetch_summaries(related_pmids)
            
            if "error" in summaries:
                return json.dumps({
                    "success": False,
                    "error": summaries["error"],
                    "pmid": pmid
                }, ensure_ascii=False, indent=2)
            
            # Format results
            articles = summaries.get("articles", [])
            formatted_articles = []
            
            for article in articles:
                # Extract and format author list
                authors = article.get("AuthorList", [])
                if isinstance(authors, list):
                    formatted_authors = authors
                else:
                    formatted_authors = []
                
                # Format publication date
                pub_date = article.get("PubDate", "")
                
                formatted_article = {
                    "pmid": article.get("pmid", ""),
                    "title": article.get("Title", ""),
                    "authors": formatted_authors,
                    "journal": article.get("FullJournalName", article.get("Source", "")),
                    "publication_date": pub_date
                }
                
                formatted_articles.append(formatted_article)
            
            return json.dumps({
                "success": True,
                "pmid": pmid,
                "total_related": len(related_pmids),
                "returned_related": len(formatted_articles),
                "related_articles": formatted_articles
            }, ensure_ascii=False, indent=2)
            
        except ET.ParseError:
            logger.warning(f"Failed to parse XML for related articles of PMID {pmid}")
            return json.dumps({
                "success": False,
                "error": "Failed to parse related articles data",
                "pmid": pmid
            }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in pubmed_fetch_related: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "pmid": pmid
        }, ensure_ascii=False, indent=2)


@tool
def pubmed_get_trending_articles(topic: str = "", days: int = 30, max_results: int = 20) -> str:
    """
    Get trending or recent articles from PubMed, optionally filtered by topic.
    
    Args:
        topic (str): Optional topic to filter articles (default: "", which returns general trending articles)
        days (int): Number of days to look back (default: 30)
        max_results (int): Maximum number of articles to return (default: 20, max: 100)
    
    Returns:
        str: JSON string containing trending articles
    """
    try:
        # Initialize client with API key if available
        api_key = os.environ.get(API_KEY_ENV_VAR)
        client = PubMedClient(api_key=api_key)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        min_date = start_date.strftime("%Y/%m/%d")
        max_date = end_date.strftime("%Y/%m/%d")
        
        # Build query
        if topic:
            query = f"{topic} AND {min_date}:{max_date}[Date - Publication]"
        else:
            query = f"{min_date}:{max_date}[Date - Publication]"
        
        # Perform search
        search_results = client.search(
            query,
            retmax=min(max_results, MAX_RETMAX),
            sort="date"  # Sort by publication date (newest first)
        )
        
        if "error" in search_results:
            return json.dumps({
                "success": False,
                "error": search_results["error"],
                "query": query
            }, ensure_ascii=False, indent=2)
        
        # Get PMIDs from search results
        pmids = search_results.get("pmids", [])
        total_count = search_results.get("count", 0)
        
        if not pmids:
            return json.dumps({
                "success": True,
                "topic": topic,
                "days": days,
                "total_count": 0,
                "returned_count": 0,
                "articles": []
            }, ensure_ascii=False, indent=2)
        
        # Fetch article summaries
        summaries = client.fetch_summaries(pmids)
        
        if "error" in summaries:
            return json.dumps({
                "success": False,
                "error": summaries["error"],
                "query": query
            }, ensure_ascii=False, indent=2)
        
        # Format results
        articles = summaries.get("articles", [])
        formatted_articles = []
        
        for article in articles:
            # Extract and format author list
            authors = article.get("AuthorList", [])
            if isinstance(authors, list):
                formatted_authors = authors
            else:
                formatted_authors = []
            
            # Format publication date
            pub_date = article.get("PubDate", "")
            
            # Extract DOI
            doi = ""
            article_ids = article.get("ArticleIds", {})
            if isinstance(article_ids, dict):
                doi = article_ids.get("doi", "")
            elif isinstance(article_ids, list):
                for id_item in article_ids:
                    if isinstance(id_item, dict) and id_item.get("IdType") == "doi":
                        doi = id_item.get("Value", "")
            elif isinstance(article_ids, str):
                # If ArticleIds is a string, try to extract DOI from it
                if "doi:" in article_ids.lower():
                    doi_match = re.search(r'doi:([^\s,]+)', article_ids, re.IGNORECASE)
                    if doi_match:
                        doi = doi_match.group(1)
            
            formatted_article = {
                "pmid": article.get("pmid", ""),
                "title": article.get("Title", ""),
                "authors": formatted_authors,
                "journal": article.get("FullJournalName", article.get("Source", "")),
                "publication_date": pub_date,
                "doi": doi,
                "abstract_available": article.get("HasAbstract", "0") == "1"
            }
            
            formatted_articles.append(formatted_article)
        
        return json.dumps({
            "success": True,
            "topic": topic,
            "days": days,
            "date_range": f"{min_date} to {max_date}",
            "total_count": total_count,
            "returned_count": len(formatted_articles),
            "articles": formatted_articles
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in pubmed_get_trending_articles: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "topic": topic,
            "days": days
        }, ensure_ascii=False, indent=2)


@tool
def pubmed_rank_articles(pmids: List[str], ranking_factors: Dict[str, float] = None) -> str:
    """
    Rank a list of PubMed articles based on multiple factors.
    
    Args:
        pmids (List[str]): List of PubMed IDs to rank
        ranking_factors (Dict[str, float], optional): Weighting factors for ranking:
            - "recency": Weight for publication recency (default: 1.0)
            - "journal_impact": Weight for journal impact (default: 1.0)
            - "citation_count": Weight for citation count (default: 1.0)
            - "relevance": Weight for relevance to search query (default: 1.0)
    
    Returns:
        str: JSON string containing ranked articles with scores
    """
    try:
        if not pmids:
            return json.dumps({
                "success": False,
                "error": "No PMIDs provided"
            }, ensure_ascii=False, indent=2)
        
        # Initialize client with API key if available
        api_key = os.environ.get(API_KEY_ENV_VAR)
        client = PubMedClient(api_key=api_key)
        
        # Set default ranking factors if not provided
        if ranking_factors is None:
            ranking_factors = {
                "recency": 1.0,
                "journal_impact": 1.0,
                "citation_count": 1.0,
                "relevance": 1.0
            }
        
        # Fetch article summaries
        summaries = client.fetch_summaries(pmids)
        
        if "error" in summaries:
            return json.dumps({
                "success": False,
                "error": summaries["error"]
            }, ensure_ascii=False, indent=2)
        
        # Get articles
        articles = summaries.get("articles", [])
        
        if not articles:
            return json.dumps({
                "success": True,
                "message": "No article data found for the provided PMIDs",
                "ranked_articles": []
            }, ensure_ascii=False, indent=2)
        
        # Fetch citation counts for all articles
        citation_counts = {}
        for pmid in pmids:
            try:
                # Use ELink to find citations
                params = {
                    'dbfrom': 'pubmed',
                    'db': 'pubmed',
                    'id': pmid,
                    'cmd': 'citation',
                    'retmode': 'xml'
                }
                
                url = f"{BASE_URL}elink.fcgi"
                
                # Respect rate limits
                client.rate_limiter.wait()
                
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                root = ET.fromstring(response.text)
                
                # Count citations
                citation_ids = root.findall('.//LinkSetDb/Link/Id')
                citation_counts[pmid] = len(citation_ids)
                
            except Exception as e:
                logger.warning(f"Failed to get citation count for PMID {pmid}: {e}")
                citation_counts[pmid] = 0
        
        # Calculate scores for each article
        current_year = datetime.now().year
        ranked_articles = []
        
        for article in articles:
            pmid = article.get("pmid", "")
            
            # Calculate recency score (0-1)
            pub_date = article.get("PubDate", "")
            pub_year = None
            if pub_date:
                match = re.search(r'\b\d{4}\b', pub_date)
                if match:
                    pub_year = int(match.group(0))
            
            if pub_year:
                years_old = current_year - pub_year
                recency_score = max(0, 1 - (years_old / 10))  # Newer is better, older than 10 years gets 0
            else:
                recency_score = 0.5  # Default if we can't determine
            
            # Journal impact score (simplified approximation)
            journal = article.get("FullJournalName", article.get("Source", ""))
            
            # This is a simplified approximation - in a real system you would use a database of impact factors
            high_impact_journals = [
                "nature", "science", "cell", "lancet", "jama", "nejm", 
                "new england journal", "proceedings of the national academy",
                "pnas", "plos", "bmj"
            ]
            
            journal_impact_score = 0.5  # Default score
            if journal:
                journal_lower = journal.lower()
                for high_impact in high_impact_journals:
                    if high_impact in journal_lower:
                        journal_impact_score = 1.0
                        break
            
            # Citation count score (0-1)
            citation_count = citation_counts.get(pmid, 0)
            citation_score = min(1.0, citation_count / 100)  # Cap at 100 citations for a score of 1
            
            # Relevance score (simplified - would normally be based on search query match)
            # Since we don't have the original query here, we use a default value
            relevance_score = 0.8  # Default value
            
            # Calculate weighted total score
            total_score = (
                recency_score * ranking_factors.get("recency", 1.0) +
                journal_impact_score * ranking_factors.get("journal_impact", 1.0) +
                citation_score * ranking_factors.get("citation_count", 1.0) +
                relevance_score * ranking_factors.get("relevance", 1.0)
            )
            
            # Normalize to 0-100 scale
            normalized_score = round(total_score * 25, 1)  # Max possible is 4 factors * 1.0 * 25 = 100
            
            # Format article data
            authors = article.get("AuthorList", [])
            if not isinstance(authors, list):
                authors = []
            
            formatted_article = {
                "pmid": pmid,
                "title": article.get("Title", ""),
                "authors": authors,
                "journal": journal,
                "publication_date": pub_date,
                "citation_count": citation_count,
                "score": normalized_score,
                "score_components": {
                    "recency": round(recency_score * 100, 1),
                    "journal_impact": round(journal_impact_score * 100, 1),
                    "citation_count": round(citation_score * 100, 1),
                    "relevance": round(relevance_score * 100, 1)
                }
            }
            
            ranked_articles.append(formatted_article)
        
        # Sort by score (highest first)
        ranked_articles.sort(key=lambda x: x["score"], reverse=True)
        
        return json.dumps({
            "success": True,
            "ranking_factors": ranking_factors,
            "ranked_articles": ranked_articles
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in pubmed_rank_articles: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "pmids": pmids
        }, ensure_ascii=False, indent=2)


@tool
def pubmed_get_author_publications(author_name: str, max_results: int = 20) -> str:
    """
    Get publications by a specific author from PubMed.
    
    Args:
        author_name (str): Author name to search for (format: "Last FM" or "Last F")
        max_results (int): Maximum number of publications to return (default: 20, max: 100)
    
    Returns:
        str: JSON string containing the author's publications
    """
    try:
        # Initialize client with API key if available
        api_key = os.environ.get(API_KEY_ENV_VAR)
        client = PubMedClient(api_key=api_key)
        
        # Format author name for search
        formatted_author = author_name.strip()
        if not formatted_author.endswith("[Author]"):
            formatted_author = f"{formatted_author}[Author]"
        
        # Perform search
        search_results = client.search(
            formatted_author,
            retmax=min(max_results, MAX_RETMAX),
            sort="date"  # Sort by publication date (newest first)
        )
        
        if "error" in search_results:
            return json.dumps({
                "success": False,
                "error": search_results["error"],
                "author": author_name
            }, ensure_ascii=False, indent=2)
        
        # Get PMIDs from search results
        pmids = search_results.get("pmids", [])
        total_count = search_results.get("count", 0)
        
        if not pmids:
            return json.dumps({
                "success": True,
                "author": author_name,
                "total_publications": 0,
                "returned_count": 0,
                "publications": []
            }, ensure_ascii=False, indent=2)
        
        # Fetch article summaries
        summaries = client.fetch_summaries(pmids)
        
        if "error" in summaries:
            return json.dumps({
                "success": False,
                "error": summaries["error"],
                "author": author_name
            }, ensure_ascii=False, indent=2)
        
        # Format results
        articles = summaries.get("articles", [])
        formatted_articles = []
        
        for article in articles:
            # Extract and format author list
            authors = article.get("AuthorList", [])
            if isinstance(authors, list):
                formatted_authors = authors
            else:
                formatted_authors = []
            
            # Format publication date
            pub_date = article.get("PubDate", "")
            
            # Extract DOI
            doi = ""
            article_ids = article.get("ArticleIds", {})
            if isinstance(article_ids, dict):
                doi = article_ids.get("doi", "")
            elif isinstance(article_ids, list):
                for id_item in article_ids:
                    if isinstance(id_item, dict) and id_item.get("IdType") == "doi":
                        doi = id_item.get("Value", "")
            elif isinstance(article_ids, str):
                # If ArticleIds is a string, try to extract DOI from it
                if "doi:" in article_ids.lower():
                    doi_match = re.search(r'doi:([^\s,]+)', article_ids, re.IGNORECASE)
                    if doi_match:
                        doi = doi_match.group(1)
            
            formatted_article = {
                "pmid": article.get("pmid", ""),
                "title": article.get("Title", ""),
                "authors": formatted_authors,
                "journal": article.get("FullJournalName", article.get("Source", "")),
                "publication_date": pub_date,
                "doi": doi,
                "abstract_available": article.get("HasAbstract", "0") == "1"
            }
            
            formatted_articles.append(formatted_article)
        
        return json.dumps({
            "success": True,
            "author": author_name,
            "total_publications": total_count,
            "returned_count": len(formatted_articles),
            "publications": formatted_articles
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in pubmed_get_author_publications: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "author": author_name
        }, ensure_ascii=False, indent=2)