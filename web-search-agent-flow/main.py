"""FastAPI service for multi-agent system."""
import os
import json
import uuid
import logging
import asyncio
import threading
import contextlib
from typing import Dict, Any, List, Optional, Sequence, Union
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from smolagents.memory import ActionStep

# Import modules
from modules.memory import MEMORY_STEP_STORE, OUTPUT_REGISTRY
from modules.telemetry import setup_telemetry

from modules.models import (
    MessageRequest, 
    AgentResponse, 
    StepResponse
)
from modules.agents import (
    initialize_agents, 
    MANAGER, 
    step_callback,
    setup_agent_relationship_tracking
)
from modules.fastapi_mcp_integration import setup_fastapi_mcp
from api import register_routes

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Silence httpx logger
logging.getLogger("httpx").setLevel(logging.WARNING)

# Set up MCP server globals
MCP_SERVER_CONTEXTS = contextlib.ExitStack()

# Declare global variables first, then assign values to avoid Python syntax errors
# "name is assigned to before global declaration"
global MCP_TOOLS
# Store all collected MCP tools as a global for agent initialization
# This follows the HuggingFace pattern of passing tools directly to agents
MCP_TOOLS = []

# Initialize FastAPI app
app = FastAPI(
    title="Agent Flow Multi-Agent System",
    description="Generated multi-agent system service",
    version="1.0.0"
)

# Register event handlers
@app.on_event("startup")
async def startup_event():
    try:
        # Check if opentelemetry module is available before attempting setup
        try:
            import opentelemetry
            logger.info(f"OpenTelemetry available: version {opentelemetry.__version__}")
            tracer_provider = setup_telemetry()
            if tracer_provider is None:
                logger.warning("Telemetry setup returned None, telemetry may be disabled")
            else:
                logger.info("Telemetry instrumentation initialized successfully")
        except ImportError:
            logger.warning("OpenTelemetry module not available. Telemetry will be disabled.")
    except Exception as e:
        logger.error(f"Error initializing telemetry: {str(e)}")
        logger.warning("Continuing without telemetry instrumentation")

@app.on_event("startup")
async def clear_memory_steps():
    MEMORY_STEP_STORE.clear()
    logger.info("Memory step store initialized")
    
    # Apply nest_asyncio patch if we're not using uvloop
    # This helps with tools like graphrag that need to create their own event loops
    try:
        import nest_asyncio
        import asyncio
        
        # Only apply the patch if we're using the standard asyncio loop
        if isinstance(asyncio.get_event_loop(), asyncio.BaseEventLoop) and not str(type(asyncio.get_event_loop())).startswith("<class 'uvloop."):
            logger.info("Applying nest_asyncio patch to standard asyncio loop")
            nest_asyncio.apply()
        else:
            logger.warning("Not applying nest_asyncio patch - incompatible loop type detected")
            logger.warning(f"Current loop type: {type(asyncio.get_event_loop())}")
    except ImportError:
        logger.warning("nest_asyncio module not available, skipping loop patch")
    except Exception as e:
        logger.warning(f"Error applying nest_asyncio patch: {str(e)}")
        logger.warning("Agent tools requiring nested event loops may not work")



