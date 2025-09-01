#!/usr/bin/env python3
"""
Multimodal Content Parser System Tool

This tool provides multimodal content parsing capabilities for the Nexus-AI platform,
enabling users to upload and process various file types (images, text, documents)
and receive structured Markdown output for AI agent consumption.

Tool Functions:
- parse_multimodal_content: Main function to process uploaded files
- get_supported_formats: Get list of supported file formats
- validate_files: Validate files before processing
- get_processing_status: Check processing status and capabilities
"""

import json
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from strands import tool
from models.data_models import FileMetadata, ParsedContent
from models.exceptions import MultimodalParserError, FileUploadError, StorageError
from utils.file_upload_manager import FileUploadManager
from utils.s3_storage_service import S3StorageService
from utils.content_parsing_engine import ContentParsingEngine
from utils.multimodal_model_service import MultimodalModelService
from utils.config_loader import ConfigLoader


# Initialize logger
logger = logging.getLogger(__name__)


class MultimodalContentParserTool:
    """
    System tool wrapper for multimodal content parsing functionality.
    
    This class provides a clean interface for the Strands framework to interact
    with the multimodal content parser system components.
    """
    
    def __init__(self):
        """Initialize the multimodal content parser tool with required services."""
        try:
            # Ensure environment variables are loaded first
            import os
            from dotenv import load_dotenv
            load_dotenv()
            
            # Load configuration
            config_loader = ConfigLoader()
            self.config = config_loader.config
            self.multimodal_config = self.config.get('multimodal_parser', {})
            
            # Initialize services
            self._init_services()
            
            logger.info("MultimodalContentParserTool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MultimodalContentParserTool: {str(e)}")
            raise MultimodalParserError(
                f"Tool initialization failed: {str(e)}",
                error_code="INITIALIZATION_ERROR"
            ) from e
    
    def _init_services(self):
        """Initialize all required services for the multimodal parser."""
        # Initialize file upload manager
        self.upload_manager = FileUploadManager(self.config)
        
        # Initialize S3 storage service
        aws_config = self.multimodal_config.get('aws', {})
        
        # Get AWS region from environment variables first, then config, then default
        import os
        aws_region = (
            os.getenv('AWS_DEFAULT_REGION') or 
            os.getenv('AWS_REGION') or
            aws_config.get('bedrock_region') or 
            self.config.get('aws', {}).get('bedrock_region_name') or
            'us-west-2'
        )
        
        self.storage_service = S3StorageService(
            bucket_name=aws_config.get('s3_bucket', 'nexus-ai-file-storage'),
            aws_region=aws_region,
            s3_prefix=aws_config.get('s3_prefix', 'multimodal-content/')
        )
        
        # Initialize multimodal model service
        self.model_service = MultimodalModelService(
            aws_region=aws_region,
            model_config=self.multimodal_config.get('model', {})
        )
        
        # Initialize content parsing engine
        processing_config = self.multimodal_config.get('processing', {})
        self.parsing_engine = ContentParsingEngine(
            multimodal_service=self.model_service,
            max_workers=processing_config.get('max_workers', 3),
            processing_timeout=processing_config.get('timeout_seconds', 300)
        )


# Global tool instance
_tool_instance = None


def _get_tool_instance() -> MultimodalContentParserTool:
    """Get or create the global tool instance."""
    global _tool_instance
    
    # Always reload environment variables to ensure latest config
    import os
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    # For now, always create a new instance to ensure fresh config
    # In production, you might want to cache this with proper invalidation
    _tool_instance = MultimodalContentParserTool()
    return _tool_instance


