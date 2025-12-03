"""AWS ECR adapter for repository management"""

import json
import subprocess
from typing import Dict, Any, Optional, Tuple


class ECRAdapter:
    """Adapter for AWS ECR operations using boto3 (preferred) or AWS CLI (fallback)"""
    
    def __init__(self):
        self.aws_cmd = "aws"
        self._boto3_client = None
        self._use_boto3 = self._check_boto3_available()
    
    def _check_boto3_available(self) -> bool:
        """Check if boto3 is available"""
        try:
            import boto3
            return True
        except ImportError:
            return False
    
    def _get_ecr_client(self, region: str):
        """Get or create boto3 ECR client
        
        Args:
            region: AWS region
            
        Returns:
            boto3 ECR client
        """
        try:
            import boto3
            return boto3.client('ecr', region_name=region)
        except Exception as e:
            raise RuntimeError(f"Failed to create boto3 ECR client: {str(e)}")
    
    def is_aws_cli_available(self) -> bool:
        """Check if AWS CLI is installed"""
        try:
            result = subprocess.run(
                [self.aws_cmd, "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def parse_ecr_uri(self, uri: str) -> Optional[Dict[str, str]]:
        """Parse ECR URI to extract components
        
        Args:
            uri: ECR URI (e.g., 123456.dkr.ecr.us-west-2.amazonaws.com/repo-name)
            
        Returns:
            Dict with account_id, region, repository_name or None if not ECR
        """
        if '.dkr.ecr.' not in uri or '.amazonaws.com' not in uri:
            return None
        
        try:
            # Format: account_id.dkr.ecr.region.amazonaws.com/repository_name
            parts = uri.split('/')
            if len(parts) < 2:
                return None
            
            registry_parts = parts[0].split('.')
            if len(registry_parts) < 5:
                return None
            
            account_id = registry_parts[0]
            region = registry_parts[3]
            repository_name = '/'.join(parts[1:])  # Handle nested repos
            
            # Remove tag if present
            if ':' in repository_name:
                repository_name = repository_name.split(':')[0]
            
            return {
                'account_id': account_id,
                'region': region,
                'repository_name': repository_name
            }
        except Exception:
            return None
    
    def repository_exists(self, repository_name: str, region: str) -> bool:
        """Check if ECR repository exists
        
        Args:
            repository_name: Name of the repository
            region: AWS region
            
        Returns:
            True if repository exists, False otherwise
        """
        if self._use_boto3:
            try:
                client = self._get_ecr_client(region)
                client.describe_repositories(repositoryNames=[repository_name])
                return True
            except client.exceptions.RepositoryNotFoundException:
                return False
            except Exception:
                return False
        else:
            # Fallback to AWS CLI
            try:
                result = subprocess.run(
                    [
                        self.aws_cmd, "ecr", "describe-repositories",
                        "--repository-names", repository_name,
                        "--region", region
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                return result.returncode == 0
            except Exception:
                return False
    
    def create_repository(
        self,
        repository_name: str,
        region: str,
        image_scanning: bool = True,
        encryption_type: str = "AES256",
        tags: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, str]:
        """Create ECR repository
        
        Args:
            repository_name: Name of the repository
            region: AWS region
            image_scanning: Enable image scanning on push
            encryption_type: Encryption type (AES256 or KMS)
            tags: Optional tags for the repository
            
        Returns:
            Tuple of (success, message)
        """
        if self._use_boto3:
            try:
                client = self._get_ecr_client(region)
                
                # Prepare parameters
                params = {
                    'repositoryName': repository_name,
                    'imageScanningConfiguration': {
                        'scanOnPush': image_scanning
                    },
                    'encryptionConfiguration': {
                        'encryptionType': encryption_type
                    }
                }
                
                # Add tags if provided
                if tags:
                    params['tags'] = [
                        {'Key': k, 'Value': v} for k, v in tags.items()
                    ]
                
                # Create repository
                response = client.create_repository(**params)
                return True, f"Repository '{repository_name}' created successfully"
                
            except client.exceptions.RepositoryAlreadyExistsException:
                return True, f"Repository '{repository_name}' already exists"
            except Exception as e:
                return False, f"Failed to create repository: {str(e)}"
        else:
            # Fallback to AWS CLI
            try:
                cmd = [
                    self.aws_cmd, "ecr", "create-repository",
                    "--repository-name", repository_name,
                    "--region", region
                ]
                
                # Add image scanning configuration
                if image_scanning:
                    cmd.extend([
                        "--image-scanning-configuration",
                        "scanOnPush=true"
                    ])
                
                # Add encryption configuration
                cmd.extend([
                    "--encryption-configuration",
                    f"encryptionType={encryption_type}"
                ])
                
                # Add tags if provided
                if tags:
                    tag_list = [f"Key={k},Value={v}" for k, v in tags.items()]
                    cmd.extend(["--tags"] + tag_list)
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    return True, f"Repository '{repository_name}' created successfully"
                else:
                    error_msg = result.stderr.strip()
                    return False, f"Failed to create repository: {error_msg}"
            
            except subprocess.TimeoutExpired:
                return False, "Repository creation timed out"
            except Exception as e:
                return False, f"Error creating repository: {str(e)}"
    
    def set_lifecycle_policy(
        self,
        repository_name: str,
        region: str,
        max_image_count: int = 100
    ) -> Tuple[bool, str]:
        """Set lifecycle policy to limit number of images
        
        Args:
            repository_name: Name of the repository
            region: AWS region
            max_image_count: Maximum number of images to keep
            
        Returns:
            Tuple of (success, message)
        """
        policy = {
            "rules": [
                {
                    "rulePriority": 1,
                    "description": f"Keep only {max_image_count} images",
                    "selection": {
                        "tagStatus": "any",
                        "countType": "imageCountMoreThan",
                        "countNumber": max_image_count
                    },
                    "action": {
                        "type": "expire"
                    }
                }
            ]
        }
        
        if self._use_boto3:
            try:
                client = self._get_ecr_client(region)
                client.put_lifecycle_policy(
                    repositoryName=repository_name,
                    lifecyclePolicyText=json.dumps(policy)
                )
                return True, "Lifecycle policy set successfully"
            except Exception as e:
                return False, f"Failed to set lifecycle policy: {str(e)}"
        else:
            # Fallback to AWS CLI
            try:
                result = subprocess.run(
                    [
                        self.aws_cmd, "ecr", "put-lifecycle-policy",
                        "--repository-name", repository_name,
                        "--region", region,
                        "--lifecycle-policy-text", json.dumps(policy)
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    return True, "Lifecycle policy set successfully"
                else:
                    return False, f"Failed to set lifecycle policy: {result.stderr}"
            
            except Exception as e:
                return False, f"Error setting lifecycle policy: {str(e)}"
    
    def get_repository_uri(
        self,
        repository_name: str,
        region: str
    ) -> Optional[str]:
        """Get repository URI
        
        Args:
            repository_name: Name of the repository
            region: AWS region
            
        Returns:
            Repository URI or None if not found
        """
        if self._use_boto3:
            try:
                client = self._get_ecr_client(region)
                response = client.describe_repositories(
                    repositoryNames=[repository_name]
                )
                repositories = response.get('repositories', [])
                if repositories:
                    return repositories[0].get('repositoryUri')
                return None
            except Exception:
                return None
        else:
            # Fallback to AWS CLI
            try:
                result = subprocess.run(
                    [
                        self.aws_cmd, "ecr", "describe-repositories",
                        "--repository-names", repository_name,
                        "--region", region,
                        "--output", "json"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    repositories = data.get('repositories', [])
                    if repositories:
                        return repositories[0].get('repositoryUri')
                
                return None
            except Exception:
                return None
    
    def ensure_repository_exists(
        self,
        image_uri: str,
        auto_create: bool = True,
        **create_options
    ) -> Tuple[bool, str]:
        """Ensure ECR repository exists, create if needed
        
        Args:
            image_uri: Full image URI
            auto_create: Whether to auto-create if not exists
            **create_options: Options for repository creation
            
        Returns:
            Tuple of (success, message)
        """
        # Parse ECR URI
        ecr_info = self.parse_ecr_uri(image_uri)
        if not ecr_info:
            return True, "Not an ECR URI, skipping repository check"
        
        repository_name = ecr_info['repository_name']
        region = ecr_info['region']
        
        # Check if repository exists
        if self.repository_exists(repository_name, region):
            return True, f"Repository '{repository_name}' already exists"
        
        # Create if auto_create is enabled
        if not auto_create:
            return False, f"Repository '{repository_name}' does not exist and auto-create is disabled"
        
        # Check if boto3 or AWS CLI is available
        if not self._use_boto3 and not self.is_aws_cli_available():
            return False, (
                "Neither boto3 nor AWS CLI is available. "
                "Please install boto3 (pip install boto3) or AWS CLI to auto-create ECR repositories."
            )
        
        # Extract lifecycle options (not passed to create_repository)
        lifecycle_enabled = create_options.pop('set_lifecycle_policy', True)
        max_images = create_options.pop('max_image_count', 100)
        
        # Create repository
        success, message = self.create_repository(
            repository_name=repository_name,
            region=region,
            **create_options
        )
        
        if success:
            # Optionally set lifecycle policy
            if lifecycle_enabled:
                self.set_lifecycle_policy(repository_name, region, max_images)
        
        return success, message
    
    def get_login_command(self, region: str) -> Optional[str]:
        """Get ECR login password
        
        Args:
            region: AWS region
            
        Returns:
            Login password or None if failed
        """
        if self._use_boto3:
            try:
                client = self._get_ecr_client(region)
                response = client.get_authorization_token()
                if response.get('authorizationData'):
                    import base64
                    token = response['authorizationData'][0]['authorizationToken']
                    # Decode base64 token (format is "AWS:password")
                    decoded = base64.b64decode(token).decode('utf-8')
                    password = decoded.split(':')[1]
                    return password
                return None
            except Exception:
                return None
        else:
            # Fallback to AWS CLI
            try:
                result = subprocess.run(
                    [
                        self.aws_cmd, "ecr", "get-login-password",
                        "--region", region
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    password = result.stdout.strip()
                    return password
                
                return None
            except Exception:
                return None
