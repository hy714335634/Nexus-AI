"""
Markdown formatting utilities for PPT to Markdown conversion.

This module provides tools for formatting and customizing Markdown output
generated from PowerPoint presentations, including styling, formatting,
and post-processing capabilities.
"""

import os
import json
import re
from typing import Dict, List, Any, Optional, Union
import logging
from datetime import datetime

from strands import tool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@tool
def format_markdown_document(
    markdown_content: str,
    add_toc: bool = False,
    add_metadata: bool = False,
    presentation_title: Optional[str] = None,
    presentation_date: Optional[str] = None,
    author: Optional[str] = None,
    custom_css: Optional[str] = None,
    heading_style: str = "atx",
) -> str:
    """
    Format and enhance a Markdown document converted from a PowerPoint presentation.

    This tool takes Markdown content generated from a PowerPoint presentation and
    applies additional formatting and enhancements, such as adding a table of contents,
    metadata, and custom styling.

    Args:
        markdown_content (str): The Markdown content to format
        add_toc (bool, optional): Whether to add a table of contents. Defaults to False.
        add_metadata (bool, optional): Whether to add YAML metadata. Defaults to False.
        presentation_title (str, optional): The title of the presentation. Defaults to None.
        presentation_date (str, optional): The date of the presentation. Defaults to None.
        author (str, optional): The author of the presentation. Defaults to None.
        custom_css (str, optional): Custom CSS to include in the document. Defaults to None.
        heading_style (str, optional): Heading style to use ('atx' for # or 'setext' for underlines). Defaults to "atx".

    Returns:
        str: JSON string containing the formatting result with the following structure:
            {
                "status": "success" or "error",
                "formatted_content": "The formatted Markdown content" (if successful),
                "error_message": "Error description" (if error occurred),
                "metadata": {
                    "has_toc": Whether a table of contents was added,
                    "has_metadata": Whether metadata was added,
                    "heading_style": The heading style used
                }
            }
    """
    try:
        if not markdown_content:
            return json.dumps({
                "status": "error",
                "error_message": "No Markdown content provided",
                "metadata": {}
            })
        
        formatted_content = markdown_content
        metadata = {
            "has_toc": False,
            "has_metadata": False,
            "heading_style": heading_style
        }
        
        # Convert heading style if needed
        if heading_style == "setext":
            formatted_content = _convert_to_setext_headings(formatted_content)
        
        # Add YAML metadata if requested
        if add_metadata:
            metadata_block = "---\n"
            if presentation_title:
                metadata_block += f"title: \"{presentation_title}\"\n"
            if presentation_date:
                metadata_block += f"date: {presentation_date}\n"
            if author:
                metadata_block += f"author: {author}\n"
            if custom_css:
                metadata_block += f"css: {custom_css}\n"
            metadata_block += "---\n\n"
            
            formatted_content = metadata_block + formatted_content
            metadata["has_metadata"] = True
        
        # Add table of contents if requested
        if add_toc:
            toc = _generate_table_of_contents(formatted_content)
            
            # Find the position to insert the TOC (after metadata and title)
            lines = formatted_content.split("\n")
            insert_position = 0
            
            # Skip YAML metadata block if present
            if formatted_content.startswith("---"):
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == "---":
                        insert_position = i + 1
                        break
            
            # Skip the main title if present
            for i, line in enumerate(lines[insert_position:], insert_position):
                if line.startswith("# "):
                    insert_position = i + 1
                    break
            
            # Insert TOC
            lines.insert(insert_position, "\n## Table of Contents\n")
            lines.insert(insert_position + 1, toc)
            lines.insert(insert_position + 2, "\n")
            
            formatted_content = "\n".join(lines)
            metadata["has_toc"] = True
        
        return json.dumps({
            "status": "success",
            "formatted_content": formatted_content,
            "metadata": metadata
        })
    
    except Exception as e:
        logger.error(f"Error formatting Markdown document: {str(e)}")
        return json.dumps({
            "status": "error",
            "error_message": f"Error formatting Markdown document: {str(e)}",
            "metadata": {}
        })


