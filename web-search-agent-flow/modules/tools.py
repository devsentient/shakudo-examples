"""Tools for interacting with external services.

This module provides classes and utilities for integrating external services as tools
that can be used by agents in the system. It handles:

1. Service tool definition and registration
2. Synchronous and asynchronous communication with service endpoints
3. Response processing and storage in the output registry
4. Tool normalization and ID mapping for consistent referencing
5. MCP tool initialization with full response structure preservation

The primary component is the ServiceTool class which wraps external service endpoints
as agent-compatible tools, enabling seamless integration of microservices into
agent workflows.
"""
import json
import asyncio
import logging
import os
from typing import Dict, Any, Optional, Union, List, Callable, TypedDict, Mapping, cast

# Get module-level logger
logger = logging.getLogger(__name__)

# Agent framework imports
from smolagents import Tool
from smolagents.tools import ToolCollection

# Import MCP-related modules (for MCP tool initialization)
try:
    # First import our custom adapter - this will set up placeholders if needed
    from .common.custom_mcp_adapter import (
        FullResponseSmolAgentsAdapter, 
        StdioServerParameters, 
        SSEServerParameters,
    )
    logger.info("✅ Successfully imported custom MCP adapter: FullResponseSmolAgentsAdapter")
    
    # Now import MCPAdapt from mcpadapt.core
    try:
        from mcpadapt.core import MCPAdapt
        logger.info("✅ Successfully imported MCPAdapt from mcpadapt.core")
        MCP_IMPORTS_AVAILABLE = True
    except ImportError as adapt_err:
        logger.error(f"❌ Failed to import MCPAdapt from mcpadapt.core: {adapt_err}")
        MCP_IMPORTS_AVAILABLE = False
        
except ImportError as e:
    logger.error(f"❌ Failed to import custom adapter module: {str(e)}")
    MCP_IMPORTS_AVAILABLE = False

# Import from local modules
from .common import OUTPUT_REGISTRY

# Type definitions for tools
class ToolMetadata(TypedDict, total=False):
    """Type definition for tool request metadata."""
    thread_id: str
    channel_id: str
    user_id: str
    timestamp: str
    session_id: str

class ServiceResponse(TypedDict):
    """Type definition for service endpoint responses."""
    success: bool
    response: Optional[str]
    error: Optional[str]

