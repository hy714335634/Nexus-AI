"""
Log analysis and script generation tools for AWS monitoring and AIOps.
"""

from typing import Dict, List, Any, Optional, Union, Tuple
import json
import time
import re
import os
import uuid
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
from strands import tool

@tool
def llm_log_analyzer(
    log_data: str,
    analysis_type: str,
    context: Optional[Dict[str, Any]] = None,
    max_log_size: int = 10000,
) -> str:
    """
    Analyze log content using LLM capabilities to identify patterns, errors, and root causes.
    
    This tool uses AWS Bedrock to analyze log data, identify error patterns, determine root causes,
    and provide insights. It can handle different types of analysis based on the specified analysis_type.
    
    Args:
        log_data: JSON string containing log entries to analyze
        analysis_type: Type of analysis to perform (error_detection, root_cause, anomaly_detection, pattern_recognition)
        context: Optional contextual information like resource type, related metrics, etc.
        max_log_size: Maximum size of log data to process (characters) to avoid token limits
    
    Returns:
        JSON string containing analysis results including identified issues, patterns, and recommendations
    """
    try:
        # Parse log data
        logs = json.loads(log_data)
        
        # Validate log data format
        if not isinstance(logs, list) and not (isinstance(logs, dict) and 'events' in logs):
            return json.dumps({
                'error': 'Invalid log data format. Expected a list of log entries or a dictionary with an "events" key.'
            })
        
        # Extract log events from different possible formats
        log_events = logs if isinstance(logs, list) else logs.get('events', [])
        
        # Truncate log data if it exceeds max size
        total_log_size = sum(len(str(event)) for event in log_events)
        if total_log_size > max_log_size:
            # Sort by timestamp if available, otherwise keep original order
            if all('timestamp' in event for event in log_events):
                log_events.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            
            # Keep most recent logs up to max_log_size
            truncated_events = []
            current_size = 0
            for event in log_events:
                event_size = len(str(event))
                if current_size + event_size <= max_log_size:
                    truncated_events.append(event)
                    current_size += event_size
                else:
                    break
            
            log_events = truncated_events
        
        # Initialize Bedrock client for LLM analysis
        bedrock_runtime = boto3.client('bedrock-runtime')
        
        # Prepare prompt based on analysis type
        prompt_prefix = "You are an expert AWS log analyst. Analyze the following logs and "
        
        if analysis_type == 'error_detection':
            prompt_suffix = "identify all errors, exceptions, and warnings. For each issue, extract the error code, message, timestamp, and affected resource if available. Categorize issues by severity."
        elif analysis_type == 'root_cause':
            prompt_suffix = "determine the root cause of the issues. Identify the primary factors contributing to the problem, any cascading effects, and the initial trigger event if possible."
        elif analysis_type == 'anomaly_detection':
            prompt_suffix = "identify any anomalous patterns or unusual behaviors. Look for unexpected values, unusual sequences of events, or deviations from normal patterns."
        elif analysis_type == 'pattern_recognition':
            prompt_suffix = "identify recurring patterns and their frequencies. Group similar log entries and summarize the common characteristics of each pattern."
        else:
            prompt_suffix = "provide a comprehensive analysis including errors, patterns, and potential issues."
        
        # Add context to prompt if provided
        context_text = ""
        if context:
            context_text = "\n\nAdditional context:\n"
            for key, value in context.items():
                context_text += f"- {key}: {value}\n"
        
        # Format log events for prompt
        log_text = json.dumps(log_events, indent=2)
        
        # Construct the full prompt
        prompt = f"{prompt_prefix}{prompt_suffix}{context_text}\n\nLogs:\n{log_text}\n\nProvide your analysis in JSON format with appropriate fields based on the analysis type."
        
        # Call Bedrock with Claude model
        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1
            })
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read())
        analysis_text = response_body['content'][0]['text']
        
        # Extract JSON from response (the LLM might wrap it in markdown code blocks)
        json_pattern = r'```json\n(.*?)\n```'
        json_match = re.search(json_pattern, analysis_text, re.DOTALL)
        
        if json_match:
            analysis_result = json.loads(json_match.group(1))
        else:
            # Try to parse the entire response as JSON
            try:
                analysis_result = json.loads(analysis_text)
            except json.JSONDecodeError:
                # If parsing fails, return the text as-is in a structured format
                analysis_result = {
                    "analysis": analysis_text,
                    "format": "text",
                    "analysis_type": analysis_type
                }
        
        # Add metadata to the result
        result = {
            "analysis_type": analysis_type,
            "timestamp": datetime.utcnow().isoformat(),
            "log_count": len(log_events),
            "truncated": total_log_size > max_log_size,
            "results": analysis_result
        }
        
        return json.dumps(result)
        
    except ClientError as e:
        return json.dumps({
            'error': f"AWS API error: {str(e)}",
            'error_code': e.response['Error']['Code'],
            'request_id': e.response.get('ResponseMetadata', {}).get('RequestId', 'unknown')
        })
    except Exception as e:
        return json.dumps({
            'error': str(e),
            'analysis_type': analysis_type
        })


