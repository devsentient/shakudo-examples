"""Job management API for tracking and executing agent jobs."""
import os
import json
import uuid
import enum
import logging
import asyncio
import datetime
import threading
from typing import Dict, Any, List, Optional, Sequence, Union, TypedDict, cast

import psycopg2
from psycopg2.extras import Json
from fastapi import APIRouter, FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field

from modules.memory import MEMORY_STEP_STORE
from modules.common import OUTPUT_REGISTRY
from modules.agents import step_callback
from modules.utils import get_database_connection, safe_json_loads, PgConnection, PgCursor

from modules.models import (
    AgentResponse,
    MessageRequest,
    # Note: JobStatus is defined in this file, not imported from modules.models
)

# Setup logging
logger = logging.getLogger(__name__)

# Type definitions for job operations
class JobStatus(str, enum.Enum):
    """Enum for job status values.
    
    Represents the possible states of a job in the system:
    - PENDING: Job has been created but not yet started processing
    - PROCESSING: Job is currently being processed by the system
    - COMPLETED: Job has successfully completed processing
    - FAILED: Job processing failed with an error
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobRequest(BaseModel):
    """Request model for creating a new job.
    
    Attributes:
        message: The input message or query for the agent system
        metadata: Optional dictionary containing additional information about the job
        non_blocking: Optional flag to indicate if the request should be non-blocking
    """
    message: str = Field(..., description="The message or query for the agent system")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for job processing")
    non_blocking: bool = Field(False, description="If True, return job ID immediately; if False (default), wait for completion")

class JobResponse(BaseModel):
    """Response model for job creation and status.
    
    Attributes:
        job_id: Unique identifier for the job
        status: Current status of the job (pending, processing, completed, failed)
        created_at: ISO format timestamp when the job was created
        completed_at: ISO format timestamp when the job was completed (if applicable)
        result: Result data from the job (may be string or structured data)
        error: Error message if job failed
    """
    job_id: str = Field(..., description="Unique identifier for the job")
    status: JobStatus = Field(..., description="Current status of the job")
    created_at: str = Field(..., description="ISO format timestamp of job creation")
    completed_at: Optional[str] = Field(None, description="ISO format timestamp of job completion")
    result: Optional[Union[str, Dict[str, Any]]] = Field(None, description="Result data from job processing")
    error: Optional[str] = Field(None, description="Error message if job failed")

# Thread-safe lock for managing active job IDs
ACTIVE_JOB_IDS_LOCK = threading.RLock()
ACTIVE_JOB_IDS: Dict[int, str] = {}  # Thread ID to job ID mapping

# In-memory job storage (will be gradually replaced with database storage)
JOB_STORE: Dict[str, JobResponse] = {}

# Global set to track background tasks and prevent garbage collection
BACKGROUND_TASKS: set = set()

# Define the module interface
__all__ = [
    "JobStatus",
    "JobRequest",
    "JobResponse",
    "JOB_STORE",
    "ACTIVE_JOB_IDS",
    "ACTIVE_JOB_IDS_LOCK",
    "BACKGROUND_TASKS",
    "router",
    "process_message",
    "process_message_async",
    "get_job_status",
    "register_job_routes",
]

# Create router for job endpoints
router = APIRouter()

@router.get("/{job_id}", response_model=JobResponse, tags=["job", "mcp"])
async def get_job_status(job_id: str) -> JobResponse:
    """Get the status of a job.
    
    Args:
        job_id: The unique identifier for the job
        
    Returns:
        JobResponse: The current job status and results
        
    Raises:
        HTTPException: If the job is not found
    """
    if job_id not in JOB_STORE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")
    
    return JOB_STORE[job_id]

@router.post("/process", response_model=AgentResponse, tags=["job", "mcp"])
# Note: This endpoint is mounted at /job/process when register_job_routes is called
# but the frontend connects to /process directly, so we also need to handle this URL
async def process_message(request: MessageRequest) -> AgentResponse:
    """Process a message, either returning the final result or a job ID for polling.
    
    Args:
        request: The message request containing the prompt, metadata, and non_blocking flag
        
    Returns:
        AgentResponse: Either the final result (blocking mode) or a job ID (non-blocking mode)
        
    Raises:
        Exception: If job creation or processing fails
    """
    try:
        # Generate a job ID
        job_id = f"job-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        
        # Store the prompt with the job for later reference
        # Create a job entry with metadata including the prompt
        job = JobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=datetime.datetime.now().isoformat(),
            result={"metadata": {"prompt": request.message}}  # Include prompt for frontend to access
        )
        
        # Store the job
        JOB_STORE[job_id] = job
        logger.info(f"Created job {job_id} for message processing (non_blocking={request.non_blocking})")
        
        # Start processing in background task
        background_task = asyncio.create_task(
            process_message_async(job_id, request.message, request.metadata)
        )
        
        # Prevent task cancellation when the request completes
        background_task.set_name(f"job-{job_id}")
        
        # In FastAPI, we need to store the task to prevent garbage collection
        # We'll use a module-level variable to keep track of background tasks
        global BACKGROUND_TASKS
        if not hasattr(globals(), "BACKGROUND_TASKS"):
            BACKGROUND_TASKS = set()
        BACKGROUND_TASKS.add(background_task)
        
        # Clean up completed tasks and handle any exceptions
        def cleanup_task(task):
            # Remove the task from the global set
            global BACKGROUND_TASKS
            if hasattr(globals(), "BACKGROUND_TASKS") and task in BACKGROUND_TASKS:
                BACKGROUND_TASKS.remove(task)
            
            # Log any exceptions that weren't handled
            if task.cancelled():
                logger.warning(f"Background task for job {job_id} was cancelled")
            elif task.exception():
                logger.error(f"Background task for job {job_id} raised an exception: {task.exception()}")
                # Update job with error status if not already done
                if job_id in JOB_STORE and JOB_STORE[job_id].status != JobStatus.FAILED:
                    try:
                        job_data = JOB_STORE[job_id].dict()
                        job_data['status'] = JobStatus.FAILED
                        job_data['completed_at'] = datetime.datetime.now().isoformat()
                        job_data['error'] = str(task.exception())
                        JOB_STORE[job_id] = JobResponse(**job_data)
                    except Exception as e:
                        logger.error(f"Error updating job status: {e}")
        
        # Add the cleanup callback
        background_task.add_done_callback(cleanup_task)
        
        # Check if we should wait for completion or return immediately
        if request.non_blocking:
            # Non-blocking mode: return job ID immediately
            logger.info(f"Returning job ID immediately for non-blocking request: {job_id}")
            return AgentResponse(
                success=True, 
                response=job_id
            )
        else:
            # Blocking mode: wait for the task to complete and return the result
            logger.info(f"Waiting for job {job_id} to complete (blocking mode)")
            try:
                # Wait for the task to complete
                await background_task
                
                # Get the final job data
                job_data = JOB_STORE[job_id]
                
                if job_data.status == JobStatus.COMPLETED:
                    # Success: return the final result
                    result = job_data.result
                    return AgentResponse(
                        success=True,
                        response=result.get('response', str(result)) if isinstance(result, dict) else str(result)
                    )
                else:
                    # Job failed: return the error
                    return AgentResponse(
                        success=False,
                        response="Job processing failed",
                        error=job_data.error or "Unknown error occurred"
                    )
            except Exception as wait_error:
                logger.error(f"Error waiting for job {job_id} completion: {str(wait_error)}")
                return AgentResponse(
                    success=False,
                    response="Error during job processing",
                    error=str(wait_error)
                )
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        return AgentResponse(success=False, response="", error=str(e))

def reset_registry():
    """Reset the OUTPUT_REGISTRY to an empty dictionary.
    
    This utility function helps avoid circular dependencies by providing
    a centralized way to reset the registry.
    
    Returns:
        None
    """
    # Access OUTPUT_REGISTRY from the common module
    from modules.common import OUTPUT_REGISTRY
    # Clear the registry by creating a new dictionary
    OUTPUT_REGISTRY.clear()
    
async def process_message_async(job_id: str, message: str, metadata: Dict[str, Any]) -> None:
    """
    Process a message asynchronously in a background task.
    This function is designed to run as a detached task that won't be affected
    by the request lifecycle.
    
    Args:
        job_id: The unique identifier for the job
        message: The input message to process
        metadata: Additional metadata for job processing
        
    Returns:
        None: The function updates the job status in-place
        
    Raises:
        Exception: If message processing fails, the exception is caught
                  and the job is marked as failed
    """
    
    try:
        # Store message in thread-specific storage for database operations
        thread_id = threading.get_ident()
        # Store message for this thread
        MEMORY_STEP_STORE.active_messages[thread_id] = message
        logger.info(f"Stored message for thread {thread_id} and job {job_id}")
        
        # Update job status to processing
        job_data = JOB_STORE[job_id].dict()
        job_data['status'] = JobStatus.PROCESSING
        
        # Make sure prompt is stored in metadata
        if job_data.get('result') is None:
            # Initialize result with metadata if not already set
            job_data['result'] = {'metadata': {'prompt': message}}
        elif isinstance(job_data.get('result'), dict) and 'metadata' not in job_data['result']:
            # Add metadata field if result exists but doesn't have metadata
            job_data['result']['metadata'] = {'prompt': message}
        elif isinstance(job_data.get('result'), dict) and 'metadata' in job_data['result']:
            # Update metadata.prompt if metadata exists
            job_data['result']['metadata']['prompt'] = message
        
        JOB_STORE[job_id] = JobResponse(**job_data)
        
        
        
        # Create or update the job in database
        if os.getenv('PG_CONNECTION_STRING'):
            try:
                # Connect to the database
                conn = get_database_connection()
                if conn:
                    cursor = conn.cursor()
                    
                    # First check if job exists in database
                    cursor.execute(
                        "SELECT job_id FROM agent_flow_jobs WHERE job_id = %s",
                        (job_id,)
                    )
                    
                    if cursor.fetchone():
                        # Update existing job record with prompt and set status to processing
                        cursor.execute(
                            """
                            UPDATE agent_flow_jobs
                            SET metadata = jsonb_set(
                                COALESCE(metadata, '{}'::jsonb),
                                '{prompt}',
                                to_jsonb(%s::text)
                            ),
                            status = 'processing',
                            updated_at = NOW()
                            WHERE job_id = %s
                            """,
                            (json.dumps(message), job_id)
                        )
                        logger.info(f"Updated job {job_id} in database with prompt and processing status")
                    else:
                        # Create new job record with processing status
                        # Use the flow name and git server name set at generation time
                        flow_name = "DynexNewDocsReport"
                        git_server_name = "demos"
                        
                        cursor.execute(
                            """
                            INSERT INTO agent_flow_jobs 
                            (job_id, git_server_name, flow_name, status, created_at, updated_at, metadata)
                            VALUES (%s, %s, %s, 'processing', NOW(), NOW(), %s::jsonb)
                            """,
                            (
                                job_id, 
                                git_server_name, 
                                flow_name,
                                json.dumps({
                                    'created_from': 'agent_service',
                                    'timestamp': datetime.datetime.now().isoformat(),
                                    'prompt': message
                                })
                            )
                        )
                        logger.info(f"Created job {job_id} in database with processing status")
                    
                    conn.commit()
            except Exception as db_error:
                logger.error(f"Failed to update job in database: {db_error}")
            finally:
                if 'conn' in locals() and conn:
                    conn.close()
        
        # Get current thread ID to manage concurrent jobs
        thread_id = threading.get_ident()
        logger.info(f"Processing job {job_id} on thread {thread_id}")
        
        # Associate this thread with the job ID for callbacks
        with ACTIVE_JOB_IDS_LOCK:
            ACTIVE_JOB_IDS[thread_id] = job_id
            logger.info(f"Set job ID {job_id} for thread {thread_id}")
        
        # Initialize or reset the output registry
        reset_registry()
        
        # Process the message with the manager agent
        try:
            # Ensure MANAGER is initialized
            from modules.agents import MANAGER, initialize_agents, step_callback
            if MANAGER is None:
                logger.error("MANAGER is None in job processing. Attempting to initialize...")
                initialize_agents()
                if MANAGER is None:
                    raise RuntimeError("Failed to initialize MANAGER. Agent processing cannot continue.")
            
            # Set up step callback to track execution
            if not hasattr(MANAGER, 'step_callbacks') or MANAGER.step_callbacks is None:
                MANAGER.step_callbacks = []
            if step_callback not in MANAGER.step_callbacks:
                MANAGER.step_callbacks.append(step_callback)
            
            # Create an initial step to establish the job context
            from modules.agents import create_initial_step
            initial_step, formatted_prompt = create_initial_step(message, job_id, metadata)
            
            # Execute the agent with the formatted prompt
            logger.info(f"Executing manager agent with message: {message[:100]}...")
            logger.warning(f"[JOB_ID_DEBUG] About to call MANAGER.run with job_id {job_id} on thread {threading.get_ident()}")
            
            # Verify job_id is set in the current thread
            with ACTIVE_JOB_IDS_LOCK:
                current_thread_job_id = ACTIVE_JOB_IDS.get(threading.get_ident())
                all_job_ids = {tid: jid for tid, jid in ACTIVE_JOB_IDS.items()}
                logger.warning(f"[JOB_ID_DEBUG] Thread {threading.get_ident()} has job_id {current_thread_job_id} before MANAGER.run")
                logger.warning(f"[JOB_ID_DEBUG] All job IDs before MANAGER.run: {all_job_ids}")
                if job_id != current_thread_job_id:
                    logger.warning(f"[JOB_ID_DEBUG] Mismatch between job_id {job_id} and thread job_id {current_thread_job_id}")
                    # Ensure job_id is set correctly
                    ACTIVE_JOB_IDS[threading.get_ident()] = job_id
                    logger.warning(f"[JOB_ID_DEBUG] Re-set job_id to {job_id} for thread {threading.get_ident()}")
            
            # Final check to ensure MANAGER is initialized
            if MANAGER is None:
                raise RuntimeError("MANAGER is None after initialization attempts. Cannot run agent.")
                
            final_result = MANAGER.run(formatted_prompt)
            logger.warning(f"[JOB_ID_DEBUG] MANAGER.run completed for job_id {job_id}")
            
            # Update the initial step with end time
            initial_step.end_time = datetime.datetime.now().timestamp()
            initial_step.duration = initial_step.end_time - initial_step.start_time
            
            logger.info(f"Agent execution completed for job {job_id}")
        except Exception as agent_error:
            import traceback
            stack_trace = traceback.format_exc()
            logger.error(f"Agent execution error for job {job_id}: {str(agent_error)}\nStack trace:\n{stack_trace}")
            
            # Also check if this is socket related
            if "write could not complete without blocking" in str(agent_error):
                logger.error(f"SOCKET BUFFER ERROR DETECTED: This is likely due to a WebSocket buffer issue")
                logger.error(f"Socket details: {getattr(agent_error, 'errno', 'N/A')}, {getattr(agent_error, 'strerror', 'N/A')}")
                
                # Try to get more info about active connections
                try:
                    import socket
                    open_sockets = len(socket._socketobjects) if hasattr(socket, '_socketobjects') else "unknown"
                    logger.error(f"Active socket count: {open_sockets}")
                except Exception as sock_err:
                    logger.error(f"Could not check socket count: {sock_err}")
            
            raise agent_error
        
        # Update job with completed status and result
        job_data = JOB_STORE[job_id].dict()
        job_data['status'] = JobStatus.COMPLETED
        job_data['completed_at'] = datetime.datetime.now().isoformat()
        
        # Check if there's a designated output node and if its output is in the registry
        output_node_id = "agent_1745420716020"
        
        # Try different formats for the output node id (with and without tool- prefix)
        if output_node_id in OUTPUT_REGISTRY:
            output_response = OUTPUT_REGISTRY[output_node_id]
            logger.info(f"Found output from designated output node {output_node_id}")
        elif f"tool-{output_node_id}" in OUTPUT_REGISTRY:
            output_response = OUTPUT_REGISTRY[f"tool-{output_node_id}"]
            logger.info(f"Found output from designated output node with tool- prefix: tool-{output_node_id}")
        elif output_node_id.startswith("tool-") and output_node_id[5:] in OUTPUT_REGISTRY:
            output_response = OUTPUT_REGISTRY[output_node_id[5:]]
            logger.info(f"Found output from designated output node without tool- prefix: {output_node_id[5:]}")
        else:
            # Fall back to the MANAGER result if no output node is found
            output_response = final_result
            logger.warning(f"No output found in registry for designated output node {output_node_id}, using MANAGER result instead")
        
        # Store result in format expected by the frontend (with response field)
        job_data['result'] = {
            'response': output_response
        }
        JOB_STORE[job_id] = JobResponse(**job_data)
        logger.info(f"Completed job {job_id}")
        
        
        
        # Update job result in the database
        if os.getenv('PG_CONNECTION_STRING'):
            try:
                # Connect to the database
                conn = get_database_connection()
                if conn:
                    cursor = conn.cursor()
                    
                    # Update job record with the result
                    # Prepare parameters and log details for debugging
                    # Use the same output_response that was used to update the job store
                    result_data = {
                        'response': output_response
                    }
                    
                    logger.info(f"Attempting to update job {job_id} in database with result data")
                    logger.info(f"Data length: {len(str(result_data))}, Job ID: {job_id}")
                    logger.info(f"Result content snippet: {str(result_data)[:200]}...")
                    
                    # Execute the update with proper JSONB handling
                    # First check if the job exists
                    cursor.execute(
                        "SELECT job_id FROM agent_flow_jobs WHERE job_id = %s",
                        (job_id,)
                    )
                    job_exists = cursor.fetchone() is not None
                    
                    if not job_exists:
                        # Job doesn't exist yet, create it
                        logger.info(f"Job {job_id} not found in database during result update, creating it")
                        # Use the flow name and git server name set at generation time
                        flow_name = "DynexNewDocsReport"
                        git_server_name = "demos"
                        logger.info(f"Using flow name '{flow_name}' and git server '{git_server_name}' from template for job {job_id}")
                        
                        # Insert job with result
                        cursor.execute(
                            """
                            INSERT INTO agent_flow_jobs 
                            (job_id, git_server_name, flow_name, status, completed_at, result, metadata, created_at, updated_at)
                            VALUES (%s, %s, %s, 'completed', NOW(), %s::jsonb, %s::jsonb, NOW(), NOW())
                            """,
                            (
                                job_id, 
                                git_server_name, 
                                flow_name,
                                json.dumps(result_data),
                                json.dumps({
                                    'created_from': 'agent_service',
                                    'timestamp': datetime.datetime.now().isoformat(),
                                    'prompt': MEMORY_STEP_STORE.active_messages.get(threading.get_ident(), '')
                                })
                            )
                        )
                        logger.info(f"Created job {job_id} with result during final update")
                    else:
                        # Update existing job
                        cursor.execute(
                            """
                            UPDATE agent_flow_jobs
                            SET status = 'completed', completed_at = NOW(), result = %s::jsonb
                            WHERE job_id = %s
                            """,
                            (json.dumps(result_data), job_id)
                        )
                    
                    # Check row count
                    rows_updated = cursor.rowcount
                    logger.info(f"Database update affected {rows_updated} rows")
                    
                    # Verify update successful by querying the row
                    cursor.execute(
                        "SELECT result FROM agent_flow_jobs WHERE job_id = %s",
                        (job_id,)
                    )
                    db_result = cursor.fetchone()
                    if db_result and db_result[0]:
                        logger.info(f"Verified result column updated successfully: {str(db_result[0])[:100]}...")
                    else:
                        logger.error(f"Result column is still NULL or empty after update for job {job_id}")
                    
                    conn.commit()
                    logger.info(f"Updated job {job_id} in database with response data")
            except Exception as db_error:
                logger.error(f"Failed to update job in database: {db_error}")
            finally:
                if 'conn' in locals() and conn:
                    conn.close()
        
    except Exception as e:
        import traceback
        stack_trace = traceback.format_exc()
        logger.error(f"Error processing job {job_id}: {str(e)}\nStack trace:\n{stack_trace}")
        # Update job with error status
        if job_id in JOB_STORE:
            job_data = JOB_STORE[job_id].dict()
            job_data['status'] = JobStatus.FAILED
            job_data['completed_at'] = datetime.datetime.now().isoformat()
            job_data['error'] = str(e)
            
            # Preserve the result structure with response for consistent frontend handling
            if isinstance(job_data.get('result'), dict) and 'metadata' in job_data['result']:
                # Keep the metadata but update with error response
                job_data['result']['response'] = f"Error: {str(e)}"
            else:
                # Create new result structure with error response
                job_data['result'] = {
                    'response': f"Error: {str(e)}",
                    'metadata': {'prompt': message} if 'message' in locals() else {}
                }
                
            JOB_STORE[job_id] = JobResponse(**job_data)
            
            
        
        # Update the error status in database
        if os.getenv('PG_CONNECTION_STRING'):
            try:
                # Connect to the database
                conn = get_database_connection()
                if conn:
                    cursor = conn.cursor()
                    
                    # Check if job exists in database
                    cursor.execute(
                        "SELECT job_id FROM agent_flow_jobs WHERE job_id = %s",
                        (job_id,)
                    )
                    
                    if cursor.fetchone():
                        # Update job with error status
                        cursor.execute(
                            """
                            UPDATE agent_flow_jobs
                            SET status = 'error', 
                                error = %s,
                                completed_at = NOW(), 
                                updated_at = NOW()
                            WHERE job_id = %s
                            """,
                            (str(e), job_id)
                        )
                        logger.info(f"Updated job {job_id} status to error in database")
                        conn.commit()
                    else:
                        logger.warning(f"Could not update job {job_id} in database: job not found")
            except Exception as db_error:
                logger.error(f"Failed to update job error status in database: {db_error}")
            finally:
                if 'conn' in locals() and conn:
                    conn.close()

def register_job_routes(app: FastAPI) -> None:
    """Register job routes with FastAPI application.
    
    Args:
        app: The FastAPI application instance
        
    Returns:
        None
    """
    app.include_router(router, prefix="/job", tags=["job"])