class ServiceTool(Tool):
    """Tool for interacting with external services.
    
    This class wraps an external service endpoint as a tool that can be used by agents.
    It handles:
    
    1. Communication with the service endpoint using HTTP POST requests
    2. Processing responses and handling errors
    3. Registering outputs in the global output registry
    4. Managing metadata for the service calls
    
    ServiceTool implements both synchronous and asynchronous interfaces for flexibility
    in different execution contexts.
    """
    
    # Schema definition for the tool's input parameters
    inputs = {
        "message": {
            "type": "string",
            "description": "The message to be processed by the service"
        },
        "metadata": {
            "type": "object",
            "description": "Additional metadata like thread_id and channel_id",
            "properties": {
                "thread_id": {"type": "string"},
                "channel_id": {"type": "string"},
                "user_id": {"type": "string"},
                "timestamp": {"type": "string"},
                "session_id": {"type": "string"}
            },
            "nullable": True
        }
    }
    output_type = "string"
    
    def __init__(self, service_name: str, service_url: str, readme: Optional[str] = None, is_output_node: bool = False):
        """Initialize a new ServiceTool instance.
        
        Args:
            service_name (str): The name of the service (used for display and identification)
            service_url (str): The base URL of the service endpoint
            readme (Optional[str]): Optional documentation for the tool
            is_output_node (bool): Whether this tool's output should be treated as a 
                designated output of the agent flow
        """
        self.service_name: str = service_name
        self.service_url: str = service_url
        self.readme: Optional[str] = readme
        self.is_output_node: bool = is_output_node
        super().__init__()
    
    @property
    def name(self) -> str:
        """Generate a unique name for the tool.
        
        This property creates a standardized name for the tool based on the service name,
        removing common prefixes and adding a consistent agent_flow_tool prefix.
        
        Returns:
            str: A unique, standardized name for the tool
        """
        clean_name = self.service_name.replace("shakbot_tool_", "").replace("shakbot-tool-", "")
        # Replace any dashes with underscores to ensure Python compatibility
        clean_name = clean_name.replace("-", "_")
        return f"agent_flow_tool_{clean_name}"
        
    @property
    def description(self) -> str:
        """Generate a description for the tool.
        
        This property creates a user-friendly description of the tool, including
        any additional documentation provided in the readme parameter.
        
        Returns:
            str: A description of the tool's functionality
        """
        extra = f"\n\n{self.readme}" if self.readme else ""
        return f"""Process messages through the {self.service_name} service.{extra}
        Returns the service's response or an error message if processing fails."""
    
    def forward(self, message: str, metadata: Optional[ToolMetadata] = None) -> str:
        """Process a message through the service endpoint synchronously.
        
        This method is the primary entry point for tool invocation. It handles detection
        of the asyncio context and appropriately routes the request to the async implementation.
        
        Args:
            message (str): The message to be processed by the service
            metadata (Optional[ToolMetadata]): Additional metadata for the service call,
                such as thread_id, channel_id, or user_id
                
        Returns:
            str: The response from the service, or an error message if processing fails
        """
        import asyncio
        try:
            # Check if we're already in an asyncio event loop
            asyncio.get_running_loop()
        except RuntimeError:
            # No event loop running, we can create a new one
            return asyncio.run(self._forward_async(message, metadata))
        else:
            # We're in an event loop, need to use nest_asyncio to avoid RuntimeError
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.run(self._forward_async(message, metadata))
    
    async def _forward_async(self, message: str, metadata: Optional[Union[ToolMetadata, Dict[str, Any]]] = None) -> str:
        """Process a message through the service endpoint asynchronously.
        
        This method handles the actual HTTP communication with the service endpoint.
        It is responsible for:
        1. Constructing the request payload
        2. Sending the HTTP POST request to the service
        3. Processing the response and handling errors
        4. Registering the output in the global OUTPUT_REGISTRY
        
        Args:
            message (str): The message to be processed by the service
            metadata (Optional[Union[ToolMetadata, Dict[str, Any]]]): Additional metadata 
                for the service call
                
        Returns:
            str: The response from the service, or an error message if processing fails
        """
        import aiohttp
        payload = {
            "message": message,
            "metadata": metadata or {},
            "non_blocking": False  # Use blocking mode by default for agent-to-agent communication
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.service_url}/process",
                    json=payload,
                    timeout=600  # 2-minute timeout for long-running operations
                ) as response:
                    response_text = await response.text()
                    if response.status == 200:
                        try:
                            result: ServiceResponse = json.loads(response_text)
                            if result.get("success"):
                                response_text = result.get("response") or "No response provided"
                                # Always save the response to OUTPUT_REGISTRY, but mark if it's an output node
                                # The tool ID will be the ID passed when creating the ServiceTool in the tool definitions
                                for node_id, tool in TOOLS.items():
                                    if tool is self:
                                        # Save with both formats - the direct ID and tool- prefixed version
                                        OUTPUT_REGISTRY[node_id] = response_text
                                        OUTPUT_REGISTRY[f"tool-{node_id}"] = response_text
                                        if self.is_output_node:
                                            logger.info(f"Tool {self.name} (ID: {node_id}) saved output as designated output node")
                                        else:
                                            logger.debug(f"Tool {self.name} (ID: {node_id}) saved output")
                                        break
                                else:
                                    # Fallback if tool not found in TOOLS dictionary
                                    fallback_id = f"tool-{id(self)}"
                                    OUTPUT_REGISTRY[fallback_id] = response_text
                                    if self.is_output_node:
                                        logger.info(f"Tool {self.name} saved output as designated output node (instance ID)")
                                    else:
                                        logger.debug(f"Tool {self.name} saved output (instance ID)")
                                return response_text
                            else:
                                error_msg = result.get("error") or "Unknown error"
                                logger.warning(f"Tool {self.name} returned error: {error_msg}")
                                return f"Error: {error_msg}"
                        except json.JSONDecodeError:
                            logger.warning(f"Tool {self.name} returned invalid JSON: {response_text[:100]}...")
                            return f"Error: Service returned invalid JSON response"
                    else:
                        logger.warning(f"Tool {self.name} returned HTTP {response.status}: {response_text[:100]}...")
                        return f"Error: Service returned status {response.status}"
        except asyncio.TimeoutError:
            logger.warning(f"Tool {self.name} request timed out after 120 seconds")
            return f"Error: Request to {self.service_name} service timed out after 120 seconds"
        except Exception as e:
            logger.error(f"Tool {self.name} failed with exception: {str(e)}")
            return f"Error: {str(e)}"

