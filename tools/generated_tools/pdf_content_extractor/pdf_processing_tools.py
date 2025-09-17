"""
PDF Processing Tools

This module provides tools for processing PDF files, including:
1. Converting PDF pages to images
2. Managing processing state for resume capability
3. Merging text content from multiple pages

Dependencies:
- PyMuPDF (fitz)
- os, json, pathlib
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
import fitz  # PyMuPDF
from strands import tool


@tool
def pdf_to_images(
    pdf_path: str,
    output_dir: str = ".cache",
    dpi: int = 300,
    start_page: int = 0,
    end_page: Optional[int] = None,
    image_format: str = "png",
    overwrite: bool = False
) -> str:
    """
    Convert PDF pages to images and save them in the specified directory.
    
    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str): Directory to save images (default: .cache)
        dpi (int): Image resolution in DPI (default: 300)
        start_page (int): First page to convert (0-based index, default: 0)
        end_page (Optional[int]): Last page to convert (None means all pages)
        image_format (str): Image format to save (png, jpg, jpeg)
        overwrite (bool): Whether to overwrite existing images
        
    Returns:
        str: JSON string with conversion results including success status,
             number of pages converted, and paths to the generated images
    """
    result = {
        "success": False,
        "message": "",
        "total_pages": 0,
        "converted_pages": 0,
        "image_paths": [],
        "failed_pages": []
    }
    
    try:
        # Validate input
        if not os.path.exists(pdf_path):
            result["message"] = f"PDF file not found: {pdf_path}"
            return json.dumps(result)
            
        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Open the PDF file
        pdf_document = fitz.open(pdf_path)
        total_pages = len(pdf_document)
        result["total_pages"] = total_pages
        
        # Validate page range
        if end_page is None:
            end_page = total_pages - 1
        elif end_page >= total_pages:
            end_page = total_pages - 1
            
        if start_page < 0:
            start_page = 0
            
        if start_page > end_page:
            result["message"] = f"Invalid page range: start_page ({start_page}) > end_page ({end_page})"
            return json.dumps(result)
        
        # Normalize image format
        if image_format.lower() not in ["png", "jpg", "jpeg"]:
            image_format = "png"
        if image_format.lower() == "jpg":
            image_format = "jpeg"
        
        # Convert pages to images
        image_paths = []
        failed_pages = []
        converted_count = 0
        
        for page_num in range(start_page, end_page + 1):
            try:
                # Generate output filename
                output_filename = f"page_{page_num}.{image_format}"
                output_file_path = output_path / output_filename
                
                # Skip if file exists and overwrite is False
                if output_file_path.exists() and not overwrite:
                    image_paths.append(str(output_file_path))
                    converted_count += 1
                    continue
                
                # Get the page
                page = pdf_document[page_num]
                
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
                
                # Save image
                pix.save(str(output_file_path))
                
                image_paths.append(str(output_file_path))
                converted_count += 1
                
            except Exception as e:
                failed_pages.append({
                    "page_number": page_num,
                    "error": str(e)
                })
        
        # Update result
        result["success"] = True
        result["message"] = f"Successfully converted {converted_count} pages"
        result["converted_pages"] = converted_count
        result["image_paths"] = image_paths
        result["failed_pages"] = failed_pages
        
    except Exception as e:
        result["success"] = False
        result["message"] = f"Error converting PDF to images: {str(e)}"
    
    finally:
        # Close the PDF document if it was opened
        if 'pdf_document' in locals():
            pdf_document.close()
    
    return json.dumps(result)


@tool
def manage_processing_state(
    action: str,
    pdf_path: str,
    state_dir: str = ".cache",
    state_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Manage the processing state for PDF extraction to support resume capability.
    
    Args:
        action (str): Action to perform: 'create', 'read', 'update', 'delete'
        pdf_path (str): Path to the PDF file being processed
        state_dir (str): Directory to store state files (default: .cache)
        state_data (Optional[Dict]): State data to write (required for 'create' and 'update')
        
    Returns:
        str: JSON string with operation results
    """
    result = {
        "success": False,
        "message": "",
        "state_file": "",
        "state_data": None
    }
    
    try:
        # Create state directory if it doesn't exist
        state_path = Path(state_dir)
        state_path.mkdir(parents=True, exist_ok=True)
        
        # Generate a safe filename for the state file
        pdf_filename = os.path.basename(pdf_path)
        state_filename = f"{pdf_filename.replace('.', '_')}_state.json"
        state_file_path = state_path / state_filename
        
        result["state_file"] = str(state_file_path)
        
        # Perform the requested action
        if action.lower() == "create":
            if state_data is None:
                result["message"] = "State data is required for 'create' action"
                return json.dumps(result)
                
            # Write state data to file
            with open(state_file_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
                
            result["success"] = True
            result["message"] = f"Created state file: {state_file_path}"
            result["state_data"] = state_data
            
        elif action.lower() == "read":
            # Check if state file exists
            if not state_file_path.exists():
                result["message"] = f"State file not found: {state_file_path}"
                return json.dumps(result)
                
            # Read state data from file
            with open(state_file_path, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
                
            result["success"] = True
            result["message"] = f"Read state file: {state_file_path}"
            result["state_data"] = state_data
            
        elif action.lower() == "update":
            if state_data is None:
                result["message"] = "State data is required for 'update' action"
                return json.dumps(result)
                
            # Check if state file exists
            if not state_file_path.exists():
                # Create new state file
                with open(state_file_path, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f, ensure_ascii=False, indent=2)
                    
                result["success"] = True
                result["message"] = f"Created state file: {state_file_path}"
                result["state_data"] = state_data
            else:
                # Update existing state file
                with open(state_file_path, 'r', encoding='utf-8') as f:
                    existing_state = json.load(f)
                    
                # Merge existing state with new state data
                if isinstance(existing_state, dict) and isinstance(state_data, dict):
                    existing_state.update(state_data)
                else:
                    existing_state = state_data
                    
                # Write updated state back to file
                with open(state_file_path, 'w', encoding='utf-8') as f:
                    json.dump(existing_state, f, ensure_ascii=False, indent=2)
                    
                result["success"] = True
                result["message"] = f"Updated state file: {state_file_path}"
                result["state_data"] = existing_state
                
        elif action.lower() == "delete":
            # Check if state file exists
            if not state_file_path.exists():
                result["message"] = f"State file not found: {state_file_path}"
                return json.dumps(result)
                
            # Delete state file
            os.remove(state_file_path)
            
            result["success"] = True
            result["message"] = f"Deleted state file: {state_file_path}"
            
        else:
            result["message"] = f"Invalid action: {action}. Must be one of: create, read, update, delete"
            
    except Exception as e:
        result["success"] = False
        result["message"] = f"Error managing processing state: {str(e)}"
    
    return json.dumps(result)


@tool
def merge_text_content(
    input_files: List[str],
    output_file: str,
    include_page_numbers: bool = True,
    handle_missing_files: bool = True,
    cleanup_temp_files: bool = False
) -> str:
    """
    Merge text content from multiple files into a single output file.
    
    Args:
        input_files (List[str]): List of text file paths to merge
        output_file (str): Path to the output merged file
        include_page_numbers (bool): Whether to include page numbers in the output
        handle_missing_files (bool): Whether to continue if some files are missing
        cleanup_temp_files (bool): Whether to delete input files after merging
        
    Returns:
        str: JSON string with merge results
    """
    result = {
        "success": False,
        "message": "",
        "output_file": output_file,
        "processed_files": 0,
        "missing_files": [],
        "total_content_length": 0
    }
    
    try:
        # Validate input
        if not input_files:
            result["message"] = "No input files provided"
            return json.dumps(result)
            
        # Create output directory if it doesn't exist
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Process each input file
        processed_files = 0
        missing_files = []
        total_content_length = 0
        
        with open(output_file, 'w', encoding='utf-8') as out_f:
            for i, file_path in enumerate(input_files):
                try:
                    if not os.path.exists(file_path):
                        if handle_missing_files:
                            missing_files.append(file_path)
                            # Write placeholder for missing file
                            if include_page_numbers:
                                out_f.write(f"\n\n--- Page {i+1} (File not found: {file_path}) ---\n\n")
                            continue
                        else:
                            result["message"] = f"Input file not found: {file_path}"
                            return json.dumps(result)
                    
                    # Read content from input file
                    with open(file_path, 'r', encoding='utf-8') as in_f:
                        content = in_f.read()
                    
                    # Write page header if requested
                    if include_page_numbers:
                        out_f.write(f"\n\n--- Page {i+1} ---\n\n")
                    
                    # Write content
                    out_f.write(content)
                    total_content_length += len(content)
                    processed_files += 1
                    
                    # Delete input file if cleanup is requested
                    if cleanup_temp_files:
                        os.remove(file_path)
                        
                except Exception as e:
                    if handle_missing_files:
                        missing_files.append(file_path)
                        # Write error information
                        if include_page_numbers:
                            out_f.write(f"\n\n--- Page {i+1} (Error: {str(e)}) ---\n\n")
                    else:
                        result["message"] = f"Error processing file {file_path}: {str(e)}"
                        return json.dumps(result)
        
        # Update result
        result["success"] = True
        result["message"] = f"Successfully merged {processed_files} files into {output_file}"
        result["processed_files"] = processed_files
        result["missing_files"] = missing_files
        result["total_content_length"] = total_content_length
        
    except Exception as e:
        result["success"] = False
        result["message"] = f"Error merging text content: {str(e)}"
    
    return json.dumps(result)


@tool
def initialize_pdf_extraction(
    pdf_path: str,
    output_dir: str = ".cache",
    output_file: str = None,
    force_restart: bool = False
) -> str:
    """
    Initialize the PDF extraction process, setting up state management.
    
    Args:
        pdf_path (str): Path to the PDF file to process
        output_dir (str): Directory to store temporary files and state
        output_file (str): Path for the final output text file (if None, auto-generated)
        force_restart (bool): Whether to force restart if a previous state exists
        
    Returns:
        str: JSON string with initialization results
    """
    result = {
        "success": False,
        "message": "",
        "pdf_info": None,
        "state_file": "",
        "output_file": "",
        "is_resumed": False
    }
    
    try:
        # Validate input
        if not os.path.exists(pdf_path):
            result["message"] = f"PDF file not found: {pdf_path}"
            return json.dumps(result)
            
        # Create output directory if it doesn't exist
        cache_dir = Path(output_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename if not provided
        if output_file is None:
            pdf_filename = os.path.basename(pdf_path)
            base_name = os.path.splitext(pdf_filename)[0]
            output_file = str(cache_dir / f"{base_name}.md")
        
        result["output_file"] = output_file
        
        # Check for existing state
        pdf_filename = os.path.basename(pdf_path)
        state_filename = f"{pdf_filename.replace('.', '_')}_state.json"
        state_file_path = cache_dir / state_filename
        
        result["state_file"] = str(state_file_path)
        
        # If force_restart, delete existing state file
        if force_restart and state_file_path.exists():
            os.remove(state_file_path)
        
        # Check if we're resuming from a previous state
        if state_file_path.exists():
            # Read existing state
            with open(state_file_path, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
                
            result["is_resumed"] = True
            result["message"] = "Resuming from previous state"
            result["pdf_info"] = state_data.get("pdf_info", {})
            result["success"] = True
            
        else:
            # Get PDF information
            try:
                pdf_document = fitz.open(pdf_path)
                pdf_info = {
                    "path": pdf_path,
                    "filename": os.path.basename(pdf_path),
                    "total_pages": len(pdf_document),
                    "metadata": {
                        "title": pdf_document.metadata.get("title", ""),
                        "author": pdf_document.metadata.get("author", ""),
                        "subject": pdf_document.metadata.get("subject", ""),
                        "creator": pdf_document.metadata.get("creator", ""),
                        "producer": pdf_document.metadata.get("producer", ""),
                        "creation_date": pdf_document.metadata.get("creationDate", ""),
                        "modification_date": pdf_document.metadata.get("modDate", "")
                    }
                }
                pdf_document.close()
                
                # Create initial state
                state_data = {
                    "pdf_info": pdf_info,
                    "processing_status": {
                        "total_pages": pdf_info["total_pages"],
                        "processed_pages": [],
                        "failed_pages": [],
                        "completed": False
                    },
                    "output_file": output_file,
                    "last_updated": None
                }
                
                # Save initial state
                with open(state_file_path, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f, ensure_ascii=False, indent=2)
                
                result["pdf_info"] = pdf_info
                result["success"] = True
                result["message"] = "Successfully initialized PDF extraction"
                
            except Exception as e:
                result["success"] = False
                result["message"] = f"Error initializing PDF extraction: {str(e)}"
        
    except Exception as e:
        result["success"] = False
        result["message"] = f"Error in initialization: {str(e)}"
    
    return json.dumps(result)


@tool
def cleanup_extraction_files(
    pdf_path: str,
    cache_dir: str = ".cache",
    keep_state_file: bool = True,
    keep_output_file: bool = True
) -> str:
    """
    Clean up temporary files created during PDF extraction.
    
    Args:
        pdf_path (str): Path to the PDF file that was processed
        cache_dir (str): Directory where temporary files are stored
        keep_state_file (bool): Whether to keep the state file
        keep_output_file (bool): Whether to keep the output text file
        
    Returns:
        str: JSON string with cleanup results
    """
    result = {
        "success": False,
        "message": "",
        "deleted_files": [],
        "kept_files": []
    }
    
    try:
        # Validate input
        cache_path = Path(cache_dir)
        if not cache_path.exists():
            result["message"] = f"Cache directory not found: {cache_dir}"
            return json.dumps(result)
            
        # Get PDF filename
        pdf_filename = os.path.basename(pdf_path)
        base_name = os.path.splitext(pdf_filename)[0]
        
        # Generate state filename
        state_filename = f"{pdf_filename.replace('.', '_')}_state.json"
        state_file_path = cache_path / state_filename
        
        # Get list of files in cache directory
        deleted_files = []
        kept_files = []
        
        # Process each file in the cache directory
        for file_path in cache_path.glob("*"):
            file_name = file_path.name
            
            # Skip directories
            if file_path.is_dir():
                continue
                
            # Check if it's a page image file
            is_page_image = file_name.startswith("page_") and any(
                file_name.endswith(f".{ext}") for ext in ["png", "jpg", "jpeg"]
            )
            
            # Check if it's a state file
            is_state_file = file_name == state_filename
            
            # Check if it's an output file
            is_output_file = file_name == f"{base_name}.md"
            
            # Determine if file should be deleted
            should_delete = False
            
            if is_page_image:
                # Always delete page images
                should_delete = True
            elif is_state_file:
                # Delete state file if not keeping it
                should_delete = not keep_state_file
            elif is_output_file:
                # Delete output file if not keeping it
                should_delete = not keep_output_file
            else:
                # Skip files not related to this PDF
                continue
            
            # Delete file if needed
            if should_delete:
                try:
                    os.remove(file_path)
                    deleted_files.append(str(file_path))
                except Exception as e:
                    result["message"] += f"Failed to delete {file_path}: {str(e)}. "
            else:
                kept_files.append(str(file_path))
        
        # Update result
        result["success"] = True
        result["message"] = f"Successfully cleaned up {len(deleted_files)} files"
        result["deleted_files"] = deleted_files
        result["kept_files"] = kept_files
        
    except Exception as e:
        result["success"] = False
        result["message"] = f"Error cleaning up extraction files: {str(e)}"
    
    return json.dumps(result)