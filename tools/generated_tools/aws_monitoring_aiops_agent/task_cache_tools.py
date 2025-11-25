"""
Task management and caching tools for AWS monitoring and AIOps.
"""

from typing import Dict, List, Any, Optional, Union, Tuple
import json
import os
import uuid
import time
import hashlib
from datetime import datetime, timedelta
import threading
import shutil
from pathlib import Path
from strands import tool

# Define cache directory
CACHE_DIR = os.path.join(".cache", "aws_monitoring_aiops_agent")

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

# Cache lock for thread safety
cache_lock = threading.Lock()

@tool
def task_manager(
    operation: str,
    task_data: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None,
    max_tasks: int = 100,
) -> str:
    """
    Manage monitoring tasks with unique IDs, state tracking, and progress monitoring.
    
    This tool provides task management capabilities for the AWS monitoring AIOps agent,
    including task creation, status updates, retrieval, and listing.
    
    Args:
        operation: Operation to perform (create, update, get, list, delete)
        task_data: Task data for create/update operations (required for create/update)
        task_id: Task ID for get/update/delete operations (required for get/update/delete)
        max_tasks: Maximum number of tasks to return when listing (default: 100)
    
    Returns:
        JSON string containing operation results or error information
        
    Operations:
        - create: Create a new task with a unique ID
        - update: Update an existing task's status or data
        - get: Retrieve a specific task by ID
        - list: List all tasks with optional filtering
        - delete: Delete a specific task by ID
    """
    try:
        # Define tasks directory
        tasks_dir = os.path.join(CACHE_DIR, "tasks")
        os.makedirs(tasks_dir, exist_ok=True)
        
        # Handle different operations
        if operation == "create":
            # Validate task_data
            if not task_data:
                return json.dumps({
                    "error": "task_data is required for create operation"
                })
            
            # Generate a unique task ID if not provided
            if not task_id:
                task_id = str(uuid.uuid4())
            
            # Add metadata to task
            task = {
                "task_id": task_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "status": task_data.get("status", "pending"),
                "data": task_data
            }
            
            # Save task to file
            task_file = os.path.join(tasks_dir, f"{task_id}.json")
            
            with cache_lock:
                with open(task_file, "w") as f:
                    json.dump(task, f, indent=2)
            
            return json.dumps({
                "operation": "create",
                "task_id": task_id,
                "status": "success",
                "message": "Task created successfully"
            })
            
        elif operation == "update":
            # Validate required parameters
            if not task_id:
                return json.dumps({
                    "error": "task_id is required for update operation"
                })
            
            if not task_data:
                return json.dumps({
                    "error": "task_data is required for update operation"
                })
            
            # Check if task exists
            task_file = os.path.join(tasks_dir, f"{task_id}.json")
            if not os.path.exists(task_file):
                return json.dumps({
                    "error": f"Task with ID {task_id} not found"
                })
            
            # Read existing task
            with cache_lock:
                with open(task_file, "r") as f:
                    task = json.load(f)
            
            # Update task data
            task["updated_at"] = datetime.utcnow().isoformat()
            task["status"] = task_data.get("status", task["status"])
            
            # Update or merge task data
            if "data" in task_data:
                if isinstance(task["data"], dict) and isinstance(task_data["data"], dict):
                    # Merge dictionaries for nested update
                    task["data"].update(task_data["data"])
                else:
                    # Replace data if not both dictionaries
                    task["data"] = task_data["data"]
            
            # Save updated task
            with cache_lock:
                with open(task_file, "w") as f:
                    json.dump(task, f, indent=2)
            
            return json.dumps({
                "operation": "update",
                "task_id": task_id,
                "status": "success",
                "message": "Task updated successfully"
            })
            
        elif operation == "get":
            # Validate required parameters
            if not task_id:
                return json.dumps({
                    "error": "task_id is required for get operation"
                })
            
            # Check if task exists
            task_file = os.path.join(tasks_dir, f"{task_id}.json")
            if not os.path.exists(task_file):
                return json.dumps({
                    "error": f"Task with ID {task_id} not found"
                })
            
            # Read task
            with cache_lock:
                with open(task_file, "r") as f:
                    task = json.load(f)
            
            return json.dumps({
                "operation": "get",
                "task_id": task_id,
                "status": "success",
                "task": task
            })
            
        elif operation == "list":
            # Get all task files
            task_files = [f for f in os.listdir(tasks_dir) if f.endswith(".json")]
            
            # Sort by modification time (newest first)
            task_files.sort(key=lambda x: os.path.getmtime(os.path.join(tasks_dir, x)), reverse=True)
            
            # Limit to max_tasks
            task_files = task_files[:max_tasks]
            
            # Read all tasks
            tasks = []
            with cache_lock:
                for file in task_files:
                    try:
                        with open(os.path.join(tasks_dir, file), "r") as f:
                            task = json.load(f)
                            tasks.append(task)
                    except Exception as e:
                        # Skip corrupted files
                        continue
            
            return json.dumps({
                "operation": "list",
                "status": "success",
                "count": len(tasks),
                "tasks": tasks
            })
            
        elif operation == "delete":
            # Validate required parameters
            if not task_id:
                return json.dumps({
                    "error": "task_id is required for delete operation"
                })
            
            # Check if task exists
            task_file = os.path.join(tasks_dir, f"{task_id}.json")
            if not os.path.exists(task_file):
                return json.dumps({
                    "error": f"Task with ID {task_id} not found"
                })
            
            # Delete task file
            with cache_lock:
                os.remove(task_file)
            
            return json.dumps({
                "operation": "delete",
                "task_id": task_id,
                "status": "success",
                "message": "Task deleted successfully"
            })
            
        else:
            return json.dumps({
                "error": f"Unsupported operation: {operation}",
                "supported_operations": ["create", "update", "get", "list", "delete"]
            })
            
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "operation": operation
        })


