"""Memory storage for agent steps with real-time event support.

This module provides a centralized storage system for tracking agent execution steps,
broadcasting real-time events to clients via SSE and WebSockets, and persisting step
information to a PostgreSQL database. It serves as the core memory and communication
backbone of the multi-agent system.

Responsibilities:
1. Store agent and tool execution steps with context
2. Manage real-time event broadcast via SSE and WebSockets
3. Persist steps to PostgreSQL database with relationship tracking
4. Support hierarchical step relationships and lineage visualization
"""
import os
import json
import logging
import asyncio
import datetime
import threading
from typing import Dict, Any, List, Optional, Sequence, Union, Set, Tuple, Awaitable, Callable, TypedDict

# Import the shared job tracking variables
try:
    from api.job import ACTIVE_JOB_IDS, ACTIVE_JOB_IDS_LOCK
except ImportError:
    # Fallback if not yet imported (for circular import prevention)
    ACTIVE_JOB_IDS: Dict[int, str] = {}
    ACTIVE_JOB_IDS_LOCK: threading.Lock = threading.Lock()

# FastAPI imports
from fastapi import WebSocket, WebSocketDisconnect

# Agent-specific imports
from smolagents.memory import ActionStep



# Setup logger
logger = logging.getLogger(__name__)

# Custom type definitions
class AgentStep(TypedDict, total=False):
    """Type definition for an agent execution step."""
    id: str
    agent_name: str
    agent_type: str
    step_number: int
    depth: int
    start_time: Union[int, float, str]
    end_time: Union[int, float, str, None]
    duration: Union[int, float, None]
    timestamp: str
    observations: Optional[str]
    error: Optional[str]
    action_output: Optional[str]
    tool_calls: List[Dict[str, Any]]
    step_type: str
    parent_step_id: Optional[str]
    child_step_ids: List[str]
    job_id: Optional[str]

class ToolStep(TypedDict, total=False):
    """Type definition for a tool execution step."""
    id: str
    tool_name: str
    tool_id: str
    agent_name: str
    agent_type: str
    step_number: int
    depth: int
    start_time: Union[int, float, str]
    end_time: Union[int, float, str, None]
    duration: Union[int, float, None]
    timestamp: str
    arguments: Dict[str, Any]
    observation: Optional[str]
    error: Optional[str]
    step_type: str
    parent_step_id: str
    job_id: Optional[str]

class SSEMessage(TypedDict):
    """Type definition for a Server-Sent Event message."""
    event: str
    data: str

