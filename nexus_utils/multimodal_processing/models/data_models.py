"""
Core data models for the multimodal content parser system.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class FileMetadata:
    """
    Metadata information for uploaded files.
    
    Attributes:
        file_id: Unique UUID identifier for the file
        original_name: Original filename as uploaded by user
        file_type: File extension/type (e.g., 'jpg', 'xlsx', 'txt')
        file_size: File size in bytes
        upload_time: Timestamp when file was uploaded
        s3_url: S3 storage URL for the file
        mime_type: MIME type of the file
    """
    file_id: str
    original_name: str
    file_type: str
    file_size: int
    upload_time: datetime
    s3_url: str
    mime_type: str


@dataclass
class ProcessedContent:
    """
    Result of processing a single file through the multimodal parser.
    
    Attributes:
        file_id: Unique identifier matching FileMetadata.file_id
        file_name: Original filename for reference
        content_type: Type of content processed ('image', 'document', 'text')
        processed_text: Processed content in text/markdown format
        metadata: Additional metadata extracted during processing
        processing_time: Time taken to process the file in seconds
        success: Whether processing completed successfully
        error_message: Error details if processing failed
    """
    file_id: str
    file_name: str
    content_type: str
    processed_text: str
    metadata: Dict[str, Any]
    processing_time: float
    success: bool
    error_message: Optional[str] = None


@dataclass
class ParsedContent:
    """
    Final result containing all processed files and summary information.
    
    Attributes:
        total_files: Total number of files submitted for processing
        successful_files: Number of files processed successfully
        failed_files: Number of files that failed processing
        markdown_output: Combined markdown output from all processed files
        file_results: List of individual file processing results
        processing_summary: Summary statistics and metadata
    """
    total_files: int
    successful_files: int
    failed_files: int
    markdown_output: str
    file_results: List[ProcessedContent]
    processing_summary: Dict[str, Any]