@tool
def script_generator(
    analysis_result: str,
    script_type: str,
    target_resources: List[str],
    aws_region: str,
    safety_level: str = "high",
) -> str:
    """
    Generate remediation scripts based on analysis results.
    
    This tool creates AWS CLI, Python, or shell scripts to address issues identified
    in the analysis results. It includes safety checks, rollback mechanisms, and
    documentation in the generated scripts.
    
    Args:
        analysis_result: JSON string containing analysis results from llm_log_analyzer
        script_type: Type of script to generate (aws_cli, python, shell)
        target_resources: List of AWS resources to target (e.g., instance IDs, function names)
        aws_region: AWS region for the resources
        safety_level: Level of safety measures to include (high, medium, low)
    
    Returns:
        JSON string containing the generated script, documentation, and execution instructions
    """
    try:
        # Parse analysis result
        analysis = json.loads(analysis_result)
        
        # Validate required fields
        if not isinstance(analysis, dict) or 'results' not in analysis:
            return json.dumps({
                'error': 'Invalid analysis result format. Expected a dictionary with a "results" key.'
            })
        
        # Initialize Bedrock client for LLM script generation
        bedrock_runtime = boto3.client('bedrock-runtime')
        
        # Prepare prompt based on script type and safety level
        safety_measures = {
            "high": [
                "Include comprehensive error handling",
                "Add dry-run or validation steps before making changes",
                "Implement automatic rollback mechanisms",
                "Add confirmation prompts before critical actions",
                "Include detailed logging of all actions",
                "Validate all inputs and parameters",
                "Check resource state before and after changes",
                "Include comments explaining each step and its purpose",
                "Add resource existence checks before operations"
            ],
            "medium": [
                "Include basic error handling",
                "Add validation steps for critical operations",
                "Log important actions",
                "Check resource existence before operations",
                "Include comments for major steps"
            ],
            "low": [
                "Include minimal error handling",
                "Add comments for critical operations",
                "Basic input validation"
            ]
        }
        
        # Get appropriate safety measures
        selected_safety = safety_measures.get(safety_level.lower(), safety_measures["high"])
        
        # Prepare script type specific instructions
        script_instructions = {
            "aws_cli": "Generate an AWS CLI script using bash with proper error handling and comments",
            "python": "Generate a Python script using boto3 with proper error handling, functions, and comments",
            "shell": "Generate a shell script with AWS CLI commands, proper error handling, and comments"
        }
        
        # Format target resources for prompt
        resources_text = "\n".join([f"- {res}" for res in target_resources])
        
        # Construct the full prompt
        prompt = f"""You are an expert AWS DevOps engineer. Generate a {script_type} remediation script to address the issues identified in the following analysis:

Analysis Result:
{json.dumps(analysis, indent=2)}

Target Resources:
{resources_text}

AWS Region: {aws_region}

Safety Requirements:
{', '.join(selected_safety)}

Script Requirements:
1. {script_instructions.get(script_type, "Generate a well-structured script")}
2. Include clear comments explaining each section
3. Implement proper error handling and logging
4. Add safety checks before making changes
5. Include usage instructions at the top of the script
6. Make the script idempotent when possible
7. Include rollback mechanisms for critical operations
8. Do not include any placeholder comments - provide complete, functional code

Provide your response in JSON format with the following structure:
{
  "script": "The complete script content with no placeholders",
  "documentation": "Usage instructions and explanation of what the script does",
  "execution_instructions": "Step-by-step instructions for executing the script",
  "prerequisites": ["List of prerequisites like required permissions, tools, etc."],
  "risk_assessment": "Assessment of potential risks and mitigation strategies"
}"""
        
        # Call Bedrock with Claude model
        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.2
            })
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read())
        script_text = response_body['content'][0]['text']
        
        # Extract JSON from response (the LLM might wrap it in markdown code blocks)
        json_pattern = r'```json\n(.*?)\n```'
        json_match = re.search(json_pattern, script_text, re.DOTALL)
        
        if json_match:
            script_result = json.loads(json_match.group(1))
        else:
            # Try to parse the entire response as JSON
            try:
                script_result = json.loads(script_text)
            except json.JSONDecodeError:
                # If parsing fails, return an error
                return json.dumps({
                    'error': 'Failed to parse LLM response as JSON',
                    'raw_response': script_text[:1000] + ('...' if len(script_text) > 1000 else '')
                })
        
        # Add metadata to the result
        result = {
            "script_type": script_type,
            "target_resources": target_resources,
            "aws_region": aws_region,
            "safety_level": safety_level,
            "generated_at": datetime.utcnow().isoformat(),
            "script_id": str(uuid.uuid4()),
            "script_data": script_result
        }
        
        return json.dumps(result)
        
    except ClientError as e:
        return json.dumps({
            'error': f"AWS API error: {str(e)}",
            'error_code': e.response['Error']['Code'],
            'request_id': e.response.get('ResponseMetadata', {}).get('RequestId', 'unknown')
        })
    except Exception as e:
        return json.dumps({
            'error': str(e),
            'script_type': script_type
        })


