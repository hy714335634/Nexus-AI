"""
Cloud Resource Manager - handles AgentCore runtime and ECR resources

Provides functionality for:
- Detecting AgentCore runtime resources
- Detecting ECR repositories
- Deleting cloud resources
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AgentCoreRuntime:
    """AgentCore runtime information"""
    arn: str
    name: str
    status: str
    region: str


@dataclass
class ECRRepository:
    """ECR repository information"""
    repository_name: str
    repository_uri: str
    repository_arn: str
    image_count: int
    region: str


@dataclass
class CloudResources:
    """Container for cloud resources"""
    agentcore_runtime: Optional[AgentCoreRuntime] = None
    ecr_repository: Optional[ECRRepository] = None
    
    def has_resources(self) -> bool:
        """Check if any cloud resources exist"""
        return self.agentcore_runtime is not None or self.ecr_repository is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {}
        if self.agentcore_runtime:
            result['agentcore_runtime'] = {
                'arn': self.agentcore_runtime.arn,
                'name': self.agentcore_runtime.name,
                'status': self.agentcore_runtime.status,
                'region': self.agentcore_runtime.region,
            }
        if self.ecr_repository:
            result['ecr_repository'] = {
                'repository_name': self.ecr_repository.repository_name,
                'repository_uri': self.ecr_repository.repository_uri,
                'repository_arn': self.ecr_repository.repository_arn,
                'image_count': self.ecr_repository.image_count,
                'region': self.ecr_repository.region,
            }
        return result


@dataclass
class DeleteResult:
    """Result of delete operation"""
    success: bool
    resource_type: str
    resource_name: str
    error: Optional[str] = None


class CloudResourceManager:
    """Manages cloud resources for Nexus-AI agents"""
    
    def __init__(self, region: str = None):
        """
        Initialize cloud resource manager.
        
        Args:
            region: AWS region (default: from settings or us-west-2)
        """
        self.region = region or self._get_default_region()
        self._agentcore_client = None
        self._ecr_client = None
    
    @staticmethod
    def _get_default_region() -> str:
        """Get default region from settings"""
        try:
            from api.v2.config import settings
            return settings.AWS_REGION
        except ImportError:
            return 'us-west-2'
    
    def _get_agentcore_client(self):
        """Get or create AgentCore client"""
        if self._agentcore_client is None:
            import boto3
            self._agentcore_client = boto3.client(
                'bedrock-agentcore',
                region_name=self.region
            )
        return self._agentcore_client
    
    def _get_ecr_client(self):
        """Get or create ECR client"""
        if self._ecr_client is None:
            import boto3
            self._ecr_client = boto3.client('ecr', region_name=self.region)
        return self._ecr_client
    
    def detect_resources(self, agent_name: str) -> CloudResources:
        """
        Detect cloud resources for an agent.
        
        Args:
            agent_name: Name of the agent
        
        Returns:
            CloudResources object with detected resources
        """
        resources = CloudResources()
        
        # Detect AgentCore runtime
        runtime = self._detect_agentcore_runtime(agent_name)
        if runtime:
            resources.agentcore_runtime = runtime
        
        # Detect ECR repository
        ecr = self._detect_ecr_repository(agent_name)
        if ecr:
            resources.ecr_repository = ecr
        
        return resources
    
    def _detect_agentcore_runtime(self, agent_name: str) -> Optional[AgentCoreRuntime]:
        """Detect AgentCore runtime for an agent"""
        try:
            from botocore.exceptions import ClientError, NoCredentialsError
            
            client = self._get_agentcore_client()
            
            # List agent runtimes and find matching one
            paginator = client.get_paginator('list_agent_runtimes')
            for page in paginator.paginate():
                for runtime in page.get('agentRuntimeSummaries', []):
                    runtime_name = runtime.get('agentRuntimeName', '')
                    # Match by name (agent name may have suffix)
                    if agent_name in runtime_name or runtime_name.startswith(agent_name):
                        return AgentCoreRuntime(
                            arn=runtime.get('agentRuntimeArn', ''),
                            name=runtime_name,
                            status=runtime.get('status', 'UNKNOWN'),
                            region=self.region
                        )
            
            return None
            
        except (ImportError, Exception) as e:
            logger.debug(f"Failed to detect AgentCore runtime: {e}")
            return None
    
    def _detect_ecr_repository(self, agent_name: str) -> Optional[ECRRepository]:
        """Detect ECR repository for an agent"""
        try:
            from botocore.exceptions import ClientError, NoCredentialsError
            
            client = self._get_ecr_client()
            
            # Common ECR repository naming patterns
            repo_patterns = [
                f"nexus-ai/{agent_name}",
                f"nexus-ai-{agent_name}",
                agent_name
            ]
            
            for repo_name in repo_patterns:
                try:
                    response = client.describe_repositories(repositoryNames=[repo_name])
                    if response.get('repositories'):
                        repo = response['repositories'][0]
                        
                        # Get image count
                        images_response = client.list_images(repositoryName=repo_name)
                        image_count = len(images_response.get('imageIds', []))
                        
                        return ECRRepository(
                            repository_name=repo.get('repositoryName', ''),
                            repository_uri=repo.get('repositoryUri', ''),
                            repository_arn=repo.get('repositoryArn', ''),
                            image_count=image_count,
                            region=self.region
                        )
                except ClientError as e:
                    if e.response['Error']['Code'] != 'RepositoryNotFoundException':
                        raise
            
            return None
            
        except (ImportError, Exception) as e:
            logger.debug(f"Failed to detect ECR repository: {e}")
            return None
    
    def delete_agentcore_runtime(self, runtime: AgentCoreRuntime) -> DeleteResult:
        """
        Delete an AgentCore runtime.
        
        Args:
            runtime: AgentCoreRuntime to delete
        
        Returns:
            DeleteResult with operation status
        """
        try:
            from botocore.exceptions import ClientError
            
            client = self._get_agentcore_client()
            client.delete_agent_runtime(agentRuntimeArn=runtime.arn)
            
            return DeleteResult(
                success=True,
                resource_type='agentcore_runtime',
                resource_name=runtime.name
            )
            
        except Exception as e:
            logger.error(f"Failed to delete AgentCore runtime: {e}")
            return DeleteResult(
                success=False,
                resource_type='agentcore_runtime',
                resource_name=runtime.name,
                error=str(e)
            )
    
    def delete_ecr_repository(self, repository: ECRRepository, force: bool = True) -> DeleteResult:
        """
        Delete an ECR repository.
        
        Args:
            repository: ECRRepository to delete
            force: If True, delete even if repository contains images
        
        Returns:
            DeleteResult with operation status
        """
        try:
            from botocore.exceptions import ClientError
            
            client = self._get_ecr_client()
            client.delete_repository(
                repositoryName=repository.repository_name,
                force=force
            )
            
            return DeleteResult(
                success=True,
                resource_type='ecr_repository',
                resource_name=repository.repository_name
            )
            
        except Exception as e:
            logger.error(f"Failed to delete ECR repository: {e}")
            return DeleteResult(
                success=False,
                resource_type='ecr_repository',
                resource_name=repository.repository_name,
                error=str(e)
            )
    
    def delete_all_resources(self, resources: CloudResources) -> List[DeleteResult]:
        """
        Delete all cloud resources.
        
        Args:
            resources: CloudResources to delete
        
        Returns:
            List of DeleteResult for each resource
        """
        results = []
        
        if resources.agentcore_runtime:
            result = self.delete_agentcore_runtime(resources.agentcore_runtime)
            results.append(result)
        
        if resources.ecr_repository:
            result = self.delete_ecr_repository(resources.ecr_repository)
            results.append(result)
        
        return results
