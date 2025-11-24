"""
Custom exceptions for Nexus-AI Platform API
"""
from typing import Optional

class APIException(Exception):
    """Base API exception class"""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[str] = None,
        suggestion: Optional[str] = None,
        docs_url: Optional[str] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        self.suggestion = suggestion
        self.docs_url = docs_url
        super().__init__(message)

class ValidationError(APIException):
    """Request validation error"""
    
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details,
            suggestion="Please check your request parameters and try again",
            docs_url="https://docs.nexus-ai.com/api/validation"
        )

class ResourceNotFoundError(APIException):
    """Resource not found error"""
    
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} not found",
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details=f"{resource_type} with ID '{resource_id}' does not exist",
            suggestion=f"Please verify the {resource_type.lower()} ID and try again",
            docs_url="https://docs.nexus-ai.com/api/errors#resource-not-found"
        )

class BuildError(APIException):
    """Agent build process error"""
    
    def __init__(self, message: str, stage: Optional[str] = None, details: Optional[str] = None):
        error_code = "BUILD_ERROR"
        if stage:
            error_code = f"BUILD_ERROR_{stage.upper()}"
            
        super().__init__(
            message=message,
            status_code=500,
            error_code=error_code,
            details=details,
            suggestion="Please check the build logs and try again",
            docs_url="https://docs.nexus-ai.com/api/errors#build-error"
        )

class RateLimitError(APIException):
    """Rate limit exceeded error"""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded",
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=f"Too many requests. Please retry after {retry_after} seconds",
            suggestion="Reduce request frequency or contact support for higher limits",
            docs_url="https://docs.nexus-ai.com/api/rate-limits"
        )

class ResourceConflictError(APIException):
    """Resource conflict error (e.g., duplicate name)"""

    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=409,
            error_code="RESOURCE_CONFLICT",
            details=details,
            suggestion="Please use a different name or identifier",
            docs_url="https://docs.nexus-ai.com/api/errors#resource-conflict"
        )

class InvalidStateError(APIException):
    """Invalid state error (e.g., pausing a completed project)"""

    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="INVALID_STATE",
            details=details,
            suggestion="Please check the resource's current state before performing this operation",
            docs_url="https://docs.nexus-ai.com/api/errors#invalid-state"
        )

class PermissionDeniedError(APIException):
    """Permission denied error"""

    def __init__(self, message: str = "Permission denied", details: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=403,
            error_code="PERMISSION_DENIED",
            details=details,
            suggestion="Please check your permissions or contact the administrator",
            docs_url="https://docs.nexus-ai.com/api/errors#permission-denied"
        )

class StageUpdateError(APIException):
    """Stage update failed error"""

    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="STAGE_UPDATE_FAILED",
            details=details,
            suggestion="Please retry or check the stage status",
            docs_url="https://docs.nexus-ai.com/api/errors#stage-update-failed"
        )

class AgentInvocationError(APIException):
    """Agent invocation failed error"""

    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="AGENT_INVOCATION_FAILED",
            details=details,
            suggestion="Please check the agent status and logs, or retry later",
            docs_url="https://docs.nexus-ai.com/api/errors#agent-invocation-failed"
        )

class DatabaseError(APIException):
    """Database operation error"""

    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details=details,
            suggestion="Please retry or contact technical support",
            docs_url="https://docs.nexus-ai.com/api/errors#database-error"
        )