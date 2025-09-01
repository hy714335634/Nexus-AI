"""
Exception classes for the multimodal content parser system.
"""


class MultimodalParserError(Exception):
    """
    Base exception class for all multimodal parser errors.
    
    Attributes:
        message: Human-readable error message
        error_code: Optional error code for programmatic handling
        context: Additional context information about the error
    """
    
    def __init__(self, message: str, error_code: str = None, context: dict = None):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(self.message)


class FileUploadError(MultimodalParserError):
    """
    Exception raised when file upload operations fail.
    
    Common scenarios:
    - Unsupported file format
    - File size exceeds limits
    - Network transmission errors
    - Invalid file content
    """
    pass


class FileProcessingError(MultimodalParserError):
    """
    Exception raised when file processing operations fail.
    
    Common scenarios:
    - Corrupted file content
    - Unsupported file structure
    - Processing timeout
    - Memory limitations
    """
    pass


class StorageError(MultimodalParserError):
    """
    Exception raised when storage operations fail.
    
    Common scenarios:
    - S3 connection failures
    - Insufficient storage space
    - Permission/access errors
    - File not found
    """
    pass


class ModelServiceError(MultimodalParserError):
    """
    Exception raised when multimodal model service operations fail.
    
    Common scenarios:
    - AWS Bedrock API failures
    - Model quota exceeded
    - Invalid model responses
    - Service timeouts
    """
    pass