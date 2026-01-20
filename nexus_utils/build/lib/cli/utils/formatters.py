"""Output formatters"""

import json
from typing import List, Dict, Any
from tabulate import tabulate


def format_json(data: Any) -> str:
    """Format data as JSON"""
    return json.dumps(data, indent=2, ensure_ascii=False)


def format_table(data: List[Dict[str, Any]], headers: List[str]) -> str:
    """Format data as table"""
    if not data:
        return "No data to display"
    
    # Extract values in header order
    rows = []
    for item in data:
        row = [item.get(h, '') for h in headers]
        rows.append(row)
    
    # Format headers (uppercase)
    formatted_headers = [h.upper().replace('_', ' ') for h in headers]
    
    return tabulate(rows, headers=formatted_headers, tablefmt='plain')


def format_text(data: List[Dict[str, Any]], headers: List[str]) -> str:
    """Format data as plain text"""
    if not data:
        return ""
    
    lines = []
    for item in data:
        values = [str(item.get(h, '')) for h in headers]
        lines.append(' '.join(values))
    
    return '\n'.join(lines)


def format_output(data: Any, output_format: str = 'table', headers: List[str] = None) -> str:
    """Format output based on format type"""
    if output_format == 'json':
        return format_json(data)
    elif output_format == 'text':
        if isinstance(data, list) and headers:
            return format_text(data, headers)
        return str(data)
    else:  # table (default)
        if isinstance(data, list) and headers:
            return format_table(data, headers)
        return str(data)
