"""
Structured Output Models

This module contains Pydantic models for structured outputs used throughout the Nexus-AI system.
These models ensure consistent data structures for agent communication and orchestration.
"""

from .project_intent_recognition import (
    IntentRecognitionResult,
    ProjectInfo
)

__all__ = [
    "IntentRecognitionResult",
    "ProjectInfo"
]