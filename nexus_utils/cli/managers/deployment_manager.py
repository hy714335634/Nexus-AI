"""
Deployment Manager - handles agent deployment to AgentCore

Provides functionality for:
- Checking project status in DynamoDB
- Deploying agents to AgentCore
- Updating deployment status
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DeploymentStatus:
    """Deployment operation status"""
    success: bool
    agent_id: Optional[str] = None
    project_id: Optional[str] = None
    deployment_type: str = 'local'
    deployment_status: str = 'pending'
    agent_runtime_arn: Optional[str] = None
    agent_alias_arn: Optional[str] = None
    region: Optional[str] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class DeploymentManager:
    """Manages agent deployment to AgentCore"""
    
    def __init__(self, base_path: str = "."):
        """
        Initialize deployment manager.
        
        Args:
            base_path: Base path to Nexus-AI installation
        """
        self.base_path = Path(base_path).resolve()
        self._db_client = None
        self._deployment_service = None
    
    def _get_db_client(self):
        """Get DynamoDB client (lazy initialization)"""
        if self._db_client is None:
            from api.v2.database import db_client
            self._db_client = db_client
        return self._db_client
    
    def _get_deployment_service(self):
        """Get deployment service (lazy initialization)"""
        if self._deployment_service is None:
            from api.v2.services.agent_deployment_service import AgentDeploymentService
            self._deployment_service = AgentDeploymentService()
        return self._deployment_service
    
    def get_project_status(self, project_name: str) -> Dict[str, Any]:
        """
        Get project status from DynamoDB.
        
        Args:
            project_name: Name of the project
        
        Returns:
            Dict with project status information
        """
        result = {
            'found': False,
            'project_id': None,
            'project_name': project_name,
            'status': None,
            'current_stage': None,
            'agent_id': None,
            'deployment_type': None,
            'deployment_status': None,
            'error': None
        }
        
        try:
            db = self._get_db_client()
            
            # Search for project by name
            projects = db.list_projects(limit=100)
            project = None
            for p in projects.get('items', []):
                if p.get('project_name') == project_name:
                    project = p
                    break
            
            if not project:
                # Try using project_name as project_id
                project = db.get_project(project_name)
                if not project:
                    # Try with proj_ prefix
                    project = db.get_project(f"proj_{project_name}")
            
            if project:
                result['found'] = True
                result['project_id'] = project.get('project_id')
                result['status'] = project.get('status')
                result['current_stage'] = project.get('current_stage')
                
                # Get agent info if available
                agent_id = project.get('agent_id')
                if agent_id:
                    result['agent_id'] = agent_id
                    agent = db.get_agent(agent_id)
                    if agent:
                        result['deployment_type'] = agent.get('deployment_type')
                        result['deployment_status'] = agent.get('deployment_status')
                        result['agent_runtime_arn'] = agent.get('agentcore_runtime_arn')
                        result['agent_status'] = agent.get('status')
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Failed to get project status: {e}")
        
        return result
    
    def check_project_ready(self, project_name: str) -> Dict[str, Any]:
        """
        Check if project is ready for deployment.
        
        Args:
            project_name: Name of the project
        
        Returns:
            Dict with readiness check results
        """
        result = {
            'ready': False,
            'project_exists': False,
            'has_agent_script': False,
            'has_config': False,
            'has_requirements': False,
            'issues': [],
            'project_dir': None
        }
        
        project_dir = self.base_path / "projects" / project_name
        result['project_dir'] = str(project_dir)
        
        # Check project directory exists
        if not project_dir.exists():
            result['issues'].append(f"Project directory not found: {project_dir}")
            return result
        
        result['project_exists'] = True
        
        # Check for project_config.json
        config_path = project_dir / "project_config.json"
        if config_path.exists():
            result['has_config'] = True
        else:
            result['issues'].append("Missing project_config.json")
        
        # Check for requirements.txt
        requirements_path = project_dir / "requirements.txt"
        if requirements_path.exists():
            result['has_requirements'] = True
        else:
            result['issues'].append("Missing requirements.txt (will be auto-generated)")
        
        # Check for agent script in agents directory
        agents_dir = project_dir / "agents"
        if agents_dir.exists():
            agent_dirs = [d for d in agents_dir.iterdir() if d.is_dir()]
            if agent_dirs:
                # Check for agent code developer output
                for agent_dir in agent_dirs:
                    code_json = agent_dir / "agent_code_developer.json"
                    if code_json.exists():
                        result['has_agent_script'] = True
                        break
                
                if not result['has_agent_script']:
                    result['issues'].append("No agent_code_developer.json found in agent directories")
            else:
                result['issues'].append("No agent directories found")
        else:
            # Check generated_agents directory
            generated_dir = self.base_path / "agents" / "generated_agents" / project_name
            if generated_dir.exists():
                py_files = list(generated_dir.glob("*.py"))
                if py_files:
                    result['has_agent_script'] = True
                else:
                    result['issues'].append("No Python files in generated_agents directory")
            else:
                result['issues'].append("No agents directory found")
        
        # Determine if ready
        result['ready'] = (
            result['project_exists'] and 
            (result['has_config'] or result['has_agent_script'])
        )
        
        return result
    
    def deploy_to_agentcore(
        self,
        project_name: str,
        region: Optional[str] = None,
        dry_run: bool = False
    ) -> DeploymentStatus:
        """
        Deploy agent to AgentCore.
        
        Args:
            project_name: Name of the project to deploy
            region: AWS region for deployment (optional)
            dry_run: If True, only validate without deploying
        
        Returns:
            DeploymentStatus with deployment results
        """
        # Check project readiness
        readiness = self.check_project_ready(project_name)
        if not readiness['ready']:
            return DeploymentStatus(
                success=False,
                error=f"Project not ready for deployment: {'; '.join(readiness['issues'])}"
            )
        
        if dry_run:
            return DeploymentStatus(
                success=True,
                deployment_status='dry_run',
                details={
                    'message': 'Dry run completed successfully',
                    'project_dir': readiness['project_dir'],
                    'has_config': readiness['has_config'],
                    'has_agent_script': readiness['has_agent_script'],
                    'has_requirements': readiness['has_requirements']
                }
            )
        
        try:
            # Get project status from DynamoDB
            project_status = self.get_project_status(project_name)
            project_id = project_status.get('project_id')
            
            # Use deployment service
            service = self._get_deployment_service()
            result = service.deploy_to_agentcore(
                project_name=project_name,
                project_id=project_id,
                region=region
            )
            
            return DeploymentStatus(
                success=True,
                agent_id=result.agent_id,
                project_id=result.project_id,
                deployment_type=result.deployment_type,
                deployment_status=result.deployment_status,
                agent_runtime_arn=result.details.get('agent_runtime_arn'),
                agent_alias_arn=result.details.get('agent_alias_arn'),
                region=result.details.get('region'),
                details=result.details
            )
            
        except Exception as e:
            logger.exception(f"Deployment failed for {project_name}")
            return DeploymentStatus(
                success=False,
                error=str(e)
            )
    
    def update_project_status(
        self,
        project_id: str,
        status: str,
        **kwargs
    ) -> bool:
        """
        Update project status in DynamoDB.
        
        Args:
            project_id: Project ID
            status: New status
            **kwargs: Additional fields to update
        
        Returns:
            True if successful
        """
        try:
            db = self._get_db_client()
            updates = {'status': status}
            updates.update(kwargs)
            db.update_project(project_id, updates)
            return True
        except Exception as e:
            logger.error(f"Failed to update project status: {e}")
            return False
