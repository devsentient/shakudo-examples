"""API endpoints for retrieving and managing agent execution steps.

This module provides API endpoints for:
1. Retrieving agent execution steps from memory
2. Filtering steps by job ID for specific execution contexts
3. Clearing steps from memory when needed

Steps represent the detailed execution trace of agents in the system,
including their actions, observations, and tool calls.
"""
import logging
from typing import Dict, Any, List, Optional, Union, Dict, cast

from fastapi import APIRouter, Query, HTTPException, status, Response
from pydantic import BaseModel, Field

from modules.memory import MEMORY_STEP_STORE
from modules.models import StepResponse, Step

# Setup logging
logger = logging.getLogger(__name__)

# Create router with standardized metadata
router = APIRouter(
    prefix="/steps",
    tags=["steps"],
    responses={
        status.HTTP_200_OK: {"description": "Success"},
        status.HTTP_404_NOT_FOUND: {"description": "No steps found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
)

# Define response models
class ClearStepsResponse(BaseModel):
    """Response model for the clear steps endpoint."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Description of the operation result")
    count: int = Field(0, description="Number of steps cleared")

# Define the module interface
__all__ = [
    "router",
    "get_steps",
    "clear_steps",
    "ClearStepsResponse",
]

@router.get(
    "", 
    response_model=StepResponse,
    summary="Get all agent execution steps",
    description="Retrieve a list of all agent execution steps, with optional filtering by job ID"
)
async def get_steps(
    limit: Optional[int] = Query(None, description="Maximum number of steps to return", gt=0),
    job_id: Optional[str] = Query(None, description="Filter steps by job ID")
) -> StepResponse:
    """Get all memory steps, optionally filtered by job ID.
    
    This endpoint retrieves agent execution steps stored in memory,
    with options to filter by job ID and limit the number of results.
    
    Args:
        limit: Maximum number of steps to return (must be > 0)
        job_id: Optional filter to get only steps for a specific job
        
    Returns:
        StepResponse: Collection of steps matching the criteria
        
    Raises:
        HTTPException: If an error occurs retrieving steps
    
    Examples:
        Get all steps:
        ```
        GET /steps
        ```
        
        Get only steps for a specific job:
        ```
        GET /steps?job_id=job-20250301123456-abcd1234
        ```
        
        Get first 10 steps:
        ```
        GET /steps?limit=10
        ```
    """
    try:
        # Get all steps from memory store
        steps = MEMORY_STEP_STORE.get_steps()
        logger.debug(f"Retrieved {len(steps)} total steps from memory")
        
        # Filter by job_id if provided
        if job_id:
            original_count = len(steps)
            steps = [step for step in steps if step.get("job_id") == job_id]
            logger.debug(f"Filtered steps by job_id {job_id}: {len(steps)} of {original_count} steps remaining")
        
        # Apply limit if provided
        if limit and limit > 0:
            original_count = len(steps)
            steps = steps[:limit]
            logger.debug(f"Applied limit {limit}: {len(steps)} of {original_count} steps returned")
        
        # Return empty response if no steps found
        if not steps:
            logger.info("No steps found matching criteria")
            return StepResponse.empty()
            
        return StepResponse(steps=steps, total=len(steps))
        
    except Exception as e:
        logger.error(f"Error retrieving steps: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error retrieving steps: {str(e)}"
        )

@router.post(
    "/clear", 
    response_model=ClearStepsResponse,
    summary="Clear all memory steps",
    description="Remove all agent execution steps from memory"
)
async def clear_steps(
    job_id: Optional[str] = Query(None, description="Clear steps for a specific job only")
) -> ClearStepsResponse:
    """Clear agent execution steps from memory.
    
    This endpoint removes stored agent steps, either all steps or
    only those belonging to a specific job.
    
    Args:
        job_id: Optional job ID to clear only steps for that job
        
    Returns:
        ClearStepsResponse: Operation result with success status and count
        
    Raises:
        HTTPException: If an error occurs clearing steps
        
    Examples:
        Clear all steps:
        ```
        POST /steps/clear
        ```
        
        Clear steps for a specific job:
        ```
        POST /steps/clear?job_id=job-20250301123456-abcd1234
        ```
    """
    try:
        # Count steps before clearing for reporting
        current_steps = MEMORY_STEP_STORE.get_steps()
        
        # Filter by job_id if provided
        if job_id:
            # Count matching steps
            matching_steps = [step for step in current_steps if step.get("job_id") == job_id]
            count = len(matching_steps)
            
            if count == 0:
                logger.info(f"No steps found for job_id {job_id}")
                return ClearStepsResponse(
                    success=True,
                    message=f"No steps found for job ID {job_id}",
                    count=0
                )
            
            # Clear only steps for the specified job
            # Since memory store doesn't support selective clearing yet,
            # we'll clear all steps and re-add the ones we want to keep
            steps_to_keep = [step for step in current_steps if step.get("job_id") != job_id]
            MEMORY_STEP_STORE.clear()
            
            # Re-add steps we want to keep
            for step in steps_to_keep:
                # Convert to Step TypedDict to ensure proper typing
                typed_step = cast(Step, step)
                MEMORY_STEP_STORE.add_step(typed_step)
                
            logger.info(f"Cleared {count} steps for job_id {job_id}")
            return ClearStepsResponse(
                success=True,
                message=f"Cleared {count} steps for job ID {job_id}",
                count=count
            )
        else:
            # Clear all steps
            count = len(current_steps)
            MEMORY_STEP_STORE.clear()
            logger.info(f"Cleared all {count} steps from memory")
            
            return ClearStepsResponse(
                success=True,
                message=f"Cleared {count} steps from memory",
                count=count
            )
    except Exception as e:
        logger.error(f"Error clearing steps: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error clearing steps: {str(e)}"
        )