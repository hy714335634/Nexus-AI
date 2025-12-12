#!/usr/bin/env python3
"""
ClinicalTrials.gov Search Agent

This agent provides intelligent search capabilities for ClinicalTrials.gov data, 
designed specifically for clinical development professionals. It processes natural 
language queries, plans search strategies, performs multiple deep searches, analyzes 
and integrates results, and presents information from a clinical development perspective.

Key capabilities:
1. Query understanding and search strategy planning
2. Multiple deep searches using ClinicalTrials.gov API
3. Results analysis and integration
4. Clinical development perspective presentation
5. Session context maintenance for continuous queries

The agent integrates specialized tools for ClinicalTrials.gov API interaction, query building,
results parsing, analysis, integration, and clinical report generation.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Union
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry
from nexus_utils.config_loader import ConfigLoader
config = ConfigLoader()
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up telemetry
os.environ["BYPASS_TOOL_CONSENT"] = "true"
otel_endpoint = config.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# Create agent parameters
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "us.anthropic.claude-opus-4-20250514-v1:0",  # Using Claude Opus for advanced clinical comprehension
    "enable_logging": True
}

# Create the ClinicalTrials.gov Search Agent
clinicaltrials_search_agent = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/clinicaltrials_search_agent/clinicaltrials_search_agent", 
    **agent_params
)

def search_clinical_trials(
    query: str, 
    max_results: int = 20,
    search_depth: int = 2,
    study_types: Optional[List[str]] = None,
    phases: Optional[List[str]] = None,
    status: Optional[List[str]] = None,
    date_range: Optional[Dict[str, str]] = None,
    report_type: str = "summary"
) -> str:
    """
    Search ClinicalTrials.gov for clinical trials based on a query and parameters.
    
    Args:
        query (str): The natural language query or research question
        max_results (int): Maximum number of results to return per search (default: 20)
        search_depth (int): Number of deep searches to perform (default: 2)
        study_types (List[str], optional): Specific study types to filter by, e.g. ["Interventional", "Observational"]
        phases (List[str], optional): Specific trial phases to filter by, e.g. ["Phase 1", "Phase 2"]
        status (List[str], optional): Trial status to filter by, e.g. ["Recruiting", "Completed"]
        date_range (Dict[str, str], optional): Date range for filtering results, e.g. {"start_date": "2020-01-01", "end_date": "2023-12-31"}
        report_type (str): Type of report to generate - "summary" or "detailed" (default: "summary")
        
    Returns:
        str: Formatted response with search results, analysis, and clinical development perspective
    """
    # Construct input with parameters
    input_text = f"{query}\n\n"
    
    # Add search parameters if provided
    params = []
    if max_results != 20:
        params.append(f"Max results per search: {max_results}")
    if search_depth != 2:
        params.append(f"Search depth: {search_depth}")
    if study_types:
        types_str = f"Study types: {', '.join(study_types)}"
        params.append(types_str)
    if phases:
        phases_str = f"Trial phases: {', '.join(phases)}"
        params.append(phases_str)
    if status:
        status_str = f"Trial status: {', '.join(status)}"
        params.append(status_str)
    if date_range:
        date_str = f"Date range: {date_range.get('start_date', '')} to {date_range.get('end_date', '')}"
        params.append(date_str)
    if report_type != "summary":
        params.append(f"Report type: {report_type}")
    
    if params:
        input_text += "Search parameters:\n" + "\n".join(f"- {param}" for param in params) + "\n\n"
    
    # Process the query through the agent
    try:
        result = clinicaltrials_search_agent(input_text)
        return result
    except Exception as e:
        logger.error(f"Error processing clinical trials search: {e}")
        return f"Error processing clinical trials search: {str(e)}"

class ClinicalTrialsSearchSession:
    """
    Manages a continuous session for clinical trials searches, maintaining context
    between queries for more effective follow-up questions and deeper analysis.
    """
    
    def __init__(self):
        """Initialize a new clinical trials search session."""
        self.session_id = os.urandom(16).hex()
        self.query_history = []
        self.result_history = []
        self.context = {}
        logger.info(f"Created new clinical trials search session: {self.session_id}")
    
    def search(self, 
              query: str, 
              max_results: int = 20,
              search_depth: int = 2,
              study_types: Optional[List[str]] = None,
              phases: Optional[List[str]] = None,
              status: Optional[List[str]] = None,
              date_range: Optional[Dict[str, str]] = None,
              report_type: str = "summary",
              clear_context: bool = False) -> str:
        """
        Perform a search within this session, maintaining context between queries.
        
        Args:
            query (str): The natural language query or research question
            max_results (int): Maximum number of results to return per search (default: 20)
            search_depth (int): Number of deep searches to perform (default: 2)
            study_types (List[str], optional): Specific study types to filter by
            phases (List[str], optional): Specific trial phases to filter by
            status (List[str], optional): Trial status to filter by
            date_range (Dict[str, str], optional): Date range for filtering results
            report_type (str): Type of report to generate - "summary" or "detailed" (default: "summary")
            clear_context (bool): Whether to clear previous context (default: False)
            
        Returns:
            str: Formatted response with search results, analysis, and clinical development perspective
        """
        if clear_context:
            self.context = {}
            logger.info(f"Cleared context for session: {self.session_id}")
        
        # Add session context to the query
        input_text = query + "\n\n"
        
        # Add search parameters
        params = []
        if max_results != 20:
            params.append(f"Max results per search: {max_results}")
        if search_depth != 2:
            params.append(f"Search depth: {search_depth}")
        if study_types:
            types_str = f"Study types: {', '.join(study_types)}"
            params.append(types_str)
        if phases:
            phases_str = f"Trial phases: {', '.join(phases)}"
            params.append(phases_str)
        if status:
            status_str = f"Trial status: {', '.join(status)}"
            params.append(status_str)
        if date_range:
            date_str = f"Date range: {date_range.get('start_date', '')} to {date_range.get('end_date', '')}"
            params.append(date_str)
        if report_type != "summary":
            params.append(f"Report type: {report_type}")
        
        if params:
            input_text += "Search parameters:\n" + "\n".join(f"- {param}" for param in params) + "\n\n"
        
        # Add session context if available
        if self.query_history and not clear_context:
            input_text += "Session context:\n"
            input_text += f"- Previous queries: {len(self.query_history)}\n"
            input_text += f"- Most recent query: {self.query_history[-1]}\n\n"
        
        # Store the query in history
        self.query_history.append(query)
        
        # Process the query through the agent
        try:
            result = clinicaltrials_search_agent(input_text)
            self.result_history.append(result)
            return result
        except Exception as e:
            error_msg = f"Error processing clinical trials search: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def get_session_summary(self) -> str:
        """
        Generate a summary of the current session, including all queries and key findings.
        
        Returns:
            str: Session summary
        """
        if not self.query_history:
            return "No searches have been performed in this session."
        
        input_text = "Generate a summary of this search session, including all queries and key findings.\n\n"
        input_text += "Session queries:\n"
        
        for i, query in enumerate(self.query_history):
            input_text += f"{i+1}. {query}\n"
        
        input_text += "\nPlease provide a comprehensive summary of all findings across these queries."
        
        try:
            result = clinicaltrials_search_agent(input_text)
            return result
        except Exception as e:
            error_msg = f"Error generating session summary: {str(e)}"
            logger.error(error_msg)
            return error_msg

if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='ClinicalTrials.gov Search Agent')
    parser.add_argument('-q', '--query', type=str, required=True,
                       help='Research question or clinical query')
    parser.add_argument('-n', '--max_results', type=int, default=20,
                       help='Maximum number of results to return per search (default: 20)')
    parser.add_argument('-d', '--search_depth', type=int, default=2,
                       help='Number of deep searches to perform (default: 2)')
    parser.add_argument('--study_types', type=str, default=None,
                       help='Comma-separated list of study types to filter by')
    parser.add_argument('--phases', type=str, default=None,
                       help='Comma-separated list of trial phases to filter by')
    parser.add_argument('--status', type=str, default=None,
                       help='Comma-separated list of trial status to filter by')
    parser.add_argument('--start_date', type=str, default=None,
                       help='Start date for filtering results (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, default=None,
                       help='End date for filtering results (YYYY-MM-DD)')
    parser.add_argument('--report_type', type=str, default="summary", choices=["summary", "detailed"],
                       help='Type of report to generate (default: summary)')
    parser.add_argument('--session', action='store_true',
                       help='Start an interactive session for multiple queries')
    
    args = parser.parse_args()
    
    # Process parameters
    study_types = None
    if args.study_types:
        study_types = [t.strip() for t in args.study_types.split(',')]
    
    phases = None
    if args.phases:
        phases = [p.strip() for p in args.phases.split(',')]
    
    status = None
    if args.status:
        status = [s.strip() for s in args.status.split(',')]
    
    date_range = None
    if args.start_date or args.end_date:
        date_range = {
            "start_date": args.start_date,
            "end_date": args.end_date
        }
    
    print(f"✅ ClinicalTrials.gov Search Agent initialized")
    
    if args.session:
        # Interactive session mode
        session = ClinicalTrialsSearchSession()
        print(f"🔄 Starting interactive session. Type 'exit' to quit, 'summary' for session summary.")
        
        # First query from command line
        print(f"🔍 Searching for: {args.query}")
        result = session.search(
            query=args.query,
            max_results=args.max_results,
            search_depth=args.search_depth,
            study_types=study_types,
            phases=phases,
            status=status,
            date_range=date_range,
            report_type=args.report_type
        )
        print("\n📋 Search Results:\n")
        print(result)
        
        # Continue with interactive session
        while True:
            try:
                query = input("\n🔍 Enter your next query (or 'exit'/'summary'): ")
                if query.lower() == 'exit':
                    print("Exiting session.")
                    break
                elif query.lower() == 'summary':
                    print("\n📋 Session Summary:\n")
                    summary = session.get_session_summary()
                    print(summary)
                    continue
                
                result = session.search(query=query)
                print("\n📋 Search Results:\n")
                print(result)
            except KeyboardInterrupt:
                print("\nExiting session.")
                break
    else:
        # Single query mode
        print(f"🔍 Searching for: {args.query}")
        result = search_clinical_trials(
            query=args.query,
            max_results=args.max_results,
            search_depth=args.search_depth,
            study_types=study_types,
            phases=phases,
            status=status,
            date_range=date_range,
            report_type=args.report_type
        )
        print("\n📋 Search Results:\n")
        print(result)