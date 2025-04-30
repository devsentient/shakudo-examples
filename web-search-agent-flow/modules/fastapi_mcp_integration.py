"""FastAPI MCP server integration module."""
import os
import logging
from fastapi import FastAPI, APIRouter

# Setup logging
logger = logging.getLogger(__name__)

def setup_fastapi_mcp(app: FastAPI, base_url: str = None) -> None:
    """
    Set up FastAPI MCP server integration.
    
    This makes the FastAPI endpoints available as MCP tools.
    
    Args:
        app: The FastAPI application instance
        base_url: Base URL for the MCP server (defaults to environment variable or standard localhost)
    """
    try:
        import httpx
        from fastapi_mcp import FastApiMCP
        logger.info("Setting up FastAPI MCP integration")
        
        # Get base URL from environment or use default
        if not base_url:
            base_url = os.environ.get("FASTAPI_MCP_BASE_URL", "http://localhost:8000")
        
        # Get timeout value from environment or use default (1200 seconds)
        timeout_seconds = int(os.environ.get("HTTPX_TIMEOUT", "1200"))
        logger.info(f"Using httpx timeout of {timeout_seconds} seconds for MCP connections")
        
        # Create custom httpx client with longer timeout
        http_client = httpx.AsyncClient(timeout=timeout_seconds)
        
        logger.info(f"Using base URL for FastAPI MCP: {base_url}")
        
        # Create the MCP server with custom httpx client
        mcp_server = FastApiMCP(
            app,  # Pass app as a positional argument
            name="Agent Flow MCP",
            description="Agent Flow MCP server for accessing agent capabilities via MCP",
            base_url=base_url,
            include_tags=["mcp", "api"], # Only expose endpoints with these tags
            describe_all_responses=True,
            describe_full_response_schema=True,
            http_client=http_client  # Pass custom httpx client with longer timeout
        )
        
        # Mount the MCP server
        mcp_server.mount()
        logger.info("FastAPI MCP server mounted successfully")
        
        # Return the server for further configuration if needed
        return mcp_server
    except ImportError:
        logger.warning("fastapi_mcp package not installed. MCP server integration disabled.")
        return None
    except Exception as e:
        logger.error(f"Error setting up FastAPI MCP integration: {str(e)}")
        return None