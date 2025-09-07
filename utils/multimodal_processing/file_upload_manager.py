"""
File upload manager for the multimodal content parser system.

This module provides the FileUploadManager class that handles file upload operations,
validation, and metadata generation for the multimodal content parser.
"""

import uuid
import mimetypes
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
import logging

from .models.data_models import FileMetadata
from .models.exceptions import FileUploadError
from ..config_loader import ConfigLoader


logger = logging.getLogger(__name__)


class FileUploadManager:
    """
    Manages file upload operations including validation, metadata generation,
    and error handling for the multimodal content parser system.
    
    This class handles:
    - File format validation
    - File size limit enforcement
    - UUID generation for unique file identification
    - MIME type detection
    - Upload status tracking and error reporting
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the FileUploadManager with configuration.
        
        Args:
            config: Optional configuration dictionary. If None, loads from default config.
        """
        if config is None:
            config_loader = ConfigLoader()
            self.config_loader = config_loader
            self.multimodal_config = config_loader.get_multimodal_parser_config()
        else:
            self.config_loader = None
            self.multimodal_config = config.get('multimodal_parser', {})
            
        self.file_limits = self.multimodal_config.get('file_limits', {})
        
        # Parse configuration values
        self.max_file_size = self._parse_file_size(
            self.file_limits.get('max_file_size', '50MB')
        )
        self.max_files_per_request = self.file_limits.get('max_files_per_request', 10)
        # Get supported formats with fallback
        configured_formats = self.file_limits.get('supported_formats', [])
        if not configured_formats:
            # Fallback to default formats if config is empty
            configured_formats = ["jpg", "jpeg", "png", "gif", "txt", "xlsx", "docx", "csv", "md", "json"]
            logger.warning("No supported formats found in config, using defaults")
        
        self.supported_formats = set(
            fmt.lower() for fmt in configured_formats
        )
        
        logger.info(f"FileUploadManager initialized with max_file_size={self.max_file_size}, "
                   f"max_files={self.max_files_per_request}, "
                   f"supported_formats={self.supported_formats}")
        
        # Debug logging
        logger.debug(f"Config path: multimodal_parser.file_limits.supported_formats")
        logger.debug(f"Raw config: {self.file_limits}")
        logger.debug(f"Configured formats: {configured_formats}")
    
    def upload_files(self, files: List[Dict[str, Any]]) -> List[FileMetadata]:
        """
        Process multiple file uploads and generate metadata for each.
        
        Args:
            files: List of file dictionaries containing 'filename', 'content', and 'size'
                  Each file dict should have:
                  - 'filename': str - Original filename
                  - 'content': bytes - File content
                  - 'size': int - File size in bytes
        
        Returns:
            List of FileMetadata objects for successfully processed files
            
        Raises:
            FileUploadError: If validation fails or upload limits are exceeded
        """
        if not files:
            raise FileUploadError(
                "No files provided for upload",
                error_code="NO_FILES",
                context={"file_count": 0}
            )
        
        if len(files) > self.max_files_per_request:
            raise FileUploadError(
                f"Too many files. Maximum {self.max_files_per_request} files allowed per request",
                error_code="TOO_MANY_FILES",
                context={
                    "provided_count": len(files),
                    "max_allowed": self.max_files_per_request
                }
            )
        
        processed_files = []
        errors = []
        
        for i, file_data in enumerate(files):
            try:
                file_metadata = self._process_single_file(file_data, i)
                processed_files.append(file_metadata)
                logger.info(f"Successfully processed file: {file_metadata.original_name}")
                
            except FileUploadError as e:
                error_msg = f"Failed to process file {i+1}: {e.message}"
                errors.append(error_msg)
                logger.error(error_msg, extra={"error_context": e.context})
        
        if errors and not processed_files:
            # All files failed
            raise FileUploadError(
                f"All files failed validation: {'; '.join(errors)}",
                error_code="ALL_FILES_FAILED",
                context={"errors": errors, "total_files": len(files)}
            )
        elif errors:
            # Some files failed - log warnings but continue
            logger.warning(f"Some files failed validation: {'; '.join(errors)}")
        
        return processed_files
    
    def _process_single_file(self, file_data: Dict[str, Any], index: int) -> FileMetadata:
        """
        Process a single file and generate its metadata.
        
        Args:
            file_data: Dictionary containing file information
            index: File index in the batch for error reporting
            
        Returns:
            FileMetadata object for the processed file
            
        Raises:
            FileUploadError: If file validation fails
        """
        # Validate required fields
        required_fields = ['filename', 'content', 'size']
        missing_fields = [field for field in required_fields if field not in file_data]
        if missing_fields:
            raise FileUploadError(
                f"Missing required fields: {', '.join(missing_fields)}",
                error_code="MISSING_FIELDS",
                context={"missing_fields": missing_fields, "file_index": index}
            )
        
        filename = file_data['filename']
        content = file_data['content']
        file_size = file_data['size']
        
        # Validate file
        self.validate_file(filename, content, file_size)
        
        # Generate file metadata
        file_id = self.generate_file_id()
        file_type = self._extract_file_type(filename)
        mime_type = self._detect_mime_type(filename, content)
        upload_time = datetime.utcnow()
        
        # S3 URL will be set by the S3StorageService
        s3_url = ""
        
        return FileMetadata(
            file_id=file_id,
            original_name=filename,
            file_type=file_type,
            file_size=file_size,
            upload_time=upload_time,
            s3_url=s3_url,
            mime_type=mime_type
        )
    
    def validate_file(self, filename: str, content: bytes, file_size: int) -> bool:
        """
        Validate a file against format and size constraints.
        
        Args:
            filename: Original filename
            content: File content as bytes
            file_size: File size in bytes
            
        Returns:
            True if validation passes
            
        Raises:
            FileUploadError: If validation fails
        """
        # Validate filename
        if not filename or not filename.strip():
            raise FileUploadError(
                "Filename cannot be empty",
                error_code="EMPTY_FILENAME",
                context={"filename": filename}
            )
        
        # Validate file size
        if file_size <= 0:
            raise FileUploadError(
                "File size must be greater than 0",
                error_code="INVALID_FILE_SIZE",
                context={"filename": filename, "size": file_size}
            )
        
        if file_size > self.max_file_size:
            raise FileUploadError(
                f"File size {self._format_file_size(file_size)} exceeds maximum allowed size "
                f"{self._format_file_size(self.max_file_size)}",
                error_code="FILE_TOO_LARGE",
                context={
                    "filename": filename,
                    "size": file_size,
                    "max_size": self.max_file_size
                }
            )
        
        # Validate file format
        file_type = self._extract_file_type(filename)
        if not file_type:
            raise FileUploadError(
                f"Cannot determine file type from filename: {filename}",
                error_code="UNKNOWN_FILE_TYPE",
                context={"filename": filename}
            )
        
        # Debug logging
        logger.debug(f"Validating file type: '{file_type}' (length: {len(file_type)})")
        logger.debug(f"Supported formats: {self.supported_formats}")
        logger.debug(f"File type in supported formats: {file_type.lower() in self.supported_formats}")
        
        if file_type.lower() not in self.supported_formats:
            raise FileUploadError(
                f"Unsupported file format: '{file_type}'. "
                f"Supported formats: {', '.join(sorted(self.supported_formats))}",
                error_code="UNSUPPORTED_FORMAT",
                context={
                    "filename": filename,
                    "file_type": file_type,
                    "file_type_repr": repr(file_type),
                    "supported_formats": list(self.supported_formats)
                }
            )
        
        # Validate content is not empty
        if not content:
            raise FileUploadError(
                "File content cannot be empty",
                error_code="EMPTY_CONTENT",
                context={"filename": filename}
            )
        
        # Validate content size matches reported size
        actual_size = len(content)
        if actual_size != file_size:
            raise FileUploadError(
                f"File size mismatch: reported {file_size} bytes, actual {actual_size} bytes",
                error_code="SIZE_MISMATCH",
                context={
                    "filename": filename,
                    "reported_size": file_size,
                    "actual_size": actual_size
                }
            )
        
        return True
    
    def generate_file_id(self) -> str:
        """
        Generate a unique UUID identifier for a file.
        
        Returns:
            UUID string in standard format (e.g., '550e8400-e29b-41d4-a716-446655440000')
        """
        return str(uuid.uuid4())
    
    def get_file_info(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract basic information about a file.
        
        Args:
            file_data: Dictionary containing file information
            
        Returns:
            Dictionary with file information including type, size, and validation status
        """
        filename = file_data.get('filename', '')
        file_size = file_data.get('size', 0)
        content = file_data.get('content', b'')
        
        file_type = self._extract_file_type(filename)
        mime_type = self._detect_mime_type(filename, content)
        
        # Check validation status
        is_valid = True
        validation_errors = []
        
        try:
            self.validate_file(filename, content, file_size)
        except FileUploadError as e:
            is_valid = False
            validation_errors.append(e.message)
        
        return {
            'filename': filename,
            'file_type': file_type,
            'file_size': file_size,
            'formatted_size': self._format_file_size(file_size),
            'mime_type': mime_type,
            'is_valid': is_valid,
            'validation_errors': validation_errors,
            'is_supported_format': file_type.lower() in self.supported_formats if file_type else False
        }
    
    def _extract_file_type(self, filename: str) -> str:
        """
        Extract file extension from filename.
        
        Args:
            filename: Original filename
            
        Returns:
            File extension without the dot (e.g., 'jpg', 'xlsx')
        """
        if not filename:
            return ""
        
        path = Path(filename)
        extension = path.suffix.lower()
        
        # Remove the leading dot and clean up the result
        file_type = extension[1:] if extension.startswith('.') else extension
        file_type = file_type.strip().rstrip('.')  # Remove any whitespace and trailing dots
        
        # Additional cleanup for any hidden characters
        file_type = ''.join(c for c in file_type if c.isalnum())
        
        # Debug logging
        logger.debug(f"Extracting file type from '{filename}': suffix='{extension}', result='{file_type}'")
        
        return file_type
    
    def _detect_mime_type(self, filename: str, content: bytes) -> str:
        """
        Detect MIME type of a file based on filename and content.
        
        Args:
            filename: Original filename
            content: File content as bytes
            
        Returns:
            MIME type string (e.g., 'image/jpeg', 'application/vnd.ms-excel')
        """
        # First try to guess from filename
        mime_type, _ = mimetypes.guess_type(filename)
        
        if mime_type:
            return mime_type
        
        # Fallback to content-based detection for common formats
        if content:
            # Check for common image formats by magic bytes
            if content.startswith(b'\xff\xd8\xff'):
                return 'image/jpeg'
            elif content.startswith(b'\x89PNG\r\n\x1a\n'):
                return 'image/png'
            elif content.startswith(b'GIF8'):
                return 'image/gif'
            elif content.startswith(b'PK\x03\x04'):
                # ZIP-based formats (Excel, Word, etc.)
                file_type = self._extract_file_type(filename)
                if file_type in ['xlsx', 'xlsm']:
                    return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                elif file_type in ['docx', 'docm']:
                    return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        
        # Default fallback
        return 'application/octet-stream'
    
    def _parse_file_size(self, size_str: str) -> int:
        """
        Parse file size string to bytes.
        
        Args:
            size_str: Size string like '50MB', '1GB', '500KB'
            
        Returns:
            Size in bytes
        """
        if not size_str:
            return 0
        
        size_str = size_str.upper().strip()
        
        # Extract number and unit
        import re
        match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?B?)$', size_str)
        if not match:
            # Try to parse as plain number (assume bytes)
            try:
                return int(float(size_str))
            except ValueError:
                logger.warning(f"Could not parse file size: {size_str}, using default 50MB")
                return 50 * 1024 * 1024
        
        number, unit = match.groups()
        number = float(number)
        
        # Convert to bytes
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3,
            'TB': 1024 ** 4,
            '': 1  # No unit means bytes
        }
        
        multiplier = multipliers.get(unit, 1)
        return int(number * multiplier)
    
    def _format_file_size(self, size_bytes: int) -> str:
        """
        Format file size in bytes to human-readable string.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string (e.g., '1.5 MB', '500 KB')
        """
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"