class MemoryStepStore:
    """Stores memory steps from all agents with agent context and supports real-time events.
    
    The MemoryStepStore serves as the central repository for all agent and tool execution steps.
    It provides functionality for:
    
    1. Adding and retrieving steps with proper locking for thread safety
    2. Broadcasting steps to clients in real-time via SSE and WebSockets
    3. Persisting steps to a PostgreSQL database
    4. Managing hierarchical relationships between steps
    5. Supporting real-time monitoring of agent execution
    
    This class is designed to be used as a singleton, with the MEMORY_STEP_STORE instance
    being imported and used throughout the application.
    """
    
    def __init__(self):
        """Initialize the MemoryStepStore with empty collections and synchronization primitives."""
        self.steps: List[AgentStep] = []
        self.tool_steps: List[ToolStep] = []  # Track tool steps separately
        self.lock: threading.Lock = threading.Lock()
        self.event_listeners: Set[asyncio.Queue] = set()  # Store listeners for SSE
        self.websocket_connections: Set[WebSocket] = set()  # Store active websocket connections
        self.active_messages: Dict[int, str] = {}  # Map of thread ID to message for thread-safe message tracking
        
    async def add_listener(self) -> asyncio.Queue:
        """Add a new SSE event listener and return the event queue.
        
        This method creates a new asyncio.Queue for the SSE client to receive events,
        registers it with the MemoryStepStore, and sends all existing steps as an initial event.
        
        Returns:
            asyncio.Queue: A queue that will receive SSE events as they occur.
            
        Raises:
            Exception: If there's an error adding the listener or sending initial steps.
        """
        queue = asyncio.Queue()
        self.event_listeners.add(queue)
        logger.info(f"[SSE] New client connection established, total listeners: {len(self.event_listeners)}")
        try:
            # Send existing steps to new listener
            with self.lock:
                combined_steps: List[Union[AgentStep, ToolStep]] = self.steps.copy() + self.tool_steps.copy()
                combined_steps.sort(key=lambda x: x.get("timestamp", ""))
                if combined_steps:
                    logger.info(f"[SSE] Sending initial event with {len(combined_steps)} existing steps to new client")
                    await queue.put({
                        "event": "initial",
                        "data": json.dumps({"steps": combined_steps, "total": len(combined_steps)})
                    })
            
            # Return the queue for the listener to consume events
            return queue
        except Exception as e:
            logger.error(f"Error adding listener: {e}")
            self.event_listeners.discard(queue)
            raise
    
    def remove_listener(self, queue: asyncio.Queue) -> None:
        """Remove an SSE event listener.
        
        Args:
            queue (asyncio.Queue): The queue that was previously registered with add_listener().
        """
        self.event_listeners.discard(queue)
        logger.info(f"[SSE] Client disconnected, remaining listeners: {len(self.event_listeners)}")
        
    async def add_websocket(self, websocket: WebSocket) -> None:
        """Add a new WebSocket connection and send initial steps.
        
        This method accepts a new WebSocket connection, registers it with the MemoryStepStore,
        and sends all existing steps as an initial event.
        
        Args:
            websocket (WebSocket): The FastAPI WebSocket connection to register.
        """
        await websocket.accept()
        self.websocket_connections.add(websocket)
        logger.info(f"[WS] New WebSocket connection established, total connections: {len(self.websocket_connections)}")
        
        # Send existing steps to new websocket connection
        with self.lock:
            combined_steps: List[Union[AgentStep, ToolStep]] = self.steps.copy() + self.tool_steps.copy()
            combined_steps.sort(key=lambda x: x.get("timestamp", ""))
            if combined_steps:
                logger.info(f"[WS] Sending initial event with {len(combined_steps)} existing steps to new WebSocket client")
                try:
                    await websocket.send_json({
                        "event": "initial",
                        "data": {"steps": combined_steps, "total": len(combined_steps)}
                    })
                except Exception as e:
                    logger.error(f"Error sending initial data to WebSocket: {e}")
                    self.websocket_connections.discard(websocket)
    
    def remove_websocket(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection.
        
        Args:
            websocket (WebSocket): The WebSocket connection to remove.
        """
        self.websocket_connections.discard(websocket)
        logger.info(f"[WS] WebSocket client disconnected, remaining connections: {len(self.websocket_connections)}")
        
    async def broadcast_step(self, step_data: Union[AgentStep, ToolStep, Dict[str, Any]]) -> None:
        """Broadcast a step to all registered SSE and WebSocket clients.
        
        This method distributes step information to all connected clients in real-time,
        allowing for live monitoring of agent execution. It handles both agent steps and
        tool steps, and manages error conditions gracefully.
        
        Args:
            step_data (Union[AgentStep, ToolStep, Dict[str, Any]]): The step data to broadcast.
                Can be either an AgentStep, ToolStep, or a compatible dictionary.
        """
        # Exit early if no listeners
        if not self.event_listeners and not self.websocket_connections:
            return
            
        # Log step information
        step_type = step_data.get("step_type", "agent")
        agent_name = step_data.get("agent_name", "unknown")
        step_number = step_data.get("step_number", "unknown")
        if step_type == "tool":
            tool_name = step_data.get("tool_name", "unknown")
            logger.info(f"[Broadcast] Broadcasting tool step: tool={tool_name}, agent={agent_name}, SSE listeners={len(self.event_listeners)}, WS connections={len(self.websocket_connections)}")
        else:
            logger.info(f"[Broadcast] Broadcasting agent step: agent={agent_name}, step={step_number}, SSE listeners={len(self.event_listeners)}, WS connections={len(self.websocket_connections)}")
        
        # Prepare SSE message
        sse_message: SSEMessage = {
            "event": "step",
            "data": json.dumps(step_data)
        }
        
        # Broadcast to SSE listeners
        if self.event_listeners:
            # Copy the set to avoid modification during iteration
            listeners = self.event_listeners.copy()
            sent_count = 0
            for queue in listeners:
                try:
                    await queue.put(sse_message)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Error broadcasting to SSE listener: {e}")
                    self.event_listeners.discard(queue)
            
            logger.debug(f"[SSE] Successfully sent step to {sent_count}/{len(listeners)} SSE listeners")
        
        # Broadcast to WebSocket connections
        if self.websocket_connections:
            # Copy the set to avoid modification during iteration
            websockets = self.websocket_connections.copy()
            ws_sent_count = 0
            for websocket in websockets:
                try:
                    await websocket.send_json({
                        "event": "step",
                        "data": step_data
                    })
                    ws_sent_count += 1
                except Exception as e:
                    logger.error(f"Error broadcasting to WebSocket: {e}")
                    self.websocket_connections.discard(websocket)
            
            logger.debug(f"[WS] Successfully sent step to {ws_sent_count}/{len(websockets)} WebSocket connections")
        
    async def store_step_in_database(self, step_data: Union[AgentStep, ToolStep, Dict[str, Any]]) -> None:
        """Store a step in the PostgreSQL database with proper relationship tracking.
        
        This method persists agent and tool steps to a PostgreSQL database, handling:
        1. Job record creation (if needed)
        2. Step creation with appropriate fields for agent vs. tool steps
        3. Relationship tracking between parent and child steps
        4. Error handling and transaction management
        
        The database schema includes:
        - agent_flow_jobs: Stores job metadata
        - agent_flow_steps: Stores individual step data
        - agent_flow_step_relationships: Tracks parent-child relationships between steps
        
        Args:
            step_data (Union[AgentStep, ToolStep, Dict[str, Any]]): The step data to store.
                Must include an 'id' field and preferably a 'job_id' field.
        """
        # Skip database operations if no database connection string is available
        if not os.getenv('PG_CONNECTION_STRING'):
            logger.debug("Skipping database storage: No PG_CONNECTION_STRING environment variable")
            return
        
        # Skip if job_id is missing
        if not step_data.get('job_id'):
            logger.debug(f"Skipping database storage for step {step_data['id']}: No job_id provided")
            return
            
        try:
            import psycopg2
            import json
            from psycopg2.extras import Json
            
            # Connect to the database
            conn = psycopg2.connect(os.getenv('PG_CONNECTION_STRING'))
            cursor = conn.cursor()
            
            # Begin transaction
            conn.autocommit = False
            
            # First, ensure the job exists in agent_flow_jobs
            job_id = step_data.get('job_id')
            
            # Check if job exists
            cursor.execute(
                "SELECT job_id FROM agent_flow_jobs WHERE job_id = %s",
                (job_id,)
            )
            
            job_exists = cursor.fetchone() is not None
            
            if not job_exists:
                # Need to create the job record first to satisfy foreign key constraint
                # Extract git_server_name and flow_name from jobs in memory if possible
                git_server_name = "unknown"
                flow_name = "unknown"
                
                # Use the flow name and git server name set at generation time
                flow_name = "DynexNewDocsReport"
                git_server_name = "demos"
                logger.info(f"Using flow name '{flow_name}' and git server '{git_server_name}' from template for job {job_id}")
                
                # Insert placeholder job record - default to processing status since we're logging steps
                logger.info(f"Creating placeholder job record in database for job_id: {job_id}")
                # Ensure we store the actual prompt instead of null
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
                            'prompt': MEMORY_STEP_STORE.active_messages.get(threading.get_ident(), '')  # Get message from thread-specific storage
                        })
                    )
                )
            
            # Now check if step already exists (for idempotency)
            cursor.execute(
                "SELECT step_id FROM agent_flow_steps WHERE step_id = %s",
                (step_data['id'],)
            )
            
            if cursor.fetchone():
                # Step already exists, update it
                logger.debug(f"Step {step_data['id']} already exists in database, updating")
                
                # Prepare update parameters
                params = []
                update_fields = []
                
                # Common fields for both agent and tool steps
                field_mappings = {
                    'status': ('status', lambda x: 'completed'),  # Always mark as completed in DB
                    'timestamp': ('updated_at', lambda x: x)
                }
                
                # Store error in metadata JSONB field since there is no dedicated error column
                if 'error' in step_data and step_data['error'] is not None:
                    update_fields.append("metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{error}', %s::jsonb, true)")
                    params.append(json.dumps(step_data['error']))
                
                # Add agent-specific fields
                if step_data.get('step_type') == 'agent':
                    field_mappings.update({
                        'action_output': ('output', lambda x: x),
                        'observations': ('observation', lambda x: x),
                        'tool_calls': ('tool_call', lambda x: Json(x) if x else None)
                    })
                # Add tool-specific fields
                elif step_data.get('step_type') == 'tool':
                    field_mappings.update({
                        'observation': ('observation', lambda x: x),
                        'arguments': ('tool_call', lambda x: Json({'arguments': x}) if x else None)
                    })
                
                # Build the update query
                for source_field, (target_field, transform_func) in field_mappings.items():
                    if source_field in step_data and step_data[source_field] is not None:
                        update_fields.append(f"{target_field} = %s")
                        params.append(transform_func(step_data[source_field]))
                
                # Add completed_at if not already set
                if step_data.get('end_time'):
                    update_fields.append("completed_at = %s")
                    # Convert numeric timestamp to ISO format string if needed
                    end_time = step_data['end_time']
                    if isinstance(end_time, (int, float)):
                        # Convert milliseconds or seconds since epoch to datetime object
                        if end_time > 1e12:  # Likely milliseconds
                            end_time = datetime.datetime.fromtimestamp(end_time / 1000.0)
                        else:  # Likely seconds
                            end_time = datetime.datetime.fromtimestamp(end_time)
                        # Format as ISO string
                        end_time = end_time.isoformat()
                    params.append(end_time)
                else:
                    update_fields.append("completed_at = NOW()")
                    
                # Only update if we have fields to update
                if update_fields:
                    # Add the step_id as the last parameter
                    params.append(step_data['id'])
                    
                    # Execute the update
                    cursor.execute(
                        f"UPDATE agent_flow_steps SET {', '.join(update_fields)} WHERE step_id = %s",
                        params
                    )
            else:
                # Step doesn't exist, insert it
                logger.debug(f"Inserting new step {step_data['id']} into database")
                
                # Common parameters for both step types
                params = [
                    step_data['id'],  # step_id
                    step_data.get('job_id'),  # job_id
                    step_data.get('parent_step_id'),  # parent_step_id
                    step_data.get('agent_name'),  # agent_name
                    step_data.get('step_type', 'agent'),  # type
                ]
                
                # Format timestamps properly
                start_time = step_data.get('start_time')
                end_time = step_data.get('end_time')
                
                # Convert numeric timestamp to ISO format string if needed
                if isinstance(start_time, (int, float)):
                    # Convert milliseconds or seconds since epoch to datetime object
                    if start_time > 1e12:  # Likely milliseconds
                        start_time = datetime.datetime.fromtimestamp(start_time / 1000.0)
                    else:  # Likely seconds
                        start_time = datetime.datetime.fromtimestamp(start_time)
                    # Format as ISO string
                    start_time = start_time.isoformat()
                    
                if isinstance(end_time, (int, float)):
                    # Convert milliseconds or seconds since epoch to datetime object
                    if end_time > 1e12:  # Likely milliseconds
                        end_time = datetime.datetime.fromtimestamp(end_time / 1000.0)
                    else:  # Likely seconds
                        end_time = datetime.datetime.fromtimestamp(end_time)
                    # Format as ISO string
                    end_time = end_time.isoformat()
                
                # Different fields based on step type
                if step_data.get('step_type') == 'agent':
                    # For agent steps
                    params.extend([
                        step_data.get('action_output'),  # input (using action_output)
                        step_data.get('action_output'),  # output
                        Json(step_data.get('tool_calls', [])) if step_data.get('tool_calls') else None,  # tool_call
                        step_data.get('observations'),  # observation
                        'completed',  # status (always completed when stored)
                        Json({  # metadata
                            'step_number': step_data.get('step_number'),
                            'depth': step_data.get('depth', 1),  # Store depth in metadata
                            'start_time': start_time,
                            'end_time': end_time,
                            'duration': step_data.get('duration'),
                            'agent_type': step_data.get('agent_type')
                        })
                    ])
                else:
                    # For tool steps
                    params.extend([
                        None,  # input (not applicable for tools)
                        None,  # output (not applicable for tools)
                        Json({'arguments': step_data.get('arguments', {})}) if step_data.get('arguments') else None,  # tool_call
                        step_data.get('observation'),  # observation
                        'completed',  # status (always completed when stored)
                        Json({  # metadata
                            'tool_name': step_data.get('tool_name'),
                            'tool_id': step_data.get('tool_id'),
                            'step_number': step_data.get('step_number'),
                            'depth': step_data.get('depth', 1),  # Store depth in metadata
                            'start_time': start_time,
                            'end_time': end_time,
                            'duration': step_data.get('duration'),
                            'agent_type': step_data.get('agent_type')
                        })
                    ])
                
                # Store the metadata as a separate variable to avoid confusion
                metadata_json = params[-1]  # Last param is the metadata Json
                params_without_metadata = params[:-1]  # All but the last param
                
                # Insert the step - include completed_at timestamp
                if end_time:
                    # Make sure end_time is a string, not a JSON object
                    end_time_str = end_time if isinstance(end_time, str) else str(end_time)
                    
                    cursor.execute(
                        """
                        INSERT INTO agent_flow_steps
                        (step_id, job_id, parent_step_id, agent_name, type, input, output, tool_call, observation, status, completed_at, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        params_without_metadata + [end_time_str, metadata_json]  # Add the end_time for completed_at
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO agent_flow_steps
                        (step_id, job_id, parent_step_id, agent_name, type, input, output, tool_call, observation, status, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        params
                    )
            
            # Create relationships between steps
            # Enable relationship creation in the database
            if step_data.get('child_step_ids'):
                for child_id in step_data['child_step_ids']:
                    try:
                        # First check if the child step exists
                        cursor.execute(
                            "SELECT step_id FROM agent_flow_steps WHERE step_id = %s",
                            (child_id,)
                        )
                        
                        if cursor.fetchone():
                            # Child exists, safe to create relationship
                            cursor.execute(
                                """
                                INSERT INTO agent_flow_step_relationships (parent_step_id, child_step_id)
                                VALUES (%s, %s)
                                ON CONFLICT (parent_step_id, child_step_id) DO NOTHING
                                """,
                                (step_data['id'], child_id)
                            )
                        else:
                            logger.debug(f"Skipping relationship creation: Child step {child_id} doesn't exist yet")
                    except Exception as rel_error:
                        logger.warning(f"Error creating relationship from {step_data['id']} to {child_id}: {rel_error}")
                        # Continue with other relationships
            
            # Commit the transaction
            conn.commit()
            logger.debug(f"Successfully stored step {step_data['id']} in database")
            
        except Exception as e:
            # Rollback transaction on error
            if 'conn' in locals() and conn:
                try:
                    conn.rollback()
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback transaction: {rollback_error}")
                    
            logger.error(f"Failed to store step in database: {e}")
            # Continue with local storage even if database operation fails
        finally:
            # Close the database connection
            if 'conn' in locals() and conn:
                conn.close()

    def get_job_metadata(self, job_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get metadata for the specified job or current job.
        
        This method retrieves metadata for the specified job, or if no job ID is provided,
        it attempts to get the job ID from the current thread.
        
        Args:
            job_id (Optional[str]): The job ID to get metadata for. If None, uses the current thread's job ID.
            
        Returns:
            Optional[Dict[str, Any]]: The job metadata if found, None otherwise.
        """
        if not job_id:
            # Try to get job ID from the current thread
            thread_id = threading.get_ident()
            with ACTIVE_JOB_IDS_LOCK:
                job_id = ACTIVE_JOB_IDS.get(thread_id)
                if not job_id:
                    logger.warning(f"No job ID found for thread {thread_id}")
                    return None
        
        # Try to get metadata from the database if available
        try:
            if os.getenv('PG_CONNECTION_STRING'):
                # Import here to avoid circular imports
                from modules.utils import get_database_connection
                
                conn = get_database_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT metadata FROM agent_flow_jobs WHERE job_id = %s",
                        (job_id,)
                    )
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result and result[0]:
                        logger.info(f"Retrieved metadata for job {job_id} from database")
                        return result[0]
        except Exception as e:
            logger.warning(f"Error retrieving job metadata from database: {e}")
        
        # Try to get metadata from the job store in memory
        try:
            # Import here to avoid circular imports
            from api.job import JOB_STORE
            
            if job_id in JOB_STORE and hasattr(JOB_STORE[job_id], 'result') and isinstance(JOB_STORE[job_id].result, dict):
                if 'metadata' in JOB_STORE[job_id].result:
                    logger.info(f"Retrieved metadata for job {job_id} from JOB_STORE")
                    return JOB_STORE[job_id].result['metadata']
        except Exception as e:
            logger.warning(f"Error retrieving job metadata from JOB_STORE: {e}")
        
        logger.warning(f"No metadata found for job {job_id}")
        return None
    
    def add_step(self, step: ActionStep, agent_name: str, agent_type: str, 
              parent_step_id: Optional[str] = None, job_id: Optional[str] = None,
              tool_name: Optional[str] = None, step_number: Optional[str] = None) -> None:
        """Add a memory step with agent context and broadcast to listeners.
        
        This is the main entry point for recording agent execution steps. It:
        1. Creates an agent step record with complete context
        2. Creates tool step records for any tool calls made by the agent
        3. Establishes parent-child relationships between steps
        4. Asynchronously persists steps to the database
        5. Broadcasts steps to all connected clients
        6. Extracts MCP tool calls from Python interpreter code
        
        Args:
            step (ActionStep): The agent's action step to record
            agent_name (str): The name of the agent executing the step
            agent_type (str): The type of agent (e.g., manager, worker)
            parent_step_id (Optional[str]): The ID of the parent step if this is a child step
            job_id (Optional[str]): The job ID this step belongs to (required for database persistence)
            tool_name (Optional[str]): For explicit tool step creation, the name of the tool
            step_number (Optional[str]): For explicit tool step creation, the step number
            
        Raises:
            ValueError: If job_id is missing but required for step creation
        """
        step_data: Optional[AgentStep] = None
        tool_step_data: Optional[ToolStep] = None
        
        with self.lock:
            # Generate a deterministic ID for this step using the job_id
            if not job_id:
                # Try to get job_id from the current thread
                thread_id = threading.get_ident()
                logger.warning(f"[JOB_ID_DEBUG] Memory.add_step: No job_id provided for agent {agent_name}, looking in thread {thread_id}")
                
                # Check all threads for job IDs (for debugging)
                with ACTIVE_JOB_IDS_LOCK:
                    all_thread_ids = {tid: jid for tid, jid in ACTIVE_JOB_IDS.items()}
                    logger.warning(f"[JOB_ID_DEBUG] All active job IDs: {all_thread_ids}")
                    thread_job_id = ACTIVE_JOB_IDS.get(thread_id)
                    logger.warning(f"[JOB_ID_DEBUG] Thread {thread_id} job_id lookup result: {thread_job_id}")
                
                if thread_job_id:
                    job_id = thread_job_id
                    logger.warning(f"[JOB_ID_DEBUG] Successfully retrieved job_id {job_id} from thread {thread_id} for agent {agent_name}")
                else:
                    # Try stack inspection to see what's calling this function
                    import traceback
                    stack_trace = ''.join(traceback.format_stack())
                    logger.warning(f"[JOB_ID_DEBUG] Call stack for missing job_id: {stack_trace}")
                    
                    logger.error(f"Missing job_id when creating step for agent {agent_name}")
                    raise ValueError("job_id is required to create agent steps")
                
            # Use the provided step number if specified, otherwise use the one from the step object
            step_number_value = step_number if step_number is not None else step.step_number
            step_id = f"{agent_name}-{step_number_value}-{job_id}"
            logger.warning(f"[JOB_ID_DEBUG] Created step_id: {step_id} with job_id: {job_id} for agent {agent_name}")
            
            # Create a serializable version of the step with agent context
            # Calculate step depth based on parent
            parent_depth = 0
            if parent_step_id:
                # Look for parent step to get its depth
                for parent_step in self.steps:
                    if parent_step.get("id") == parent_step_id:
                        parent_depth = parent_step.get("depth", 0)
                        break
                        
            step_data = {
                "id": step_id,
                "agent_name": agent_name,
                "agent_type": agent_type,
                "step_number": step_number_value,
                "depth": parent_depth + 1,  # Set depth based on parent
                "start_time": step.start_time,
                "end_time": step.end_time,
                "duration": step.duration,
                "timestamp": datetime.datetime.now().isoformat(),
                "observations": step.observations if hasattr(step, "observations") else None,
                "error": str(step.error) if hasattr(step, "error") and step.error else None,
                "action_output": str(step.action_output) if hasattr(step, "action_output") and step.action_output else None,
                "tool_calls": [
                    {"name": tc.name, "arguments": tc.arguments}
                    for tc in step.tool_calls
                ] if hasattr(step, "tool_calls") and step.tool_calls else [],
                "step_type": "agent",  # Mark as agent step
                "parent_step_id": parent_step_id,  # Set from parameter
                "child_step_ids": [],  # List of child step IDs to enable hierarchical view
                "job_id": job_id       # Associate with specific job
            }
            self.steps.append(step_data)
            
            # If this step has a parent, update the parent step's child_step_ids list
            if parent_step_id:
                parent_found = False
                # Find the parent step in the actual steps list to ensure modifications persist
                for i, parent_step in enumerate(self.steps):
                    if parent_step.get("id") == parent_step_id:
                        parent_found = True
                        if "child_step_ids" not in self.steps[i]:
                            self.steps[i]["child_step_ids"] = []
                        if step_id not in self.steps[i]["child_step_ids"]:
                            self.steps[i]["child_step_ids"].append(step_id)
                            logger.info(f"Added step {step_id} as child of {parent_step_id}")
                        break
                
                if not parent_found:
                    # This scenario occurs when the parent step wasn't stored yet
                    # or the parent_step_id format doesn't match stored steps
                    logger.warning(f"Parent step {parent_step_id} not found in step store. Will attempt fallback matching.")
                    
                    # Try a more flexible match based on agent name and step number
                    parent_agent = parent_step_id.split('-')[0] if '-' in parent_step_id else None
                    parent_step_num = parent_step_id.split('-')[1] if '-' in parent_step_id and len(parent_step_id.split('-')) > 1 else None
                    
                    if parent_agent and parent_step_num and parent_step_num.isdigit():
                        # Try to find matching parent step by agent name and step number
                        for parent_step in self.steps:
                            if (parent_step.get("agent_name") == parent_agent and 
                                str(parent_step.get("step_number")) == parent_step_num):
                                if "child_step_ids" not in parent_step:
                                    parent_step["child_step_ids"] = []
                                parent_step["child_step_ids"].append(step_id)
                                logger.info(f"Added step {step_id} as child of {parent_step.get('id')} (fallback matching)")
                                break
            
            # Also create separate tool steps if tool calls exist
            if hasattr(step, "tool_calls") and step.tool_calls and hasattr(step, "observations"):
                tool_step_ids = []  # Track IDs of tool steps created
                
                from .common import get_tool_id
                for tc in step.tool_calls:
                    tool_name_value = tool_name if tool_name is not None else tc.name
                    tool_id = get_tool_id(tool_name_value)
                    
                    # Generate a deterministic ID for this tool step using the job_id
                    if not job_id:
                        logger.error(f"Missing job_id when creating tool step for agent {agent_name}")
                        raise ValueError("job_id is required to create tool steps")
                        
                    tool_step_id = f"tool-{tool_name_value}-{agent_name}-{step_number_value}-{job_id}"
                    tool_step_ids.append(tool_step_id)
                    
                    # Tool steps should be one level deeper than their parent agent step
                    tool_depth = step_data["depth"] + 1  # Use the parent agent step's depth + 1
                    
                    tool_step_data = {
                        "id": tool_step_id,
                        "tool_name": tool_name_value,
                        "tool_id": tool_id,
                        "agent_name": agent_name,  # Link back to the agent
                        "agent_type": agent_type,
                        "step_number": step_number_value,
                        "depth": tool_depth,  # Add depth to tool steps
                        "start_time": step.start_time,
                        "end_time": step.end_time,
                        "duration": step.duration,
                        "timestamp": datetime.datetime.now().isoformat(),
                        "arguments": tc.arguments,
                        "observation": step.observations if hasattr(step, "observations") else None,
                        "error": str(step.error) if hasattr(step, "error") and step.error else None,
                        "step_type": "tool",  # Mark as tool step
                        "parent_step_id": step_id,  # Link back to the parent agent step
                        "job_id": job_id  # Associate with the same job as the parent step
                    }
                    self.tool_steps.append(tool_step_data)
                
                # Update the agent step with references to its child tool steps
                step_data["child_step_ids"] = tool_step_ids
                
            # Check for managed agent calls to track hierarchies in agent-agent interactions
            if hasattr(step, "tool_calls") and step.tool_calls:
                for tc in step.tool_calls:
                    if tc.name in globals().get('MANAGED_AGENTS', {}) or hasattr(tc.name, 'managed_agents'):
                        # This is a call to another agent - mark it for lineage tracking
                        logger.info(f"Agent {agent_name} called managed agent {tc.name} - will track lineage")
                        # Lineage tracking is handled in the step_callback function
            
            
        
        # Store step in database asynchronously
        if job_id and os.getenv('PG_CONNECTION_STRING'):
            # Create a task to store in database without waiting for completion
            asyncio.create_task(self.store_step_in_database(step_data))
            if tool_step_data:
                asyncio.create_task(self.store_step_in_database(tool_step_data))
            logger.debug(f"Created async tasks to store steps in database for job {job_id}")
        
        # Broadcast the step outside the lock to avoid blocking
        if self.event_listeners and step_data:
            # Create async task to broadcast step
            asyncio.create_task(self.broadcast_step(step_data))
            if tool_step_data:
                asyncio.create_task(self.broadcast_step(tool_step_data))
                
        # Extract MCP tool calls from Python interpreter code
        try:
            # Import the MCP tool extractor module
            from .mcp_tool_extractor import register_mcp_tool_steps
            
            # Register MCP tool steps
            register_mcp_tool_steps(self, step_data, agent_name, agent_type, job_id)
        except Exception as e:
            logger.error(f"Error extracting MCP tool calls: {e}")
            
    async def create_step_relationships(self, job_id: str) -> None:
        """Create relationship records between steps for a given job in the database.
        
        This method examines all steps for a given job and ensures proper parent-child
        relationships are recorded in the database. This is typically called after all
        steps for a job have been processed to ensure complete lineage tracking.
        
        Args:
            job_id (str): The unique identifier of the job whose steps should be linked.
        """
        if not os.getenv('PG_CONNECTION_STRING') or not job_id:
            return
            
        try:
            import psycopg2
            import json
            from psycopg2.extras import Json
            
            # Connect to the database
            conn = psycopg2.connect(os.getenv('PG_CONNECTION_STRING'))
            cursor = conn.cursor()
            
            # Get all steps for this job
            with self.lock:
                combined_steps = self.steps.copy() + self.tool_steps.copy()
                job_steps = [step for step in combined_steps if step.get('job_id') == job_id]
            
            if not job_steps:
                logger.debug(f"No steps found for job {job_id} to create relationships")
                return
                
            logger.info(f"Creating relationships for {len(job_steps)} steps in job {job_id}")
            
            # Build a dictionary of all step IDs for quick lookup
            all_step_ids = set()
            relationships = []
            
            # First, verify all steps exist in database
            for step in job_steps:
                step_id = step.get('id')
                if step_id:
                    all_step_ids.add(step_id)
                    # Check for child relationships
                    if step.get('child_step_ids'):
                        for child_id in step.get('child_step_ids'):
                            relationships.append((step_id, child_id))
            
            # Verify all steps exist in database
            for step_id in all_step_ids:
                cursor.execute(
                    "SELECT step_id FROM agent_flow_steps WHERE step_id = %s",
                    (step_id,)
                )
                if not cursor.fetchone():
                    # Step doesn't exist in database, create it
                    logger.info(f"Step {step_id} not found in database, creating it now")
                    # Find step data
                    step_data = next((step for step in job_steps if step.get('id') == step_id), None)
                    if step_data:
                        # Store the step
                        await self.store_step_in_database(step_data)
            
            # Now create relationships
            for parent_id, child_id in relationships:
                # Verify both parent and child exist
                cursor.execute(
                    "SELECT step_id FROM agent_flow_steps WHERE step_id IN (%s, %s)",
                    (parent_id, child_id)
                )
                existing_ids = set(row[0] for row in cursor.fetchall())
                
                if parent_id in existing_ids and child_id in existing_ids:
                    # Both exist, create relationship
                    try:
                        cursor.execute(
                            """
                            INSERT INTO agent_flow_step_relationships (parent_step_id, child_step_id)
                            VALUES (%s, %s)
                            ON CONFLICT (parent_step_id, child_step_id) DO NOTHING
                            """,
                            (parent_id, child_id)
                        )
                        logger.debug(f"Created relationship: {parent_id} -> {child_id}")
                    except Exception as e:
                        logger.warning(f"Failed to create relationship {parent_id} -> {child_id}: {e}")
                else:
                    missing = []
                    if parent_id not in existing_ids:
                        missing.append(f"parent {parent_id}")
                    if child_id not in existing_ids:
                        missing.append(f"child {child_id}")
                    logger.warning(f"Cannot create relationship: {', '.join(missing)} not in database")
            
            conn.commit()
            logger.info(f"Completed creating step relationships for job {job_id}")
            
        except Exception as e:
            logger.error(f"Error creating step relationships: {e}")
        finally:
            if 'conn' in locals() and conn:
                conn.close()
    
    def get_steps(self) -> List[Union[AgentStep, ToolStep]]:
        """Get all memory steps in chronological order.
        
        This method returns a combined list of all agent and tool steps,
        sorted by timestamp to maintain chronological order. It creates a copy
        of the internal step collections to ensure thread safety.
        
        Returns:
            List[Union[AgentStep, ToolStep]]: A combined list of all steps in chronological order.
        """
        with self.lock:
            # Combine agent and tool steps in the response
            combined_steps: List[Union[AgentStep, ToolStep]] = self.steps.copy() + self.tool_steps.copy()
            # Sort by timestamp to maintain chronological order
            combined_steps.sort(key=lambda x: x.get("timestamp", ""))
            return combined_steps
            
    def clear(self) -> None:
        """Clear all memory steps and broadcast a clear event.
        
        This method removes all agent and tool steps from memory and broadcasts
        a clear event to all connected clients.
        """
        with self.lock:
            self.steps = []
            self.tool_steps = []
            
        # Broadcast clear event
        if self.event_listeners or self.websocket_connections:
            asyncio.create_task(self.broadcast_step({
                "event": "clear",
                "timestamp": datetime.datetime.now().isoformat(),
            }))

# Create a global memory step store instance
MEMORY_STEP_STORE = MemoryStepStore()

# Import shared registry from common module
from .common import OUTPUT_REGISTRY

# Public exports from this module
__all__ = [
    'MEMORY_STEP_STORE',  # The singleton memory store instance
    'MemoryStepStore',    # The class definition for type hinting
    'AgentStep',          # Type definition for agent steps
    'ToolStep',           # Type definition for tool steps
    'get_job_metadata',   # Helper function to get job metadata (via singleton instance)
]

# Helper function to more easily access job metadata
def get_job_metadata(job_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get metadata for the specified job or current job.
    
    Convenience function that calls MEMORY_STEP_STORE.get_job_metadata.
    
    Args:
        job_id (Optional[str]): The job ID to get metadata for. If None, uses the current thread's job ID.
        
    Returns:
        Optional[Dict[str, Any]]: The job metadata if found, None otherwise.
    """
    return MEMORY_STEP_STORE.get_job_metadata(job_id)