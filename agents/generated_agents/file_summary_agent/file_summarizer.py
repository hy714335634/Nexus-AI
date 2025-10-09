#!/usr/bin/env python3
"""
File Summarizer Agent

A professional file summarization expert that can read various file formats,
extract content, and generate high-quality summaries.

Features:
- Multi-format file support (PDF, DOCX, TXT, MD, etc.)
- Intelligent summary generation
- Key information extraction
- Summary length control (short/standard/detailed)
- Multiple output formats (JSON, Markdown, plain text)
- Keyword extraction
- Batch file processing
- Robust error handling
"""

import os
import sys
import json
from typing import Union, List, Dict, Any, Optional, Literal
from pathlib import Path

from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# Configure telemetry
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

class FileSummarizerAgent:
    """
    File Summarizer Agent class that provides an interface to the underlying agent.
    
    This class provides convenient methods to interact with the file summarizer agent,
    including summary generation with various options and batch processing capabilities.
    """
    
    def __init__(self, env: str = "production", version: str = "latest", model_id: str = "default"):
        """
        Initialize the File Summarizer Agent.
        
        Args:
            env: Environment setting ('production', 'development', or 'testing')
            version: Agent version to use
            model_id: Model ID to use for the agent
        """
        # Set environment variables
        os.environ["BYPASS_TOOL_CONSENT"] = "true"
        
        # Create agent parameters
        self.agent_params = {
            "env": env,
            "version": version,
            "model_id": model_id
        }
        
        # Create the agent
        self.agent = create_agent_from_prompt_template(
            agent_name="generated_agents_prompts/file_summary_agent/file_summarizer", 
            **self.agent_params
        )
    
    def summarize_file(
        self,
        file_path: str,
        summary_length: Literal["short", "standard", "detailed"] = "standard",
        output_format: Literal["json", "markdown", "plain"] = "json",
        extract_keywords: bool = False
    ) -> str:
        """
        Summarize a single file.
        
        Args:
            file_path: Path to the file to summarize
            summary_length: Length of summary ('short', 'standard', or 'detailed')
            output_format: Format for the output ('json', 'markdown', or 'plain')
            extract_keywords: Whether to extract keywords from the content
            
        Returns:
            Structured summary of the file content in the specified format
            
        Raises:
            ValueError: If file format is unsupported or file cannot be read
            RuntimeError: If summary generation fails
        """
        # Validate file exists
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
        
        # Prepare the input prompt
        prompt = self._build_summarize_prompt(
            file_path=file_path,
            summary_length=summary_length,
            output_format=output_format,
            extract_keywords=extract_keywords
        )
        
        # Call the agent
        return self.agent(prompt)
    
    def summarize_files(
        self,
        file_paths: List[str],
        summary_length: Literal["short", "standard", "detailed"] = "standard",
        output_format: Literal["json", "markdown", "plain"] = "json",
        extract_keywords: bool = False
    ) -> str:
        """
        Summarize multiple files in batch mode.
        
        Args:
            file_paths: List of paths to the files to summarize
            summary_length: Length of summary ('short', 'standard', or 'detailed')
            output_format: Format for the output ('json', 'markdown', or 'plain')
            extract_keywords: Whether to extract keywords from the content
            
        Returns:
            Structured summary of the file contents in the specified format
            
        Raises:
            ValueError: If any file format is unsupported or files cannot be read
            RuntimeError: If summary generation fails
        """
        # Validate files exist
        for path in file_paths:
            if not os.path.exists(path):
                raise ValueError(f"File not found: {path}")
        
        # Prepare the input prompt
        prompt = self._build_batch_summarize_prompt(
            file_paths=file_paths,
            summary_length=summary_length,
            output_format=output_format,
            extract_keywords=extract_keywords
        )
        
        # Call the agent
        return self.agent(prompt)
    
    def _build_summarize_prompt(
        self,
        file_path: str,
        summary_length: str,
        output_format: str,
        extract_keywords: bool
    ) -> str:
        """
        Build the prompt for summarizing a single file.
        
        Args:
            file_path: Path to the file to summarize
            summary_length: Length of summary
            output_format: Format for the output
            extract_keywords: Whether to extract keywords
            
        Returns:
            Formatted prompt string
        """
        prompt = f"Please summarize the following file:\n\nFile path: {file_path}\n"
        prompt += f"Summary length: {summary_length}\n"
        prompt += f"Output format: {output_format}\n"
        prompt += f"Extract keywords: {'Yes' if extract_keywords else 'No'}\n\n"
        prompt += "Please use the file_summarizer_tool to read and summarize the file content."
        
        return prompt
    
    def _build_batch_summarize_prompt(
        self,
        file_paths: List[str],
        summary_length: str,
        output_format: str,
        extract_keywords: bool
    ) -> str:
        """
        Build the prompt for summarizing multiple files in batch mode.
        
        Args:
            file_paths: List of paths to the files to summarize
            summary_length: Length of summary
            output_format: Format for the output
            extract_keywords: Whether to extract keywords
            
        Returns:
            Formatted prompt string
        """
        file_paths_str = "\n".join([f"- {path}" for path in file_paths])
        
        prompt = f"Please summarize the following files in batch mode:\n\nFiles:\n{file_paths_str}\n\n"
        prompt += f"Summary length: {summary_length}\n"
        prompt += f"Output format: {output_format}\n"
        prompt += f"Extract keywords: {'Yes' if extract_keywords else 'No'}\n\n"
        prompt += "Please use the file_summarizer_tool with batch_process=True to read and summarize the files."
        
        return prompt


