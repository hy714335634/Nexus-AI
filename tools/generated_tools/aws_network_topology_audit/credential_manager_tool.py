"""
AWS Network Topology Visualizer - Credential Manager Tool

This module provides tools for securely managing AWS credentials,
supporting various authentication methods and cross-account access.
"""

from typing import Dict, List, Optional, Any, Union
import os
import json
import logging
import boto3
import base64
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound
from strands import tool

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Cache directory
CACHE_DIR = os.path.join(".cache", "aws_network_topology_visualizer")
os.makedirs(CACHE_DIR, exist_ok=True)

@tool
def validate_aws_credentials(
    profile_name: Optional[str] = None,
    region_name: Optional[str] = None,
    access_key_id: Optional[str] = None,
    secret_access_key: Optional[str] = None,
    session_token: Optional[str] = None,
    test_service: str = "sts"
) -> Dict[str, Any]:
    """
    Validate AWS credentials by testing authentication with a specified service.
    
    This tool validates AWS credentials by attempting to authenticate with a specified
    AWS service, and returns information about the authenticated identity.
    
    Args:
        profile_name: AWS profile name from ~/.aws/credentials. If provided, other credential parameters are ignored.
        region_name: AWS region name (e.g., 'us-east-1'). If None, uses default region.
        access_key_id: AWS access key ID. Required if profile_name is not provided.
        secret_access_key: AWS secret access key. Required if profile_name is not provided.
        session_token: AWS session token for temporary credentials (optional).
        test_service: AWS service to use for testing authentication (default: "sts")
        
    Returns:
        Dictionary with validation results:
        {
            "status": "success" or "error",
            "authenticated": whether authentication was successful,
            "identity": information about the authenticated identity (if successful),
            "account_id": AWS account ID (if successful),
            "user_id": AWS user ID (if successful),
            "arn": ARN of the authenticated identity (if successful),
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "authenticated": False
        }
        
        # Create session based on provided credentials
        if profile_name:
            try:
                session = boto3.Session(profile_name=profile_name, region_name=region_name)
            except ProfileNotFound:
                return {
                    "status": "error",
                    "authenticated": False,
                    "error": f"AWS profile '{profile_name}' not found. Check your ~/.aws/credentials file."
                }
        elif access_key_id and secret_access_key:
            session = boto3.Session(
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                aws_session_token=session_token,
                region_name=region_name
            )
        else:
            # Try to use default credentials
            session = boto3.Session(region_name=region_name)
        
        # Get the actual region being used
        actual_region = region_name or session.region_name
        if not actual_region:
            return {
                "status": "error",
                "authenticated": False,
                "error": "No region specified and no default region found in AWS configuration"
            }
        
        # Test authentication with the specified service
        if test_service == "sts":
            client = session.client('sts')
            response = client.get_caller_identity()
            
            # Update result with identity information
            result.update({
                "authenticated": True,
                "identity": response,
                "account_id": response.get("Account"),
                "user_id": response.get("UserId"),
                "arn": response.get("Arn")
            })
        else:
            # For other services, just try to create a client and make a simple API call
            client = session.client(test_service)
            
            # Make a simple API call based on the service
            if test_service == "ec2":
                client.describe_regions(MaxResults=5)
            elif test_service == "s3":
                client.list_buckets()
            elif test_service == "iam":
                client.list_account_aliases()
            # Add more service-specific tests as needed
            
            # If we get here, authentication was successful
            # Get identity information from STS
            sts_client = session.client('sts')
            identity = sts_client.get_caller_identity()
            
            result.update({
                "authenticated": True,
                "identity": identity,
                "account_id": identity.get("Account"),
                "user_id": identity.get("UserId"),
                "arn": identity.get("Arn")
            })
        
        return result
        
    except NoCredentialsError:
        return {
            "status": "error",
            "authenticated": False,
            "error": "No AWS credentials found. Configure AWS credentials via environment variables, ~/.aws/credentials, or instance profile."
        }
    except ClientError as e:
        return {
            "status": "error",
            "authenticated": False,
            "error": f"AWS client error: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "authenticated": False,
            "error": f"Unexpected error: {str(e)}"
        }


@tool
def assume_role(
    role_arn: str,
    session_name: str = "NetworkTopologyAudit",
    duration_seconds: int = 3600,
    profile_name: Optional[str] = None,
    region_name: Optional[str] = None,
    external_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Assume an IAM role and return temporary credentials.
    
    This tool assumes an IAM role using AWS STS and returns temporary credentials,
    which can be used for cross-account access or elevated permissions.
    
    Args:
        role_arn: ARN of the IAM role to assume
        session_name: Name for the assumed role session (default: "NetworkTopologyAudit")
        duration_seconds: Duration of the session in seconds (default: 3600, max: 43200)
        profile_name: AWS profile name to use for the initial credentials
        region_name: AWS region name to use
        external_id: External ID to use when assuming the role (if required)
        
    Returns:
        Dictionary with assume role results:
        {
            "status": "success" or "error",
            "credentials": temporary credentials (if successful),
            "assumed_role": information about the assumed role (if successful),
            "expiration": expiration time of the temporary credentials (if successful),
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success"
        }
        
        # Create session based on provided profile or default credentials
        if profile_name:
            try:
                session = boto3.Session(profile_name=profile_name, region_name=region_name)
            except ProfileNotFound:
                return {
                    "status": "error",
                    "error": f"AWS profile '{profile_name}' not found. Check your ~/.aws/credentials file."
                }
        else:
            session = boto3.Session(region_name=region_name)
        
        # Create STS client
        sts_client = session.client('sts')
        
        # Assume the role
        assume_role_kwargs = {
            'RoleArn': role_arn,
            'RoleSessionName': session_name,
            'DurationSeconds': duration_seconds
        }
        
        if external_id:
            assume_role_kwargs['ExternalId'] = external_id
        
        response = sts_client.assume_role(**assume_role_kwargs)
        
        # Extract credentials from response
        credentials = response['Credentials']
        
        # Update result with credentials and role information
        result.update({
            "credentials": {
                "access_key_id": credentials['AccessKeyId'],
                "secret_access_key": credentials['SecretAccessKey'],
                "session_token": credentials['SessionToken']
            },
            "assumed_role": {
                "role_arn": role_arn,
                "session_name": session_name,
                "assumed_role_id": response['AssumedRoleUser']['AssumedRoleId'],
                "assumed_role_arn": response['AssumedRoleUser']['Arn']
            },
            "expiration": credentials['Expiration'].isoformat()
        })
        
        return result
        
    except NoCredentialsError:
        return {
            "status": "error",
            "error": "No AWS credentials found. Configure AWS credentials via environment variables, ~/.aws/credentials, or instance profile."
        }
    except ClientError as e:
        return {
            "status": "error",
            "error": f"AWS client error: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}"
        }


@tool
def get_required_permissions(
    resource_types: List[str] = ["vpc", "subnet", "security_group", "route_table"],
    include_cross_account: bool = False,
    include_cross_region: bool = False,
    format_type: str = "policy"
) -> Dict[str, Any]:
    """
    Get the required AWS permissions for accessing specified resource types.
    
    This tool returns the AWS permissions required to access specified resource types,
    formatted as an IAM policy or a list of actions.
    
    Args:
        resource_types: List of AWS resource types to include (default: ["vpc", "subnet", "security_group", "route_table"])
        include_cross_account: Whether to include permissions for cross-account access (default: False)
        include_cross_region: Whether to include permissions for cross-region access (default: False)
        format_type: Format of the returned permissions (policy, actions) (default: "policy")
        
    Returns:
        Dictionary with permissions information:
        {
            "status": "success" or "error",
            "format": format of the returned permissions,
            "permissions": permissions in the specified format,
            "resource_types": list of resource types included,
            "cross_account": whether cross-account permissions are included,
            "cross_region": whether cross-region permissions are included,
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "format": format_type,
            "resource_types": resource_types,
            "cross_account": include_cross_account,
            "cross_region": include_cross_region
        }
        
        # Define permissions for each resource type
        permissions_map = {
            "vpc": [
                "ec2:DescribeVpcs",
                "ec2:DescribeVpcAttribute",
                "ec2:DescribeVpcClassicLink",
                "ec2:DescribeVpcEndpoints",
                "ec2:DescribeVpcEndpointServices"
            ],
            "subnet": [
                "ec2:DescribeSubnets"
            ],
            "security_group": [
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeSecurityGroupRules"
            ],
            "route_table": [
                "ec2:DescribeRouteTables"
            ],
            "internet_gateway": [
                "ec2:DescribeInternetGateways"
            ],
            "nat_gateway": [
                "ec2:DescribeNatGateways"
            ],
            "transit_gateway": [
                "ec2:DescribeTransitGateways",
                "ec2:DescribeTransitGatewayAttachments",
                "ec2:DescribeTransitGatewayRouteTables"
            ],
            "vpc_peering": [
                "ec2:DescribeVpcPeeringConnections"
            ],
            "vpc_endpoint": [
                "ec2:DescribeVpcEndpoints",
                "ec2:DescribeVpcEndpointServices"
            ],
            "network_acl": [
                "ec2:DescribeNetworkAcls"
            ],
            "vpc_flow_logs": [
                "ec2:DescribeFlowLogs"
            ],
            "direct_connect": [
                "directconnect:DescribeConnections",
                "directconnect:DescribeDirectConnectGateways",
                "directconnect:DescribeVirtualInterfaces"
            ],
            "vpn": [
                "ec2:DescribeVpnConnections",
                "ec2:DescribeVpnGateways",
                "ec2:DescribeCustomerGateways"
            ],
            "network_firewall": [
                "network-firewall:ListFirewalls",
                "network-firewall:DescribeFirewall"
            ],
            "route53": [
                "route53:ListHostedZones",
                "route53:GetHostedZone",
                "route53:ListResourceRecordSets"
            ]
        }
        
        # Add general permissions
        all_permissions = [
            "ec2:DescribeRegions",
            "ec2:DescribeAvailabilityZones"
        ]
        
        # Add permissions for specified resource types
        for resource_type in resource_types:
            if resource_type in permissions_map:
                all_permissions.extend(permissions_map[resource_type])
        
        # Add cross-account permissions if requested
        if include_cross_account:
            all_permissions.extend([
                "sts:AssumeRole",
                "organizations:ListAccounts",
                "organizations:DescribeAccount"
            ])
        
        # Add cross-region permissions if requested
        if include_cross_region:
            # No additional permissions needed, as we already have ec2:DescribeRegions
            pass
        
        # Remove duplicates and sort
        all_permissions = sorted(list(set(all_permissions)))
        
        # Format permissions as requested
        if format_type == "policy":
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": all_permissions,
                        "Resource": "*"
                    }
                ]
            }
            
            result["permissions"] = policy
        else:  # actions
            result["permissions"] = all_permissions
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error generating permissions: {str(e)}"
        }


