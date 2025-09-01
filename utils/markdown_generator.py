"""
Markdown generator for the multimodal content parser system.

This module provides functionality to convert processed content from various file types
into well-structured Markdown format with proper formatting, metadata, and table support.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import re
from models.data_models import ProcessedContent, FileMetadata, ParsedContent


class MarkdownGenerator:
    """
    Generates formatted Markdown output from processed file content.
    
    This class handles the final formatting stage of the multimodal content parser,
    converting processed content from various file types into a unified Markdown
    document with proper structure, metadata, and formatting.
    """
    
    def __init__(self):
        """Initialize the Markdown generator."""
        self.section_separator = "\n\n---\n\n"
        self.subsection_separator = "\n\n"
    
    def generate_output(self, file_results: List[ProcessedContent], 
                       files_metadata: Optional[List[FileMetadata]] = None) -> str:
        """
        Generate complete Markdown output from processed file results.
        
        Args:
            file_results: List of processed content from individual files
            files_metadata: Optional list of file metadata for additional context
            
        Returns:
            Complete Markdown document as string
        """
        if not file_results:
            return self._generate_empty_output()
        
        # Build the complete markdown document
        sections = []
        
        # Add header section
        sections.append(self._generate_header(file_results, files_metadata))
        
        # Add summary section
        sections.append(self._generate_summary(file_results))
        
        # Add individual file sections
        for i, file_result in enumerate(file_results, 1):
            sections.append(self._format_file_section(file_result, i))
        
        # Add metadata section if available
        if files_metadata:
            sections.append(self._add_metadata_section(files_metadata))
        
        return self.section_separator.join(sections)
    
    def _generate_header(self, file_results: List[ProcessedContent], 
                        files_metadata: Optional[List[FileMetadata]] = None) -> str:
        """Generate the main header section."""
        total_files = len(file_results)
        successful_files = sum(1 for result in file_results if result.success)
        
        header = "# 多模态内容解析结果\n\n"
        header += f"**处理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        header += f"**文件总数**: {total_files}\n\n"
        header += f"**成功处理**: {successful_files}\n\n"
        header += f"**处理失败**: {total_files - successful_files}\n\n"
        
        return header
    
    def _generate_summary(self, file_results: List[ProcessedContent]) -> str:
        """Generate processing summary section."""
        summary = "## 处理摘要\n\n"
        
        # Group by content type
        content_types = {}
        total_processing_time = 0
        
        for result in file_results:
            content_type = result.content_type
            if content_type not in content_types:
                content_types[content_type] = {'count': 0, 'success': 0, 'failed': 0}
            
            content_types[content_type]['count'] += 1
            if result.success:
                content_types[content_type]['success'] += 1
            else:
                content_types[content_type]['failed'] += 1
            
            total_processing_time += result.processing_time
        
        # Create summary table
        summary += "| 文件类型 | 总数 | 成功 | 失败 |\n"
        summary += "|---------|------|------|------|\n"
        
        for content_type, stats in content_types.items():
            summary += f"| {content_type} | {stats['count']} | {stats['success']} | {stats['failed']} |\n"
        
        summary += f"\n**总处理时间**: {total_processing_time:.2f} 秒\n\n"
        
        return summary
    
    def _format_file_section(self, file_result: ProcessedContent, file_number: int) -> str:
        """
        Format individual file processing result into Markdown section.
        
        Args:
            file_result: Processed content for a single file
            file_number: Sequential number for the file
            
        Returns:
            Formatted Markdown section for the file
        """
        section = f"## 文件 {file_number}: {file_result.file_name}\n\n"
        
        # Add file information
        section += f"**文件ID**: `{file_result.file_id}`\n\n"
        section += f"**内容类型**: {file_result.content_type}\n\n"
        section += f"**处理时间**: {file_result.processing_time:.2f} 秒\n\n"
        section += f"**处理状态**: {'✅ 成功' if file_result.success else '❌ 失败'}\n\n"
        
        if not file_result.success and file_result.error_message:
            section += f"**错误信息**: {file_result.error_message}\n\n"
            return section
        
        # Add metadata if available
        if file_result.metadata:
            section += self._format_metadata_subsection(file_result.metadata)
        
        # Add processed content
        section += "### 内容描述\n\n"
        section += file_result.processed_text + "\n\n"
        
        return section
    
    def _format_metadata_subsection(self, metadata: Dict[str, Any]) -> str:
        """Format metadata into a readable subsection."""
        if not metadata:
            return ""
        
        subsection = "### 文件信息\n\n"
        
        # Handle common metadata fields
        if 'file_size' in metadata:
            subsection += f"**文件大小**: {self._format_file_size(metadata['file_size'])}\n\n"
        
        if 'dimensions' in metadata:
            dims = metadata['dimensions']
            subsection += f"**图片尺寸**: {dims.get('width', 'N/A')} x {dims.get('height', 'N/A')}\n\n"
        
        if 'sheets' in metadata:
            subsection += f"**工作表数量**: {len(metadata['sheets'])}\n\n"
            if metadata['sheets']:
                subsection += "**工作表列表**:\n"
                for sheet in metadata['sheets']:
                    subsection += f"- {sheet}\n"
                subsection += "\n"
        
        if 'word_count' in metadata:
            subsection += f"**字数统计**: {metadata['word_count']}\n\n"
        
        # Handle table data
        if 'tables' in metadata and metadata['tables']:
            subsection += self._format_tables_from_metadata(metadata['tables'])
        
        return subsection
    
    def _format_tables_from_metadata(self, tables: List[Dict[str, Any]]) -> str:
        """Format table data from metadata into Markdown tables."""
        if not tables:
            return ""
        
        tables_section = "### 表格数据\n\n"
        
        for i, table in enumerate(tables, 1):
            if len(tables) > 1:
                tables_section += f"#### 表格 {i}\n\n"
            
            tables_section += self.create_table_from_data(table)
            tables_section += "\n\n"
        
        return tables_section
    
    def create_table_from_data(self, data: Dict[str, Any]) -> str:
        """
        Convert structured data into Markdown table format.
        
        Args:
            data: Dictionary containing table data with headers and rows
            
        Returns:
            Formatted Markdown table string
        """
        if not data:
            return ""
        
        # Handle different data structures
        if 'headers' in data and 'rows' in data:
            return self._create_table_from_headers_rows(data['headers'], data['rows'])
        elif 'columns' in data:
            return self._create_table_from_columns(data['columns'])
        elif isinstance(data, list) and data:
            return self._create_table_from_list(data)
        elif isinstance(data, dict):
            return self._create_table_from_dict(data)
        
        return f"```\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```\n"
    
    def _create_table_from_headers_rows(self, headers: List[str], rows: List[List[Any]]) -> str:
        """Create table from headers and rows format."""
        if not headers or not rows:
            return ""
        
        # Create header row
        table = "| " + " | ".join(str(header) for header in headers) + " |\n"
        
        # Create separator row
        table += "|" + "|".join("---" for _ in headers) + "|\n"
        
        # Add data rows
        for row in rows:
            # Ensure row has same length as headers
            padded_row = list(row) + [''] * (len(headers) - len(row))
            table += "| " + " | ".join(str(cell) for cell in padded_row[:len(headers)]) + " |\n"
        
        return table
    
    def _create_table_from_columns(self, columns: Dict[str, List[Any]]) -> str:
        """Create table from columns dictionary format."""
        if not columns:
            return ""
        
        headers = list(columns.keys())
        max_rows = max(len(col) for col in columns.values()) if columns else 0
        
        rows = []
        for i in range(max_rows):
            row = []
            for header in headers:
                col_data = columns[header]
                row.append(col_data[i] if i < len(col_data) else '')
            rows.append(row)
        
        return self._create_table_from_headers_rows(headers, rows)
    
    def _create_table_from_list(self, data: List[Any]) -> str:
        """Create table from list of dictionaries or lists."""
        if not data:
            return ""
        
        first_item = data[0]
        
        if isinstance(first_item, dict):
            # List of dictionaries
            headers = list(first_item.keys())
            rows = []
            for item in data:
                row = [item.get(header, '') for header in headers]
                rows.append(row)
            return self._create_table_from_headers_rows(headers, rows)
        
        elif isinstance(first_item, (list, tuple)):
            # List of lists/tuples
            headers = [f"列{i+1}" for i in range(len(first_item))]
            return self._create_table_from_headers_rows(headers, data)
        
        else:
            # Simple list
            headers = ["值"]
            rows = [[item] for item in data]
            return self._create_table_from_headers_rows(headers, rows)
    
    def _create_table_from_dict(self, data: Dict[str, Any]) -> str:
        """Create table from simple dictionary."""
        headers = ["键", "值"]
        rows = [[str(key), str(value)] for key, value in data.items()]
        return self._create_table_from_headers_rows(headers, rows)
    
    def _add_metadata_section(self, files_metadata: List[FileMetadata]) -> str:
        """Add comprehensive metadata section for all files."""
        if not files_metadata:
            return ""
        
        section = "## 文件元数据详情\n\n"
        
        # Create metadata table
        section += "| 文件名 | 文件ID | 类型 | 大小 | 上传时间 | MIME类型 |\n"
        section += "|--------|--------|------|------|----------|----------|\n"
        
        for metadata in files_metadata:
            section += (
                f"| {metadata.original_name} | "
                f"`{metadata.file_id[:8]}...` | "
                f"{metadata.file_type} | "
                f"{self._format_file_size(metadata.file_size)} | "
                f"{metadata.upload_time.strftime('%Y-%m-%d %H:%M')} | "
                f"{metadata.mime_type} |\n"
            )
        
        return section
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def _generate_empty_output(self) -> str:
        """Generate output when no files were processed."""
        return (
            "# 多模态内容解析结果\n\n"
            "**处理时间**: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n\n"
            "**状态**: 没有文件需要处理\n\n"
            "请上传文件后重试。\n"
        )
    
    def _sanitize_markdown(self, text: str) -> str:
        """Sanitize text for safe Markdown output."""
        if not text:
            return ""
        
        # Escape special Markdown characters in regular text
        # But preserve intentional Markdown formatting
        text = str(text)
        
        # Replace problematic characters that could break table formatting
        text = text.replace('|', '\\|')
        text = text.replace('\n', ' ')  # Replace newlines in table cells
        
        return text.strip()