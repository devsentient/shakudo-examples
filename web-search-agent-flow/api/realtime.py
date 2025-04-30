"""API endpoints for real-time event streaming.

This module provides real-time communication endpoints using:
1. Server-Sent Events (SSE) for one-way streaming of agent execution steps
2. WebSocket for bidirectional communication with clients

These endpoints allow clients to receive updates without polling,
enabling real-time monitoring and display of agent execution.
"""
import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, AsyncGenerator, Set

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, status, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from modules.memory import MEMORY_STEP_STORE
from modules.models import SSEEvent

# Setup logger
logger = logging.getLogger(__name__)

# Constants for real-time communication
SSE_HEADERS = {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Transfer-Encoding": "chunked",
}
SSE_KEEP_ALIVE_TIMEOUT = 60.0  # Seconds to wait before sending keep-alive
WEBSOCKET_PING_INTERVAL = 30.0  # Seconds between WebSocket ping messages

# Define the module interface
__all__ = [
    "router",
    "stream_steps",
    "websocket_steps",
]

# Create router with detailed metadata
router = APIRouter(
    tags=["realtime"],
    responses={
        status.HTTP_200_OK: {"description": "Successful connection established"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Server error during stream processing"},
    }
)

@router.get(
    "/steps-stream", 
    summary="Stream memory steps in real-time (SSE)",
    description="Provides a Server-Sent Events stream of agent execution steps as they occur",
    response_class=StreamingResponse
)
async def stream_steps(
    request: Request,
    job_id: Optional[str] = Query(None, description="Filter stream to a specific job ID")
) -> StreamingResponse:
    """Stream memory steps as Server-Sent Events (SSE).
    
    This endpoint provides a real-time stream of agent steps as they occur.
    Clients can subscribe to this endpoint to receive updates without polling.
    
    Args:
        request: The FastAPI request object
        job_id: Optional filter to only receive events for a specific job
        
    Returns:
        StreamingResponse: An event stream that remains open until the client disconnects
        
    Raises:
        HTTPException: If an error occurs during stream setup
        
    Technical Details:
        - Uses Server-Sent Events (SSE) protocol for real-time updates
        - Sends keep-alive messages every 60 seconds to maintain connection
        - Automatically cleans up resources when client disconnects
        - Delivers events in chronological order with event type and JSON data
        
    Examples:
        Subscribe to all events:
        ```
        GET /steps-stream
        ```
        
        Subscribe to events for a specific job:
        ```
        GET /steps-stream?job_id=job-20250301123456-abcd1234
        ```
    """
    queue = None
    connection_time = time.time()
    client_id = str(hash(request))[:8]  # Generate a short client identifier for logging
    
    try:
        # Register a new event listener and get the queue
        queue = await MEMORY_STEP_STORE.add_listener()
        logger.info(f"SSE connection established for client {client_id}" +
                   (f" filtering for job {job_id}" if job_id else ""))
        
        # Define async generator for streaming events
        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                # Send initial keep-alive comment to establish the connection
                yield ": connection-established\n\n"
                
                # Initial event with connection info
                connection_data = {
                    "connectionId": client_id,
                    "connectedAt": connection_time,
                    "filterJobId": job_id
                }
                yield f"event: connected\ndata: {json.dumps(connection_data)}\n\n"
                
                # Send all existing steps that match the filter as an initial payload
                if job_id:
                    # Filter steps by job_id
                    steps = [step for step in MEMORY_STEP_STORE.get_steps() 
                            if step.get("job_id") == job_id]
                else:
                    # Send all steps
                    steps = MEMORY_STEP_STORE.get_steps()
                
                if steps:
                    yield f"event: initial\ndata: {json.dumps({'steps': steps, 'total': len(steps)})}\n\n"
                
                # Keep the connection open and stream events as they arrive
                while True:
                    try:
                        # Wait for the next event with a timeout
                        event = await asyncio.wait_for(queue.get(), timeout=SSE_KEEP_ALIVE_TIMEOUT)
                        
                        # Apply job_id filter if specified
                        if job_id and event.get("event") == "step":
                            # Parse the data to check if step belongs to specified job
                            try:
                                data = json.loads(event.get("data", "{}"))
                                step = data.get("step", {})
                                
                                # Skip if step is for a different job
                                if step.get("job_id") != job_id:
                                    continue
                            except json.JSONDecodeError:
                                logger.warning(f"Could not parse event data for job filtering: {event.get('data')}")
                        
                        # Format the SSE message
                        if event.get("event"):
                            event_type = event["event"]
                            yield f"event: {event_type}\n"
                        
                        if event.get("data"):
                            yield f"data: {event['data']}\n\n"
                            
                    except asyncio.TimeoutError:
                        # Send keep-alive comment to prevent connection timeout
                        yield ": keep-alive\n\n"
                        
            except asyncio.CancelledError:
                # Client disconnected - normal termination
                duration = time.time() - connection_time
                logger.info(f"SSE connection cancelled for client {client_id} after {duration:.1f}s")
                yield f"event: disconnected\ndata: {json.dumps({'reason': 'cancelled'})}\n\n"
                raise
                
            except Exception as e:
                # Unexpected error in stream
                logger.error(f"Error in SSE stream for client {client_id}: {e}", exc_info=True)
                # Send error event to client before terminating
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                
            finally:
                # Ensure the listener is removed when the generator exits
                if queue:
                    removed = MEMORY_STEP_STORE.remove_listener(queue)
                    logger.debug(f"SSE listener removed for client {client_id}: {removed}")
        
        # Return streaming response with appropriate headers
        return StreamingResponse(
            event_generator(),
            headers=SSE_HEADERS,
        )
        
    except Exception as e:
        # Clean up in case of error during setup
        if queue:
            MEMORY_STEP_STORE.remove_listener(queue)
            
        logger.error(f"Error setting up SSE connection for client {client_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to establish event stream: {str(e)}"
        )
        
@router.websocket(
    "/ws/steps",
    name="websocket_steps"
)
async def websocket_steps(
    websocket: WebSocket,
    job_id: Optional[str] = None
) -> None:
    """WebSocket endpoint for real-time memory steps.
    
    This endpoint provides a bidirectional connection for receiving agent steps
    in real-time as they occur. It also supports filtering by job ID.
    
    Args:
        websocket: The WebSocket connection
        job_id: Optional filter to only receive events for a specific job
        
    Returns:
        None: This function runs until the WebSocket connection is closed
        
    Technical Details:
        - Accepts WebSocket connections and sends step updates in real-time
        - Sends regular ping messages to ensure connection remains active
        - Supports filtering by job ID to reduce message volume
        - Cleans up resources automatically when client disconnects
        - Delivers initial state on connection and incremental updates thereafter
        
    Protocol:
        - Server sends messages in JSON format with type and payload fields
        - Client can send filter commands to change filtering options
        - Server sends ping messages periodically to maintain connection
        - Clients should respond to pings to avoid disconnection
    """
    # Generate a client identifier for logging
    client_id = f"ws-{id(websocket) % 10000}"
    connection_time = time.time()
    
    try:
        # Accept the WebSocket connection
        await websocket.accept()
        logger.info(f"WebSocket connection established for client {client_id}" +
                   (f" filtering for job {job_id}" if job_id else ""))
        
        # Send welcome message with connection info
        await websocket.send_json({
            "type": "connected",
            "payload": {
                "connectionId": client_id,
                "connectedAt": connection_time,
                "filterJobId": job_id
            }
        })
        
        # Add the WebSocket to the memory store
        await MEMORY_STEP_STORE.add_websocket(websocket)
        
        # Send initial steps for the required job id
        if job_id:
            # Filter steps by job_id
            steps = [step for step in MEMORY_STEP_STORE.get_steps() 
                    if step.get("job_id") == job_id]
        else:
            # Send all steps
            steps = MEMORY_STEP_STORE.get_steps()
            
        if steps:
            await websocket.send_json({
                "type": "initial",
                "payload": {
                    "steps": steps,
                    "total": len(steps)
                }
            })
        
        # Start a background task for periodic pings (if needed)
        ping_task = None
        if WEBSOCKET_PING_INTERVAL > 0:
            # Define a ping sender coroutine
            async def send_pings():
                ping_count = 0
                try:
                    while True:
                        await asyncio.sleep(WEBSOCKET_PING_INTERVAL)
                        ping_count += 1
                        await websocket.send_json({
                            "type": "ping",
                            "payload": {
                                "count": ping_count,
                                "timestamp": time.time()
                            }
                        })
                        logger.debug(f"Sent ping #{ping_count} to WebSocket client {client_id}")
                except Exception as e:
                    logger.debug(f"Ping task terminated for client {client_id}: {e}")
            
            # Start the ping task in the background
            ping_task = asyncio.create_task(send_pings())
        
        # Main loop: wait for client messages
        while True:
            # Wait for any message from client (can be used for commands or just keep-alive)
            message = await websocket.receive_text()
            
            # Process commands from the client (e.g., changing filters)
            try:
                cmd = json.loads(message)
                cmd_type = cmd.get("type", "")
                
                if cmd_type == "filter":
                    # Update the job ID filter
                    new_job_id = cmd.get("job_id")
                    job_id = new_job_id  # Update the filter
                    logger.info(f"WebSocket client {client_id} changed filter to job_id={new_job_id}")
                    
                    # Acknowledge the filter change
                    await websocket.send_json({
                        "type": "filter_changed",
                        "payload": {"job_id": new_job_id}
                    })
                
                elif cmd_type == "pong":
                    # Client responding to our ping
                    logger.debug(f"Received pong from client {client_id}")
                
                else:
                    logger.debug(f"Received message from client {client_id}: {message[:100]}")
            
            except json.JSONDecodeError:
                # Not JSON, treat as simple keep-alive
                logger.debug(f"Received non-JSON message from client {client_id}: {message[:20]}")
            
    except WebSocketDisconnect:
        # Client disconnected normally
        duration = time.time() - connection_time
        logger.info(f"WebSocket client {client_id} disconnected after {duration:.1f}s")
        
    except Exception as e:
        # Error handling for unexpected errors
        logger.error(f"WebSocket error for client {client_id}: {e}", exc_info=True)
        
        # Try to send an error message to the client
        try:
            await websocket.send_json({
                "type": "error",
                "payload": {"error": str(e)}
            })
        except:
            pass  # If this fails, we can't do much about it
        
    finally:
        # Cancel ping task if it's running
        if ping_task:
            ping_task.cancel()
            try:
                await ping_task
            except asyncio.CancelledError:
                pass
                
        # Ensure the WebSocket is removed from the memory store
        removed = MEMORY_STEP_STORE.remove_websocket(websocket)
        logger.debug(f"WebSocket removed for client {client_id}: {removed}")
        
        # Ensure the connection is closed
        if websocket.client_state.CONNECTED:
            await websocket.close()
            logger.debug(f"WebSocket connection closed for client {client_id}")