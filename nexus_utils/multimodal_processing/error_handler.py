"""
Comprehensive error handling system for the multimodal content parser.

This module provides centralized error handling, logging, retry mechanisms,
and service degradation strategies for all components of the system.
"""

import logging
import time
import traceback
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from functools import wraps

from .models.exceptions import (
    MultimodalParserError,
    FileUploadError,
    FileProcessingError,
    StorageError,
    ModelServiceError
)


class ErrorSeverity(Enum):
    """Error severity levels for classification and handling."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for systematic handling."""
    FILE_UPLOAD = "file_upload"
    FILE_PROCESSING = "file_processing"
    STORAGE = "storage"
    MODEL_SERVICE = "model_service"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    SYSTEM = "system"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    error_id: str
    timestamp: float
    category: ErrorCategory
    severity: ErrorSeverity
    component: str
    operation: str
    user_message: str
    technical_message: str
    context_data: Dict[str, Any]
    retry_count: int = 0
    max_retries: int = 3
    recoverable: bool = True


@dataclass
class RetryConfig:
    """Configuration for retry mechanisms."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


class ErrorHandler:
    """
    Centralized error handling system with logging, retry mechanisms,
    and service degradation strategies.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the error handler.
        
        Args:
            logger: Optional logger instance. If not provided, creates a default logger.
        """
        self.logger = logger or self._create_default_logger()
        self.error_stats = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "recovery_success_rate": 0.0
        }
        self.active_errors = {}  # Track ongoing error situations
        
    def _create_default_logger(self) -> logging.Logger:
        """Create a default logger for error handling."""
        logger = logging.getLogger("multimodal_parser.error_handler")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def handle_upload_error(
        self, 
        error: Exception, 
        file_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """
        Handle file upload errors with appropriate classification and response.
        
        Args:
            error: The exception that occurred
            file_name: Name of the file being uploaded
            context: Additional context information
            
        Returns:
            ErrorContext with error details and handling information
        """
        error_context = self._create_error_context(
            error=error,
            category=ErrorCategory.FILE_UPLOAD,
            component="FileUploadManager",
            operation="upload_file",
            context_data={"file_name": file_name, **(context or {})}
        )
        
        # Classify specific upload errors
        if "unsupported format" in str(error).lower():
            error_context.severity = ErrorSeverity.LOW
            error_context.user_message = f"File format not supported for '{file_name}'. Please use supported formats: JPG, PNG, TXT, XLSX, DOCX."
            error_context.recoverable = False
            
        elif "file size" in str(error).lower():
            error_context.severity = ErrorSeverity.MEDIUM
            error_context.user_message = f"File '{file_name}' exceeds size limit. Please use files smaller than 50MB."
            error_context.recoverable = False
            
        elif "network" in str(error).lower() or "timeout" in str(error).lower():
            error_context.severity = ErrorSeverity.MEDIUM
            error_context.user_message = f"Network error uploading '{file_name}'. Please try again."
            error_context.recoverable = True
            error_context.max_retries = 3
            
        else:
            error_context.severity = ErrorSeverity.HIGH
            error_context.user_message = f"Failed to upload '{file_name}'. Please check the file and try again."
            
        self._log_error(error_context)
        self._update_error_stats(error_context)
        
        return error_context
    
    def handle_processing_error(
        self,
        error: Exception,
        file_id: str,
        processor_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """
        Handle file processing errors with recovery strategies.
        
        Args:
            error: The exception that occurred
            file_id: ID of the file being processed
            processor_type: Type of processor (image, document, text)
            context: Additional context information
            
        Returns:
            ErrorContext with error details and handling information
        """
        error_context = self._create_error_context(
            error=error,
            category=ErrorCategory.FILE_PROCESSING,
            component=f"{processor_type}Processor",
            operation="process_file",
            context_data={"file_id": file_id, "processor_type": processor_type, **(context or {})}
        )
        
        # Classify processing errors
        if "corrupted" in str(error).lower() or "invalid format" in str(error).lower():
            error_context.severity = ErrorSeverity.HIGH
            error_context.user_message = "File appears to be corrupted or in an invalid format."
            error_context.recoverable = False
            
        elif "timeout" in str(error).lower():
            error_context.severity = ErrorSeverity.MEDIUM
            error_context.user_message = "File processing timed out. This may be due to file complexity."
            error_context.recoverable = True
            error_context.max_retries = 2
            
        elif "memory" in str(error).lower():
            error_context.severity = ErrorSeverity.HIGH
            error_context.user_message = "File is too large to process. Please try with a smaller file."
            error_context.recoverable = False
            
        else:
            error_context.severity = ErrorSeverity.MEDIUM
            error_context.user_message = "File processing failed. Attempting alternative processing method."
            error_context.recoverable = True
            
        self._log_error(error_context)
        self._update_error_stats(error_context)
        
        return error_context
    
    def handle_model_error(
        self,
        error: Exception,
        retry_count: int = 0,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """
        Handle multimodal model service errors with retry and degradation strategies.
        
        Args:
            error: The exception that occurred
            retry_count: Current retry attempt number
            context: Additional context information
            
        Returns:
            ErrorContext with error details and handling information
        """
        error_context = self._create_error_context(
            error=error,
            category=ErrorCategory.MODEL_SERVICE,
            component="MultimodalModelService",
            operation="model_call",
            context_data={"retry_count": retry_count, **(context or {})}
        )
        
        error_context.retry_count = retry_count
        
        # Classify model service errors
        if "quota" in str(error).lower() or "rate limit" in str(error).lower():
            error_context.severity = ErrorSeverity.HIGH
            error_context.user_message = "AI service is temporarily overloaded. Please try again in a few minutes."
            error_context.recoverable = True
            error_context.max_retries = 5
            
        elif "timeout" in str(error).lower():
            error_context.severity = ErrorSeverity.MEDIUM
            error_context.user_message = "AI service response timed out. Retrying with optimized parameters."
            error_context.recoverable = True
            error_context.max_retries = 3
            
        elif "unauthorized" in str(error).lower() or "credentials" in str(error).lower():
            error_context.severity = ErrorSeverity.CRITICAL
            error_context.user_message = "AI service authentication failed. Please check configuration."
            error_context.recoverable = False
            
        elif "service unavailable" in str(error).lower():
            error_context.severity = ErrorSeverity.HIGH
            error_context.user_message = "AI service is temporarily unavailable. Using fallback processing."
            error_context.recoverable = True
            error_context.max_retries = 2
            
        else:
            error_context.severity = ErrorSeverity.MEDIUM
            error_context.user_message = "AI service encountered an error. Attempting recovery."
            error_context.recoverable = True
            
        self._log_error(error_context)
        self._update_error_stats(error_context)
        
        return error_context
    
    def handle_storage_error(
        self,
        error: Exception,
        operation: str,
        file_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """
        Handle storage service errors with fallback strategies.
        
        Args:
            error: The exception that occurred
            operation: Storage operation being performed
            file_id: Optional file ID involved in the operation
            context: Additional context information
            
        Returns:
            ErrorContext with error details and handling information
        """
        error_context = self._create_error_context(
            error=error,
            category=ErrorCategory.STORAGE,
            component="S3StorageService",
            operation=operation,
            context_data={"file_id": file_id, **(context or {})}
        )
        
        # Classify storage errors
        if "connection" in str(error).lower() or "network" in str(error).lower():
            error_context.severity = ErrorSeverity.MEDIUM
            error_context.user_message = "Storage service connection failed. Using local temporary storage."
            error_context.recoverable = True
            error_context.max_retries = 3
            
        elif "permission" in str(error).lower() or "access denied" in str(error).lower():
            error_context.severity = ErrorSeverity.HIGH
            error_context.user_message = "Storage access denied. Please check permissions."
            error_context.recoverable = False
            
        elif "not found" in str(error).lower():
            error_context.severity = ErrorSeverity.MEDIUM
            error_context.user_message = "File not found in storage. It may have been moved or deleted."
            error_context.recoverable = False
            
        elif "quota" in str(error).lower() or "space" in str(error).lower():
            error_context.severity = ErrorSeverity.HIGH
            error_context.user_message = "Storage quota exceeded. Please contact administrator."
            error_context.recoverable = False
            
        else:
            error_context.severity = ErrorSeverity.MEDIUM
            error_context.user_message = "Storage operation failed. Attempting alternative approach."
            error_context.recoverable = True
            
        self._log_error(error_context)
        self._update_error_stats(error_context)
        
        return error_context
    
    def with_retry(
        self,
        func: Callable,
        retry_config: Optional[RetryConfig] = None,
        error_handler: Optional[Callable[[Exception, int], ErrorContext]] = None
    ) -> Callable:
        """
        Decorator to add retry functionality to any function.
        
        Args:
            func: Function to wrap with retry logic
            retry_config: Retry configuration
            error_handler: Optional custom error handler
            
        Returns:
            Wrapped function with retry capability
        """
        config = retry_config or RetryConfig()
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_error = e
                    
                    # Handle error if handler provided
                    if error_handler:
                        error_context = error_handler(e, attempt)
                        if not error_context.recoverable:
                            break
                    
                    # Don't retry on last attempt
                    if attempt == config.max_attempts - 1:
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    # Add jitter if enabled
                    if config.jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)
                    
                    self.logger.info(f"Retrying {func.__name__} in {delay:.2f}s (attempt {attempt + 1}/{config.max_attempts})")
                    time.sleep(delay)
            
            # All retries exhausted, raise the last error
            raise last_error
            
        return wrapper
    
    def cleanup_error_state(self, error_id: str) -> bool:
        """
        Clean up error state and resources after error resolution.
        
        Args:
            error_id: ID of the error to clean up
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            if error_id in self.active_errors:
                error_context = self.active_errors[error_id]
                
                # Perform cleanup based on error category
                if error_context.category == ErrorCategory.STORAGE:
                    self._cleanup_storage_error(error_context)
                elif error_context.category == ErrorCategory.FILE_PROCESSING:
                    self._cleanup_processing_error(error_context)
                elif error_context.category == ErrorCategory.MODEL_SERVICE:
                    self._cleanup_model_error(error_context)
                
                # Remove from active errors
                del self.active_errors[error_id]
                
                self.logger.info(f"Cleaned up error state for {error_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup error state for {error_id}: {e}")
            
        return False
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive error statistics for monitoring and analysis.
        
        Returns:
            Dictionary containing error statistics
        """
        return {
            **self.error_stats,
            "active_errors": len(self.active_errors),
            "error_categories": list(ErrorCategory),
            "severity_levels": list(ErrorSeverity)
        }
    
    def _create_error_context(
        self,
        error: Exception,
        category: ErrorCategory,
        component: str,
        operation: str,
        context_data: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """Create an ErrorContext from an exception."""
        import uuid
        
        error_id = str(uuid.uuid4())
        timestamp = time.time()
        
        # Extract technical message
        technical_message = f"{type(error).__name__}: {str(error)}"
        if hasattr(error, '__traceback__') and error.__traceback__:
            technical_message += f"\n{''.join(traceback.format_tb(error.__traceback__))}"
        
        error_context = ErrorContext(
            error_id=error_id,
            timestamp=timestamp,
            category=category,
            severity=ErrorSeverity.MEDIUM,  # Default, will be updated by specific handlers
            component=component,
            operation=operation,
            user_message="An error occurred during processing.",  # Default, will be updated
            technical_message=technical_message,
            context_data=context_data or {}
        )
        
        # Store in active errors for tracking
        self.active_errors[error_id] = error_context
        
        return error_context
    
    def _log_error(self, error_context: ErrorContext) -> None:
        """Log error with appropriate level based on severity."""
        log_message = (
            f"[{error_context.error_id}] {error_context.component}.{error_context.operation} - "
            f"{error_context.user_message}"
        )
        
        if error_context.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
            self.logger.debug(f"Technical details: {error_context.technical_message}")
        elif error_context.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
            self.logger.debug(f"Technical details: {error_context.technical_message}")
        elif error_context.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def _update_error_stats(self, error_context: ErrorContext) -> None:
        """Update error statistics."""
        self.error_stats["total_errors"] += 1
        
        # Update category stats
        category_key = error_context.category.value
        if category_key not in self.error_stats["errors_by_category"]:
            self.error_stats["errors_by_category"][category_key] = 0
        self.error_stats["errors_by_category"][category_key] += 1
        
        # Update severity stats
        severity_key = error_context.severity.value
        if severity_key not in self.error_stats["errors_by_severity"]:
            self.error_stats["errors_by_severity"][severity_key] = 0
        self.error_stats["errors_by_severity"][severity_key] += 1
    
    def _cleanup_storage_error(self, error_context: ErrorContext) -> None:
        """Clean up storage-related error state."""
        # Remove temporary files, reset connections, etc.
        self.logger.debug(f"Cleaning up storage error: {error_context.error_id}")
    
    def _cleanup_processing_error(self, error_context: ErrorContext) -> None:
        """Clean up processing-related error state."""
        # Clear processing caches, reset processors, etc.
        self.logger.debug(f"Cleaning up processing error: {error_context.error_id}")
    
    def _cleanup_model_error(self, error_context: ErrorContext) -> None:
        """Clean up model service-related error state."""
        # Reset model connections, clear caches, etc.
        self.logger.debug(f"Cleaning up model error: {error_context.error_id}")


# Global error handler instance
_global_error_handler = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def handle_errors(
    error_handler_func: Optional[Callable[[Exception, int], ErrorContext]] = None,
    retry_config: Optional[RetryConfig] = None
):
    """
    Decorator for automatic error handling and retry.
    
    Args:
        error_handler_func: Optional custom error handler function
        retry_config: Optional retry configuration
    """
    def decorator(func):
        error_handler = get_error_handler()
        return error_handler.with_retry(func, retry_config, error_handler_func)
    return decorator