@tool
def create_aws_profile(
    profile_name: str,
    region_name: str,
    access_key_id: Optional[str] = None,
    secret_access_key: Optional[str] = None,
    session_token: Optional[str] = None,
    role_arn: Optional[str] = None,
    source_profile: Optional[str] = None,
    credential_process: Optional[str] = None,
    output_format: str = "json"
) -> Dict[str, Any]:
    """
    Create or update an AWS profile in the credentials and config files.
    
    This tool creates or updates an AWS profile in the ~/.aws/credentials and ~/.aws/config files,
    supporting various authentication methods including access keys, role assumption, and credential processes.
    
    Args:
        profile_name: Name of the profile to create or update
        region_name: AWS region for the profile
        access_key_id: AWS access key ID (for credential-based profiles)
        secret_access_key: AWS secret access key (for credential-based profiles)
        session_token: AWS session token (for temporary credentials)
        role_arn: ARN of the role to assume (for role-based profiles)
        source_profile: Source profile for role assumption (required if role_arn is provided)
        credential_process: Command to execute for credential process authentication
        output_format: Output format for AWS CLI (json, text, table) (default: "json")
        
    Returns:
        Dictionary with profile creation results:
        {
            "status": "success" or "error",
            "profile_name": name of the created/updated profile,
            "profile_type": type of profile created (credential, role, process),
            "config_file": path to the AWS config file,
            "credentials_file": path to the AWS credentials file,
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "profile_name": profile_name
        }
        
        # Determine profile type
        if access_key_id and secret_access_key:
            profile_type = "credential"
        elif role_arn and source_profile:
            profile_type = "role"
        elif credential_process:
            profile_type = "process"
        else:
            return {
                "status": "error",
                "error": "Invalid profile configuration. Must provide either access keys, role ARN with source profile, or credential process."
            }
        
        result["profile_type"] = profile_type
        
        # Get AWS config directory and create if it doesn't exist
        aws_dir = os.path.expanduser("~/.aws")
        os.makedirs(aws_dir, exist_ok=True)
        
        config_file = os.path.join(aws_dir, "config")
        credentials_file = os.path.join(aws_dir, "credentials")
        
        result["config_file"] = config_file
        result["credentials_file"] = credentials_file
        
        # Update config file
        import configparser
        config = configparser.ConfigParser()
        
        # Read existing config if it exists
        if os.path.exists(config_file):
            config.read(config_file)
        
        # Create or update profile section
        profile_section = f"profile {profile_name}" if profile_name != "default" else "default"
        
        if not config.has_section(profile_section):
            config.add_section(profile_section)
        
        config[profile_section]["region"] = region_name
        config[profile_section]["output"] = output_format
        
        if profile_type == "role":
            config[profile_section]["role_arn"] = role_arn
            config[profile_section]["source_profile"] = source_profile
        
        elif profile_type == "process":
            config[profile_section]["credential_process"] = credential_process
        
        # Write config file
        with open(config_file, 'w') as f:
            config.write(f)
        
        # Update credentials file if using access keys
        if profile_type == "credential":
            credentials = configparser.ConfigParser()
            
            # Read existing credentials if they exist
            if os.path.exists(credentials_file):
                credentials.read(credentials_file)
            
            # Create or update profile section
            if not credentials.has_section(profile_name):
                credentials.add_section(profile_name)
            
            credentials[profile_name]["aws_access_key_id"] = access_key_id
            credentials[profile_name]["aws_secret_access_key"] = secret_access_key
            
            if session_token:
                credentials[profile_name]["aws_session_token"] = session_token
            
            # Write credentials file
            with open(credentials_file, 'w') as f:
                credentials.write(f)
            
            # Set permissions to be readable only by the user
            os.chmod(credentials_file, 0o600)
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error creating AWS profile: {str(e)}"
        }


@tool
def get_aws_accounts(
    profile_name: Optional[str] = None,
    region_name: Optional[str] = None,
    include_organization: bool = True
) -> Dict[str, Any]:
    """
    Get a list of accessible AWS accounts.
    
    This tool retrieves a list of AWS accounts that are accessible to the current credentials,
    including the current account and, optionally, accounts in the same organization.
    
    Args:
        profile_name: AWS profile name to use
        region_name: AWS region name to use
        include_organization: Whether to include accounts from the AWS Organization (default: True)
        
    Returns:
        Dictionary with account information:
        {
            "status": "success" or "error",
            "current_account": information about the current account,
            "accounts": list of accessible accounts (if include_organization is True),
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success"
        }
        
        # Create session based on provided profile or default credentials
        if profile_name:
            try:
                session = boto3.Session(profile_name=profile_name, region_name=region_name)
            except ProfileNotFound:
                return {
                    "status": "error",
                    "error": f"AWS profile '{profile_name}' not found. Check your ~/.aws/credentials file."
                }
        else:
            session = boto3.Session(region_name=region_name)
        
        # Get current account information
        sts_client = session.client('sts')
        identity = sts_client.get_caller_identity()
        
        current_account = {
            "account_id": identity.get("Account"),
            "user_id": identity.get("UserId"),
            "arn": identity.get("Arn"),
            "is_current": True
        }
        
        result["current_account"] = current_account
        
        # Get accounts from organization if requested
        if include_organization:
            try:
                org_client = session.client('organizations')
                accounts_response = org_client.list_accounts()
                
                accounts = []
                for account in accounts_response.get("Accounts", []):
                    account_info = {
                        "account_id": account.get("Id"),
                        "name": account.get("Name"),
                        "email": account.get("Email"),
                        "status": account.get("Status"),
                        "joined_method": account.get("JoinedMethod"),
                        "joined_timestamp": account.get("JoinedTimestamp").isoformat() if account.get("JoinedTimestamp") else None,
                        "is_current": account.get("Id") == current_account["account_id"]
                    }
                    accounts.append(account_info)
                
                result["accounts"] = accounts
                
            except ClientError as e:
                # If the user doesn't have permission to list accounts, just return the current account
                logger.warning(f"Could not list organization accounts: {str(e)}")
                result["accounts"] = [current_account]
                result["organization_access"] = False
        
        return result
        
    except NoCredentialsError:
        return {
            "status": "error",
            "error": "No AWS credentials found. Configure AWS credentials via environment variables, ~/.aws/credentials, or instance profile."
        }
    except ClientError as e:
        return {
            "status": "error",
            "error": f"AWS client error: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}"
        }


