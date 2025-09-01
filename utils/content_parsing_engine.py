"""
Content parsing engine for the multimodal content parser system.

This module provides the ContentParsingEngine class that serves as the core coordinator
for processing multiple files through different processors and generating unified output.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Type
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from models.interfaces import FileProcessor
from models.data_models import FileMetadata, ProcessedContent, ParsedContent
from models.exceptions import FileProcessingError, MultimodalParserError
from utils.text_processor import TextProcessor
from utils.image_processor import ImageProcessor
from utils.document_processor import DocumentProcessor
from utils.markdown_generator import MarkdownGenerator
from utils.multimodal_model_service import MultimodalModelService


class ContentParsingEngine:
    """
    Core coordinator for the multimodal content parsing system.
    
    This engine handles:
    - File type detection and processor selection
    - Batch file processing with status management
    - Result combination and error aggregation
    - Unified Markdown output generation
    """
    
    def __init__(self, multimodal_service: Optional[MultimodalModelService] = None,
                 max_workers: int = 3, processing_timeout: int = 300):
        """
        Initialize the content parsing engine.
        
        Args:
            multimodal_service: Optional multimodal model service instance
            max_workers: Maximum number of concurrent processing threads
            processing_timeout: Timeout for individual file processing in seconds
        """
        self.logger = logging.getLogger(__name__)
        self.multimodal_service = multimodal_service or MultimodalModelService()
        self.max_workers = max_workers
        self.processing_timeout = processing_timeout
        
        # Initialize processors
        self.processors: List[FileProcessor] = [
            TextProcessor(self.multimodal_service),
            ImageProcessor(self.multimodal_service),
            DocumentProcessor(self.multimodal_service)
        ]
        
        # Initialize markdown generator
        self.markdown_generator = MarkdownGenerator()
        
        # Create processor mapping for quick lookup
        self._processor_map = self._build_processor_map()
        
        self.logger.info(f"ContentParsingEngine initialized with {len(self.processors)} processors")
    
    def parse_files(self, file_metadata_list: List[FileMetadata]) -> ParsedContent:
        """
        Parse multiple files and return combined results.
        
        Args:
            file_metadata_list: List of file metadata to process
            
        Returns:
            ParsedContent object containing all processing results
            
        Raises:
            MultimodalParserError: If critical parsing errors occur
        """
        if not file_metadata_list:
            return self._create_empty_result()
        
        start_time = time.time()
        self.logger.info(f"Starting batch processing of {len(file_metadata_list)} files")
        
        try:
            # Process files (with optional parallel processing)
            file_results = self._process_files_batch(file_metadata_list)
            
            # Generate combined markdown output
            markdown_output = self.markdown_generator.generate_output(
                file_results, file_metadata_list
            )
            
            # Calculate summary statistics
            total_files = len(file_metadata_list)
            successful_files = sum(1 for result in file_results if result.success)
            failed_files = total_files - successful_files
            
            processing_time = time.time() - start_time
            
            # Create processing summary
            processing_summary = self._create_processing_summary(
                file_results, processing_time
            )
            
            self.logger.info(
                f"Batch processing completed: {successful_files}/{total_files} files successful "
                f"in {processing_time:.2f} seconds"
            )
            
            return ParsedContent(
                total_files=total_files,
                successful_files=successful_files,
                failed_files=failed_files,
                markdown_output=markdown_output,
                file_results=file_results,
                processing_summary=processing_summary
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Batch processing failed after {processing_time:.2f}s: {str(e)}"
            self.logger.error(error_msg)
            
            # Return partial results if any files were processed
            return self._create_error_result(file_metadata_list, error_msg)
    
    def get_processor(self, file_type: str) -> Optional[FileProcessor]:
        """
        Get the appropriate processor for a given file type.
        
        Args:
            file_type: File extension or type identifier
            
        Returns:
            FileProcessor instance that can handle the file type, or None if unsupported
        """
        file_type_lower = file_type.lower().lstrip('.')
        return self._processor_map.get(file_type_lower)
    
    def get_supported_file_types(self) -> List[str]:
        """
        Get list of all supported file types across all processors.
        
        Returns:
            List of supported file extensions
        """
        supported_types = set()
        for processor in self.processors:
            supported_types.update(processor.get_supported_types())
        return sorted(list(supported_types))
    
    def _process_files_batch(self, file_metadata_list: List[FileMetadata]) -> List[ProcessedContent]:
        """
        Process multiple files, optionally in parallel.
        
        Args:
            file_metadata_list: List of file metadata to process
            
        Returns:
            List of ProcessedContent results in the same order as input
        """
        if len(file_metadata_list) == 1 or self.max_workers == 1:
            # Process sequentially for single file or when parallel processing is disabled
            return [self._process_single_file(metadata) for metadata in file_metadata_list]
        
        # Process in parallel
        results = [None] * len(file_metadata_list)  # Preserve order
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(self._process_single_file, metadata): i
                for i, metadata in enumerate(file_metadata_list)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_index, timeout=self.processing_timeout * len(file_metadata_list)):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as e:
                    # Create error result for failed processing
                    metadata = file_metadata_list[index]
                    error_msg = f"Parallel processing failed: {str(e)}"
                    self.logger.error(f"Failed to process {metadata.original_name}: {error_msg}")
                    
                    results[index] = ProcessedContent(
                        file_id=metadata.file_id,
                        file_name=metadata.original_name,
                        content_type="unknown",
                        processed_text="",
                        metadata={},
                        processing_time=0.0,
                        success=False,
                        error_message=error_msg
                    )
        
        return results
    
    def _process_single_file(self, file_metadata: FileMetadata) -> ProcessedContent:
        """
        Process a single file using the appropriate processor.
        
        Args:
            file_metadata: Metadata for the file to process
            
        Returns:
            ProcessedContent result for the file
        """
        start_time = time.time()
        
        try:
            self.logger.debug(f"Processing file: {file_metadata.original_name}")
            
            # Get appropriate processor
            processor = self.get_processor(file_metadata.file_type)
            
            if processor is None:
                raise FileProcessingError(
                    f"No processor available for file type: {file_metadata.file_type}",
                    error_code="UNSUPPORTED_FILE_TYPE",
                    context={
                        "file_type": file_metadata.file_type,
                        "supported_types": self.get_supported_file_types()
                    }
                )
            
            # Process the file
            result = processor.process(file_metadata)
            
            processing_time = time.time() - start_time
            self.logger.debug(
                f"File {file_metadata.original_name} processed in {processing_time:.2f}s "
                f"(success: {result.success})"
            )
            
            return result
            
        except FileProcessingError as e:
            # Handle known processing errors
            processing_time = time.time() - start_time
            self.logger.warning(f"Processing error for {file_metadata.original_name}: {e.message}")
            
            return ProcessedContent(
                file_id=file_metadata.file_id,
                file_name=file_metadata.original_name,
                content_type="error",
                processed_text="",
                metadata={"error_code": e.error_code, "error_context": e.context},
                processing_time=processing_time,
                success=False,
                error_message=e.message
            )
            
        except Exception as e:
            # Handle unexpected errors
            processing_time = time.time() - start_time
            error_msg = f"Unexpected error processing {file_metadata.original_name}: {str(e)}"
            self.logger.error(error_msg)
            
            return ProcessedContent(
                file_id=file_metadata.file_id,
                file_name=file_metadata.original_name,
                content_type="error",
                processed_text="",
                metadata={"error_type": type(e).__name__},
                processing_time=processing_time,
                success=False,
                error_message=error_msg
            )
    
    def _build_processor_map(self) -> Dict[str, FileProcessor]:
        """
        Build a mapping from file types to processors for quick lookup.
        
        Returns:
            Dictionary mapping file extensions to processor instances
        """
        processor_map = {}
        
        for processor in self.processors:
            for file_type in processor.get_supported_types():
                file_type_lower = file_type.lower().lstrip('.')
                if file_type_lower in processor_map:
                    self.logger.warning(
                        f"File type '{file_type_lower}' is supported by multiple processors. "
                        f"Using {type(processor).__name__}"
                    )
                processor_map[file_type_lower] = processor
        
        self.logger.info(f"Built processor map for {len(processor_map)} file types")
        return processor_map
    
    def _create_processing_summary(self, file_results: List[ProcessedContent], 
                                 total_processing_time: float) -> Dict[str, Any]:
        """
        Create summary statistics for the processing session.
        
        Args:
            file_results: List of processing results
            total_processing_time: Total time taken for all processing
            
        Returns:
            Dictionary containing processing summary statistics
        """
        # Group results by content type and success status
        content_type_stats = {}
        error_summary = {}
        
        total_individual_time = 0.0
        
        for result in file_results:
            content_type = result.content_type
            
            # Update content type statistics
            if content_type not in content_type_stats:
                content_type_stats[content_type] = {
                    'total': 0, 'successful': 0, 'failed': 0, 'processing_time': 0.0
                }
            
            stats = content_type_stats[content_type]
            stats['total'] += 1
            stats['processing_time'] += result.processing_time
            total_individual_time += result.processing_time
            
            if result.success:
                stats['successful'] += 1
            else:
                stats['failed'] += 1
                
                # Track error types
                if result.error_message:
                    error_type = result.metadata.get('error_code', 'UNKNOWN_ERROR')
                    error_summary[error_type] = error_summary.get(error_type, 0) + 1
        
        return {
            'processing_start_time': datetime.now().isoformat(),
            'total_processing_time': total_processing_time,
            'individual_processing_time': total_individual_time,
            'parallel_efficiency': total_individual_time / total_processing_time if total_processing_time > 0 else 1.0,
            'content_type_statistics': content_type_stats,
            'error_summary': error_summary,
            'processor_count': len(self.processors),
            'max_workers': self.max_workers,
            'supported_file_types': self.get_supported_file_types()
        }
    
    def _create_empty_result(self) -> ParsedContent:
        """Create result for empty file list."""
        return ParsedContent(
            total_files=0,
            successful_files=0,
            failed_files=0,
            markdown_output=self.markdown_generator._generate_empty_output(),
            file_results=[],
            processing_summary={
                'processing_start_time': datetime.now().isoformat(),
                'total_processing_time': 0.0,
                'message': 'No files provided for processing'
            }
        )
    
    def _create_error_result(self, file_metadata_list: List[FileMetadata], 
                           error_message: str) -> ParsedContent:
        """
        Create result for critical processing errors.
        
        Args:
            file_metadata_list: Original file metadata list
            error_message: Error message describing the failure
            
        Returns:
            ParsedContent with error information
        """
        # Create error results for all files
        error_results = []
        for metadata in file_metadata_list:
            error_results.append(ProcessedContent(
                file_id=metadata.file_id,
                file_name=metadata.original_name,
                content_type="error",
                processed_text="",
                metadata={},
                processing_time=0.0,
                success=False,
                error_message=error_message
            ))
        
        # Generate error markdown
        error_markdown = f"""# 多模态内容解析结果

**处理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**状态**: ❌ 处理失败

**错误信息**: {error_message}

**文件总数**: {len(file_metadata_list)}

**成功处理**: 0

**处理失败**: {len(file_metadata_list)}

## 错误详情

批量处理过程中发生严重错误，无法完成文件处理。请检查文件格式和系统配置后重试。

"""
        
        return ParsedContent(
            total_files=len(file_metadata_list),
            successful_files=0,
            failed_files=len(file_metadata_list),
            markdown_output=error_markdown,
            file_results=error_results,
            processing_summary={
                'processing_start_time': datetime.now().isoformat(),
                'total_processing_time': 0.0,
                'error_message': error_message,
                'critical_failure': True
            }
        )