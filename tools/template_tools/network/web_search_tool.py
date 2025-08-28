#!/usr/bin/env python3
"""
Web search tool using DuckDuckGo Search (ddgs) for deep research capabilities.
"""

from strands.tools import tool
from ddgs.exceptions import DDGSException, RatelimitException
from ddgs import DDGS
import time
from typing import Optional


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web for information using DuckDuckGo.
    
    Args:
        query: Search query for information
        max_results: Maximum number of results to return (default: 5)
        
    Returns:
        Search results with titles, URLs, and snippets
    """
    try:
        results = DDGS().text(query, region="us-en", max_results=max_results)
        if not results:
            return "No search results found."
            
        formatted_results = []
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            url = result.get('href', 'No URL')
            body = result.get('body', 'No description')
            formatted_results.append(f"{i}. **{title}**\n   URL: {url}\n   {body}\n")
            
        return "\n".join(formatted_results)
    except RatelimitException:
        return "Rate limit reached: Please try again after a short delay."
    except DDGSException as d:
        return f"Search Error: {d}"
    except Exception as e:
        return f"Search error: {str(e)}"


@tool
def web_search_news(query: str, max_results: int = 5) -> str:
    """Search for recent news articles using DuckDuckGo.
    
    Args:
        query: Search query for news
        max_results: Maximum number of results to return (default: 5)
        
    Returns:
        News search results with titles, URLs, dates, and snippets
    """
    try:
        results = DDGS().news(query, region="us-en", max_results=max_results)
        if not results:
            return "No news results found."
            
        formatted_results = []
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            url = result.get('url', 'No URL')
            body = result.get('body', 'No description')
            date = result.get('date', 'No date')
            source = result.get('source', 'Unknown source')
            formatted_results.append(f"{i}. **{title}**\n   Source: {source} | Date: {date}\n   URL: {url}\n   {body}\n")
            
        return "\n".join(formatted_results)
    except RatelimitException:
        return "Rate limit reached: Please try again after a short delay."
    except DDGSException as d:
        return f"Search Error: {d}"
    except Exception as e:
        return f"Search error: {str(e)}"


@tool
def web_search_academic(query: str, max_results: int = 3) -> str:
    """Search for academic and scholarly content using targeted search terms.
    
    Args:
        query: Search query for academic content
        max_results: Maximum number of results to return (default: 3)
        
    Returns:
        Academic search results with enhanced filtering
    """
    try:
        # Enhance query for academic content
        academic_query = f"{query} site:scholar.google.com OR site:arxiv.org OR site:researchgate.net OR site:ieee.org OR site:acm.org OR filetype:pdf"
        
        results = DDGS().text(academic_query, region="us-en", max_results=max_results)
        if not results:
            return "No academic results found."
            
        formatted_results = []
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            url = result.get('href', 'No URL')
            body = result.get('body', 'No description')
            formatted_results.append(f"{i}. **{title}**\n   URL: {url}\n   {body}\n")
            
        return "\n".join(formatted_results)
    except RatelimitException:
        return "Rate limit reached: Please try again after a short delay."
    except DDGSException as d:
        return f"Search Error: {d}"
    except Exception as e:
        return f"Search error: {str(e)}"


@tool
def multi_source_search(query: str, include_news: bool = True, include_academic: bool = True) -> str:
    """Perform comprehensive search across multiple sources.
    
    Args:
        query: Search query
        include_news: Whether to include news results
        include_academic: Whether to include academic results
        
    Returns:
        Combined search results from multiple sources
    """
    results = []
    
    # General web search
    results.append("=== GENERAL WEB SEARCH ===")
    web_results = web_search(query, max_results=3)
    results.append(web_results)
    
    # Add delay to avoid rate limiting
    time.sleep(1)
    
    # News search
    if include_news:
        results.append("\n=== NEWS SEARCH ===")
        news_results = web_search_news(query, max_results=3)
        results.append(news_results)
        time.sleep(1)
    
    # Academic search
    if include_academic:
        results.append("\n=== ACADEMIC SEARCH ===")
        academic_results = web_search_academic(query, max_results=2)
        results.append(academic_results)
    
    return "\n".join(results)