@tool
def create_cross_account_role_template(
    role_name: str,
    trusted_account_ids: List[str],
    policy_type: str = "readonly",
    external_id: Optional[str] = None,
    require_mfa: bool = False
) -> Dict[str, Any]:
    """
    Create a CloudFormation template for a cross-account IAM role.
    
    This tool creates a CloudFormation template for an IAM role that can be assumed
    by specified accounts, with customizable trust policy and permissions.
    
    Args:
        role_name: Name of the IAM role to create
        trusted_account_ids: List of AWS account IDs that can assume the role
        policy_type: Type of policy to attach (readonly, network-readonly, custom) (default: "readonly")
        external_id: External ID to require when assuming the role (optional)
        require_mfa: Whether to require MFA when assuming the role (default: False)
        
    Returns:
        Dictionary with template information:
        {
            "status": "success" or "error",
            "template": CloudFormation template for the role,
            "role_name": name of the role,
            "trusted_accounts": list of trusted account IDs,
            "policy_type": type of policy attached,
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "role_name": role_name,
            "trusted_accounts": trusted_account_ids,
            "policy_type": policy_type
        }
        
        # Create trust policy
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": [f"arn:aws:iam::{account_id}:root" for account_id in trusted_account_ids]
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        # Add external ID condition if provided
        if external_id:
            trust_policy["Statement"][0]["Condition"] = {
                "StringEquals": {
                    "sts:ExternalId": external_id
                }
            }
        
        # Add MFA condition if required
        if require_mfa:
            if "Condition" not in trust_policy["Statement"][0]:
                trust_policy["Statement"][0]["Condition"] = {}
            
            trust_policy["Statement"][0]["Condition"]["Bool"] = {
                "aws:MultiFactorAuthPresent": "true"
            }
        
        # Define policy based on type
        if policy_type == "readonly":
            managed_policy = "arn:aws:iam::aws:policy/ReadOnlyAccess"
        elif policy_type == "network-readonly":
            # Create custom policy for network read-only access
            inline_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "ec2:Describe*",
                            "directconnect:Describe*",
                            "route53:List*",
                            "route53:Get*",
                            "elasticloadbalancing:Describe*",
                            "network-firewall:ListFirewalls",
                            "network-firewall:DescribeFirewall"
                        ],
                        "Resource": "*"
                    }
                ]
            }
        elif policy_type == "custom":
            # Create a minimal custom policy template that can be modified
            inline_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            # Add custom actions here
                            "ec2:DescribeVpcs",
                            "ec2:DescribeSubnets"
                        ],
                        "Resource": "*"
                    }
                ]
            }
        else:
            return {
                "status": "error",
                "error": f"Invalid policy type: {policy_type}. Valid types are: readonly, network-readonly, custom"
            }
        
        # Create CloudFormation template
        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": f"Cross-account IAM role for network topology visualization",
            "Resources": {
                "CrossAccountRole": {
                    "Type": "AWS::IAM::Role",
                    "Properties": {
                        "RoleName": role_name,
                        "AssumeRolePolicyDocument": trust_policy,
                        "Path": "/",
                        "Tags": [
                            {
                                "Key": "Purpose",
                                "Value": "NetworkTopologyVisualization"
                            }
                        ]
                    }
                }
            },
            "Outputs": {
                "RoleARN": {
                    "Description": "ARN of the created IAM role",
                    "Value": {"Fn::GetAtt": ["CrossAccountRole", "Arn"]}
                }
            }
        }
        
        # Add policy based on type
        if policy_type == "readonly":
            template["Resources"]["CrossAccountRole"]["Properties"]["ManagedPolicyArns"] = [managed_policy]
        else:
            template["Resources"]["CrossAccountPolicy"] = {
                "Type": "AWS::IAM::Policy",
                "Properties": {
                    "PolicyName": f"{role_name}Policy",
                    "PolicyDocument": inline_policy,
                    "Roles": [{"Ref": "CrossAccountRole"}]
                }
            }
        
        result["template"] = template
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error creating cross-account role template: {str(e)}"
        }