# Tool registry - populated by the templating engine
TOOLS: Dict[str, ServiceTool] = {
        "tool-89fc99d5-b85b-423b-aad9-b372a734b62e": ServiceTool(
        service_name="agent_webresearcher",
        service_url="http://hyperplane-service-89fc99.hyperplane-pipelines.svc.cluster.local:8787",
        readme="",
        is_output_node=False
    )
}

# Create a reverse map from tool names to tool IDs for efficient lookups
# First create a local variable for use within this module
TOOL_NAME_TO_ID: Dict[str, str] = {tool.name: tool_id for tool_id, tool in TOOLS.items()}

# Now update the common module's TOOL_NAME_TO_ID for global access
from .common import TOOL_NAME_TO_ID as COMMON_TOOL_NAME_TO_ID
# Use update to add the entries to the common module's dictionary 
COMMON_TOOL_NAME_TO_ID.update(TOOL_NAME_TO_ID)

# Create a map that normalizes the tool IDs to handle both with and without 'tool-' prefixes
# This enables flexible referencing of tools in agent code
NORMALIZED_TOOL_IDS: Dict[str, str] = {}
for tool_id in TOOLS.keys():
    # Store both the original ID and prefixed ID
    NORMALIZED_TOOL_IDS[tool_id] = tool_id
    NORMALIZED_TOOL_IDS[f"tool-{tool_id}"] = tool_id
    # Also handle the case where the ID already has a tool- prefix
    if tool_id.startswith("tool-"):
        NORMALIZED_TOOL_IDS[tool_id[5:]] = tool_id
    
    # For Python code compatibility - create versions with dashes replaced by underscores
    python_safe_id = tool_id.replace("-", "_")
    if python_safe_id != tool_id:
        NORMALIZED_TOOL_IDS[python_safe_id] = tool_id

# Initialize MCP tools function
def initialize_mcp_tools() -> Dict[str, Tool]:
    """Initialize MCP servers with custom adapter to preserve full response structure.
    
    This function initializes MCP servers using our custom adapter that preserves
    the complete response structure, including structured data. This allows
    agents to access both the text preview and the complete structured data.
    
    Returns:
        Dict[str, Tool]: Dictionary of initialized MCP tools
    """
    if not MCP_IMPORTS_AVAILABLE:
        logger.warning("MCP imports not available, skipping MCP tool initialization")
        return {}
    
    # Check if all required components are available
    required_globals = ['MCPAdapt', 'StdioServerParameters', 'FullResponseSmolAgentsAdapter']
    missing_globals = []
    for global_name in required_globals:
        if global_name not in globals():
            missing_globals.append(global_name)
    
    if missing_globals:
        logger.warning(f"Missing required MCP components: {', '.join(missing_globals)}")
        logger.warning("MCP tools will not be initialized")
        return {}
    
    mcp_tools = {}
    
    # Initialize command-line based MCP servers
    
    
    # Initialize URL-based MCP servers
    
    
    # Log and analyze all initialized MCP tools
    if mcp_tools:
        logger.info(f"✅ Initialized {len(mcp_tools)} MCP tools with full response preservation")
        
        # Detailed analysis of each tool
        for tool_name, tool in mcp_tools.items():
            logger.info(f"🔧 TOOL: {tool_name}")
            
            # Check if tool has expected methods of our custom adapter
            tool_class_name = tool.__class__.__name__
            
            # Determine if this is using our custom adapter by checking its class name
            is_custom_adapter = tool_class_name == "MCPFullResponseTool"
            if is_custom_adapter:
                logger.info(f"  ✅ Using custom adapter: class={tool_class_name}")
            else:
                logger.warning(f"  ⚠️ NOT using custom adapter: class={tool_class_name}")
            
            # Check if tool has __call__ method
            if hasattr(tool, "__call__"):
                logger.debug(f"  ✓ Has __call__ method")
            else:
                logger.error(f"  ✗ Missing __call__ method!")
            
            # Log methods to help debugging
            logger.debug(f"  Methods: {[m for m in dir(tool) if not m.startswith('_') and callable(getattr(tool, m))]}")
    else:
        logger.warning("❌ No MCP tools were initialized")
    
    return mcp_tools

# Initialize MCP tools if configuration available
MCP_TOOLS = initialize_mcp_tools()

# Public exports from this module
__all__ = [
    'ServiceTool',        # The main service tool class
    'TOOLS',              # Dictionary of all tool instances by ID
    'TOOL_NAME_TO_ID',    # Mapping from tool names to IDs
    'NORMALIZED_TOOL_IDS', # Normalized tool ID mapping
    'MCP_TOOLS',          # Dictionary of initialized MCP tools
    'initialize_mcp_tools' # Function to initialize MCP tools
]