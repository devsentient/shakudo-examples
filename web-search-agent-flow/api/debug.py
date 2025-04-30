"""Debug API endpoints for the multi-agent system.

This module provides diagnostic and debugging endpoints for:
1. Visualizing agent execution lineage
2. Inspecting agent configurations and relationships
3. Monitoring system health and resource usage
4. Examining internal execution state

These endpoints are intended for development, debugging, and monitoring
purposes and should be secured in production environments.
"""
import logging
import datetime
import os
from typing import Dict, Any, List, Optional, Sequence, Set, TypedDict, cast

from fastapi import APIRouter, Query, HTTPException, status, Response, Depends
from pydantic import BaseModel, Field

from modules.memory import MEMORY_STEP_STORE
from modules.agents import (
    MANAGER, 
    WORKER_AGENTS, 
    MANAGER_AGENTS, 
    AGENT_RELATIONSHIPS, 
    ACTIVE_AGENT_CALLS,
    ACTIVE_AGENT_CALLS_LOCK
)
from modules.models import Step

# Setup logger
logger = logging.getLogger(__name__)

# Define response models
class LineageNode(BaseModel):
    """Node representing a step in the lineage graph."""
    id: str = Field(..., description="Unique identifier for the step")
    label: str = Field(..., description="Display label for the step")
    type: str = Field(..., description="Step type (agent or tool)")
    agent: str = Field(..., description="Name of the agent that executed the step")
    step_number: Any = Field(..., description="Sequence number of the step")
    depth: int = Field(1, description="Depth in the execution tree")
    timestamp: str = Field("", description="Timestamp when the step was executed")
    duration: int = Field(0, description="Duration of the step execution in milliseconds")
    parent_id: Optional[str] = Field(None, description="ID of the parent step")

class LineageEdge(BaseModel):
    """Edge representing a relationship between steps."""
    from_: str = Field(..., description="Source step ID", alias="from")
    to: str = Field(..., description="Target step ID")
    type: str = Field(..., description="Type of relationship")

class LineageResponse(BaseModel):
    """Response model for step lineage endpoints."""
    job_id: str = Field(..., description="Job ID the lineage is for")
    timestamp: str = Field(..., description="Request timestamp")
    nodes: List[LineageNode] = Field(..., description="Step nodes in the lineage graph")
    edges: List[LineageEdge] = Field(..., description="Relationship edges in the lineage graph")
    total_steps: int = Field(..., description="Total number of steps in the lineage")
    total_relationships: int = Field(..., description="Total number of relationships")

class AgentInfo(BaseModel):
    """Information about an agent in the system."""
    id: str = Field(..., description="Unique identifier for the agent")
    name: str = Field(..., description="Agent name")
    type: str = Field(..., description="Agent type (worker, manager, or top_manager)")
    max_steps: int = Field(..., description="Maximum steps allowed for this agent")
    parent: Optional[str] = Field(None, description="Parent agent name if applicable")
    managed_agents: List[str] = Field(default_factory=list, description="List of managed agent names")

class AgentsResponse(BaseModel):
    """Response model for the agents endpoint."""
    timestamp: str = Field(..., description="Request timestamp")
    top_manager: AgentInfo = Field(..., description="Top-level manager agent")
    managers: List[AgentInfo] = Field(..., description="Manager agents in the system")
    workers: List[AgentInfo] = Field(..., description="Worker agents in the system")
    total_agents: int = Field(..., description="Total number of agents in the system")

class SystemHealthResponse(BaseModel):
    """Response model for the system health endpoint."""
    status: str = Field(..., description="Health status of the system")
    timestamp: str = Field(..., description="Request timestamp")
    memory: Dict[str, Any] = Field(..., description="Memory usage statistics")
    agents: Dict[str, Any] = Field(..., description="Agent statistics")
    connections: Dict[str, Any] = Field(..., description="Client connection statistics")
    environment: Dict[str, str] = Field(default_factory=dict, description="Selected environment variables")

# Define the module interface
__all__ = [
    "router",
    "get_step_lineage",
    "get_agents",
    "get_system_health",
    "LineageResponse",
    "AgentsResponse",
    "SystemHealthResponse",
]

# Create router with detailed metadata
router = APIRouter(
    prefix="/debug",
    tags=["debug"],
    responses={
        status.HTTP_200_OK: {"description": "Successful request"},
        status.HTTP_404_NOT_FOUND: {"description": "Requested resource not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Server error"},
    }
)

def get_job_steps(job_id: str) -> List[Dict[str, Any]]:
    """Helper function to get steps for a specific job.
    
    Args:
        job_id: The job ID to filter steps by
        
    Returns:
        List[Dict[str, Any]]: Steps matching the job ID
        
    Raises:
        HTTPException: If no steps are found for the job
    """
    # Get all steps from memory store
    all_steps = MEMORY_STEP_STORE.get_steps()
    
    # Filter steps for the specified job
    job_steps = [step for step in all_steps if step.get("job_id") == job_id]
    
    if not job_steps:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"No steps found for job {job_id}"
        )
        
    return job_steps

