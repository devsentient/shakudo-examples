"""Data models for the multi-agent system.

This module defines the Pydantic models used throughout the multi-agent system.
These models provide:

1. Request and response validation for API endpoints
2. Consistent data structures for communication between components
3. Type definitions for the system's core concepts
4. Serialization/deserialization for JSON data

The models here represent the core data structures for agent-client communication
and memory step representation. Job-related models are now in api/job.py.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Literal, TypedDict, Set, Tuple

from pydantic import BaseModel, Field, validator

class MessageMetadata(TypedDict, total=False):
    """Type definition for message metadata.
    
    This defines optional contextual information that can be
    provided with message requests.
    """
    thread_id: str           # For threading/conversation context
    channel_id: str          # For multi-channel systems
    user_id: str             # Identifier for the sender
    timestamp: str           # When the message was sent
    session_id: str          # For tracking session context
    source: str              # Where the message originated from

class MessageRequest(BaseModel):
    """Request model for processing messages.
    
    This model represents the primary input to the agent system,
    containing the message to be processed and optional metadata
    for context.
    """
    message: str = Field(..., description="The content of the message to be processed")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional contextual information about the message"
    )
    non_blocking: bool = Field(
        False, 
        description="If True, return job ID immediately; if False (default), wait for completion"
    )
    
    @validator('message')
    def message_not_empty(cls, v: str) -> str:
        """Validate that the message is not empty.
        
        Args:
            v (str): The message string to validate
            
        Returns:
            str: The validated message string
            
        Raises:
            ValueError: If the message is empty
        """
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v

class AgentResponse(BaseModel):
    """Response model for agent outputs.
    
    This model represents the standard response format from agent operations,
    including success status, the main response content, and optional error information.
    The response field can be either a string or a dictionary to support both simple
    text responses and structured data responses.
    """
    success: bool = Field(..., description="Whether the operation was successful")
    response: Union[str, Dict[str, Any]] = Field(..., description="The main response content (text or structured data)")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    
    @classmethod
    def success_response(cls, response: Union[str, Dict[str, Any]]) -> 'AgentResponse':
        """Create a successful response.
        
        Args:
            response (Union[str, Dict[str, Any]]): The response content as text or structured data
            
        Returns:
            AgentResponse: A successful response object
        """
        return cls(success=True, response=response)
    
    @classmethod
    def error_response(cls, error: str) -> 'AgentResponse':
        """Create an error response.
        
        Args:
            error (str): The error message
            
        Returns:
            AgentResponse: An error response object
        """
        return cls(success=False, response="Operation failed", error=error)

class Step(TypedDict, total=False):
    """Type definition for a memory step."""
    id: str
    agent_name: str
    step_number: int
    timestamp: str
    action_output: Optional[str]
    observations: Optional[str]
    tool_calls: List[Dict[str, Any]]
    step_type: str
    parent_step_id: Optional[str]
    child_step_ids: List[str]
    job_id: str

class StepResponse(BaseModel):
    """Model for returning memory steps.
    
    This model represents a collection of memory steps, typically used
    for API responses that return step information to clients.
    """
    steps: List[Dict[str, Any]] = Field(..., description="The collection of memory steps")
    total: int = Field(..., description="The total number of steps")
    
    @classmethod
    def empty(cls) -> 'StepResponse':
        """Create an empty step response.
        
        Returns:
            StepResponse: A response with no steps
        """
        return cls(steps=[], total=0)

class HealthResponse(BaseModel):
    """Response model for health check endpoints.
    
    This model provides information about the service's health status
    and important runtime information.
    """
    status: str = Field(..., description="Health status of the service")
    version: str = Field(..., description="Service version number")
    uptime: float = Field(..., description="Service uptime in seconds")
    memory_usage: Dict[str, Any] = Field(..., description="Memory usage statistics")
    
    @classmethod
    def healthy(cls, version: str, uptime: float, memory_usage: Dict[str, Any]) -> 'HealthResponse':
        """Create a response indicating the service is healthy.
        
        Args:
            version (str): Service version
            uptime (float): Service uptime in seconds
            memory_usage (Dict[str, Any]): Memory statistics
            
        Returns:
            HealthResponse: A healthy status response
        """
        return cls(
            status="healthy",
            version=version,
            uptime=uptime,
            memory_usage=memory_usage
        )

class SSEEvent(BaseModel):
    """Model for Server-Sent Events.
    
    This model represents an event to be sent via SSE, with an event type
    and the data payload.
    """
    event: str = Field(..., description="The type of event")
    data: str = Field(..., description="The event data")

# Public exports from this module
__all__ = [
    # Type definitions
    'MessageMetadata',
    'Step',
    
    # Request models
    'MessageRequest',
    
    # Response models
    'AgentResponse',
    'StepResponse',
    'HealthResponse',
    'SSEEvent'
]