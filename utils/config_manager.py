"""
Configuration Manager for Multimodal Content Parser

This module provides configuration loading, validation, and management
functionality for the multimodal content parser system.
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
import logging
from threading import Lock
import time

logger = logging.getLogger(__name__)


@dataclass
class AWSConfig:
    """AWS configuration settings"""
    s3_bucket: str
    s3_prefix: str = "multimodal-content/"
    bedrock_region: str = "us-west-2"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    endpoint_url: Optional[str] = None
    verify: bool = True


@dataclass
class FileLimitsConfig:
    """File processing limits configuration"""
    max_file_size: str = "50MB"
    max_files_per_request: int = 10
    supported_formats: List[str] = field(default_factory=lambda: [
        "jpg", "jpeg", "png", "gif", "txt", "xlsx", "docx", "csv"
    ])


@dataclass
class ProcessingConfig:
    """Processing behavior configuration"""
    timeout_seconds: int = 300
    retry_attempts: int = 3
    batch_size: int = 5


@dataclass
class StorageConfig:
    """Storage management configuration"""
    presigned_url_expiration: int = 3600  # 1 hour
    cleanup_days: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class ModelConfig:
    """AI model configuration"""
    primary_model: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    fallback_model: str = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    max_tokens: int = 4000


@dataclass
class MultimodalParserConfig:
    """Complete multimodal parser configuration"""
    aws: AWSConfig
    file_limits: FileLimitsConfig
    processing: ProcessingConfig
    storage: StorageConfig
    model: ModelConfig


class ConfigurationError(Exception):
    """Configuration-related errors"""
    pass


class ConfigManager:
    """
    Configuration manager with validation, hot-reload, and environment variable support
    """
    
    def __init__(self, config_path: str = "config/default_config.yaml"):
        self.config_path = Path(config_path)
        self._config: Optional[Dict[str, Any]] = None
        self._parser_config: Optional[MultimodalParserConfig] = None
        self._last_modified: Optional[float] = None
        self._lock = Lock()
        
        # Load initial configuration
        self.reload_config()
    
    def reload_config(self) -> None:
        """Reload configuration from file"""
        with self._lock:
            try:
                if not self.config_path.exists():
                    raise ConfigurationError(f"Configuration file not found: {self.config_path}")
                
                # Check if file has been modified
                current_modified = self.config_path.stat().st_mtime
                if self._last_modified and current_modified <= self._last_modified:
                    return  # No changes
                
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f)
                
                self._last_modified = current_modified
                self._parser_config = None  # Reset parsed config
                
                logger.info(f"Configuration reloaded from {self.config_path}")
                
            except Exception as e:
                logger.error(f"Failed to reload configuration: {e}")
                raise ConfigurationError(f"Failed to reload configuration: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """Get the raw configuration dictionary"""
        if self._config is None:
            self.reload_config()
        return self._config
    
    def get_parser_config(self) -> MultimodalParserConfig:
        """Get the parsed multimodal parser configuration"""
        if self._parser_config is None:
            self._parse_multimodal_config()
        return self._parser_config
    
    def _parse_multimodal_config(self) -> None:
        """Parse and validate multimodal parser configuration"""
        config = self.get_config()
        
        if 'default-config' not in config:
            raise ConfigurationError("Missing 'default-config' section in configuration")
        
        default_config = config['default-config']
        
        if 'multimodal_parser' not in default_config:
            raise ConfigurationError("Missing 'multimodal_parser' section in configuration")
        
        parser_config = default_config['multimodal_parser']
        
        try:
            # Parse AWS configuration with environment variable overrides
            aws_config_data = parser_config.get('aws', {})
            aws_config = AWSConfig(
                s3_bucket=self._get_env_or_config('AWS_S3_BUCKET', aws_config_data.get('s3_bucket')),
                s3_prefix=self._get_env_or_config('AWS_S3_PREFIX', aws_config_data.get('s3_prefix', 'multimodal-content/')),
                bedrock_region=self._get_env_or_config('AWS_BEDROCK_REGION', aws_config_data.get('bedrock_region', 'us-west-2')),
                aws_access_key_id=self._get_env_or_config('AWS_ACCESS_KEY_ID', aws_config_data.get('aws_access_key_id')),
                aws_secret_access_key=self._get_env_or_config('AWS_SECRET_ACCESS_KEY', aws_config_data.get('aws_secret_access_key')),
                endpoint_url=self._get_env_or_config('AWS_ENDPOINT_URL', aws_config_data.get('endpoint_url')),
                verify=self._get_env_or_config('AWS_VERIFY_SSL', aws_config_data.get('verify', True), bool)
            )
            
            # Parse file limits configuration
            file_limits_data = parser_config.get('file_limits', {})
            file_limits = FileLimitsConfig(
                max_file_size=file_limits_data.get('max_file_size', '50MB'),
                max_files_per_request=file_limits_data.get('max_files_per_request', 10),
                supported_formats=file_limits_data.get('supported_formats', [
                    "jpg", "jpeg", "png", "gif", "txt", "xlsx", "docx", "csv"
                ])
            )
            
            # Parse processing configuration
            processing_data = parser_config.get('processing', {})
            processing = ProcessingConfig(
                timeout_seconds=processing_data.get('timeout_seconds', 300),
                retry_attempts=processing_data.get('retry_attempts', 3),
                batch_size=processing_data.get('batch_size', 5)
            )
            
            # Parse storage configuration
            storage_data = parser_config.get('storage', {})
            storage = StorageConfig(
                presigned_url_expiration=storage_data.get('presigned_url_expiration', 3600),
                cleanup_days=storage_data.get('cleanup_days', 30),
                max_retries=storage_data.get('max_retries', 3),
                retry_delay=storage_data.get('retry_delay', 1.0)
            )
            
            # Parse model configuration
            model_data = parser_config.get('model', {})
            model = ModelConfig(
                primary_model=model_data.get('primary_model', 'us.anthropic.claude-3-7-sonnet-20250219-v1:0'),
                fallback_model=model_data.get('fallback_model', 'us.anthropic.claude-3-5-haiku-20241022-v1:0'),
                max_tokens=model_data.get('max_tokens', 4000)
            )
            
            self._parser_config = MultimodalParserConfig(
                aws=aws_config,
                file_limits=file_limits,
                processing=processing,
                storage=storage,
                model=model
            )
            
            # Validate configuration
            self._validate_config()
            
        except Exception as e:
            logger.error(f"Failed to parse multimodal parser configuration: {e}")
            raise ConfigurationError(f"Failed to parse multimodal parser configuration: {e}")
    
    def _get_env_or_config(self, env_var: str, config_value: Any, value_type: type = str) -> Any:
        """Get value from environment variable or configuration, with type conversion"""
        env_value = os.getenv(env_var)
        if env_value is not None:
            if value_type == bool:
                return env_value.lower() in ('true', '1', 'yes', 'on')
            elif value_type == int:
                return int(env_value)
            elif value_type == float:
                return float(env_value)
            return env_value
        return config_value
    
    def _validate_config(self) -> None:
        """Validate the parsed configuration"""
        if not self._parser_config:
            raise ConfigurationError("No configuration to validate")
        
        config = self._parser_config
        
        # Validate AWS configuration
        if not config.aws.s3_bucket:
            raise ConfigurationError("AWS S3 bucket name is required")
        
        # Validate file limits
        if config.file_limits.max_files_per_request <= 0:
            raise ConfigurationError("max_files_per_request must be greater than 0")
        
        if not config.file_limits.supported_formats:
            raise ConfigurationError("At least one supported format must be specified")
        
        # Validate processing configuration
        if config.processing.timeout_seconds <= 0:
            raise ConfigurationError("timeout_seconds must be greater than 0")
        
        if config.processing.retry_attempts < 0:
            raise ConfigurationError("retry_attempts must be non-negative")
        
        if config.processing.batch_size <= 0:
            raise ConfigurationError("batch_size must be greater than 0")
        
        # Validate storage configuration
        if config.storage.presigned_url_expiration <= 0:
            raise ConfigurationError("presigned_url_expiration must be greater than 0")
        
        if config.storage.cleanup_days <= 0:
            raise ConfigurationError("cleanup_days must be greater than 0")
        
        # Validate model configuration
        if not config.model.primary_model:
            raise ConfigurationError("primary_model is required")
        
        if not config.model.fallback_model:
            raise ConfigurationError("fallback_model is required")
        
        if config.model.max_tokens <= 0:
            raise ConfigurationError("max_tokens must be greater than 0")
        
        logger.info("Configuration validation passed")
    
    def check_for_updates(self) -> bool:
        """Check if configuration file has been updated"""
        if not self.config_path.exists():
            return False
        
        current_modified = self.config_path.stat().st_mtime
        return self._last_modified is None or current_modified > self._last_modified
    
    def auto_reload_if_changed(self) -> bool:
        """Automatically reload configuration if file has changed"""
        if self.check_for_updates():
            try:
                self.reload_config()
                return True
            except Exception as e:
                logger.error(f"Failed to auto-reload configuration: {e}")
                return False
        return False
    
    def get_file_size_bytes(self) -> int:
        """Convert max_file_size string to bytes"""
        size_str = self.get_parser_config().file_limits.max_file_size.upper()
        
        # Parse size string (e.g., "50MB", "1GB", "500KB")
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024
        }
        
        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                try:
                    number = float(size_str[:-len(suffix)])
                    return int(number * multiplier)
                except ValueError:
                    break
        
        raise ConfigurationError(f"Invalid file size format: {size_str}")
    
    def is_supported_format(self, file_extension: str) -> bool:
        """Check if file format is supported"""
        return file_extension.lower() in [
            fmt.lower() for fmt in self.get_parser_config().file_limits.supported_formats
        ]


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_parser_config() -> MultimodalParserConfig:
    """Get the multimodal parser configuration"""
    return get_config_manager().get_parser_config()


def reload_config() -> None:
    """Reload the global configuration"""
    get_config_manager().reload_config()