@router.get(
    "/lineage", 
    response_model=LineageResponse,
    summary="Get step lineage and relationships",
    description="Retrieves execution lineage information for visualizing agent call graphs"
)
async def get_step_lineage(
    job_id: str = Query(..., description="Job ID to get lineage for")
) -> LineageResponse:
    """Get the lineage relationships between steps for a job.
    
    This endpoint is useful for visualizing or analyzing the agent execution flow,
    showing parent-child relationships between steps and the overall call hierarchy.
    
    Args:
        job_id: The unique identifier for the job to retrieve lineage information for
        
    Returns:
        LineageResponse: Graph data structure with nodes (steps) and edges (relationships)
        
    Raises:
        HTTPException: If no steps are found for the job or if an error occurs
        
    Examples:
        Get lineage for a job:
        ```
        GET /debug/lineage?job_id=job-20250301123456-abcd1234
        ```
        
    Technical Notes:
        The returned graph data structure is designed for visualization and 
        can be rendered with libraries like vis.js or d3.js. The steps include 
        both agent steps and tool execution steps for a complete picture of the
        execution flow.
    """
    try:
        # Get the steps for the job
        job_steps = get_job_steps(job_id)
        
        # Build node and edge data structures for visualization
        nodes: List[LineageNode] = []
        edges: List[LineageEdge] = []
        node_map: Dict[str, LineageNode] = {}
        
        # First, build all nodes
        for step in job_steps:
            step_id = step.get("id")
            if not step_id:
                continue
                
            # Create a node for the step
            step_number = step.get("step_number", "?")
            agent_name = step.get("agent_name", "unknown")
            step_type = step.get("step_type", "agent")
            
            # Create a friendly node label based on type
            if step_type == "agent":
                label = f"{agent_name} #{step_number}"
            else:  # Tool step
                tool_name = step.get("tool_name", "unknown_tool")
                label = f"{tool_name} (by {agent_name})"
            
            # Create node data
            node_data = LineageNode(
                id=step_id,
                label=label,
                type=step_type,
                agent=agent_name,
                step_number=step_number,
                depth=step.get("depth", 1),
                timestamp=step.get("timestamp", ""),
                duration=step.get("duration", 0),
                parent_id=step.get("parent_step_id")
            )
            
            # Add the node to our list and map
            nodes.append(node_data)
            node_map[step_id] = node_data
        
        # Now, build all edges (relationships)
        for step in job_steps:
            step_id = step.get("id")
            if not step_id:
                continue
                
            # Check if this step has a parent
            parent_step_id = step.get("parent_step_id")
            if parent_step_id and parent_step_id in node_map:
                # Create an edge to represent the relationship
                edges.append(LineageEdge(
                    from_=parent_step_id,
                    to=step_id,
                    type="parent_child"
                ))
            
            # Check if this step has child steps
            child_step_ids = step.get("child_step_ids", [])
            if child_step_ids:
                for child_id in child_step_ids:
                    if child_id in node_map:
                        edges.append(LineageEdge(
                            from_=step_id,
                            to=child_id,
                            type="parent_child"
                        ))
        
        # Create the response
        logger.info(f"Generated lineage graph for job {job_id}: {len(nodes)} nodes, {len(edges)} edges")
        
        return LineageResponse(
            job_id=job_id,
            timestamp=datetime.datetime.now().isoformat(),
            nodes=nodes,
            edges=edges,
            total_steps=len(nodes),
            total_relationships=len(edges)
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error generating lineage for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error generating lineage: {str(e)}"
        )

