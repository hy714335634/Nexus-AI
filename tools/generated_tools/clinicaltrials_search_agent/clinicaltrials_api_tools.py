from strands import tool
import requests
import json
import time
import hashlib
import os
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import urllib.parse

class ClinicalTrialsAPIClient:
    """Client for interacting with ClinicalTrials.gov API."""
    
    BASE_URL = "https://clinicaltrials.gov/api/v2"
    DEFAULT_FORMAT = "json"
    DEFAULT_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    CACHE_DIR = ".cache/clinicaltrials_search_agent"
    CACHE_EXPIRY = 86400  # 24 hours in seconds
    
    def __init__(self):
        """Initialize the ClinicalTrials.gov API client."""
        # Create cache directory if it doesn't exist
        os.makedirs(self.CACHE_DIR, exist_ok=True)
    
    def _get_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate a cache key based on endpoint and parameters."""
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(f"{endpoint}:{param_str}".encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if it exists and is not expired."""
        cache_file = os.path.join(self.CACHE_DIR, f"{cache_key}.json")
        
        if not os.path.exists(cache_file):
            return None
            
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
                
            # Check if cache is expired
            if time.time() - cached_data.get('timestamp', 0) > self.CACHE_EXPIRY:
                return None
                
            return cached_data.get('data')
        except Exception:
            return None
    
    def _cache_response(self, cache_key: str, response_data: Dict[str, Any]) -> None:
        """Cache API response data."""
        cache_file = os.path.join(self.CACHE_DIR, f"{cache_key}.json")
        
        try:
            cache_data = {
                'timestamp': time.time(),
                'data': response_data
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            print(f"Warning: Failed to cache response: {str(e)}")
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None, use_cache: bool = True) -> Dict[str, Any]:
        """Make a request to the ClinicalTrials.gov API with retry logic and caching."""
        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        
        # Add default format if not specified
        if 'format' not in params:
            params['format'] = self.DEFAULT_FORMAT
            
        # Check cache first if enabled
        if use_cache:
            cache_key = self._get_cache_key(endpoint, params)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                return cached_response
        
        # Make the request with retries
        retries = 0
        while retries <= self.MAX_RETRIES:
            try:
                response = requests.get(url, params=params, timeout=self.DEFAULT_TIMEOUT)
                response.raise_for_status()
                
                data = response.json()
                
                # Cache the successful response if caching is enabled
                if use_cache:
                    cache_key = self._get_cache_key(endpoint, params)
                    self._cache_response(cache_key, data)
                    
                return data
            except requests.exceptions.RequestException as e:
                retries += 1
                
                # If we've reached max retries, raise the exception
                if retries > self.MAX_RETRIES:
                    raise Exception(f"Failed to connect to ClinicalTrials.gov API after {self.MAX_RETRIES} attempts: {str(e)}")
                
                # Exponential backoff
                time.sleep(self.RETRY_DELAY * (2 ** (retries - 1)))
    
    def search_studies(self, query: str = None, fields: List[str] = None, 
                      max_results: int = 20, page: int = 1, 
                      use_cache: bool = True, **kwargs) -> Dict[str, Any]:
        """
        Search for clinical trials using the ClinicalTrials.gov API.
        
        Args:
            query: Search query string
            fields: List of fields to include in the response
            max_results: Maximum number of results to return
            page: Page number for pagination
            use_cache: Whether to use cached responses
            **kwargs: Additional search parameters
            
        Returns:
            API response containing search results
        """
        params = {
            'query': query,
            'pageSize': max_results,
            'page': page
        }
        
        # Add fields parameter if specified
        if fields:
            params['fields'] = ','.join(fields)
            
        # Add any additional parameters
        params.update(kwargs)
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        return self._make_request('studies', params, use_cache)
    
    def get_study(self, nct_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get detailed information about a specific study by its NCT ID.
        
        Args:
            nct_id: The NCT ID of the study
            use_cache: Whether to use cached responses
            
        Returns:
            API response containing study details
        """
        return self._make_request(f'studies/{nct_id}', use_cache=use_cache)
    
    def get_study_fields(self, fields: List[str], query: str = None, 
                        max_results: int = 20, page: int = 1,
                        use_cache: bool = True, **kwargs) -> Dict[str, Any]:
        """
        Get specific fields from studies matching a query.
        
        Args:
            fields: List of fields to retrieve
            query: Search query string
            max_results: Maximum number of results to return
            page: Page number for pagination
            use_cache: Whether to use cached responses
            **kwargs: Additional search parameters
            
        Returns:
            API response containing the requested fields
        """
        params = {
            'query': query,
            'fields': ','.join(fields),
            'pageSize': max_results,
            'page': page
        }
        
        # Add any additional parameters
        params.update(kwargs)
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        return self._make_request('studies', params, use_cache)
    
    def get_field_values(self, field: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get all possible values for a specific field.
        
        Args:
            field: The field to get values for
            use_cache: Whether to use cached responses
            
        Returns:
            API response containing field values
        """
        return self._make_request(f'field_values/{field}', use_cache=use_cache)


@tool
def clinical_trials_search(query: str, max_results: int = 20, 
                          fields: List[str] = None, 
                          use_cache: bool = True, 
                          **kwargs) -> str:
    """
    Search for clinical trials using the ClinicalTrials.gov API.
    
    Args:
        query: Search query string (can include condition, intervention, sponsor, etc.)
        max_results: Maximum number of results to return (default: 20)
        fields: List of specific fields to include in the response
        use_cache: Whether to use cached responses (default: True)
        **kwargs: Additional search parameters like status, phase, etc.
        
    Returns:
        JSON string containing search results
    """
    try:
        client = ClinicalTrialsAPIClient()
        results = client.search_studies(query=query, 
                                       fields=fields, 
                                       max_results=max_results, 
                                       use_cache=use_cache, 
                                       **kwargs)
        
        return json.dumps({
            "status": "success",
            "query": query,
            "total_count": results.get("totalCount", 0),
            "page_size": max_results,
            "results": results.get("studies", []),
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "query": query,
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }, indent=2)


@tool
def clinical_trials_get_study(nct_id: str, use_cache: bool = True) -> str:
    """
    Get detailed information about a specific clinical trial by its NCT ID.
    
    Args:
        nct_id: The NCT ID of the clinical trial (e.g., NCT01234567)
        use_cache: Whether to use cached responses (default: True)
        
    Returns:
        JSON string containing detailed study information
    """
    try:
        client = ClinicalTrialsAPIClient()
        study = client.get_study(nct_id, use_cache=use_cache)
        
        return json.dumps({
            "status": "success",
            "nct_id": nct_id,
            "study": study,
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "nct_id": nct_id,
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }, indent=2)


class QueryBuilder:
    """Helper class for building ClinicalTrials.gov API queries."""
    
    FIELD_MAPPINGS = {
        "condition": "Condition",
        "intervention": "Intervention",
        "title": "BriefTitle",
        "sponsor": "Sponsor",
        "location": "LocationFacility",
        "country": "LocationCountry",
        "status": "OverallStatus",
        "phase": "Phase",
        "study_type": "StudyType",
        "gender": "Gender",
        "age": "MinimumAge,MaximumAge",
        "start_date": "StartDate",
        "completion_date": "CompletionDate",
        "results_first_posted": "ResultsFirstPostDate"
    }
    
    @staticmethod
    def build_query(params: Dict[str, Any]) -> str:
        """
        Build a query string from a dictionary of parameters.
        
        Args:
            params: Dictionary of search parameters
            
        Returns:
            Formatted query string for ClinicalTrials.gov API
        """
        query_parts = []
        
        for key, value in params.items():
            if not value:
                continue
                
            field = QueryBuilder.FIELD_MAPPINGS.get(key.lower(), key)
            
            if isinstance(value, list):
                # Handle list values (OR condition)
                value_parts = [f'"{v}"' for v in value]
                query_parts.append(f"{field}:{' OR '.join(value_parts)}")
            else:
                # Handle single values
                query_parts.append(f'{field}:"{value}"')
        
        return " AND ".join(query_parts)
    
    @staticmethod
    def parse_natural_language(text: str) -> Dict[str, Any]:
        """
        Parse natural language query to extract structured search parameters.
        This is a simplified implementation that would need to be enhanced with NLP.
        
        Args:
            text: Natural language query text
            
        Returns:
            Dictionary of extracted search parameters
        """
        params = {}
        
        # Extract condition (simplified approach)
        condition_keywords = ["condition", "disease", "disorder", "indication"]
        for keyword in condition_keywords:
            if keyword in text.lower():
                # Very simplified extraction - would need more sophisticated NLP
                parts = text.lower().split(keyword + ":")
                if len(parts) > 1:
                    condition = parts[1].split(",")[0].strip()
                    params["condition"] = condition
                    break
        
        # Extract intervention (simplified approach)
        intervention_keywords = ["intervention", "treatment", "drug", "therapy", "device"]
        for keyword in intervention_keywords:
            if keyword in text.lower():
                parts = text.lower().split(keyword + ":")
                if len(parts) > 1:
                    intervention = parts[1].split(",")[0].strip()
                    params["intervention"] = intervention
                    break
        
        # Extract phase
        if "phase" in text.lower():
            for phase in ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]:
                if phase.lower() in text.lower():
                    params["phase"] = phase
                    break
        
        # Extract status
        status_keywords = ["recruiting", "completed", "active", "not recruiting", "terminated"]
        for status in status_keywords:
            if status in text.lower():
                params["status"] = status.title()
                break
        
        return params