def _convert_to_setext_headings(markdown_content: str) -> str:
    """
    Convert ATX-style headings (# Heading) to Setext-style headings (Heading\n======).
    
    Args:
        markdown_content: Markdown content with ATX headings
        
    Returns:
        str: Markdown content with Setext headings
    """
    lines = markdown_content.split("\n")
    result = []
    
    for line in lines:
        if line.startswith("# "):
            # H1: Convert "# Heading" to "Heading\n========"
            heading_text = line[2:]
            result.append(heading_text)
            result.append("=" * len(heading_text))
        elif line.startswith("## "):
            # H2: Convert "## Heading" to "Heading\n--------"
            heading_text = line[3:]
            result.append(heading_text)
            result.append("-" * len(heading_text))
        else:
            # Keep other lines as they are
            result.append(line)
    
    return "\n".join(result)


def _generate_table_of_contents(markdown_content: str) -> str:
    """
    Generate a table of contents from Markdown headings.
    
    Args:
        markdown_content: Markdown content
        
    Returns:
        str: Table of contents in Markdown format
    """
    lines = markdown_content.split("\n")
    toc_lines = []
    
    # Regular expressions for ATX and Setext headings
    atx_heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
    setext_h1_pattern = re.compile(r'^=+$')
    setext_h2_pattern = re.compile(r'^-+$')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check for ATX headings (# Heading)
        atx_match = atx_heading_pattern.match(line)
        if atx_match:
            level = len(atx_match.group(1))
            heading_text = atx_match.group(2).strip()
            
            # Create anchor and add to TOC
            anchor = _create_anchor(heading_text)
            indent = "    " * (level - 1)
            toc_lines.append(f"{indent}* [{heading_text}](#{anchor})")
        
        # Check for Setext headings (Heading\n======)
        elif i < len(lines) - 1:
            next_line = lines[i + 1].strip()
            
            if setext_h1_pattern.match(next_line):
                heading_text = line
                anchor = _create_anchor(heading_text)
                toc_lines.append(f"* [{heading_text}](#{anchor})")
                i += 1  # Skip the underline
            
            elif setext_h2_pattern.match(next_line):
                heading_text = line
                anchor = _create_anchor(heading_text)
                toc_lines.append(f"    * [{heading_text}](#{anchor})")
                i += 1  # Skip the underline
        
        i += 1
    
    return "\n".join(toc_lines)


def _create_anchor(heading_text: str) -> str:
    """
    Create an anchor ID from a heading text.
    
    Args:
        heading_text: The heading text
        
    Returns:
        str: Anchor ID for the heading
    """
    # Remove special characters and replace spaces with hyphens
    anchor = re.sub(r'[^\w\s-]', '', heading_text.lower())
    anchor = re.sub(r'[\s]+', '-', anchor)
    return anchor


@tool
def customize_markdown_styling(
    markdown_content: str,
    style_preset: str = "default",
    custom_replacements: Optional[Dict[str, str]] = None,
    enhance_lists: bool = False,
    enhance_tables: bool = False,
    add_page_breaks: bool = True,
) -> str:
    """
    Apply custom styling to Markdown content converted from PowerPoint.

    This tool enhances the visual appearance of Markdown content by applying
    custom styling rules, such as adding emojis, enhancing lists and tables,
    and applying predefined style presets.

    Args:
        markdown_content (str): The Markdown content to style
        style_preset (str, optional): Style preset to apply ('default', 'academic', 'business', 'minimal'). Defaults to "default".
        custom_replacements (Dict[str, str], optional): Custom text replacements to apply. Defaults to None.
        enhance_lists (bool, optional): Whether to enhance list formatting. Defaults to False.
        enhance_tables (bool, optional): Whether to enhance table formatting. Defaults to False.
        add_page_breaks (bool, optional): Whether to add page breaks between slides. Defaults to True.

    Returns:
        str: JSON string containing the styling result with the following structure:
            {
                "status": "success" or "error",
                "styled_content": "The styled Markdown content" (if successful),
                "error_message": "Error description" (if error occurred),
                "metadata": {
                    "style_preset": The style preset used,
                    "replacements_applied": Number of custom replacements applied,
                    "enhancements_applied": List of enhancements applied
                }
            }
    """
    try:
        if not markdown_content:
            return json.dumps({
                "status": "error",
                "error_message": "No Markdown content provided",
                "metadata": {}
            })
        
        styled_content = markdown_content
        enhancements_applied = []
        replacements_count = 0
        
        # Apply style preset
        if style_preset == "academic":
            styled_content = _apply_academic_style(styled_content)
            enhancements_applied.append("academic_style")
        elif style_preset == "business":
            styled_content = _apply_business_style(styled_content)
            enhancements_applied.append("business_style")
        elif style_preset == "minimal":
            styled_content = _apply_minimal_style(styled_content)
            enhancements_applied.append("minimal_style")
        else:  # default
            styled_content = _apply_default_style(styled_content)
            enhancements_applied.append("default_style")
        
        # Apply custom replacements
        if custom_replacements:
            for pattern, replacement in custom_replacements.items():
                original = styled_content
                styled_content = re.sub(pattern, replacement, styled_content)
                if original != styled_content:
                    replacements_count += 1
        
        # Enhance lists
        if enhance_lists:
            styled_content = _enhance_markdown_lists(styled_content)
            enhancements_applied.append("enhanced_lists")
        
        # Enhance tables
        if enhance_tables:
            styled_content = _enhance_markdown_tables(styled_content)
            enhancements_applied.append("enhanced_tables")
        
        # Add page breaks
        if add_page_breaks:
            styled_content = _add_page_breaks(styled_content)
            enhancements_applied.append("page_breaks")
        
        return json.dumps({
            "status": "success",
            "styled_content": styled_content,
            "metadata": {
                "style_preset": style_preset,
                "replacements_applied": replacements_count,
                "enhancements_applied": enhancements_applied
            }
        })
    
    except Exception as e:
        logger.error(f"Error styling Markdown content: {str(e)}")
        return json.dumps({
            "status": "error",
            "error_message": f"Error styling Markdown content: {str(e)}",
            "metadata": {}
        })


def _apply_default_style(content: str) -> str:
    """Apply default styling to Markdown content."""
    # Add emoji to slide headers
    content = re.sub(r'^## Slide (\d+)', r'## 📑 Slide \1', content, flags=re.MULTILINE)
    
    # Enhance section headers
    content = re.sub(r'^### (.+)', r'### 📌 \1', content, flags=re.MULTILINE)
    
    return content


def _apply_academic_style(content: str) -> str:
    """Apply academic styling to Markdown content."""
    # Add academic-style slide headers
    content = re.sub(r'^## Slide (\d+)', r'## Section \1', content, flags=re.MULTILINE)
    
    # Format section headers
    content = re.sub(r'^### (.+)', r'### \1', content, flags=re.MULTILINE)
    
    # Add blockquote style to important points
    content = re.sub(r'(\*\*Note:)([^\*]+)(\*\*)', r'> **Note:**\1', content)
    
    return content


def _apply_business_style(content: str) -> str:
    """Apply business styling to Markdown content."""
    # Add business-style slide headers
    content = re.sub(r'^## Slide (\d+)', r'## 📊 Slide \1', content, flags=re.MULTILINE)
    
    # Format section headers
    content = re.sub(r'^### (.+)', r'### 🔷 \1', content, flags=re.MULTILINE)
    
    # Highlight key points
    content = re.sub(r'\*\*Key Point:([^\*]+)\*\*', r'**💡 Key Point:**\1', content)
    
    return content


def _apply_minimal_style(content: str) -> str:
    """Apply minimal styling to Markdown content."""
    # Simplify slide headers
    content = re.sub(r'^## Slide (\d+)', r'## \1', content, flags=re.MULTILINE)
    
    # Simplify section headers
    content = re.sub(r'^### (.+)', r'### \1', content, flags=re.MULTILINE)
    
    return content


def _enhance_markdown_lists(content: str) -> str:
    """Enhance Markdown list formatting."""
    # Convert plain asterisk lists to varied symbols
    lines = content.split("\n")
    list_symbols = ["* ", "- ", "+ "]
    symbol_index = 0
    
    for i in range(len(lines)):
        if lines[i].strip().startswith("* "):
            indent = len(lines[i]) - len(lines[i].lstrip())
            symbol = list_symbols[symbol_index % len(list_symbols)]
            lines[i] = " " * indent + symbol + lines[i].strip()[2:]
            symbol_index += 1
    
    return "\n".join(lines)


def _enhance_markdown_tables(content: str) -> str:
    """Enhance Markdown table formatting."""
    # Add table caption
    table_pattern = r'(\n\|[^\n]+\|\n\|[-:\|\s]+\|\n)'
    content = re.sub(table_pattern, r'\n<div class="table-caption">Table</div>\1', content)
    
    return content


def _add_page_breaks(content: str) -> str:
    """Add page breaks between slides."""
    # Add page break before each slide
    content = re.sub(r'\n## Slide', r'\n\n<div class="page-break"></div>\n\n## Slide', content)
    
    return content


@tool
def extract_markdown_sections(
    markdown_content: str,
    section_type: str = "all",
    include_content: bool = True,
) -> str:
    """
    Extract specific sections from Markdown content converted from PowerPoint.

    This tool extracts specific sections from Markdown content, such as headings,
    lists, tables, or code blocks, making it easier to analyze or manipulate
    specific parts of the content.

    Args:
        markdown_content (str): The Markdown content to analyze
        section_type (str, optional): Type of sections to extract ('all', 'headings', 'lists', 'tables', 'code'). Defaults to "all".
        include_content (bool, optional): Whether to include the content of each section. Defaults to True.

    Returns:
        str: JSON string containing the extracted sections with the following structure:
            {
                "status": "success" or "error",
                "sections": {
                    "headings": [List of headings],
                    "lists": [List of lists],
                    "tables": [List of tables],
                    "code_blocks": [List of code blocks]
                },
                "error_message": "Error description" (if error occurred),
                "metadata": {
                    "section_count": Total number of sections extracted,
                    "section_type": Type of sections extracted
                }
            }
    """
    try:
        if not markdown_content:
            return json.dumps({
                "status": "error",
                "error_message": "No Markdown content provided",
                "metadata": {}
            })
        
        sections = {}
        section_count = 0
        
        # Extract headings
        if section_type in ["all", "headings"]:
            headings = _extract_headings(markdown_content, include_content)
            sections["headings"] = headings
            section_count += len(headings)
        
        # Extract lists
        if section_type in ["all", "lists"]:
            lists = _extract_lists(markdown_content, include_content)
            sections["lists"] = lists
            section_count += len(lists)
        
        # Extract tables
        if section_type in ["all", "tables"]:
            tables = _extract_tables(markdown_content, include_content)
            sections["tables"] = tables
            section_count += len(tables)
        
        # Extract code blocks
        if section_type in ["all", "code"]:
            code_blocks = _extract_code_blocks(markdown_content, include_content)
            sections["code_blocks"] = code_blocks
            section_count += len(code_blocks)
        
        return json.dumps({
            "status": "success",
            "sections": sections,
            "metadata": {
                "section_count": section_count,
                "section_type": section_type
            }
        })
    
    except Exception as e:
        logger.error(f"Error extracting Markdown sections: {str(e)}")
        return json.dumps({
            "status": "error",
            "error_message": f"Error extracting Markdown sections: {str(e)}",
            "metadata": {}
        })


def _extract_headings(markdown_content: str, include_content: bool) -> List[Dict[str, Any]]:
    """
    Extract headings from Markdown content.
    
    Args:
        markdown_content: Markdown content
        include_content: Whether to include content under each heading
        
    Returns:
        List of heading information
    """
    headings = []
    lines = markdown_content.split("\n")
    
    # Pattern for ATX headings (# Heading)
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
    
    current_heading = None
    current_content = []
    
    for i, line in enumerate(lines):
        heading_match = heading_pattern.match(line)
        
        if heading_match:
            # Save previous heading if exists
            if current_heading and include_content:
                headings.append({
                    "level": current_heading["level"],
                    "text": current_heading["text"],
                    "content": "\n".join(current_content)
                })
            elif current_heading:
                headings.append({
                    "level": current_heading["level"],
                    "text": current_heading["text"]
                })
            
            # Start new heading
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            current_heading = {"level": level, "text": text}
            current_content = []
        
        elif current_heading and include_content:
            # Collect content under current heading
            current_content.append(line)
    
    # Add the last heading
    if current_heading and include_content:
        headings.append({
            "level": current_heading["level"],
            "text": current_heading["text"],
            "content": "\n".join(current_content)
        })
    elif current_heading:
        headings.append({
            "level": current_heading["level"],
            "text": current_heading["text"]
        })
    
    return headings


def _extract_lists(markdown_content: str, include_content: bool) -> List[Dict[str, Any]]:
    """
    Extract lists from Markdown content.
    
    Args:
        markdown_content: Markdown content
        include_content: Whether to include list items
        
    Returns:
        List of list information
    """
    lists = []
    lines = markdown_content.split("\n")
    
    # Pattern for list items
    list_pattern = re.compile(r'^(\s*)([*\-+]|\d+\.)\s+(.+)$')
    
    current_list = []
    in_list = False
    list_start_line = 0
    
    for i, line in enumerate(lines):
        list_match = list_pattern.match(line)
        
        if list_match:
            if not in_list:
                in_list = True
                list_start_line = i
                current_list = []
            
            if include_content:
                indent = len(list_match.group(1))
                marker = list_match.group(2)
                content = list_match.group(3)
                current_list.append({
                    "indent": indent,
                    "marker": marker,
                    "content": content
                })
            else:
                current_list.append(line)
        
        elif in_list and line.strip() == "":
            # Empty line might be part of the list
            current_list.append(line)
        
        elif in_list:
            # End of list
            in_list = False
            if current_list:
                list_type = "ordered" if current_list[0].get("marker", "").endswith(".") else "unordered"
                lists.append({
                    "type": list_type,
                    "items": current_list if include_content else None,
                    "raw": "\n".join(current_list) if not include_content else None
                })
            current_list = []
    
    # Add the last list if exists
    if in_list and current_list:
        list_type = "ordered" if current_list[0].get("marker", "").endswith(".") else "unordered"
        lists.append({
            "type": list_type,
            "items": current_list if include_content else None,
            "raw": "\n".join(current_list) if not include_content else None
        })
    
    return lists


def _extract_tables(markdown_content: str, include_content: bool) -> List[Dict[str, Any]]:
    """
    Extract tables from Markdown content.
    
    Args:
        markdown_content: Markdown content
        include_content: Whether to include table content
        
    Returns:
        List of table information
    """
    tables = []
    
    # Pattern for Markdown tables
    table_pattern = re.compile(r'(\|[^\n]+\|\n\|[-:\|\s]+\|(\n\|[^\n]+\|)+)', re.MULTILINE)
    
    for match in table_pattern.finditer(markdown_content):
        table_text = match.group(0)
        
        if include_content:
            # Parse table structure
            rows = table_text.strip().split("\n")
            header_row = rows[0]
            separator_row = rows[1]
            data_rows = rows[2:] if len(rows) > 2 else []
            
            # Parse header
            headers = [cell.strip() for cell in header_row.strip("|").split("|")]
            
            # Parse alignment
            alignments = []
            for cell in separator_row.strip("|").split("|"):
                cell = cell.strip()
                if cell.startswith(":") and cell.endswith(":"):
                    alignments.append("center")
                elif cell.endswith(":"):
                    alignments.append("right")
                else:
                    alignments.append("left")
            
            # Parse data rows
            data = []
            for row in data_rows:
                cells = [cell.strip() for cell in row.strip("|").split("|")]
                data.append(cells)
            
            tables.append({
                "headers": headers,
                "alignments": alignments,
                "data": data
            })
        else:
            tables.append({
                "raw": table_text
            })
    
    return tables


def _extract_code_blocks(markdown_content: str, include_content: bool) -> List[Dict[str, Any]]:
    """
    Extract code blocks from Markdown content.
    
    Args:
        markdown_content: Markdown content
        include_content: Whether to include code content
        
    Returns:
        List of code block information
    """
    code_blocks = []
    
    # Pattern for fenced code blocks
    code_pattern = re.compile(r'```([^\n]*)\n(.*?)```', re.DOTALL)
    
    for match in code_pattern.finditer(markdown_content):
        language = match.group(1).strip()
        code = match.group(2) if include_content else None
        
        code_blocks.append({
            "language": language,
            "code": code if include_content else None,
            "raw": match.group(0) if not include_content else None
        })
    
    return code_blocks