@tool
def report_formatter(
    analysis_data: str,
    remediation_scripts: Optional[str] = None,
    format_type: str = "markdown",
    include_summary: bool = True,
    include_details: bool = True,
) -> str:
    """
    Generate structured reports from analysis results and remediation scripts.
    
    This tool formats analysis results and remediation scripts into structured reports
    in various formats (JSON, Markdown, HTML). It can include summaries, detailed findings,
    and remediation instructions.
    
    Args:
        analysis_data: JSON string containing analysis results
        remediation_scripts: Optional JSON string containing remediation scripts
        format_type: Output format (json, markdown, html)
        include_summary: Whether to include an executive summary
        include_details: Whether to include detailed findings
    
    Returns:
        Formatted report in the specified format
    """
    try:
        # Parse input data
        analysis = json.loads(analysis_data)
        
        # Parse remediation scripts if provided
        scripts = None
        if remediation_scripts:
            scripts = json.loads(remediation_scripts)
        
        # Validate analysis data format
        if not isinstance(analysis, dict) or 'results' not in analysis:
            return json.dumps({
                'error': 'Invalid analysis data format. Expected a dictionary with a "results" key.'
            })
        
        # Generate report based on format type
        if format_type.lower() == 'json':
            # Create structured JSON report
            report = {
                "report_id": str(uuid.uuid4()),
                "generated_at": datetime.utcnow().isoformat(),
                "report_type": "AWS Monitoring Analysis",
                "summary": None,
                "details": None,
                "remediation": None
            }
            
            # Add summary if requested
            if include_summary:
                # Extract key information for summary
                summary = {
                    "analysis_type": analysis.get("analysis_type", "unknown"),
                    "timestamp": analysis.get("timestamp", datetime.utcnow().isoformat()),
                    "log_count": analysis.get("log_count", 0)
                }
                
                # Add issue summary if available
                results = analysis.get("results", {})
                if isinstance(results, dict):
                    if "issues" in results:
                        summary["issue_count"] = len(results["issues"])
                        
                        # Count issues by severity if available
                        severity_counts = {}
                        for issue in results["issues"]:
                            severity = issue.get("severity", "unknown")
                            severity_counts[severity] = severity_counts.get(severity, 0) + 1
                        
                        if severity_counts:
                            summary["severity_distribution"] = severity_counts
                    
                    # Add root cause summary if available
                    if "root_causes" in results:
                        summary["root_cause_count"] = len(results["root_causes"])
                
                report["summary"] = summary
            
            # Add details if requested
            if include_details:
                report["details"] = analysis.get("results", {})
            
            # Add remediation information if available
            if scripts:
                if isinstance(scripts, list):
                    report["remediation"] = scripts
                elif isinstance(scripts, dict):
                    report["remediation"] = [scripts]
            
            return json.dumps(report, indent=2)
            
        elif format_type.lower() == 'markdown':
            # Generate markdown report
            md_report = []
            
            # Add header
            md_report.append("# AWS Monitoring Analysis Report")
            md_report.append(f"**Generated:** {datetime.utcnow().isoformat()}")
            md_report.append(f"**Report ID:** {str(uuid.uuid4())}")
            md_report.append("")
            
            # Add summary if requested
            if include_summary:
                md_report.append("## Executive Summary")
                
                # Add analysis metadata
                md_report.append(f"**Analysis Type:** {analysis.get('analysis_type', 'Unknown')}")
                md_report.append(f"**Logs Analyzed:** {analysis.get('log_count', 'Unknown')}")
                md_report.append(f"**Analysis Timestamp:** {analysis.get('timestamp', 'Unknown')}")
                
                # Add summary of findings
                results = analysis.get("results", {})
                if isinstance(results, dict):
                    # Handle error detection results
                    if "issues" in results:
                        issues = results["issues"]
                        md_report.append(f"\n**Issues Detected:** {len(issues)}")
                        
                        # Count issues by severity
                        severity_counts = {}
                        for issue in issues:
                            severity = issue.get("severity", "unknown")
                            severity_counts[severity] = severity_counts.get(severity, 0) + 1
                        
                        if severity_counts:
                            md_report.append("\n**Issues by Severity:**")
                            for severity, count in severity_counts.items():
                                md_report.append(f"- {severity.capitalize()}: {count}")
                    
                    # Handle root cause analysis results
                    if "root_causes" in results:
                        root_causes = results["root_causes"]
                        md_report.append(f"\n**Root Causes Identified:** {len(root_causes)}")
                        
                        # List primary root causes
                        md_report.append("\n**Primary Issues:**")
                        for i, cause in enumerate(root_causes[:3], 1):
                            md_report.append(f"{i}. {cause.get('description', 'Unknown issue')}")
                    
                    # Handle pattern recognition results
                    if "patterns" in results:
                        patterns = results["patterns"]
                        md_report.append(f"\n**Patterns Detected:** {len(patterns)}")
                
                md_report.append("\n")
            
            # Add details if requested
            if include_details:
                md_report.append("## Detailed Findings")
                
                results = analysis.get("results", {})
                if isinstance(results, dict):
                    # Handle error detection results
                    if "issues" in results:
                        issues = results["issues"]
                        md_report.append("\n### Issues Detected")
                        
                        for i, issue in enumerate(issues, 1):
                            md_report.append(f"\n#### Issue {i}: {issue.get('title', 'Unknown issue')}")
                            md_report.append(f"**Severity:** {issue.get('severity', 'Unknown')}")
                            if "timestamp" in issue:
                                md_report.append(f"**Timestamp:** {issue['timestamp']}")
                            if "error_code" in issue:
                                md_report.append(f"**Error Code:** {issue['error_code']}")
                            if "affected_resource" in issue:
                                md_report.append(f"**Affected Resource:** {issue['affected_resource']}")
                            if "message" in issue:
                                md_report.append(f"\n**Message:**\n```\n{issue['message']}\n```")
                            if "description" in issue:
                                md_report.append(f"\n{issue['description']}")
                    
                    # Handle root cause analysis results
                    if "root_causes" in results:
                        root_causes = results["root_causes"]
                        md_report.append("\n### Root Cause Analysis")
                        
                        for i, cause in enumerate(root_causes, 1):
                            md_report.append(f"\n#### Root Cause {i}: {cause.get('title', 'Unknown cause')}")
                            if "description" in cause:
                                md_report.append(f"\n{cause['description']}")
                            if "evidence" in cause:
                                md_report.append("\n**Supporting Evidence:**")
                                for evidence in cause["evidence"]:
                                    md_report.append(f"- {evidence}")
                            if "impact" in cause:
                                md_report.append(f"\n**Impact:** {cause['impact']}")
                    
                    # Handle pattern recognition results
                    if "patterns" in results:
                        patterns = results["patterns"]
                        md_report.append("\n### Pattern Analysis")
                        
                        for i, pattern in enumerate(patterns, 1):
                            md_report.append(f"\n#### Pattern {i}: {pattern.get('name', 'Unnamed pattern')}")
                            if "frequency" in pattern:
                                md_report.append(f"**Frequency:** {pattern['frequency']}")
                            if "description" in pattern:
                                md_report.append(f"\n{pattern['description']}")
                            if "examples" in pattern:
                                md_report.append("\n**Examples:**")
                                for example in pattern["examples"][:3]:  # Limit to 3 examples
                                    md_report.append(f"```\n{example}\n```")
                
                md_report.append("\n")
            
            # Add remediation section if scripts are provided
            if scripts:
                md_report.append("## Remediation")
                
                script_list = scripts if isinstance(scripts, list) else [scripts]
                
                for i, script_data in enumerate(script_list, 1):
                    if isinstance(script_data, dict) and "script_data" in script_data:
                        script_info = script_data["script_data"]
                        
                        md_report.append(f"\n### Remediation Script {i}")
                        md_report.append(f"**Type:** {script_data.get('script_type', 'Unknown')}")
                        md_report.append(f"**Target Resources:** {', '.join(script_data.get('target_resources', ['Unknown']))}")
                        
                        if "documentation" in script_info:
                            md_report.append(f"\n**Purpose:**\n{script_info['documentation']}")
                        
                        if "prerequisites" in script_info:
                            md_report.append("\n**Prerequisites:**")
                            for prereq in script_info["prerequisites"]:
                                md_report.append(f"- {prereq}")
                        
                        if "risk_assessment" in script_info:
                            md_report.append(f"\n**Risk Assessment:**\n{script_info['risk_assessment']}")
                        
                        if "execution_instructions" in script_info:
                            md_report.append(f"\n**Execution Instructions:**\n{script_info['execution_instructions']}")
                        
                        if "script" in script_info:
                            script_type = script_data.get("script_type", "").lower()
                            lang = "bash" if script_type in ["aws_cli", "shell"] else script_type
                            md_report.append(f"\n**Script:**\n```{lang}\n{script_info['script']}\n```")
            
            return "\n".join(md_report)
            
        elif format_type.lower() == 'html':
            # Generate HTML report
            html_report = []
            
            # Add header
            html_report.append("<!DOCTYPE html>")
            html_report.append("<html lang=\"en\">")
            html_report.append("<head>")
            html_report.append("  <meta charset=\"UTF-8\">")
            html_report.append("  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">")
            html_report.append("  <title>AWS Monitoring Analysis Report</title>")
            html_report.append("  <style>")
            html_report.append("    body { font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; color: #333; }")
            html_report.append("    h1 { color: #0066cc; }")
            html_report.append("    h2 { color: #0066cc; border-bottom: 1px solid #ddd; padding-bottom: 5px; }")
            html_report.append("    h3 { color: #333; }")
            html_report.append("    h4 { color: #666; }")
            html_report.append("    .severity-critical { color: #d13212; font-weight: bold; }")
            html_report.append("    .severity-high { color: #ff9900; font-weight: bold; }")
            html_report.append("    .severity-medium { color: #e69f00; }")
            html_report.append("    .severity-low { color: #669900; }")
            html_report.append("    pre { background-color: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; }")
            html_report.append("    .metadata { color: #666; margin-bottom: 20px; }")
            html_report.append("    .summary-box { background-color: #f0f7ff; border: 1px solid #cce0ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; }")
            html_report.append("    .issue { background-color: #fff; border: 1px solid #ddd; padding: 15px; border-radius: 5px; margin-bottom: 15px; }")
            html_report.append("    .script { background-color: #f9f9f9; border: 1px solid #ddd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }")
            html_report.append("  </style>")
            html_report.append("</head>")
            html_report.append("<body>")
            
            html_report.append("  <h1>AWS Monitoring Analysis Report</h1>")
            html_report.append(f"  <div class=\"metadata\">")
            html_report.append(f"    <strong>Generated:</strong> {datetime.utcnow().isoformat()}<br>")
            html_report.append(f"    <strong>Report ID:</strong> {str(uuid.uuid4())}")
            html_report.append("  </div>")
            
            # Add summary if requested
            if include_summary:
                html_report.append("  <h2>Executive Summary</h2>")
                html_report.append("  <div class=\"summary-box\">")
                
                # Add analysis metadata
                html_report.append(f"    <p><strong>Analysis Type:</strong> {analysis.get('analysis_type', 'Unknown')}<br>")
                html_report.append(f"    <strong>Logs Analyzed:</strong> {analysis.get('log_count', 'Unknown')}<br>")
                html_report.append(f"    <strong>Analysis Timestamp:</strong> {analysis.get('timestamp', 'Unknown')}</p>")
                
                # Add summary of findings
                results = analysis.get("results", {})
                if isinstance(results, dict):
                    # Handle error detection results
                    if "issues" in results:
                        issues = results["issues"]
                        html_report.append(f"    <p><strong>Issues Detected:</strong> {len(issues)}</p>")
                        
                        # Count issues by severity
                        severity_counts = {}
                        for issue in issues:
                            severity = issue.get("severity", "unknown")
                            severity_counts[severity] = severity_counts.get(severity, 0) + 1
                        
                        if severity_counts:
                            html_report.append("    <p><strong>Issues by Severity:</strong></p>")
                            html_report.append("    <ul>")
                            for severity, count in severity_counts.items():
                                severity_class = f"severity-{severity.lower()}" if severity.lower() in ["critical", "high", "medium", "low"] else ""
                                html_report.append(f"      <li><span class=\"{severity_class}\">{severity.capitalize()}:</span> {count}</li>")
                            html_report.append("    </ul>")
                    
                    # Handle root cause analysis results
                    if "root_causes" in results:
                        root_causes = results["root_causes"]
                        html_report.append(f"    <p><strong>Root Causes Identified:</strong> {len(root_causes)}</p>")
                        
                        # List primary root causes
                        html_report.append("    <p><strong>Primary Issues:</strong></p>")
                        html_report.append("    <ol>")
                        for cause in root_causes[:3]:  # Limit to top 3
                            html_report.append(f"      <li>{cause.get('description', 'Unknown issue')}</li>")
                        html_report.append("    </ol>")
                
                html_report.append("  </div>")
            
            # Add details if requested
            if include_details:
                html_report.append("  <h2>Detailed Findings</h2>")
                
                results = analysis.get("results", {})
                if isinstance(results, dict):
                    # Handle error detection results
                    if "issues" in results:
                        issues = results["issues"]
                        html_report.append("  <h3>Issues Detected</h3>")
                        
                        for i, issue in enumerate(issues, 1):
                            severity = issue.get('severity', 'unknown').lower()
                            severity_class = f"severity-{severity}" if severity in ["critical", "high", "medium", "low"] else ""
                            
                            html_report.append(f"  <div class=\"issue\">")
                            html_report.append(f"    <h4>Issue {i}: {issue.get('title', 'Unknown issue')}</h4>")
                            html_report.append(f"    <p><strong>Severity:</strong> <span class=\"{severity_class}\">{issue.get('severity', 'Unknown')}</span></p>")
                            
                            if "timestamp" in issue:
                                html_report.append(f"    <p><strong>Timestamp:</strong> {issue['timestamp']}</p>")
                            if "error_code" in issue:
                                html_report.append(f"    <p><strong>Error Code:</strong> {issue['error_code']}</p>")
                            if "affected_resource" in issue:
                                html_report.append(f"    <p><strong>Affected Resource:</strong> {issue['affected_resource']}</p>")
                            if "message" in issue:
                                html_report.append(f"    <p><strong>Message:</strong></p>")
                                html_report.append(f"    <pre>{issue['message']}</pre>")
                            if "description" in issue:
                                html_report.append(f"    <p>{issue['description']}</p>")
                            
                            html_report.append("  </div>")
                    
                    # Handle root cause analysis results
                    if "root_causes" in results:
                        root_causes = results["root_causes"]
                        html_report.append("  <h3>Root Cause Analysis</h3>")
                        
                        for i, cause in enumerate(root_causes, 1):
                            html_report.append(f"  <div class=\"issue\">")
                            html_report.append(f"    <h4>Root Cause {i}: {cause.get('title', 'Unknown cause')}</h4>")
                            
                            if "description" in cause:
                                html_report.append(f"    <p>{cause['description']}</p>")
                            if "evidence" in cause:
                                html_report.append("    <p><strong>Supporting Evidence:</strong></p>")
                                html_report.append("    <ul>")
                                for evidence in cause["evidence"]:
                                    html_report.append(f"      <li>{evidence}</li>")
                                html_report.append("    </ul>")
                            if "impact" in cause:
                                html_report.append(f"    <p><strong>Impact:</strong> {cause['impact']}</p>")
                            
                            html_report.append("  </div>")
            
            # Add remediation section if scripts are provided
            if scripts:
                html_report.append("  <h2>Remediation</h2>")
                
                script_list = scripts if isinstance(scripts, list) else [scripts]
                
                for i, script_data in enumerate(script_list, 1):
                    if isinstance(script_data, dict) and "script_data" in script_data:
                        script_info = script_data["script_data"]
                        
                        html_report.append(f"  <div class=\"script\">")
                        html_report.append(f"    <h3>Remediation Script {i}</h3>")
                        html_report.append(f"    <p><strong>Type:</strong> {script_data.get('script_type', 'Unknown')}<br>")
                        html_report.append(f"    <strong>Target Resources:</strong> {', '.join(script_data.get('target_resources', ['Unknown']))}</p>")
                        
                        if "documentation" in script_info:
                            html_report.append(f"    <p><strong>Purpose:</strong><br>{script_info['documentation']}</p>")
                        
                        if "prerequisites" in script_info:
                            html_report.append("    <p><strong>Prerequisites:</strong></p>")
                            html_report.append("    <ul>")
                            for prereq in script_info["prerequisites"]:
                                html_report.append(f"      <li>{prereq}</li>")
                            html_report.append("    </ul>")
                        
                        if "risk_assessment" in script_info:
                            html_report.append(f"    <p><strong>Risk Assessment:</strong><br>{script_info['risk_assessment']}</p>")
                        
                        if "execution_instructions" in script_info:
                            html_report.append(f"    <p><strong>Execution Instructions:</strong><br>{script_info['execution_instructions']}</p>")
                        
                        if "script" in script_info:
                            html_report.append(f"    <p><strong>Script:</strong></p>")
                            html_report.append(f"    <pre>{script_info['script']}</pre>")
                        
                        html_report.append("  </div>")
            
            html_report.append("</body>")
            html_report.append("</html>")
            
            return "\n".join(html_report)
            
        else:
            return json.dumps({
                'error': f"Unsupported format type: {format_type}",
                'supported_formats': ['json', 'markdown', 'html']
            })
        
    except json.JSONDecodeError as e:
        return json.dumps({
            'error': f"Invalid JSON input: {str(e)}"
        })
    except Exception as e:
        return json.dumps({
            'error': str(e),
            'format_type': format_type
        })