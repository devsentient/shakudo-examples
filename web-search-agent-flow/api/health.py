"""Health check endpoints for monitoring service status.

This module provides health check endpoints for:
1. General health status checking
2. Kubernetes readiness probes
3. Kubernetes liveness probes
4. Detailed diagnostic information

These endpoints allow monitoring systems and orchestration platforms
to determine the availability and status of the service.
"""
import os
import time
import platform
import logging
import gc
import psutil
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from modules.models import HealthResponse
from modules.memory import MEMORY_STEP_STORE

# Setup logger
logger = logging.getLogger(__name__)

# Track service start time for uptime reporting
SERVICE_START_TIME = time.time()
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")

# Define the module interface
__all__ = [
    "router",
    "health_check",
    "readiness_check",
    "liveness_check",
    "detailed_status",
]

# Create router with detailed metadata
router = APIRouter(
    prefix="/health",
    tags=["health"],
    responses={
        status.HTTP_200_OK: {"description": "Service is healthy"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service is not healthy"},
    }
)

@router.get(
    "", 
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Returns basic health status information about the service",
    responses={
        status.HTTP_200_OK: {"description": "Service is healthy"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service is unhealthy"},
    }
)
async def health_check() -> HealthResponse:
    """Check if the service is healthy.
    
    This endpoint provides a basic health check that returns a 200 OK
    response if the service is running and able to handle requests.
    
    Returns:
        HealthResponse: Service health information
        
    Examples:
        Example response:
        ```json
        {
            "status": "healthy",
            "version": "1.0.0",
            "uptime": 3600.5,
            "memory_usage": {
                "total": 100000000,
                "available": 50000000,
                "percent": 50.0
            }
        }
        ```
    """
    # Calculate basic memory usage
    memory = psutil.virtual_memory()
    memory_usage = {
        "total": memory.total,
        "available": memory.available,
        "percent": memory.percent
    }
    
    # Calculate uptime
    uptime = time.time() - SERVICE_START_TIME
    
    logger.debug(f"Health check: service is healthy, uptime: {uptime:.1f}s")
    
    return HealthResponse.healthy(
        version=SERVICE_VERSION,
        uptime=uptime,
        memory_usage=memory_usage
    )

@router.get(
    "/readiness", 
    summary="Readiness check endpoint",
    description="Checks if the service is ready to accept requests",
    responses={
        status.HTTP_200_OK: {"description": "Service is ready to accept requests"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service is not ready"},
    }
)
async def readiness_check() -> Dict[str, Any]:
    """Check if the service is ready to accept requests.
    
    This endpoint is intended for use by Kubernetes readiness probes.
    It verifies that the service has completed initialization and is
    able to handle incoming requests.
    
    Returns:
        Dict[str, Any]: Readiness status information
        
    Response Codes:
        - 200 OK: Service is ready to accept requests
        - 503 Service Unavailable: Service is not ready
    """
    # Add checks that must pass for the service to be considered ready
    # Example: database connections, external service availability, etc.
    
    is_ready = True  # Implement actual checks as needed
    
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return Response(
        content='{"status": "ready", "version": "' + SERVICE_VERSION + '"}',
        media_type="application/json",
        status_code=status_code
    )

@router.get(
    "/liveness", 
    summary="Liveness check endpoint",
    description="Checks if the service is running and not deadlocked",
    responses={
        status.HTTP_200_OK: {"description": "Service is alive"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service is not responding correctly"},
    }
)
async def liveness_check() -> Dict[str, Any]:
    """Check if the service is alive.
    
    This endpoint is intended for use by Kubernetes liveness probes.
    It verifies that the service is running and not deadlocked.
    
    Returns:
        Dict[str, Any]: Liveness status information
        
    Response Codes:
        - 200 OK: Service is alive and functioning
        - 503 Service Unavailable: Service is not functioning correctly
    """
    # Add checks that must pass for the service to be considered alive
    # Example: response time, thread deadlock detection, etc.
    
    is_alive = True  # Implement actual checks as needed
    
    status_code = status.HTTP_200_OK if is_alive else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return Response(
        content='{"status": "alive", "version": "' + SERVICE_VERSION + '"}',
        media_type="application/json",
        status_code=status_code
    )

class DetailedHealthResponse(BaseModel):
    """Detailed health information response."""
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="Service version")
    uptime: float = Field(..., description="Uptime in seconds")
    memory: Dict[str, Any] = Field(..., description="Memory usage statistics")
    system: Dict[str, Any] = Field(..., description="System information")
    memory_store: Dict[str, Any] = Field(..., description="Memory store statistics")
    environment: Dict[str, str] = Field(..., description="Selected environment variables")

@router.get(
    "/detailed", 
    response_model=DetailedHealthResponse,
    summary="Detailed health status endpoint",
    description="Provides comprehensive health information and diagnostics"
)
async def detailed_status() -> DetailedHealthResponse:
    """Get detailed diagnostic information about the service.
    
    This endpoint provides comprehensive information about the service,
    including system information, memory usage, and service-specific metrics.
    It is intended for debugging and monitoring purposes.
    
    Returns:
        DetailedHealthResponse: Comprehensive health information
        
    Note:
        This endpoint may expose sensitive information and should be
        protected with appropriate authentication in production.
    """
    # Calculate uptime
    uptime = time.time() - SERVICE_START_TIME
    
    # Get memory information
    memory_info = psutil.virtual_memory()
    memory = {
        "total": memory_info.total,
        "available": memory_info.available,
        "used": memory_info.used,
        "percent": memory_info.percent,
        "gc_objects": len(gc.get_objects()),
        "process": {
            "rss": psutil.Process().memory_info().rss,  # Resident Set Size
            "vms": psutil.Process().memory_info().vms,  # Virtual Memory Size
        }
    }
    
    # Get system information
    system = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpus": psutil.cpu_count(),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "hostname": platform.node(),
    }
    
    # Memory store statistics
    memory_store = {
        "steps_count": len(MEMORY_STEP_STORE.get_steps()),
        "tool_steps_count": len(MEMORY_STEP_STORE.tool_steps),
        "listeners_count": len(MEMORY_STEP_STORE.event_listeners),
        "websocket_count": len(MEMORY_STEP_STORE.websocket_connections),
    }
    
    # Get selected environment variables (avoid exposing secrets)
    safe_env_vars = [
        "SERVICE_VERSION", "LOG_LEVEL", "ENVIRONMENT", 
        "PYTHONPATH", "PORT", "HOST"
    ]
    environment = {k: v for k, v in os.environ.items() 
                  if k in safe_env_vars or k.startswith("PUBLIC_")}
    
    logger.debug(f"Detailed health check requested, uptime: {uptime:.1f}s")
    
    return DetailedHealthResponse(
        status="healthy",
        version=SERVICE_VERSION,
        uptime=uptime,
        memory=memory,
        system=system,
        memory_store=memory_store,
        environment=environment
    )