@router.get(
    "/agents", 
    response_model=AgentsResponse,
    summary="Get all agent information",
    description="Returns configuration and relationship information for all agents in the system"
)
async def get_agents() -> AgentsResponse:
    """Get information about all configured agents.
    
    Returns information about manager agents, worker agents, and their relationships.
    This endpoint is useful for debugging hierarchical relationships between agents
    and understanding the overall agent architecture.
    
    Returns:
        AgentsResponse: Information about all agents in the system
        
    Raises:
        HTTPException: If an error occurs retrieving agent information
        
    Examples:
        ```
        GET /debug/agents
        ```
        
    The response includes:
    - Top-level manager agent configuration
    - List of all manager agents with their relationships
    - List of all worker agents with their parent relationships
    - Total count of agents in the system
    """
    try:
        # Build a list of all worker agents
        workers: List[AgentInfo] = []
        for worker_id, worker in WORKER_AGENTS.items():
            workers.append(AgentInfo(
                id=worker_id,
                name=worker.name,
                type="worker",
                max_steps=worker.max_steps,
                parent=AGENT_RELATIONSHIPS.get(worker.name, {}).get("parent_agent", "unknown")
            ))
            
        # Build a list of all manager agents
        managers: List[AgentInfo] = []
        for manager_id, manager in MANAGER_AGENTS.items():
            managers.append(AgentInfo(
                id=manager_id,
                name=manager.name,
                type="manager",
                max_steps=manager.max_steps,
                parent=AGENT_RELATIONSHIPS.get(manager.name, {}).get("parent_agent", "unknown"),
                managed_agents=[agent.name for agent in manager.managed_agents] if hasattr(manager, "managed_agents") else []
            ))
            
        # Add the top manager
        top_manager = AgentInfo(
            id="top_manager",
            name=MANAGER.name,
            type="top_manager",
            max_steps=MANAGER.max_steps,
            managed_agents=[agent.name for agent in MANAGER.managed_agents] if hasattr(MANAGER, "managed_agents") else []
        )
        
        logger.info(f"Retrieved agent information: {1 + len(managers) + len(workers)} total agents")
        
        return AgentsResponse(
            timestamp=datetime.datetime.now().isoformat(),
            top_manager=top_manager,
            managers=managers,
            workers=workers,
            total_agents=1 + len(managers) + len(workers)
        )
        
    except Exception as e:
        logger.error(f"Error retrieving agent information: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error retrieving agent information: {str(e)}"
        )

@router.get(
    "/health", 
    response_model=SystemHealthResponse,
    summary="Detailed system health status",
    description="Provides comprehensive system health information for monitoring and debugging"
)
async def get_system_health() -> SystemHealthResponse:
    """Get detailed system health status.
    
    Returns information about the system's health, including memory usage,
    active steps, agent status, and other diagnostic information.
    
    Returns:
        SystemHealthResponse: Comprehensive health information
        
    Raises:
        HTTPException: If an error occurs retrieving system health information
        
    Examples:
        ```
        GET /debug/health
        ```
        
    The response includes:
    - Memory usage statistics for steps and connections
    - Agent configuration and activity information
    - Client connection statistics
    - Environment information (non-sensitive only)
    
    Note:
        This endpoint provides more detailed information than the standard
        /health endpoint and is intended for debugging and monitoring.
    """
    try:
        # Get memory steps info
        num_steps = len(MEMORY_STEP_STORE.get_steps())
        
        # Get active agent calls info
        with ACTIVE_AGENT_CALLS_LOCK:
            active_agents = list(ACTIVE_AGENT_CALLS.keys())
        
        # Get selected environment variables (avoid exposing secrets)
        safe_env_vars = [
            "SERVICE_VERSION", "LOG_LEVEL", "ENVIRONMENT", 
            "PYTHONPATH", "PORT", "HOST"
        ]
        environment = {k: v for k, v in os.environ.items() 
                    if k in safe_env_vars or k.startswith("PUBLIC_")}
        
        # Build health status info
        health_info = SystemHealthResponse(
            status="healthy",
            timestamp=datetime.datetime.now().isoformat(),
            memory={
                "total_steps": num_steps,
                "agent_steps": len(MEMORY_STEP_STORE.steps),
                "tool_steps": len(MEMORY_STEP_STORE.tool_steps)
            },
            agents={
                "total_worker_agents": len(WORKER_AGENTS),
                "total_manager_agents": len(MANAGER_AGENTS) + 1,  # +1 for top manager
                "active_agent_calls": len(active_agents),
                "active_agents": active_agents
            },
            connections={
                "sse_clients": len(MEMORY_STEP_STORE.event_listeners),
                "websocket_clients": len(MEMORY_STEP_STORE.websocket_connections)
            },
            environment=environment
        )
        
        logger.debug("Retrieved detailed system health information")
        return health_info
        
    except Exception as e:
        logger.error(f"Error retrieving system health: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error retrieving system health: {str(e)}"
        )

@router.post(
    "/clear-agent-calls",
    summary="Clear active agent calls tracking",
    description="Clears the internal tracking of active agent calls",
    status_code=status.HTTP_204_NO_CONTENT
)
async def clear_agent_calls() -> None:
    """Clear the active agent calls tracking.
    
    This endpoint is intended for debugging and recovery scenarios where
    the active agent calls tracking might be out of sync with reality.
    
    Returns:
        None: The endpoint returns no content on success
        
    Raises:
        HTTPException: If an error occurs while clearing the tracking
        
    Examples:
        ```
        POST /debug/clear-agent-calls
        ```
        
    Note:
        This is primarily for debugging and should be used with caution
        as it may affect monitoring of currently running agent executions.
    """
    try:
        with ACTIVE_AGENT_CALLS_LOCK:
            count = len(ACTIVE_AGENT_CALLS)
            ACTIVE_AGENT_CALLS.clear()
            
        logger.warning(f"Cleared {count} active agent calls from tracking")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        logger.error(f"Error clearing active agent calls: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing active agent calls: {str(e)}"
        )