# Create a singleton instance for easy import
def get_file_summarizer(env: str = "production", version: str = "latest", model_id: str = "default") -> FileSummarizerAgent:
    """
    Get a configured instance of the FileSummarizerAgent.
    
    Args:
        env: Environment setting ('production', 'development', or 'testing')
        version: Agent version to use
        model_id: Model ID to use for the agent
        
    Returns:
        Configured FileSummarizerAgent instance
    """
    return FileSummarizerAgent(env=env, version=version, model_id=model_id)


if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='File Summarizer Agent')
    parser.add_argument('-f', '--file', type=str, help='Path to file to summarize')
    parser.add_argument('-b', '--batch', type=str, help='Comma-separated list of file paths for batch processing')
    parser.add_argument('-l', '--length', type=str, choices=['short', 'standard', 'detailed'], 
                        default='standard', help='Summary length')
    parser.add_argument('-o', '--output', type=str, choices=['json', 'markdown', 'plain'], 
                        default='json', help='Output format')
    parser.add_argument('-k', '--keywords', action='store_true', help='Extract keywords')
    parser.add_argument('-e', '--env', type=str, choices=['production', 'development', 'testing'],
                        default='production', help='Environment setting')
    args = parser.parse_args()
    
    # Create the agent
    file_summarizer = get_file_summarizer(env=args.env)
    
    print(f"✅ File Summarizer Agent created successfully")
    
    try:
        if args.batch:
            # Batch processing mode
            file_paths = [path.strip() for path in args.batch.split(',')]
            print(f"🔄 Processing {len(file_paths)} files in batch mode...")
            result = file_summarizer.summarize_files(
                file_paths=file_paths,
                summary_length=args.length,
                output_format=args.output,
                extract_keywords=args.keywords
            )
        elif args.file:
            # Single file mode
            print(f"🔄 Processing file: {args.file}")
            result = file_summarizer.summarize_file(
                file_path=args.file,
                summary_length=args.length,
                output_format=args.output,
                extract_keywords=args.keywords
            )
        else:
            print("❌ Error: Please provide a file path using -f/--file or a batch of files using -b/--batch")
            sys.exit(1)
        
        print(f"📋 Summary Result:\n{result}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)