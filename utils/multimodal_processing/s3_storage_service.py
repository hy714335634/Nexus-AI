"""
S3 Storage Service for the multimodal content parser system.

This module provides secure file storage capabilities using AWS S3,
including upload, download, deletion, and URL generation functionality.
"""

import boto3
import logging
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
from botocore.config import Config
import time
import hashlib
import os
from datetime import datetime, timedelta

from .models.exceptions import StorageError


class S3StorageService:
    """
    Service for managing file storage operations with AWS S3.
    
    Provides secure file upload, download, deletion, and URL generation
    with built-in error handling and retry mechanisms.
    """
    
    def __init__(
        self,
        bucket_name: str,
        aws_region: str = 'us-west-2',
        s3_prefix: str = 'multimodal-content/',
        max_retries: int = 3,
        retry_delay: float = 1.0,
        presigned_url_expiration: int = 3600
    ):
        """
        Initialize S3 storage service.
        
        Args:
            bucket_name: Name of the S3 bucket for file storage
            aws_region: AWS region for S3 operations
            s3_prefix: Prefix for all stored files in the bucket
            max_retries: Maximum number of retry attempts for failed operations
            retry_delay: Initial delay between retries in seconds
            presigned_url_expiration: Expiration time for presigned URLs in seconds
        """
        # Initialize logger first
        self.logger = logging.getLogger(__name__)
        
        self.bucket_name = bucket_name
        self.aws_region = aws_region
        self.s3_prefix = s3_prefix.rstrip('/') + '/'
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.presigned_url_expiration = presigned_url_expiration
        
        # Configure S3 client with retry settings
        config = Config(
            region_name=aws_region,
            retries={
                'max_attempts': max_retries,
                'mode': 'adaptive'
            },
            max_pool_connections=50
        )
        
        try:
            # Ensure environment variables are loaded
            import os
            from dotenv import load_dotenv
            load_dotenv()
            
            # Get AWS credentials from environment variables first, then config
            aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            
            # If no environment variables, try to load from config
            if not aws_access_key_id or not aws_secret_access_key:
                try:
                    from ..config_loader import ConfigLoader
                    config_loader = ConfigLoader()
                    aws_config = config_loader.get_aws_config()
                    aws_access_key_id = aws_config.get('aws_access_key_id')
                    aws_secret_access_key = aws_config.get('aws_secret_access_key')
                except Exception as e:
                    self.logger.warning(f"Failed to load AWS credentials from config: {e}")
            
            # If still no credentials, use AWS credentials provider chain
            if not aws_access_key_id or not aws_secret_access_key:
                self.logger.info("Using AWS credentials provider chain")
                session = boto3.Session(region_name=aws_region)
            else:
                # Create session with explicit credentials
                session = boto3.Session(
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=aws_region
                )
            
            self.s3_client = session.client('s3', config=config)
            
            self.logger.info(f"S3StorageService initialized for bucket: {bucket_name} in region: {aws_region}")
            
            # Test credentials by listing buckets
            try:
                response = self.s3_client.list_buckets()
                self.logger.info("AWS credentials validated successfully")
                
                # Check if the target bucket exists
                bucket_names = [bucket['Name'] for bucket in response.get('Buckets', [])]
                if bucket_name not in bucket_names:
                    self.logger.warning(f"Target bucket '{bucket_name}' not found in account. Available buckets: {bucket_names}")
                else:
                    self.logger.info(f"Target bucket '{bucket_name}' found and accessible")
                    
            except Exception as cred_test_error:
                self.logger.error(f"AWS credential validation failed: {cred_test_error}")
                raise StorageError(
                    f"AWS credential validation failed: {str(cred_test_error)}",
                    error_code="CREDENTIALS_INVALID",
                    context={"bucket": bucket_name, "region": aws_region}
                ) from cred_test_error
                
        except StorageError:
            # Re-raise StorageError as-is
            raise
        except NoCredentialsError as e:
            raise StorageError(
                "AWS credentials not found. Please configure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env file.",
                error_code="CREDENTIALS_ERROR",
                context={"bucket": bucket_name, "region": aws_region}
            ) from e
        except Exception as e:
            raise StorageError(
                f"Failed to initialize S3 client: {str(e)}",
                error_code="INITIALIZATION_ERROR",
                context={"bucket": bucket_name, "region": aws_region, "error_type": type(e).__name__}
            ) from e
    
    def store_file(
        self,
        file_data: bytes,
        file_id: str,
        file_name: str,
        content_type: str = 'application/octet-stream',
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Store file data in S3 bucket.
        
        Args:
            file_data: Binary file content to store
            file_id: Unique identifier for the file
            file_name: Original filename for metadata
            content_type: MIME type of the file
            metadata: Additional metadata to store with the file
        
        Returns:
            S3 URL of the stored file
            
        Raises:
            StorageError: If file storage fails after all retry attempts
        """
        s3_key = self._generate_s3_key(file_id, file_name)
        
        # Prepare metadata
        file_metadata = {
            'original-filename': file_name,
            'file-id': file_id,
            'upload-timestamp': datetime.utcnow().isoformat(),
            'content-hash': hashlib.md5(file_data).hexdigest()
        }
        
        if metadata:
            file_metadata.update(metadata)
        
        # Attempt to upload with retry logic
        for attempt in range(self.max_retries + 1):
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=file_data,
                    ContentType=content_type,
                    Metadata=file_metadata,
                    ServerSideEncryption='AES256'
                )
                
                s3_url = f"s3://{self.bucket_name}/{s3_key}"
                # s3_url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
                self.logger.info(f"Successfully stored file {file_id} at {s3_url}")
                return s3_url
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                
                if attempt < self.max_retries and error_code in ['ServiceUnavailable', 'SlowDown', 'RequestTimeout']:
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"S3 upload attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise StorageError(
                        f"Failed to store file in S3: {str(e)}",
                        error_code=f"S3_{error_code}",
                        context={
                            "file_id": file_id,
                            "file_name": file_name,
                            "bucket": self.bucket_name,
                            "key": s3_key,
                            "attempt": attempt + 1
                        }
                    ) from e
            
            except Exception as e:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"S3 upload attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise StorageError(
                        f"Unexpected error storing file in S3: {str(e)}",
                        error_code="STORAGE_ERROR",
                        context={
                            "file_id": file_id,
                            "file_name": file_name,
                            "bucket": self.bucket_name,
                            "key": s3_key,
                            "attempt": attempt + 1
                        }
                    ) from e
        
        # This should never be reached due to the loop structure, but included for completeness
        raise StorageError(
            "Maximum retry attempts exceeded for file storage",
            error_code="MAX_RETRIES_EXCEEDED",
            context={"file_id": file_id, "max_retries": self.max_retries}
        )    
    def get_file_url(
        self,
        file_id: str,
        file_name: str,
        expiration: Optional[int] = None
    ) -> str:
        """
        Generate a presigned URL for file access.
        
        Args:
            file_id: Unique identifier for the file
            file_name: Original filename for S3 key generation
            expiration: URL expiration time in seconds (defaults to instance setting)
        
        Returns:
            Presigned URL for file access
            
        Raises:
            StorageError: If URL generation fails
        """
        s3_key = self._generate_s3_key(file_id, file_name)
        expiration = expiration or self.presigned_url_expiration
        
        try:
            # First check if file exists
            if not self.check_file_exists(file_id, file_name):
                raise StorageError(
                    f"File not found: {file_id}",
                    error_code="FILE_NOT_FOUND",
                    context={"file_id": file_id, "file_name": file_name}
                )
            
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            
            self.logger.debug(f"Generated presigned URL for file {file_id}, expires in {expiration}s")
            return presigned_url
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise StorageError(
                f"Failed to generate presigned URL: {str(e)}",
                error_code=f"S3_{error_code}",
                context={
                    "file_id": file_id,
                    "file_name": file_name,
                    "bucket": self.bucket_name,
                    "key": s3_key
                }
            ) from e
        except Exception as e:
            raise StorageError(
                f"Unexpected error generating presigned URL: {str(e)}",
                error_code="URL_GENERATION_ERROR",
                context={"file_id": file_id, "file_name": file_name}
            ) from e
    
    def download_file(self, file_id: str, file_name: str) -> bytes:
        """
        Download file content from S3.
        
        Args:
            file_id: Unique identifier for the file
            file_name: Original filename for S3 key generation
        
        Returns:
            Binary file content
            
        Raises:
            StorageError: If file download fails
        """
        s3_key = self._generate_s3_key(file_id, file_name)
        
        for attempt in range(self.max_retries + 1):
            try:
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
                
                file_content = response['Body'].read()
                self.logger.debug(f"Successfully downloaded file {file_id}")
                return file_content
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                
                if error_code == 'NoSuchKey':
                    raise StorageError(
                        f"File not found: {file_id}",
                        error_code="FILE_NOT_FOUND",
                        context={"file_id": file_id, "file_name": file_name, "key": s3_key}
                    ) from e
                
                if attempt < self.max_retries and error_code in ['ServiceUnavailable', 'SlowDown', 'RequestTimeout']:
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"S3 download attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise StorageError(
                        f"Failed to download file from S3: {str(e)}",
                        error_code=f"S3_{error_code}",
                        context={
                            "file_id": file_id,
                            "file_name": file_name,
                            "bucket": self.bucket_name,
                            "key": s3_key,
                            "attempt": attempt + 1
                        }
                    ) from e
            
            except Exception as e:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"S3 download attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise StorageError(
                        f"Unexpected error downloading file from S3: {str(e)}",
                        error_code="DOWNLOAD_ERROR",
                        context={
                            "file_id": file_id,
                            "file_name": file_name,
                            "bucket": self.bucket_name,
                            "key": s3_key,
                            "attempt": attempt + 1
                        }
                    ) from e
    
    def download_file_by_key(self, s3_key: str) -> bytes:
        """
        Download file content from S3 using the S3 key directly.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Binary file content
            
        Raises:
            StorageError: If file download fails
        """
        for attempt in range(self.max_retries + 1):
            try:
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
                
                file_content = response['Body'].read()
                self.logger.debug(f"Successfully downloaded file with key: {s3_key}")
                return file_content
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                
                if error_code == 'NoSuchKey':
                    raise StorageError(
                        f"File not found with key: {s3_key}",
                        error_code="FILE_NOT_FOUND",
                        context={"s3_key": s3_key, "bucket": self.bucket_name}
                    ) from e
                
                if attempt < self.max_retries and error_code in ['ServiceUnavailable', 'SlowDown', 'RequestTimeout']:
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"S3 download attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise StorageError(
                        f"Failed to download file from S3: {str(e)}",
                        error_code=f"S3_{error_code}",
                        context={
                            "s3_key": s3_key,
                            "bucket": self.bucket_name,
                            "attempt": attempt + 1
                        }
                    ) from e
            
            except Exception as e:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"S3 download attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise StorageError(
                        f"Unexpected error downloading file from S3: {str(e)}",
                        error_code="DOWNLOAD_ERROR",
                        context={
                            "s3_key": s3_key,
                            "bucket": self.bucket_name,
                            "attempt": attempt + 1
                        }
                    ) from e
    
    def delete_file(self, file_id: str, file_name: str) -> bool:
        """
        Delete file from S3 bucket.
        
        Args:
            file_id: Unique identifier for the file
            file_name: Original filename for S3 key generation
        
        Returns:
            True if file was deleted successfully, False if file didn't exist
            
        Raises:
            StorageError: If file deletion fails
        """
        s3_key = self._generate_s3_key(file_id, file_name)
        
        for attempt in range(self.max_retries + 1):
            try:
                # Check if file exists first
                if not self.check_file_exists(file_id, file_name):
                    self.logger.info(f"File {file_id} does not exist, nothing to delete")
                    return False
                
                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
                
                self.logger.info(f"Successfully deleted file {file_id}")
                return True
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                
                if attempt < self.max_retries and error_code in ['ServiceUnavailable', 'SlowDown', 'RequestTimeout']:
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"S3 delete attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise StorageError(
                        f"Failed to delete file from S3: {str(e)}",
                        error_code=f"S3_{error_code}",
                        context={
                            "file_id": file_id,
                            "file_name": file_name,
                            "bucket": self.bucket_name,
                            "key": s3_key,
                            "attempt": attempt + 1
                        }
                    ) from e
            
            except Exception as e:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"S3 delete attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise StorageError(
                        f"Unexpected error deleting file from S3: {str(e)}",
                        error_code="DELETE_ERROR",
                        context={
                            "file_id": file_id,
                            "file_name": file_name,
                            "bucket": self.bucket_name,
                            "key": s3_key,
                            "attempt": attempt + 1
                        }
                    ) from e
    
    def check_file_exists(self, file_id: str, file_name: str) -> bool:
        """
        Check if file exists in S3 bucket.
        
        Args:
            file_id: Unique identifier for the file
            file_name: Original filename for S3 key generation
        
        Returns:
            True if file exists, False otherwise
            
        Raises:
            StorageError: If existence check fails due to service errors
        """
        s3_key = self._generate_s3_key(file_id, file_name)
        
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            
            if error_code == 'NoSuchKey' or error_code == '404':
                return False
            else:
                raise StorageError(
                    f"Failed to check file existence: {str(e)}",
                    error_code=f"S3_{error_code}",
                    context={
                        "file_id": file_id,
                        "file_name": file_name,
                        "bucket": self.bucket_name,
                        "key": s3_key
                    }
                ) from e
        
        except Exception as e:
            raise StorageError(
                f"Unexpected error checking file existence: {str(e)}",
                error_code="EXISTENCE_CHECK_ERROR",
                context={"file_id": file_id, "file_name": file_name}
            ) from e
    
    def get_file_metadata(self, file_id: str, file_name: str) -> Dict[str, Any]:
        """
        Retrieve file metadata from S3.
        
        Args:
            file_id: Unique identifier for the file
            file_name: Original filename for S3 key generation
        
        Returns:
            Dictionary containing file metadata
            
        Raises:
            StorageError: If metadata retrieval fails
        """
        s3_key = self._generate_s3_key(file_id, file_name)
        
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            metadata = {
                'file_size': response.get('ContentLength', 0),
                'content_type': response.get('ContentType', 'application/octet-stream'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag', '').strip('"'),
                'custom_metadata': response.get('Metadata', {})
            }
            
            return metadata
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            
            if error_code == 'NoSuchKey':
                raise StorageError(
                    f"File not found: {file_id}",
                    error_code="FILE_NOT_FOUND",
                    context={"file_id": file_id, "file_name": file_name}
                ) from e
            else:
                raise StorageError(
                    f"Failed to retrieve file metadata: {str(e)}",
                    error_code=f"S3_{error_code}",
                    context={
                        "file_id": file_id,
                        "file_name": file_name,
                        "bucket": self.bucket_name,
                        "key": s3_key
                    }
                ) from e
        
        except Exception as e:
            raise StorageError(
                f"Unexpected error retrieving file metadata: {str(e)}",
                error_code="METADATA_ERROR",
                context={"file_id": file_id, "file_name": file_name}
            ) from e
    
    def _generate_s3_key(self, file_id: str, file_name: str) -> str:
        """
        Generate S3 key for file storage.
        
        Args:
            file_id: Unique identifier for the file
            file_name: Original filename
        
        Returns:
            S3 key path for the file
        """
        # Extract file extension
        file_extension = os.path.splitext(file_name)[1].lower()
        
        # Create date-based folder structure for organization
        date_prefix = datetime.utcnow().strftime('%Y/%m/%d')
        
        # Combine prefix, date, and file info
        s3_key = f"{self.s3_prefix}{date_prefix}/{file_id}{file_extension}"
        
        return s3_key
    
    def cleanup_expired_files(self, days_old: int = 30) -> int:
        """
        Clean up files older than specified number of days.
        
        Args:
            days_old: Number of days after which files should be deleted
        
        Returns:
            Number of files deleted
            
        Raises:
            StorageError: If cleanup operation fails
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            deleted_count = 0
            
            # List objects with the prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=self.s3_prefix)
            
            objects_to_delete = []
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                            objects_to_delete.append({'Key': obj['Key']})
                            
                            # Delete in batches of 1000 (S3 limit)
                            if len(objects_to_delete) >= 1000:
                                self._delete_objects_batch(objects_to_delete)
                                deleted_count += len(objects_to_delete)
                                objects_to_delete = []
            
            # Delete remaining objects
            if objects_to_delete:
                self._delete_objects_batch(objects_to_delete)
                deleted_count += len(objects_to_delete)
            
            self.logger.info(f"Cleaned up {deleted_count} expired files older than {days_old} days")
            return deleted_count
            
        except Exception as e:
            raise StorageError(
                f"Failed to cleanup expired files: {str(e)}",
                error_code="CLEANUP_ERROR",
                context={"days_old": days_old, "bucket": self.bucket_name}
            ) from e
    
    def _delete_objects_batch(self, objects: list) -> None:
        """
        Delete a batch of objects from S3.
        
        Args:
            objects: List of objects to delete in format [{'Key': 'key1'}, ...]
        """
        self.s3_client.delete_objects(
            Bucket=self.bucket_name,
            Delete={'Objects': objects}
        )