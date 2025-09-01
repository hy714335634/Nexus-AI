"""
Abstract interfaces for the multimodal content parser system.
"""

from abc import ABC, abstractmethod
from typing import List
from .data_models import FileMetadata, ProcessedContent


class FileProcessor(ABC):
    """
    Abstract base class for file processors.
    
    This interface defines the contract that all file processors must implement
    to handle different file types in the multimodal content parser system.
    """
    
    @abstractmethod
    def can_process(self, file_type: str) -> bool:
        """
        Check if this processor can handle the given file type.
        
        Args:
            file_type: File extension or type identifier (e.g., 'jpg', 'xlsx')
            
        Returns:
            True if this processor can handle the file type, False otherwise
        """
        pass
    
    @abstractmethod
    def process(self, file_metadata: FileMetadata) -> ProcessedContent:
        """
        Process a file and return the processed content.
        
        Args:
            file_metadata: Metadata about the file to process
            
        Returns:
            ProcessedContent object containing the processing results
            
        Raises:
            FileProcessingError: If processing fails
        """
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[str]:
        """
        Get list of file types supported by this processor.
        
        Returns:
            List of supported file extensions/types
        """
        pass