@tool
def cache_manager(
    operation: str,
    cache_key: Optional[str] = None,
    data: Optional[Any] = None,
    cache_type: str = "monitoring_data",
    ttl_days: int = 30,
    max_size_mb: int = 100,
) -> str:
    """
    Cache monitoring data and analysis results for improved performance and reduced API calls.
    
    This tool provides caching capabilities for the AWS monitoring AIOps agent,
    including storing and retrieving monitoring data, analysis results, and other information.
    
    Args:
        operation: Operation to perform (set, get, delete, list, clear, stats)
        cache_key: Key for the cached data (required for set/get/delete)
        data: Data to cache (required for set)
        cache_type: Type of cache (monitoring_data, analysis_results, scripts, reports)
        ttl_days: Time-to-live in days for cached data (default: 30)
        max_size_mb: Maximum cache size in MB (default: 100)
    
    Returns:
        JSON string containing operation results or error information
        
    Operations:
        - set: Store data in cache
        - get: Retrieve data from cache
        - delete: Remove data from cache
        - list: List all cached items of a specific type
        - clear: Clear all cached items of a specific type
        - stats: Get cache statistics
    """
    try:
        # Define cache type directory
        cache_type_dir = os.path.join(CACHE_DIR, cache_type)
        os.makedirs(cache_type_dir, exist_ok=True)
        
        # Handle different operations
        if operation == "set":
            # Validate required parameters
            if not cache_key:
                return json.dumps({
                    "error": "cache_key is required for set operation"
                })
            
            if data is None:
                return json.dumps({
                    "error": "data is required for set operation"
                })
            
            # Create a safe filename from the cache key
            safe_key = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = os.path.join(cache_type_dir, f"{safe_key}.json")
            
            # Create cache entry with metadata
            cache_entry = {
                "key": cache_key,
                "type": cache_type,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(days=ttl_days)).isoformat(),
                "data": data
            }
            
            # Check cache size before writing
            if _get_directory_size_mb(cache_type_dir) > max_size_mb:
                # Clean up oldest files to make space
                _clean_cache(cache_type_dir, max_size_mb * 0.8)  # Clean to 80% of max
            
            # Save data to cache
            with cache_lock:
                with open(cache_file, "w") as f:
                    json.dump(cache_entry, f)
            
            return json.dumps({
                "operation": "set",
                "cache_key": cache_key,
                "status": "success",
                "expires_at": cache_entry["expires_at"]
            })
            
        elif operation == "get":
            # Validate required parameters
            if not cache_key:
                return json.dumps({
                    "error": "cache_key is required for get operation"
                })
            
            # Create a safe filename from the cache key
            safe_key = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = os.path.join(cache_type_dir, f"{safe_key}.json")
            
            # Check if cache file exists
            if not os.path.exists(cache_file):
                return json.dumps({
                    "operation": "get",
                    "cache_key": cache_key,
                    "status": "miss",
                    "message": "Cache miss"
                })
            
            # Read cache entry
            with cache_lock:
                with open(cache_file, "r") as f:
                    cache_entry = json.load(f)
            
            # Check if cache entry has expired
            if datetime.fromisoformat(cache_entry["expires_at"]) < datetime.utcnow():
                # Delete expired cache entry
                with cache_lock:
                    os.remove(cache_file)
                
                return json.dumps({
                    "operation": "get",
                    "cache_key": cache_key,
                    "status": "expired",
                    "message": "Cache entry expired"
                })
            
            return json.dumps({
                "operation": "get",
                "cache_key": cache_key,
                "status": "hit",
                "data": cache_entry["data"],
                "metadata": {
                    "created_at": cache_entry["created_at"],
                    "expires_at": cache_entry["expires_at"],
                    "type": cache_entry["type"]
                }
            })
            
        elif operation == "delete":
            # Validate required parameters
            if not cache_key:
                return json.dumps({
                    "error": "cache_key is required for delete operation"
                })
            
            # Create a safe filename from the cache key
            safe_key = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = os.path.join(cache_type_dir, f"{safe_key}.json")
            
            # Check if cache file exists
            if not os.path.exists(cache_file):
                return json.dumps({
                    "operation": "delete",
                    "cache_key": cache_key,
                    "status": "not_found",
                    "message": "Cache entry not found"
                })
            
            # Delete cache file
            with cache_lock:
                os.remove(cache_file)
            
            return json.dumps({
                "operation": "delete",
                "cache_key": cache_key,
                "status": "success",
                "message": "Cache entry deleted"
            })
            
        elif operation == "list":
            # Get all cache files
            cache_files = [f for f in os.listdir(cache_type_dir) if f.endswith(".json")]
            
            # Read cache entries
            cache_entries = []
            with cache_lock:
                for file in cache_files:
                    try:
                        with open(os.path.join(cache_type_dir, file), "r") as f:
                            entry = json.load(f)
                            # Include only metadata, not the full data
                            cache_entries.append({
                                "key": entry["key"],
                                "type": entry["type"],
                                "created_at": entry["created_at"],
                                "expires_at": entry["expires_at"]
                            })
                    except Exception:
                        # Skip corrupted files
                        continue
            
            return json.dumps({
                "operation": "list",
                "cache_type": cache_type,
                "status": "success",
                "count": len(cache_entries),
                "entries": cache_entries
            })
            
        elif operation == "clear":
            # Count files before clearing
            cache_files = [f for f in os.listdir(cache_type_dir) if f.endswith(".json")]
            count = len(cache_files)
            
            # Clear all files in the cache directory
            with cache_lock:
                for file in cache_files:
                    try:
                        os.remove(os.path.join(cache_type_dir, file))
                    except Exception:
                        # Skip files that can't be deleted
                        continue
            
            return json.dumps({
                "operation": "clear",
                "cache_type": cache_type,
                "status": "success",
                "cleared_count": count,
                "message": f"Cleared {count} cache entries"
            })
            
        elif operation == "stats":
            # Get cache statistics
            cache_files = [f for f in os.listdir(cache_type_dir) if f.endswith(".json")]
            
            # Calculate total size
            total_size_bytes = sum(os.path.getsize(os.path.join(cache_type_dir, f)) for f in cache_files)
            total_size_mb = total_size_bytes / (1024 * 1024)
            
            # Count expired entries
            expired_count = 0
            with cache_lock:
                for file in cache_files:
                    try:
                        with open(os.path.join(cache_type_dir, file), "r") as f:
                            entry = json.load(f)
                            if datetime.fromisoformat(entry["expires_at"]) < datetime.utcnow():
                                expired_count += 1
                    except Exception:
                        # Skip corrupted files
                        continue
            
            # Get cache types and their sizes
            cache_types = {}
            for cache_type_subdir in os.listdir(CACHE_DIR):
                subdir_path = os.path.join(CACHE_DIR, cache_type_subdir)
                if os.path.isdir(subdir_path):
                    cache_types[cache_type_subdir] = _get_directory_size_mb(subdir_path)
            
            return json.dumps({
                "operation": "stats",
                "status": "success",
                "current_cache_type": cache_type,
                "total_entries": len(cache_files),
                "expired_entries": expired_count,
                "size_mb": round(total_size_mb, 2),
                "cache_types": cache_types,
                "total_cache_size_mb": round(sum(cache_types.values()), 2)
            })
            
        else:
            return json.dumps({
                "error": f"Unsupported operation: {operation}",
                "supported_operations": ["set", "get", "delete", "list", "clear", "stats"]
            })
            
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "operation": operation
        })


# Helper functions for cache management

def _get_directory_size_mb(directory):
    """Calculate the total size of a directory in megabytes."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            total_size += os.path.getsize(file_path)
    
    # Convert bytes to megabytes
    return total_size / (1024 * 1024)


def _clean_cache(directory, target_size_mb):
    """Clean cache by removing oldest files until target size is reached."""
    # Get all files with their modification times
    files = []
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            files.append((file_path, os.path.getmtime(file_path)))
    
    # Sort files by modification time (oldest first)
    files.sort(key=lambda x: x[1])
    
    # Remove files until target size is reached
    current_size_mb = _get_directory_size_mb(directory)
    for file_path, _ in files:
        if current_size_mb <= target_size_mb:
            break
            
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        try:
            os.remove(file_path)
            current_size_mb -= file_size_mb
        except Exception:
            # Skip files that can't be deleted
            continue