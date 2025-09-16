"""
File management utilities for PPT to Markdown conversion.

This module provides tools for managing files during the PPT to Markdown conversion process,
including file validation, directory operations, and batch processing capabilities.
"""

import os
import json
import re
import glob
import shutil
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
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
def validate_ppt_file(file_path: str) -> str:
    """
    Validate a PowerPoint file and extract basic metadata.

    This tool checks if a file exists, is accessible, and is a valid PowerPoint file (.ppt or .pptx).
    It also extracts basic metadata about the file.

    Args:
        file_path (str): Path to the PowerPoint file to validate

    Returns:
        str: JSON string containing the validation result with the following structure:
            {
                "status": "success" or "error",
                "is_valid": Whether the file is valid,
                "error_message": Error description (if error occurred),
                "metadata": {
                    "file_name": File name,
                    "file_size": File size in bytes,
                    "file_type": File type (.ppt or .pptx),
                    "last_modified": Last modification timestamp
                }
            }
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            return json.dumps({
                "status": "error",
                "is_valid": False,
                "error_message": f"File not found: {file_path}",
                "metadata": {}
            })
        
        # Check if file is accessible
        if not os.path.isfile(file_path):
            return json.dumps({
                "status": "error",
                "is_valid": False,
                "error_message": f"Not a file: {file_path}",
                "metadata": {}
            })
        
        # Check file extension
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext not in ['.ppt', '.pptx']:
            return json.dumps({
                "status": "error",
                "is_valid": False,
                "error_message": f"Invalid file format: {file_ext}. Only .ppt and .pptx files are supported.",
                "metadata": {
                    "file_name": file_name,
                    "file_size": os.path.getsize(file_path),
                    "file_type": file_ext,
                    "last_modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                }
            })
        
        # Try to open the file to check if it's readable
        try:
            with open(file_path, 'rb') as f:
                # Just read a small part to check if file is readable
                f.read(10)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "is_valid": False,
                "error_message": f"File is not readable: {str(e)}",
                "metadata": {
                    "file_name": file_name,
                    "file_size": os.path.getsize(file_path),
                    "file_type": file_ext,
                    "last_modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                }
            })
        
        # All checks passed
        return json.dumps({
            "status": "success",
            "is_valid": True,
            "metadata": {
                "file_name": file_name,
                "file_size": os.path.getsize(file_path),
                "file_type": file_ext,
                "last_modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
            }
        })
    
    except Exception as e:
        logger.error(f"Error validating PPT file: {str(e)}")
        return json.dumps({
            "status": "error",
            "is_valid": False,
            "error_message": f"Error validating PPT file: {str(e)}",
            "metadata": {}
        })


@tool
def find_ppt_files(
    directory_path: str,
    recursive: bool = False,
    include_ppt: bool = True,
    include_pptx: bool = True,
    max_files: int = 100,
) -> str:
    """
    Find PowerPoint files in a directory.

    This tool searches for PowerPoint files (.ppt and/or .pptx) in a specified directory,
    with options for recursive search and filtering.

    Args:
        directory_path (str): Path to the directory to search
        recursive (bool, optional): Whether to search recursively in subdirectories. Defaults to False.
        include_ppt (bool, optional): Whether to include .ppt files. Defaults to True.
        include_pptx (bool, optional): Whether to include .pptx files. Defaults to True.
        max_files (int, optional): Maximum number of files to return. Defaults to 100.

    Returns:
        str: JSON string containing the search results with the following structure:
            {
                "status": "success" or "error",
                "files": [
                    {
                        "file_path": Full path to the file,
                        "file_name": File name,
                        "file_size": File size in bytes,
                        "file_type": File type (.ppt or .pptx),
                        "last_modified": Last modification timestamp
                    }
                ],
                "error_message": Error description (if error occurred),
                "metadata": {
                    "total_files": Total number of files found,
                    "directory": Directory searched,
                    "recursive": Whether search was recursive
                }
            }
    """
    try:
        # Check if directory exists
        if not os.path.exists(directory_path):
            return json.dumps({
                "status": "error",
                "files": [],
                "error_message": f"Directory not found: {directory_path}",
                "metadata": {}
            })
        
        # Check if path is a directory
        if not os.path.isdir(directory_path):
            return json.dumps({
                "status": "error",
                "files": [],
                "error_message": f"Not a directory: {directory_path}",
                "metadata": {}
            })
        
        # Build file patterns
        patterns = []
        if include_ppt:
            patterns.append("*.ppt")
        if include_pptx:
            patterns.append("*.pptx")
        
        if not patterns:
            return json.dumps({
                "status": "error",
                "files": [],
                "error_message": "No file types selected (include_ppt and include_pptx are both False)",
                "metadata": {
                    "directory": directory_path,
                    "recursive": recursive
                }
            })
        
        # Find files
        files = []
        total_files = 0
        
        for pattern in patterns:
            if recursive:
                search_pattern = os.path.join(directory_path, "**", pattern)
                matching_files = glob.glob(search_pattern, recursive=True)
            else:
                search_pattern = os.path.join(directory_path, pattern)
                matching_files = glob.glob(search_pattern)
            
            for file_path in matching_files:
                total_files += 1
                
                if len(files) < max_files:
                    file_name = os.path.basename(file_path)
                    file_ext = os.path.splitext(file_path)[1].lower()
                    
                    files.append({
                        "file_path": file_path,
                        "file_name": file_name,
                        "file_size": os.path.getsize(file_path),
                        "file_type": file_ext,
                        "last_modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                    })
        
        # Return results
        return json.dumps({
            "status": "success",
            "files": files,
            "metadata": {
                "total_files": total_files,
                "directory": directory_path,
                "recursive": recursive,
                "max_reached": total_files > max_files
            }
        })
    
    except Exception as e:
        logger.error(f"Error finding PPT files: {str(e)}")
        return json.dumps({
            "status": "error",
            "files": [],
            "error_message": f"Error finding PPT files: {str(e)}",
            "metadata": {
                "directory": directory_path,
                "recursive": recursive
            }
        })


@tool
def create_output_directory(
    base_directory: str,
    output_name: Optional[str] = None,
    clear_existing: bool = False,
) -> str:
    """
    Create an output directory for Markdown files.

    This tool creates a directory to store Markdown files generated from PowerPoint presentations.
    It can create a new directory or clear an existing one.

    Args:
        base_directory (str): Base directory where the output directory will be created
        output_name (str, optional): Name of the output directory. If None, a default name will be used. Defaults to None.
        clear_existing (bool, optional): Whether to clear the directory if it already exists. Defaults to False.

    Returns:
        str: JSON string containing the result with the following structure:
            {
                "status": "success" or "error",
                "output_directory": Path to the created output directory,
                "error_message": Error description (if error occurred),
                "metadata": {
                    "created_new": Whether a new directory was created,
                    "cleared": Whether an existing directory was cleared
                }
            }
    """
    try:
        # Check if base directory exists
        if not os.path.exists(base_directory):
            return json.dumps({
                "status": "error",
                "error_message": f"Base directory not found: {base_directory}",
                "metadata": {}
            })
        
        # Check if base path is a directory
        if not os.path.isdir(base_directory):
            return json.dumps({
                "status": "error",
                "error_message": f"Not a directory: {base_directory}",
                "metadata": {}
            })
        
        # Set output directory name
        if output_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"markdown_output_{timestamp}"
        
        # Create full path
        output_directory = os.path.join(base_directory, output_name)
        created_new = False
        cleared = False
        
        # Check if directory already exists
        if os.path.exists(output_directory):
            if clear_existing:
                # Clear directory
                try:
                    for item in os.listdir(output_directory):
                        item_path = os.path.join(output_directory, item)
                        if os.path.isfile(item_path):
                            os.unlink(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    cleared = True
                except Exception as e:
                    return json.dumps({
                        "status": "error",
                        "error_message": f"Failed to clear directory: {str(e)}",
                        "metadata": {
                            "output_directory": output_directory
                        }
                    })
            else:
                # Directory exists and not clearing
                return json.dumps({
                    "status": "success",
                    "output_directory": output_directory,
                    "metadata": {
                        "created_new": False,
                        "cleared": False,
                        "already_exists": True
                    }
                })
        else:
            # Create new directory
            try:
                os.makedirs(output_directory)
                created_new = True
            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "error_message": f"Failed to create directory: {str(e)}",
                    "metadata": {}
                })
        
        # Return success
        return json.dumps({
            "status": "success",
            "output_directory": output_directory,
            "metadata": {
                "created_new": created_new,
                "cleared": cleared
            }
        })
    
    except Exception as e:
        logger.error(f"Error creating output directory: {str(e)}")
        return json.dumps({
            "status": "error",
            "error_message": f"Error creating output directory: {str(e)}",
            "metadata": {}
        })


@tool
def save_markdown_file(
    content: str,
    output_directory: str,
    file_name: Optional[str] = None,
    source_file_path: Optional[str] = None,
    overwrite: bool = False,
) -> str:
    """
    Save Markdown content to a file.

    This tool saves Markdown content generated from a PowerPoint presentation to a file,
    with options for naming and overwrite control.

    Args:
        content (str): Markdown content to save
        output_directory (str): Directory where the file will be saved
        file_name (str, optional): Name of the output file. If None, derived from source_file_path or a default name. Defaults to None.
        source_file_path (str, optional): Path to the source PowerPoint file. Used to derive the output file name if file_name is None. Defaults to None.
        overwrite (bool, optional): Whether to overwrite the file if it already exists. Defaults to False.

    Returns:
        str: JSON string containing the result with the following structure:
            {
                "status": "success" or "error",
                "file_path": Path to the saved file,
                "error_message": Error description (if error occurred),
                "metadata": {
                    "file_name": Name of the saved file,
                    "file_size": Size of the saved file in bytes,
                    "overwritten": Whether an existing file was overwritten
                }
            }
    """
    try:
        # Check if output directory exists
        if not os.path.exists(output_directory):
            return json.dumps({
                "status": "error",
                "error_message": f"Output directory not found: {output_directory}",
                "metadata": {}
            })
        
        # Check if output directory is a directory
        if not os.path.isdir(output_directory):
            return json.dumps({
                "status": "error",
                "error_message": f"Not a directory: {output_directory}",
                "metadata": {}
            })
        
        # Determine file name
        if file_name is None:
            if source_file_path:
                # Derive from source file
                base_name = os.path.splitext(os.path.basename(source_file_path))[0]
                file_name = f"{base_name}.md"
            else:
                # Use default name with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_name = f"markdown_{timestamp}.md"
        
        # Ensure file has .md extension
        if not file_name.lower().endswith('.md'):
            file_name += '.md'
        
        # Create full path
        file_path = os.path.join(output_directory, file_name)
        
        # Check if file already exists
        file_exists = os.path.exists(file_path)
        if file_exists and not overwrite:
            return json.dumps({
                "status": "error",
                "error_message": f"File already exists: {file_path}. Use overwrite=True to overwrite.",
                "metadata": {
                    "file_path": file_path,
                    "file_exists": True
                }
            })
        
        # Save file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Return success
            return json.dumps({
                "status": "success",
                "file_path": file_path,
                "metadata": {
                    "file_name": file_name,
                    "file_size": file_size,
                    "overwritten": file_exists
                }
            })
        
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error_message": f"Failed to save file: {str(e)}",
                "metadata": {
                    "file_path": file_path
                }
            })
    
    except Exception as e:
        logger.error(f"Error saving Markdown file: {str(e)}")
        return json.dumps({
            "status": "error",
            "error_message": f"Error saving Markdown file: {str(e)}",
            "metadata": {}
        })