@tool
def parse_multimodal_content(
    files: List[Dict[str, Any]],
    context_description: str = "",
    include_metadata: bool = True,
    processing_options: Optional[Dict[str, Any]] = None
) -> str:
    """
    Parse multiple files of various types and generate structured Markdown output.
    
    This is the main function for processing multimodal content. It handles file upload,
    validation, processing through appropriate processors, and generates unified Markdown output.
    
    Args:
        files: List of file dictionaries, each containing:
               - 'filename': str - Original filename
               - 'content': bytes - File content as bytes
               - 'size': int - File size in bytes
        context_description: Optional context or description for the processing task
        include_metadata: Whether to include detailed metadata in the output
        processing_options: Optional processing configuration overrides
    
    Returns:
        JSON string containing processing results with the following structure:
        {
            "status": "success" | "partial_success" | "error",
            "message": "Processing completion message",
            "results": {
                "total_files": int,
                "successful_files": int,
                "failed_files": int,
                "markdown_output": "Generated Markdown content",
                "processing_summary": {...},
                "file_results": [...]
            },
            "timestamp": "ISO timestamp"
        }
    
    Raises:
        Returns error information in JSON format rather than raising exceptions
        to provide user-friendly error handling in the Strands framework.
    """
    start_time = datetime.utcnow()
    
    try:
        # Input validation
        if not files or not isinstance(files, list):
            return _create_error_response(
                "No files provided or invalid file format",
                "INVALID_INPUT",
                {"provided_type": type(files).__name__}
            )
        
        logger.info(f"Starting multimodal content parsing for {len(files)} files")
        
        # Get tool instance
        tool = _get_tool_instance()
        
        # Step 1: Process file uploads and generate metadata
        try:
            file_metadata_list = tool.upload_manager.upload_files(files)
            logger.info(f"Successfully processed {len(file_metadata_list)} file uploads")
        except FileUploadError as e:
            return _create_error_response(
                f"File upload validation failed: {e.message}",
                e.error_code,
                e.context
            )
        
        # Step 2: Store files in S3 and update metadata with URLs
        stored_files = []
        storage_errors = []
        
        for i, (file_metadata, file_data) in enumerate(zip(file_metadata_list, files)):
            try:
                s3_url = tool.storage_service.store_file(
                    file_data=file_data['content'],
                    file_id=file_metadata.file_id,
                    file_name=file_metadata.original_name,
                    content_type=file_metadata.mime_type
                )
                
                # Update metadata with S3 URL
                file_metadata.s3_url = s3_url
                stored_files.append(file_metadata)
                
            except StorageError as e:
                error_msg = f"Failed to store file {file_metadata.original_name}: {e.message}"
                storage_errors.append(error_msg)
                logger.error(error_msg)
        
        if not stored_files:
            return _create_error_response(
                f"All files failed to store: {'; '.join(storage_errors)}",
                "STORAGE_FAILED",
                {"storage_errors": storage_errors}
            )
        
        # Step 3: Parse files using the content parsing engine
        try:
            parsed_content = tool.parsing_engine.parse_files(stored_files)
            logger.info(f"Content parsing completed: {parsed_content.successful_files}/{parsed_content.total_files} successful")
        except Exception as e:
            return _create_error_response(
                f"Content parsing failed: {str(e)}",
                "PARSING_ERROR",
                {"stored_files": len(stored_files)}
            )
        
        # Step 4: Prepare response
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Determine overall status
        if parsed_content.failed_files == 0:
            status = "success"
            message = f"Successfully processed all {parsed_content.total_files} files"
        elif parsed_content.successful_files > 0:
            status = "partial_success"
            message = f"Processed {parsed_content.successful_files}/{parsed_content.total_files} files successfully"
        else:
            status = "error"
            message = f"Failed to process any files successfully"
        
        # Build response
        response = {
            "status": status,
            "message": message,
            "results": {
                "total_files": parsed_content.total_files,
                "successful_files": parsed_content.successful_files,
                "failed_files": parsed_content.failed_files,
                "markdown_output": parsed_content.markdown_output,
                "processing_time": processing_time,
                "context_description": context_description
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add detailed information if requested
        if include_metadata:
            response["results"]["processing_summary"] = parsed_content.processing_summary
            response["results"]["file_results"] = [
                {
                    "file_id": result.file_id,
                    "file_name": result.file_name,
                    "content_type": result.content_type,
                    "success": result.success,
                    "processing_time": result.processing_time,
                    "error_message": result.error_message
                }
                for result in parsed_content.file_results
            ]
        
        # Add storage warnings if any
        if storage_errors:
            response["warnings"] = {
                "storage_errors": storage_errors,
                "message": "Some files failed to store but processing continued with available files"
            }
        
        logger.info(f"Multimodal content parsing completed in {processing_time:.2f}s")
        return json.dumps(response, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Unexpected error in parse_multimodal_content: {str(e)}")
        return _create_error_response(
            f"Unexpected error during processing: {str(e)}",
            "UNEXPECTED_ERROR",
            {"error_type": type(e).__name__}
        )


@tool
def get_supported_formats() -> str:
    """
    Get information about supported file formats and processing capabilities.
    
    Returns:
        JSON string containing supported formats, file size limits, and processing capabilities
    """
    try:
        tool = _get_tool_instance()
        
        # Get supported file types from the parsing engine
        supported_types = tool.parsing_engine.get_supported_file_types()
        
        # Get configuration limits
        file_limits = tool.multimodal_config.get('file_limits', {})
        
        response = {
            "status": "success",
            "supported_formats": {
                "image_formats": [fmt for fmt in supported_types if fmt in ['jpg', 'jpeg', 'png', 'gif', 'webp']],
                "document_formats": [fmt for fmt in supported_types if fmt in ['xlsx', 'xls', 'docx', 'doc', 'csv']],
                "text_formats": [fmt for fmt in supported_types if fmt in ['txt', 'md', 'json', 'yaml', 'yml']],
                "all_formats": supported_types
            },
            "limits": {
                "max_file_size": file_limits.get('max_file_size', '50MB'),
                "max_files_per_request": file_limits.get('max_files_per_request', 10)
            },
            "capabilities": {
                "image_analysis": "AWS Bedrock Claude multimodal model for image content recognition",
                "document_processing": "Excel and Word document content extraction and structuring",
                "text_processing": "Text content formatting and structure analysis",
                "batch_processing": "Support for multiple files in a single request",
                "markdown_output": "Unified Markdown format output for AI agent consumption"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting supported formats: {str(e)}")
        return _create_error_response(
            f"Failed to retrieve supported formats: {str(e)}",
            "FORMAT_INFO_ERROR",
            {"error_type": type(e).__name__}
        )


@tool
def validate_files(files: List[Dict[str, Any]]) -> str:
    """
    Validate files without processing them to check format support and size limits.
    
    Args:
        files: List of file dictionaries with 'filename', 'content', and 'size'
    
    Returns:
        JSON string containing validation results for each file
    """
    try:
        if not files or not isinstance(files, list):
            return _create_error_response(
                "No files provided or invalid file format",
                "INVALID_INPUT",
                {"provided_type": type(files).__name__}
            )
        
        tool = _get_tool_instance()
        
        validation_results = []
        overall_valid = True
        
        for i, file_data in enumerate(files):
            try:
                # Get file information and validation status
                file_info = tool.upload_manager.get_file_info(file_data)
                
                validation_result = {
                    "file_index": i,
                    "filename": file_info['filename'],
                    "file_type": file_info['file_type'],
                    "file_size": file_info['file_size'],
                    "formatted_size": file_info['formatted_size'],
                    "mime_type": file_info['mime_type'],
                    "is_valid": file_info['is_valid'],
                    "is_supported_format": file_info['is_supported_format'],
                    "validation_errors": file_info['validation_errors']
                }
                
                if not file_info['is_valid']:
                    overall_valid = False
                
                validation_results.append(validation_result)
                
            except Exception as e:
                validation_results.append({
                    "file_index": i,
                    "filename": file_data.get('filename', 'unknown'),
                    "is_valid": False,
                    "validation_errors": [f"Validation error: {str(e)}"]
                })
                overall_valid = False
        
        response = {
            "status": "success",
            "validation_summary": {
                "total_files": len(files),
                "valid_files": sum(1 for r in validation_results if r.get('is_valid', False)),
                "invalid_files": sum(1 for r in validation_results if not r.get('is_valid', False)),
                "overall_valid": overall_valid
            },
            "file_validations": validation_results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error validating files: {str(e)}")
        return _create_error_response(
            f"File validation failed: {str(e)}",
            "VALIDATION_ERROR",
            {"error_type": type(e).__name__}
        )


@tool
def get_processing_status() -> str:
    """
    Get current processing capabilities and system status.
    
    Returns:
        JSON string containing system status and processing capabilities
    """
    try:
        tool = _get_tool_instance()
        
        # Get system configuration
        processing_config = tool.multimodal_config.get('processing', {})
        aws_config = tool.multimodal_config.get('aws', {})
        model_config = tool.multimodal_config.get('model', {})
        
        # Get actual AWS region being used
        import os
        actual_aws_region = (
            os.getenv('AWS_DEFAULT_REGION') or 
            os.getenv('AWS_REGION') or
            aws_config.get('bedrock_region') or 
            tool.config.get('aws', {}).get('bedrock_region_name') or
            'us-west-2'
        )
        
        response = {
            "status": "success",
            "system_status": {
                "service_available": True,
                "initialization_time": datetime.utcnow().isoformat()
            },
            "processing_capabilities": {
                "max_concurrent_workers": processing_config.get('max_workers', 3),
                "processing_timeout": processing_config.get('timeout_seconds', 300),
                "retry_attempts": processing_config.get('retry_attempts', 3),
                "batch_size": processing_config.get('batch_size', 5)
            },
            "aws_configuration": {
                "region": actual_aws_region,
                "s3_bucket": aws_config.get('s3_bucket', 'nexus-ai-file-storage'),
                "s3_prefix": aws_config.get('s3_prefix', 'multimodal-content/'),
                "region_source": "environment" if os.getenv('AWS_DEFAULT_REGION') or os.getenv('AWS_REGION') else "config"
            },
            "model_configuration": {
                "primary_model": model_config.get('primary_model', 'us.anthropic.claude-3-7-sonnet-20250219-v1:0'),
                "fallback_model": model_config.get('fallback_model', 'us.anthropic.claude-3-5-haiku-20241022-v1:0'),
                "max_tokens": model_config.get('max_tokens', 4000)
            },
            "supported_processors": [
                "TextProcessor - Plain text file processing",
                "ImageProcessor - Image content analysis using multimodal models",
                "DocumentProcessor - Excel and Word document processing"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting processing status: {str(e)}")
        return _create_error_response(
            f"Failed to retrieve processing status: {str(e)}",
            "STATUS_ERROR",
            {"error_type": type(e).__name__}
        )


def _create_error_response(message: str, error_code: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Create a standardized error response in JSON format.
    
    Args:
        message: Error message
        error_code: Error code identifier
        context: Additional error context
    
    Returns:
        JSON string containing error information
    """
    response = {
        "status": "error",
        "error": {
            "message": message,
            "code": error_code,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    return json.dumps(response, ensure_ascii=False, indent=2)