@app.on_event("startup")
async def initialize_mcp_servers():
    """Initialize MCP server connections."""
    # Set up more detailed logging for MCP server initialization
    import sys
    import io
    import traceback
    import inspect
    import json
    import os.path
    
    # Import ToolCollection - try the newer location first, then fall back to the older location
    try:
        from smolagents import ToolCollection
        logger.info("Using ToolCollection from smolagents package")
        # Log version if available
        try:
            import smolagents
            logger.info(f"smolagents version: {smolagents.__version__}")
        except (ImportError, AttributeError):
            logger.info("Could not determine smolagents version")
    except ImportError:
        try:
            from smolagents.agents import ToolCollection
            logger.info("Using ToolCollection from smolagents.agents package")
        except ImportError:
            logger.error("Failed to import ToolCollection from either smolagents or smolagents.agents")
            raise
    
    try:
        # Try to import MCP module and log version
        try:
            import mcp
            logger.info(f"mcp module available, version: {getattr(mcp, '__version__', 'unknown')}")
        except ImportError:
            logger.info("mcp module not available")
        
        global MCP_SERVER_CONTEXTS
        
        # Command-based MCP servers - fully auto-discover all server paths without hardcoding
        import os.path
        import glob
        
        # In production, MCP servers are located at ../../mcp-servers relative to the service
        # This accommodates the standard project layout where services and MCP servers are siblings
        mcp_servers_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "mcp-servers"))
        logger.info(f"Looking for MCP servers in: {mcp_servers_dir}")
        
        # Automatically discover all available MCP servers by finding build/index.js files
        available_mcp_servers = {}
        
        # Only scan if the directory exists
        if os.path.isdir(mcp_servers_dir):
            logger.info(f"Scanning MCP servers directory: {mcp_servers_dir}")
            
            # Find all directories that contain a build/index.js file
            for dir_name in os.listdir(mcp_servers_dir):
                dir_path = os.path.join(mcp_servers_dir, dir_name)
                if os.path.isdir(dir_path):
                    index_js_path = os.path.join(dir_path, "build", "index.js")
                    if os.path.isfile(index_js_path):
                        logger.info(f"Found MCP server in {dir_name}: {index_js_path}")
                        
                        # Store the information about this MCP server
                        available_mcp_servers[dir_name] = {
                            "path": index_js_path,
                            "directory": dir_name
                        }
            
            logger.info(f"Found {len(available_mcp_servers)} MCP servers with build/index.js files")
        else:
            logger.warning(f"MCP servers directory not found: {mcp_servers_dir}")
        
        # Function to find the most appropriate MCP server directory for a given server name
        def find_mcp_server_dir(server_name):
            # First try exact match (case-insensitive)
            server_name_lower = server_name.lower()
            for dir_name, info in available_mcp_servers.items():
                if dir_name.lower() == server_name_lower:
                    logger.info(f"Found exact match for {server_name}: {dir_name}")
                    return dir_name
            
            # No exact match, look for partial matches
            # Score each directory by how well it matches the server name
            # Higher score = better match
            match_scores = {}
            for dir_name, info in available_mcp_servers.items():
                dir_lower = dir_name.lower()
                
                # Calculate match score: prioritize exact substrings and prefix/suffix matches
                score = 0
                
                # Exact substring match
                if server_name_lower in dir_lower:
                    score += 10
                    # If server name is at start/end, even better
                    if dir_lower.startswith(server_name_lower):
                        score += 5
                    if dir_lower.endswith(server_name_lower):
                        score += 5
                
                # Reverse check: directory name in server name
                if dir_lower in server_name_lower:
                    score += 8
                
                # Word boundary matches with the server's name parts
                server_parts = server_name_lower.replace('-', ' ').split()
                dir_parts = dir_lower.replace('-', ' ').split()
                
                # Count matching words
                for part in server_parts:
                    if part in dir_parts:
                        score += 3
                
                # Only consider directories with a positive score
                if score > 0:
                    match_scores[dir_name] = score
            
            # If we have matches, pick the highest score
            if match_scores:
                best_match = max(match_scores.items(), key=lambda x: x[1])[0]
                logger.info(f"Best partial match for {server_name}: {best_match} (score: {match_scores[best_match]})")
                return best_match
            
            # No good matches found - try simple substring search as fallback
            substring_matches = []
            for dir_name in available_mcp_servers:
                # Check if any part of the server name is in the directory name
                if any(part in dir_name.lower() for part in server_name_lower.split('-')):
                    substring_matches.append(dir_name)
            
            if substring_matches:
                # Sort by length (prefer shorter names) and take the first
                substring_matches.sort(key=len)
                logger.info(f"Using substring match for {server_name}: {substring_matches[0]}")
                return substring_matches[0]
            
            # No matching MCP server found, return the original name as fallback
            # This will likely fail but we'll catch and handle that error later
            logger.warning(f"No matching MCP server found for {server_name}, using original name")
            return server_name
            
        # Define all configured MCP servers
        command_servers = [
            
        ]
        
        # URL-based MCP servers
        url_servers = [
            
        ]
        
        # NEW: Get required MCP servers by analyzing the agent graph
        required_server_names = set()
        try:
            # Try to load the agent-graph.json file
            graph_path = os.path.join(os.path.dirname(__file__), "agent-graph.json")
            if os.path.exists(graph_path):
                logger.info(f"Loading agent graph from {graph_path} to determine required MCP servers")
                with open(graph_path, 'r') as f:
                    agent_graph = json.load(f)
                
                # Extract all edge relationships
                edges = agent_graph.get('edges', [])
                
                # Get all tool nodes
                nodes = agent_graph.get('nodes', [])
                tool_nodes = {node['id']: node for node in nodes if node.get('type') == 'tool'}
                
                # Extract server names from tool IDs
                for _, tool_node in tool_nodes.items():
                    tool_id = tool_node.get('id', '')
                    if 'mcp-' in tool_id or 'mcp_' in tool_id:
                        # Extract server name from tool ID (format: mcp-server-function)
                        parts = tool_id.replace('_', '-').split('-')
                        if len(parts) > 1 and parts[0] == 'mcp':
                            server_name = parts[1]
                            required_server_names.add(server_name)
                            logger.info(f"Found required MCP server '{server_name}' from tool ID '{tool_id}'")
                
                # Also scan node data for tool references
                for node in nodes:
                    if node.get('type') == 'agent':
                        # Check service_tool_ids if present
                        service_tool_ids = node.get('data', {}).get('service_tool_ids', [])
                        for tool_id in service_tool_ids:
                            if 'mcp-' in tool_id or 'mcp_' in tool_id:
                                parts = tool_id.replace('_', '-').split('-')
                                if len(parts) > 1 and parts[0] == 'mcp':
                                    server_name = parts[1]
                                    required_server_names.add(server_name)
                                    logger.info(f"Found required MCP server '{server_name}' from service_tool_ids in agent '{node.get('id')}'")
            else:
                logger.warning(f"Agent graph file not found at {graph_path}. Will initialize all configured MCP servers.")
                # If we can't determine the required servers, initialize all of them
                required_server_names = {server['name'] for server in command_servers + url_servers}
        except Exception as e:
            logger.error(f"Error analyzing agent graph to determine required MCP servers: {str(e)}")
            logger.error(f"Detailed traceback: {traceback.format_exc()}")
            # Fall back to initializing all servers
            required_server_names = {server['name'] for server in command_servers + url_servers}
        
        # If no required servers were found, initialize all
        if not required_server_names:
            logger.warning("No required MCP servers found in agent graph. Will initialize all configured servers.")
            required_server_names = {server['name'] for server in command_servers + url_servers}
        
        # Filter servers to only include those required by the agent graph
        filtered_command_servers = [s for s in command_servers if s['name'] in required_server_names]
        filtered_url_servers = [s for s in url_servers if s['name'] in required_server_names]
        
        # Log server filtering results
        logger.info(f"Required MCP servers from agent graph: {sorted(required_server_names)}")
        logger.info(f"Command MCP servers to initialize: {len(filtered_command_servers)} of {len(command_servers)}")
        logger.info(f"URL MCP servers to initialize: {len(filtered_url_servers)} of {len(url_servers)}")
        logger.info(f"Command-based MCP servers to initialize: {[s['name'] for s in filtered_command_servers]}")
        logger.info(f"URL-based MCP servers to initialize: {[s['name'] for s in filtered_url_servers]}")
        
        # Initialize filtered command-based MCP servers
        for server in filtered_command_servers:
            try:
                logger.info(f"=============== INITIALIZING MCP SERVER: {server['name']} ===============")
                logger.info(f"Server details: command={server['command']}")
                logger.info(f"Server args: {server.get('args', [])}")
                # Log environment variables without sensitive values
                safe_env = {}
                if "env" in server and server["env"]:
                    for k, v in server["env"].items():
                        if any(sensitive in k.lower() for sensitive in ["key", "token", "secret", "password", "credential"]):
                            safe_env[k] = "********" # Mask sensitive values
                        else:
                            safe_env[k] = v
                logger.info(f"Server environment variables: {safe_env}")
                
                # For command-based MCP servers, we need to use StdioServerParameters
                # First try to import StdioServerParameters from mcp
                logger.info("Trying to use StdioServerParameters from mcp package")
                try:
                    from mcp import StdioServerParameters
                    
                    # Log signature of StdioServerParameters constructor
                    try:
                        sig = inspect.signature(StdioServerParameters.__init__)
                        logger.info(f"StdioServerParameters signature: {sig}")
                    except Exception as sig_err:
                        logger.info(f"Could not get signature: {sig_err}")
                    
                    # Import in a way that ensures no SyntaxError
                    # By passing a simple Python dictionary (no keyword args)
                    server_dict = {
                        "command": server["command"]
                    }
                    logger.info(f"Creating base server_dict with command: {server_dict}")
                    
                    # Only add optional args if present
                    if "args" in server and server["args"]:
                        server_dict["args"] = server["args"]
                        logger.info(f"Added args to server_dict: {server['args']}")
                    
                    if "env" in server and server["env"]:
                        server_dict["env"] = server["env"]
                        logger.info(f"Added env to server_dict (with sensitive values masked): {safe_env}")
                    
                    # Log the final dictionary we're passing to StdioServerParameters
                    logger.info(f"Final server_dict for {server['name']}: {server_dict.keys()}")
                    
                    # Check if this is a file path or a command in the system PATH
                    import shutil
                    is_file_path = '/' in server["command"] or '\\' in server["command"]
                    
                    if is_file_path:
                        # This is a file path, verify it exists
                        if not os.path.isfile(server["command"]):
                            logger.error(f"MCP server executable not found: {server['command']}")
                            logger.error(f"This is likely due to the MCP server not being built.")
                            logger.error(f"To build the MCP server, run: cd {os.path.dirname(os.path.dirname(server['command']))} && pnpm install && pnpm build")
                            logger.error(f"For more information, see the mcp-subtrees-instructions.md file.")
                            
                            # Continue with other servers instead of failing
                            logger.warning(f"Skipping MCP server {server['name']} due to missing executable")
                            continue
                    else:
                        # This is a command from the system PATH (like 'uv', 'node', 'python')
                        cmd_in_path = shutil.which(server["command"])
                        
                        if cmd_in_path:
                            logger.info(f"Found command '{server['command']}' in system PATH: {cmd_in_path}")
                        else:
                            logger.warning(f"Command '{server['command']}' not found in system PATH, will try it anyway")
                            
                        # Command is valid, continue with initialization
                        logger.info(f"Using command from system PATH: {server['command']}")
                    
                    # Pass as unpacked keyword arguments to avoid parameter order issues
                    try:
                        logger.info(f"Creating StdioServerParameters for {server['name']}")
                        server_parameters = StdioServerParameters(**server_dict)
                        logger.info(f"Created StdioServerParameters successfully: {type(server_parameters)}")
                    except Exception as param_err:
                        logger.error(f"Error creating StdioServerParameters: {str(param_err)}")
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        raise
                except ImportError:
                    # If mcp package is not available, create a compatible dict
                    logger.info("mcp package not available, using dictionary format")
                    server_parameters = {
                        "command": server["command"],
                        "args": server.get("args", []),
                        "env": server.get("env", {})
                    }
                    logger.info(f"Created server_parameters dictionary: {server_parameters.keys()}")
                
                # Use ToolCollection.from_mcp directly
                logger.info(f"Calling ToolCollection.from_mcp for {server['name']}")
                try:
                    # We cannot pass stderr to from_mcp because it doesn't accept this parameter
                    # Pass trust_remote_code=True to acknowledge we trust the MCP server
                    tool_collection = ToolCollection.from_mcp(server_parameters, trust_remote_code=True)
                    logger.info(f"ToolCollection.from_mcp succeeded for {server['name']}")
                except Exception as tc_err:
                    # Special handling for the specific error message we're seeing
                    error_str = str(tc_err)
                    if "parameter without a default follows parameter with a default" in error_str:
                        logger.error("DETECTED PARAMETER ORDER ERROR in MCP server")
                        logger.error(f"This is likely due to a parameter ordering issue in the Node.js script: {server['command']}")
                        logger.error("Examine line numbers mentioned in the error message to locate the problematic code")
                        
                        # Check if this is the tavily-search server
                        if server['name'] == 'tavily-search':
                            logger.error("This is the Tavily MCP server which may have a specific issue with environment variables")
                            # Log the environment variables we're trying to pass (sanitized)
                            if "env" in server and server["env"]:
                                env_keys = list(server["env"].keys())
                                logger.error(f"Environment variables being passed: {env_keys}")
                                if "TAVILY_API_KEY" in env_keys:
                                    logger.error("TAVILY_API_KEY is present in the environment")
                                else:
                                    logger.error("TAVILY_API_KEY is NOT present in the environment - this is likely the issue")
                    
                    logger.error(f"Error in ToolCollection.from_mcp: {error_str}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    raise
                
                # Enter the context and store it in our ExitStack
                logger.info(f"Entering context for {server['name']} tool collection")
                activated_tc = MCP_SERVER_CONTEXTS.enter_context(tool_collection)
                logger.info(f"Context entered successfully for {server['name']}")
                
                # Per HuggingFace documentation, MCP tools should be used directly
                # "with ToolCollection.from_mcp(server_parameters) as tool_collection:
                #     agent = CodeAgent(tools=[*tool_collection.tools], add_base_tools=True)"
                
                # Log the available tools
                if hasattr(activated_tc, 'tools') and activated_tc.tools:
                    logger.info(f"Found {len(activated_tc.tools)} tools in {server['name']} MCP server")
                    
                    # Also maintain the existing behavior for compatibility
                    from modules.tools import TOOLS
                    
                    # Create copies of tools with prefixed names to avoid collisions
                    prefixed_tools = []
                    for i, tool in enumerate(activated_tc.tools):
                        # Log information about the tool
                        original_name = tool.name
                        logger.info(f"Tool {i+1}: {original_name} (type: {type(tool).__name__})")
                        logger.info(f"  Description: {getattr(tool, 'description', 'No description')}")
                        
                        # Create a prefixed name to avoid collisions with other MCP servers
                        # Also ensure the name is Python-safe by replacing dashes with underscores
                        server_name_safe = server['name'].replace('-', '_')
                        original_name_safe = original_name.replace('-', '_')
                        prefixed_name = f"{server_name_safe}_{original_name_safe}"
                        
                        # Create a copy of the tool with modified name
                        import copy
                        prefixed_tool = copy.copy(tool)
                        prefixed_tool.name = prefixed_name
                        
                        # Store the original names for reference
                        prefixed_tool._server_name = server['name']
                        prefixed_tool._original_name = original_name
                        logger.info(f"  Renamed tool '{original_name}' to '{prefixed_name}' to avoid collisions")
                        
                        # Add the prefixed tool to our list
                        prefixed_tools.append(prefixed_tool)
                        
                        # Register in TOOLS for compatibility with existing code
                        tool_id = f"mcp-{server['name']}-{original_name}"
                        logger.info(f"  Also registering in TOOLS as: {tool_id}")
                        TOOLS[tool_id] = prefixed_tool
                        
                        # Log tool names for debugging agent prompts
                        logger.info(f"  This tool should be referenced as '{prefixed_name}' in agent code")
                    
                    # Add each prefixed MCP tool to the global list
                    # global declaration is now at the top level of the module
                    MCP_TOOLS.extend(prefixed_tools)
                else:
                    logger.warning(f"No tools found in {server['name']} MCP server")
                
                # We don't capture stderr separately anymore
                # No need to check for captured error output
                    
                logger.info(f"MCP server initialized successfully: {server['name']}")
            except Exception as e:
                logger.error(f"Error initializing command MCP server {server['name']}: {str(e)}")
                logger.error(f"Detailed traceback: {traceback.format_exc()}")
        
        # Initialize filtered URL-based MCP servers
        for server in filtered_url_servers:
            try:
                logger.info(f"=============== INITIALIZING URL MCP SERVER: {server['name']} ===============")
                logger.info(f"Server URL: {server['url']}")
                # Log non-sensitive headers
                safe_headers = {}
                if "headers" in server and server["headers"]:
                    for k, v in server["headers"].items():
                        if any(sensitive in k.lower() for sensitive in ["key", "token", "secret", "password", "credential", "auth"]):
                            safe_headers[k] = "********" # Mask sensitive values
                        else:
                            safe_headers[k] = v
                logger.info(f"Server headers: {safe_headers}")
                
                # URL-based MCP server parameters should be formatted as a dictionary
                logger.info(f"Creating URL-based parameters for MCP server: {server['name']}")
                server_parameters = {
                    "url": server["url"]
                }
                
                # Add headers if provided
                if server["headers"]:
                    server_parameters["headers"] = server["headers"]
                    logger.info(f"Added headers to URL parameters (sensitive values masked): {safe_headers}")
                
                # Use ToolCollection.from_mcp directly
                logger.info(f"Calling ToolCollection.from_mcp for URL server {server['name']}")
                try:
                    # For URL-based servers, pass parameters directly and trust_remote_code=True
                    tool_collection = ToolCollection.from_mcp(server_parameters, trust_remote_code=True)
                    logger.info(f"ToolCollection.from_mcp succeeded for URL server {server['name']}")
                except Exception as tc_err:
                    error_str = str(tc_err)
                    logger.error(f"Error in ToolCollection.from_mcp for URL server: {error_str}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    
                    # Provide helpful error message for common issues
                    if "ECONNREFUSED" in error_str or "ConnectTimeoutError" in error_str:
                        logger.error(f"Could not connect to MCP server at {server['url']}")
                        logger.error(f"Check that the server is running and accessible.")
                        
                        # Continue with other servers instead of failing
                        logger.warning(f"Skipping MCP server {server['name']} due to connection failure")
                        continue
                    
                    raise
                
                # Enter the context and store it in our ExitStack
                logger.info(f"Entering context for URL server {server['name']} tool collection")
                activated_tc = MCP_SERVER_CONTEXTS.enter_context(tool_collection)
                logger.info(f"Context entered successfully for URL server {server['name']}")
                
                # Per HuggingFace documentation, MCP tools should be used directly
                # "with ToolCollection.from_mcp(server_parameters) as tool_collection:
                #     agent = CodeAgent(tools=[*tool_collection.tools], add_base_tools=True)"
                
                # Log the available tools
                if hasattr(activated_tc, 'tools') and activated_tc.tools:
                    logger.info(f"Found {len(activated_tc.tools)} tools in URL server {server['name']}")
                    
                    # Also maintain the existing behavior for compatibility
                    from modules.tools import TOOLS
                    
                    # Create copies of tools with prefixed names to avoid collisions
                    prefixed_tools = []
                    for i, tool in enumerate(activated_tc.tools):
                        # Log information about the tool
                        original_name = tool.name
                        logger.info(f"Tool {i+1}: {original_name} (type: {type(tool).__name__})")
                        logger.info(f"  Description: {getattr(tool, 'description', 'No description')}")
                        
                        # Create a prefixed name to avoid collisions with other MCP servers
                        # Also ensure the name is Python-safe by replacing dashes with underscores
                        server_name_safe = server['name'].replace('-', '_')
                        original_name_safe = original_name.replace('-', '_')
                        prefixed_name = f"{server_name_safe}_{original_name_safe}"
                        
                        # Create a copy of the tool with modified name
                        import copy
                        prefixed_tool = copy.copy(tool)
                        prefixed_tool.name = prefixed_name
                        
                        # Store the original names for reference
                        prefixed_tool._server_name = server['name']
                        prefixed_tool._original_name = original_name
                        logger.info(f"  Renamed tool '{original_name}' to '{prefixed_name}' to avoid collisions")
                        
                        # Add the prefixed tool to our list
                        prefixed_tools.append(prefixed_tool)
                        
                        # Register in TOOLS for compatibility with existing code
                        tool_id = f"mcp-{server['name']}-{original_name}"
                        logger.info(f"  Also registering in TOOLS as: {tool_id}")
                        TOOLS[tool_id] = prefixed_tool
                        
                        # Log tool names for debugging agent prompts
                        logger.info(f"  This tool should be referenced as '{prefixed_name}' in agent code")
                    
                    # Add each prefixed MCP tool to the global list
                    # global declaration is now at the top level of the module
                    MCP_TOOLS.extend(prefixed_tools)
                else:
                    logger.warning(f"No tools found in URL server {server['name']}")
                
                logger.info(f"URL MCP server initialized successfully: {server['name']}")
            except Exception as e:
                logger.error(f"Error initializing URL MCP server {server['name']}: {str(e)}")
                logger.error(f"Detailed traceback: {traceback.format_exc()}")
                
        logger.info("========== MCP SERVER INITIALIZATION COMPLETE ==========")
    except Exception as e:
        logger.error(f"Error in MCP server initialization: {str(e)}")
        logger.error(f"Detailed traceback: {traceback.format_exc()}")

@app.on_event("startup")
async def initialize_agent_system():
    # Initialize the agent system
    initialize_agents()
    logger.info("Agent system initialized")
    
    # Log important reminder about MCP tool usage
    logger.info("IMPORTANT NOTE: MCP tools are only accessible through the agent's tools list.")
    logger.info("This ensures the custom adapter is used for preserving full response structure.")

@app.on_event("startup")
async def setup_mcp_server():
    """Set up this agent as an MCP server itself."""
    try:
        # Determine base URL from environment variables or default
        port = os.environ.get("PORT", "8000")
        host = os.environ.get("HOST", "0.0.0.0")
        base_url = os.environ.get("FASTAPI_MCP_BASE_URL", f"http://{host}:{port}")
        
        # Initialize the FastAPI MCP integration
        mcp_server = setup_fastapi_mcp(app, base_url=base_url)
        
        if mcp_server:
            logger.info("This Agent Flow service is now available as an MCP server")
            logger.info(f"MCP server base URL: {base_url}")
            logger.info("MCP server provides all API endpoints as MCP tools")
        else:
            logger.warning("Failed to set up FastAPI MCP integration - this service will not be available as an MCP server")
    except Exception as e:
        logger.error(f"Error setting up MCP server: {str(e)}")
        logger.warning("Service will continue without MCP server capabilities")

@app.on_event("shutdown")
async def shutdown_mcp_servers():
    """Clean up MCP server connections."""
    try:
        global MCP_SERVER_CONTEXTS
        MCP_SERVER_CONTEXTS.close()
        logger.info("MCP server connections closed")
    except Exception as e:
        logger.error(f"Error closing MCP server connections: {str(e)}")

# Register all routes from API modules
register_routes(app)

# Add a direct route to /process for compatibility with the frontend
# which tries to access this endpoint without the /job prefix
from api.job import process_message

# Forward requests from /process to /job/process to maintain compatibility
@app.post("/process", response_model=AgentResponse, tags=["compatibility"])
async def root_process_message(request: MessageRequest) -> AgentResponse:
    """Compatibility endpoint that forwards to the job processor.
    
    The frontend expects this endpoint at the root level, but our API
    structure has it under /job/process. This is a simple forwarder.
    """
    return await process_message(request)