@tool
def build_clinical_trials_query(natural_language_query: str = None, 
                               structured_params: Dict[str, Any] = None) -> str:
    """
    Build a structured query for ClinicalTrials.gov API from natural language or parameters.
    
    Args:
        natural_language_query: Natural language description of the search
        structured_params: Dictionary of structured search parameters
        
    Returns:
        JSON string containing the built query and parameters
    """
    try:
        if not natural_language_query and not structured_params:
            return json.dumps({
                "status": "error",
                "error_message": "Either natural_language_query or structured_params must be provided",
                "timestamp": datetime.now().isoformat()
            }, indent=2)
        
        params = {}
        
        # Parse natural language if provided
        if natural_language_query:
            params = QueryBuilder.parse_natural_language(natural_language_query)
        
        # Override with structured params if provided
        if structured_params:
            params.update(structured_params)
        
        # Build the query string
        query_string = QueryBuilder.build_query(params)
        
        return json.dumps({
            "status": "success",
            "query_string": query_string,
            "extracted_params": params,
            "natural_language_query": natural_language_query,
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }, indent=2)


class ResultsParser:
    """Parser for ClinicalTrials.gov API results."""
    
    @staticmethod
    def extract_key_information(study: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract key information from a study record.
        
        Args:
            study: Study data from API response
            
        Returns:
            Dictionary containing key study information
        """
        protocol_section = study.get("protocolSection", {})
        derived_section = study.get("derivedSection", {})
        
        # Extract identification information
        identification = protocol_section.get("identificationModule", {})
        nct_id = identification.get("nctId", "")
        title = identification.get("briefTitle", "")
        official_title = identification.get("officialTitle", "")
        
        # Extract status information
        status_module = protocol_section.get("statusModule", {})
        status = status_module.get("overallStatus", "")
        why_stopped = status_module.get("whyStopped", "")
        start_date = status_module.get("startDateStruct", {}).get("date", "")
        completion_date = status_module.get("completionDateStruct", {}).get("date", "")
        
        # Extract sponsor information
        sponsor_module = protocol_section.get("sponsorCollaboratorsModule", {})
        lead_sponsor = sponsor_module.get("leadSponsor", {}).get("name", "")
        
        # Extract conditions
        conditions_module = protocol_section.get("conditionsModule", {})
        conditions = conditions_module.get("conditions", [])
        
        # Extract interventions
        arms_module = protocol_section.get("armsInterventionsModule", {})
        interventions = arms_module.get("interventions", [])
        intervention_names = [i.get("name", "") for i in interventions]
        
        # Extract eligibility criteria
        eligibility_module = protocol_section.get("eligibilityModule", {})
        eligibility_criteria = eligibility_module.get("eligibilityCriteria", "")
        gender = eligibility_module.get("gender", "")
        min_age = eligibility_module.get("minimumAge", "")
        max_age = eligibility_module.get("maximumAge", "")
        
        # Extract phase
        design_module = protocol_section.get("designModule", {})
        phase = design_module.get("phases", [])
        
        # Extract study type
        study_type = design_module.get("studyType", "")
        
        # Extract locations
        contacts_module = protocol_section.get("contactsLocationsModule", {})
        locations = contacts_module.get("locations", [])
        location_names = [l.get("facility", {}).get("name", "") for l in locations]
        countries = list(set(l.get("country", "") for l in locations if "country" in l))
        
        # Extract results information
        has_results = derived_section.get("hasResults", False)
        
        return {
            "nct_id": nct_id,
            "title": title,
            "official_title": official_title,
            "status": status,
            "why_stopped": why_stopped if why_stopped else None,
            "start_date": start_date,
            "completion_date": completion_date,
            "lead_sponsor": lead_sponsor,
            "conditions": conditions,
            "interventions": intervention_names,
            "eligibility_criteria": eligibility_criteria,
            "gender": gender,
            "age_range": f"{min_age} - {max_age}" if min_age and max_age else None,
            "phase": phase,
            "study_type": study_type,
            "locations": location_names,
            "countries": countries,
            "has_results": has_results
        }
    
    @staticmethod
    def parse_studies(studies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse a list of studies to extract key information.
        
        Args:
            studies: List of study data from API response
            
        Returns:
            List of dictionaries containing key information for each study
        """
        return [ResultsParser.extract_key_information(study) for study in studies]


@tool
def parse_clinical_trials_results(results_json: str) -> str:
    """
    Parse and extract key information from ClinicalTrials.gov API results.
    
    Args:
        results_json: JSON string containing API results (from clinical_trials_search)
        
    Returns:
        JSON string containing parsed and structured results
    """
    try:
        results = json.loads(results_json)
        
        if results.get("status") != "success":
            return json.dumps({
                "status": "error",
                "error_message": "Invalid results JSON or error in original results",
                "original_error": results.get("error_message", "Unknown error"),
                "timestamp": datetime.now().isoformat()
            }, indent=2)
        
        studies = results.get("results", [])
        parsed_studies = ResultsParser.parse_studies(studies)
        
        return json.dumps({
            "status": "success",
            "query": results.get("query", ""),
            "total_count": results.get("total_count", 0),
            "parsed_results": parsed_studies,
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }, indent=2)


class ResultsAnalyzer:
    """Analyzer for clinical trial search results."""
    
    @staticmethod
    def evaluate_relevance(study: Dict[str, Any], query_terms: List[str]) -> float:
        """
        Evaluate the relevance of a study to the query terms.
        
        Args:
            study: Study data
            query_terms: List of query terms
            
        Returns:
            Relevance score between 0 and 1
        """
        if not query_terms:
            return 1.0
            
        # Convert query terms to lowercase for case-insensitive matching
        query_terms_lower = [term.lower() for term in query_terms]
        
        # Fields to check for relevance
        text_fields = [
            study.get("title", ""),
            study.get("official_title", ""),
            " ".join(study.get("conditions", [])),
            " ".join(study.get("interventions", []))
        ]
        
        # Combine all text fields into a single string and convert to lowercase
        combined_text = " ".join(text_fields).lower()
        
        # Count how many query terms appear in the combined text
        matches = sum(1 for term in query_terms_lower if term in combined_text)
        
        # Calculate relevance score
        if not query_terms:
            return 1.0
        return matches / len(query_terms)
    
    @staticmethod
    def identify_duplicates(studies: List[Dict[str, Any]]) -> List[List[str]]:
        """
        Identify potential duplicate studies based on title and other criteria.
        
        Args:
            studies: List of study data
            
        Returns:
            List of lists containing NCT IDs of potential duplicate groups
        """
        # Group studies by normalized title
        title_groups = {}
        for study in studies:
            title = study.get("title", "").lower().strip()
            if title:
                if title not in title_groups:
                    title_groups[title] = []
                title_groups[title].append(study.get("nct_id"))
        
        # Return groups with more than one study
        return [group for group in title_groups.values() if len(group) > 1]
    
    @staticmethod
    def identify_conflicts(studies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify potential conflicts in study data.
        
        Args:
            studies: List of study data
            
        Returns:
            List of dictionaries describing potential conflicts
        """
        conflicts = []
        
        # Group studies by condition
        condition_groups = {}
        for study in studies:
            for condition in study.get("conditions", []):
                condition = condition.lower().strip()
                if condition:
                    if condition not in condition_groups:
                        condition_groups[condition] = []
                    condition_groups[condition].append(study)
        
        # Check for conflicting phases for the same condition and intervention
        for condition, condition_studies in condition_groups.items():
            # Group by intervention
            intervention_groups = {}
            for study in condition_studies:
                for intervention in study.get("interventions", []):
                    intervention = intervention.lower().strip()
                    if intervention:
                        if intervention not in intervention_groups:
                            intervention_groups[intervention] = []
                        intervention_groups[intervention].append(study)
            
            # Check for conflicts within each intervention group
            for intervention, int_studies in intervention_groups.items():
                if len(int_studies) > 1:
                    # Check for phase conflicts
                    phases = {}
                    for study in int_studies:
                        for phase in study.get("phase", []):
                            if phase not in phases:
                                phases[phase] = []
                            phases[phase].append(study.get("nct_id"))
                    
                    if len(phases) > 1:
                        conflicts.append({
                            "type": "phase_conflict",
                            "condition": condition,
                            "intervention": intervention,
                            "phases": phases
                        })
        
        return conflicts


@tool
def analyze_clinical_trials_results(parsed_results_json: str, query_terms: List[str] = None) -> str:
    """
    Analyze clinical trial results for relevance, duplicates, and conflicts.
    
    Args:
        parsed_results_json: JSON string containing parsed results (from parse_clinical_trials_results)
        query_terms: List of query terms to evaluate relevance against
        
    Returns:
        JSON string containing analysis results
    """
    try:
        results = json.loads(parsed_results_json)
        
        if results.get("status") != "success":
            return json.dumps({
                "status": "error",
                "error_message": "Invalid results JSON or error in original results",
                "original_error": results.get("error_message", "Unknown error"),
                "timestamp": datetime.now().isoformat()
            }, indent=2)
        
        studies = results.get("parsed_results", [])
        
        # Evaluate relevance for each study
        for study in studies:
            study["relevance_score"] = ResultsAnalyzer.evaluate_relevance(study, query_terms or [])
        
        # Sort studies by relevance score
        sorted_studies = sorted(studies, key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        # Identify potential duplicates
        duplicate_groups = ResultsAnalyzer.identify_duplicates(studies)
        
        # Identify potential conflicts
        conflicts = ResultsAnalyzer.identify_conflicts(studies)
        
        return json.dumps({
            "status": "success",
            "query": results.get("query", ""),
            "total_count": len(studies),
            "analyzed_results": sorted_studies,
            "potential_duplicates": duplicate_groups,
            "potential_conflicts": conflicts,
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }, indent=2)


class ResultsIntegrator:
    """Integrator for multiple clinical trial search results."""
    
    @staticmethod
    def merge_results(result_sets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple result sets into a single integrated result.
        
        Args:
            result_sets: List of result set dictionaries
            
        Returns:
            Integrated results dictionary
        """
        all_studies = {}
        queries = []
        
        # Collect all studies and queries
        for result_set in result_sets:
            if result_set.get("status") != "success":
                continue
                
            studies = result_set.get("analyzed_results", [])
            query = result_set.get("query", "")
            
            if query and query not in queries:
                queries.append(query)
            
            # Add studies to the combined dictionary, using NCT ID as key to avoid duplicates
            for study in studies:
                nct_id = study.get("nct_id")
                if not nct_id:
                    continue
                    
                if nct_id in all_studies:
                    # Update relevance score if the new one is higher
                    current_score = all_studies[nct_id].get("relevance_score", 0)
                    new_score = study.get("relevance_score", 0)
                    if new_score > current_score:
                        all_studies[nct_id]["relevance_score"] = new_score
                        
                    # Add query reference if not already present
                    if "query_references" not in all_studies[nct_id]:
                        all_studies[nct_id]["query_references"] = []
                    
                    if query and query not in all_studies[nct_id]["query_references"]:
                        all_studies[nct_id]["query_references"].append(query)
                else:
                    # Add new study
                    all_studies[nct_id] = study
                    
                    # Initialize query references
                    all_studies[nct_id]["query_references"] = [query] if query else []
        
        # Convert back to a list and sort by relevance
        integrated_studies = list(all_studies.values())
        integrated_studies.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return {
            "integrated_studies": integrated_studies,
            "queries": queries,
            "total_count": len(integrated_studies)
        }


@tool
def integrate_clinical_trials_results(result_json_list: List[str]) -> str:
    """
    Integrate multiple clinical trial search results into a comprehensive result set.
    
    Args:
        result_json_list: List of JSON strings containing analyzed results
        
    Returns:
        JSON string containing integrated results
    """
    try:
        # Parse each result JSON
        result_sets = []
        for result_json in result_json_list:
            try:
                result = json.loads(result_json)
                result_sets.append(result)
            except json.JSONDecodeError:
                continue
        
        if not result_sets:
            return json.dumps({
                "status": "error",
                "error_message": "No valid result sets provided",
                "timestamp": datetime.now().isoformat()
            }, indent=2)
        
        # Integrate the results
        integrated_results = ResultsIntegrator.merge_results(result_sets)
        
        return json.dumps({
            "status": "success",
            "queries": integrated_results.get("queries", []),
            "total_count": integrated_results.get("total_count", 0),
            "integrated_results": integrated_results.get("integrated_studies", []),
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }, indent=2)


class ClinicalReportGenerator:
    """Generator for clinical development reports based on trial data."""
    
    @staticmethod
    def generate_summary_report(studies: List[Dict[str, Any]], query: str = None) -> Dict[str, Any]:
        """
        Generate a summary report for clinical development.
        
        Args:
            studies: List of study data
            query: Original query string
            
        Returns:
            Dictionary containing the summary report
        """
        if not studies:
            return {
                "title": "Clinical Trials Summary Report",
                "query": query or "Unknown query",
                "summary": "No studies found matching the criteria.",
                "date_generated": datetime.now().isoformat(),
                "sections": []
            }
        
        # Count studies by phase
        phase_counts = {}
        for study in studies:
            phases = study.get("phase", [])
            for phase in phases:
                if phase not in phase_counts:
                    phase_counts[phase] = 0
                phase_counts[phase] += 1
        
        # Count studies by status
        status_counts = {}
        for study in studies:
            status = study.get("status", "Unknown")
            if status not in status_counts:
                status_counts[status] = 0
            status_counts[status] += 1
        
        # Count studies by sponsor type (simplified)
        sponsor_types = {"Industry": 0, "Academic/Government": 0, "Other": 0}
        for study in studies:
            sponsor = study.get("lead_sponsor", "").lower()
            if any(term in sponsor for term in ["inc", "corp", "ltd", "llc", "pharmaceutical", "pharma"]):
                sponsor_types["Industry"] += 1
            elif any(term in sponsor for term in ["university", "college", "institute", "hospital", "clinic", "foundation", "gov"]):
                sponsor_types["Academic/Government"] += 1
            else:
                sponsor_types["Other"] += 1
        
        # Collect all conditions and interventions
        all_conditions = []
        all_interventions = []
        for study in studies:
            all_conditions.extend(study.get("conditions", []))
            all_interventions.extend(study.get("interventions", []))
        
        # Count frequency of each condition and intervention
        condition_counts = {}
        for condition in all_conditions:
            if condition not in condition_counts:
                condition_counts[condition] = 0
            condition_counts[condition] += 1
        
        intervention_counts = {}
        for intervention in all_interventions:
            if intervention not in intervention_counts:
                intervention_counts[intervention] = 0
            intervention_counts[intervention] += 1
        
        # Sort by frequency
        top_conditions = sorted(condition_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_interventions = sorted(intervention_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Generate report sections
        sections = [
            {
                "title": "Overview",
                "content": f"This report summarizes {len(studies)} clinical trials related to the query: '{query or 'Not specified'}'. The trials span various phases and statuses, with detailed breakdowns provided in the following sections."
            },
            {
                "title": "Trial Phases",
                "content": "Distribution of trials by phase:",
                "data": phase_counts
            },
            {
                "title": "Trial Status",
                "content": "Distribution of trials by status:",
                "data": status_counts
            },
            {
                "title": "Sponsor Types",
                "content": "Distribution of trials by sponsor type:",
                "data": sponsor_types
            },
            {
                "title": "Top Conditions",
                "content": "Most frequent conditions under study:",
                "data": dict(top_conditions)
            },
            {
                "title": "Top Interventions",
                "content": "Most frequent interventions under study:",
                "data": dict(top_interventions)
            },
            {
                "title": "Key Trials",
                "content": "Highlighted trials of interest:",
                "trials": studies[:5]  # Include top 5 most relevant trials
            }
        ]
        
        return {
            "title": "Clinical Trials Summary Report",
            "query": query or "Unknown query",
            "summary": f"Analysis of {len(studies)} clinical trials related to the specified criteria.",
            "date_generated": datetime.now().isoformat(),
            "sections": sections
        }
    
    @staticmethod
    def generate_detailed_report(studies: List[Dict[str, Any]], query: str = None) -> Dict[str, Any]:
        """
        Generate a detailed report for clinical development.
        
        Args:
            studies: List of study data
            query: Original query string
            
        Returns:
            Dictionary containing the detailed report
        """
        # Start with the summary report
        report = ClinicalReportGenerator.generate_summary_report(studies, query)
        
        if not studies:
            return report
        
        # Add additional detailed sections
        
        # Group studies by phase
        phase_groups = {}
        for study in studies:
            phases = study.get("phase", [])
            for phase in phases:
                if phase not in phase_groups:
                    phase_groups[phase] = []
                phase_groups[phase].append(study)
        
        # Add phase-specific sections
        phase_sections = []
        for phase, phase_studies in phase_groups.items():
            if not phase:
                continue
                
            phase_section = {
                "title": f"{phase} Trials",
                "content": f"Analysis of {len(phase_studies)} trials in {phase}:",
                "studies": [
                    {
                        "nct_id": s.get("nct_id"),
                        "title": s.get("title"),
                        "status": s.get("status"),
                        "sponsor": s.get("lead_sponsor"),
                        "conditions": s.get("conditions"),
                        "interventions": s.get("interventions")
                    }
                    for s in phase_studies[:10]  # Limit to top 10 per phase
                ]
            }
            phase_sections.append(phase_section)
        
        # Add detailed sections to the report
        report["detailed_sections"] = phase_sections
        
        # Add clinical development implications section
        report["sections"].append({
            "title": "Clinical Development Implications",
            "content": "Based on the analyzed trials, the following implications for clinical development can be drawn:",
            "implications": [
                "The distribution of trials across phases indicates the maturity of research in this area.",
                f"There are {status_counts.get('Recruiting', 0)} actively recruiting trials, suggesting ongoing research interest.",
                "The diversity of interventions suggests multiple therapeutic approaches are being explored.",
                "Consider the geographic distribution of trials when planning new studies to avoid oversaturation."
            ] if (status_counts := {s.get("status", "Unknown"): 0 for s in studies}) else []
        })
        
        return report


@tool
def generate_clinical_report(integrated_results_json: str, report_type: str = "summary") -> str:
    """
    Generate a clinical development report from integrated trial results.
    
    Args:
        integrated_results_json: JSON string containing integrated results
        report_type: Type of report to generate ("summary" or "detailed")
        
    Returns:
        JSON string containing the clinical development report
    """
    try:
        results = json.loads(integrated_results_json)
        
        if results.get("status") != "success":
            return json.dumps({
                "status": "error",
                "error_message": "Invalid results JSON or error in original results",
                "original_error": results.get("error_message", "Unknown error"),
                "timestamp": datetime.now().isoformat()
            }, indent=2)
        
        studies = results.get("integrated_results", [])
        queries = results.get("queries", [])
        query_str = ", ".join(queries) if queries else None
        
        # Generate the appropriate report
        if report_type.lower() == "detailed":
            report = ClinicalReportGenerator.generate_detailed_report(studies, query_str)
        else:
            report = ClinicalReportGenerator.generate_summary_report(studies, query_str)
        
        return json.dumps({
            "status": "success",
            "report": report,
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }, indent=2)


@tool
def get_clinical_trials_field_values(field: str) -> str:
    """
    Get all possible values for a specific field in ClinicalTrials.gov.
    
    Args:
        field: The field to get values for (e.g., "Phase", "OverallStatus", "StudyType")
        
    Returns:
        JSON string containing all possible values for the specified field
    """
    try:
        client = ClinicalTrialsAPIClient()
        field_values = client.get_field_values(field)
        
        return json.dumps({
            "status": "success",
            "field": field,
            "values": field_values.get("fieldValues", []),
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "field": field,
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }, indent=2)


@tool
def clear_clinical_trials_cache() -> str:
    """
    Clear the ClinicalTrials.gov API response cache.
    
    Returns:
        JSON string containing cache clearing result
    """
    try:
        cache_dir = ClinicalTrialsAPIClient.CACHE_DIR
        
        if not os.path.exists(cache_dir):
            return json.dumps({
                "status": "success",
                "message": "Cache directory does not exist, nothing to clear",
                "timestamp": datetime.now().isoformat()
            }, indent=2)
        
        # Count files before deletion
        files_before = [f for f in os.listdir(cache_dir) if f.endswith('.json')]
        file_count = len(files_before)
        
        # Delete all JSON files in the cache directory
        for filename in files_before:
            file_path = os.path.join(cache_dir, filename)
            try:
                os.remove(file_path)
            except OSError:
                pass
        
        return json.dumps({
            "status": "success",
            "message": f"Successfully cleared {file_count} cached responses",
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }, indent=2)