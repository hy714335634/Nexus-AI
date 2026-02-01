---
name: multi-search-engine
description: A universal search tool that provides unified access to multiple search engines (Baidu, Sogou, 360, Google, Bing, DuckDuckGo) with automatic environment detection and intelligent engine selection for both China and overseas regions
---

# Multi Search Engine Skill

Use this skill when you need to search for information across different search engines, especially when working in environments that require access to both Chinese and international search engines.

## When to Use This Skill

- When you need to search for information and want the best available search engine automatically selected
- When you need to search specifically on Chinese search engines (Baidu, Sogou, 360)
- When you need to search on international search engines (Google, Bing, DuckDuckGo)
- When you need to check which search engines are currently available
- When you need to filter and sort search results based on keywords
- When working in different network environments (China vs overseas)

## Core Capabilities

### 1. Unified Search Interface
- Search across 6 major search engines with a single function call
- Automatic engine selection based on network environment, region, and language preferences
- Support for multiple output formats (JSON, Markdown, plain text)
- Automatic fallback to alternative engines if primary engine fails

### 2. Environment-Aware Search
- Automatically detects network environment (China vs overseas)
- Prioritizes appropriate search engines based on region and language
- Concurrent availability testing to select the fastest responsive engine
- Configurable timeout and retry mechanisms

### 3. Result Processing
- Standardizes results from different search engines into a unified format
- Filters results by including or excluding specific keywords
- Removes duplicate results based on URLs
- Supports multiple sorting options (relevance, date, random)

### 4. Health Monitoring
- Checks availability and response time of search engines
- Provides detailed status information for system monitoring
- Supports batch checking or specific engine checking

## Usage Guidelines

### For Basic Search
1. Use `search()` with just a query to let the tool automatically select the best engine
2. Specify `region="china"` when searching from mainland China
3. Specify `region="overseas"` when searching from outside China
4. Use `language="zh-CN"` for Chinese content, `language="en-US"` for English content

### For Specific Engine Search
1. Use `engine="baidu"` for Chinese search engine
2. Use `engine="google"` for international search engine
3. Adjust `num_results` (1-20) based on your needs
4. Set appropriate `timeout` (5-30 seconds) based on network conditions

### For Result Processing
1. First perform a search with `search()`
2. Then use `filter_and_sort_results()` to refine the results
3. Use `filter_keywords` to keep only relevant results
4. Use `exclude_keywords` to remove unwanted results (e.g., ads)
5. Enable `deduplicate=true` to remove duplicate URLs

### For System Monitoring
1. Use `check_engine_health()` periodically to monitor engine availability
2. Check specific engines by passing a JSON array: `engines='["baidu", "google"]'`
3. Adjust `check_timeout` for faster or more thorough checks

## Examples

### Example 1: Basic Auto Search
```python
# Let the tool automatically select the best search engine
result = search(
    query="artificial intelligence trends 2026",
    num_results=10
)
```

### Example 2: Region-Specific Search
```python
# Search from China region with Chinese language preference
result = search(
    query="深度学习教程",
    region="china",
    language="zh-CN",
    num_results=10
)

# Search from overseas with English preference
result = search(
    query="machine learning tutorial",
    region="overseas",
    language="en-US",
    num_results=10
)
```

### Example 3: Specific Engine Search
```python
# Search specifically on Google
result = search(
    query="transformer architecture paper",
    engine="google",
    num_results=15
)
```

### Example 4: Search with Result Filtering
```python
# First, perform the search
search_result = search(
    query="Python programming",
    num_results=30
)

# Then filter the results
filtered_result = filter_and_sort_results(
    results_json=search_result,
    filter_keywords='["tutorial", "beginner"]',
    exclude_keywords='["video", "paid"]',
    deduplicate=True
)
```

### Example 5: Health Check
```python
# Check all search engines
health_status = check_engine_health()

# Check specific engines with custom timeout
health_status = check_engine_health(
    engines='["baidu", "google", "bing"]',
    check_timeout=3
)
```

### Example 6: Multi-Format Output
```python
# JSON format (default)
json_result = search(query="Python", format="json")

# Markdown format for documentation
markdown_result = search(query="Python", format="markdown")

# Plain text format for simple display
text_result = search(query="Python", format="text")
```

## Best Practices

1. **Always handle errors gracefully**: Check the `status` field in the returned JSON
2. **Use appropriate timeouts**: Set shorter timeouts (5-10s) for quick checks, longer (15-30s) for thorough searches
3. **Respect rate limits**: Don't make too many requests in a short time to avoid being blocked
4. **Use auto mode when possible**: Let the tool select the best engine based on environment
5. **Filter results to reduce noise**: Use `filter_and_sort_results()` to get more relevant results
6. **Monitor engine health**: Periodically check engine availability, especially in production
7. **Use appropriate region settings**: Specify `region` when you know the network environment
8. **Consider language preferences**: Set `language` to get better-localized results
9. **Enable metadata for debugging**: Keep `include_metadata=true` to track search performance
10. **Deduplicate results**: Always enable deduplication when filtering results

## Important Considerations

### Network Environment
- The tool works best when it can access both Chinese and international search engines
- If behind a firewall, some engines may not be accessible
- Use `check_engine_health()` to verify which engines are available before searching

### Search Engine Limitations
- Each search engine has its own rate limits and anti-scraping measures
- HTML structure of search engines may change, requiring updates
- Some engines may block automated requests despite User-Agent rotation

### Performance
- Concurrent health checks use thread pools (max 6 concurrent)
- Search failures automatically trigger retries with exponential backoff (max 3 retries)
- Consider implementing caching for frequently repeated queries

### Error Handling
- All errors return JSON with `status: "error"` and descriptive messages
- Common errors: ValidationError, EngineUnavailableError, ParseError
- Always check the `status` field before processing results

## Return Format

All tools return JSON strings with a consistent structure:

**Success Response:**
```json
{
  "status": "success",
  "engine_used": "baidu",
  "query": "search term",
  "results": [...],
  "total_results": 10,
  "metadata": {
    "search_time_ms": 235,
    "timestamp": "2026-01-31T16:00:00Z"
  }
}
```

**Error Response:**
```json
{
  "status": "error",
  "error_type": "ValidationError",
  "message": "Descriptive error message"
}
```

## Supported Search Engines

| Engine | Region | Language | Strengths |
|--------|--------|----------|-----------|
| Baidu (百度) | China | Chinese | Best for Chinese content, local information |
| Sogou (搜狗) | China | Chinese | Good for Chinese content, WeChat integration |
| 360 Search | China | Chinese | Alternative Chinese search engine |
| Google | International | Multi-language | Best for international content, academic papers |
| Bing | International | Multi-language | Good for international content, Microsoft ecosystem |
| DuckDuckGo | International | Multi-language | Privacy-focused, no tracking |

## Workflow Integration

This skill integrates seamlessly with other Agent capabilities:
- Use search results to gather information for analysis tasks
- Combine with document processing tools to extract key information
- Use health checks for system monitoring and alerting
- Filter results before feeding them to summarization tools
- Use multi-engine search for comprehensive research tasks
