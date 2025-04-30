"""MCP Tool Extractor for Python Interpreter Code.

This module provides utilities to extract MCP tool calls from Python code
executed through the Python interpreter. It enhances the visibility of
MCP tool calls in the agent execution graph by creating "virtual" tool steps
that represent individual MCP calls.

It is designed to work with the memory step store system to add these
extracted tool calls as child steps of the original Python interpreter step.
"""

import re
import logging
import datetime
import os
from typing import List, Dict, Any, Tuple, Optional, Set

# Setup logger
logger = logging.getLogger(__name__)

def extract_mcp_tool_calls(
    code: str
) -> List[Tuple[str, str]]:
    """Extract MCP tool calls from Python code.
    
    Parses Python code to identify calls to MCP tools. This looks for
    patterns like 'mattermost_login(...)' where MCP tools are registered
    with their server name as a prefix.
    
    Args:
        code (str): The Python code to analyze
        
    Returns:
        List[Tuple[str, str]]: A list of (tool_name, arguments) tuples
    """
    # Track which mcp tools were found
    found_mcp_tools = []
    
    # Universal pattern to match MCP tool calls following the naming pattern:
    # <mcp_server_name>_<function_name>(arguments)
    # Examples: mattermost_login(...), dremio_execute_query(...), tavily_search(...)
    # This pattern focuses on the naming conventions set in main.py.jinja2
    # where MCP tools are registered with server name prefixes
    
    # Create a pattern that matches any word with underscore followed by a word and parentheses
    # This is the pattern used for MCP tool calls in Python code
    pattern = r'(\w+_\w+)\s*\(([^)]*)\)'
    
    try:
        # Find all matches
        matches = re.finditer(pattern, code)
        for match in matches:
            func_name = match.group(1)
            args = match.group(2)
            
            # Make a basic check if this is likely an MCP tool call
            # Since all MCP tools follow the naming pattern <server>_<function>,
            # simply check if the function name contains an underscore
            is_mcp_tool = False
            
            # Check if the function follows the server_function naming pattern
            if "_" in func_name:
                parts = func_name.split("_", 1)
                if len(parts) == 2 and len(parts[0]) > 0 and len(parts[1]) > 0:
                    # This is the MCP tool naming pattern used in the code
                    is_mcp_tool = True
            
            if is_mcp_tool:
                found_mcp_tools.append((func_name, args))
                logger.info(f"Found MCP tool call: {func_name}({args})")
        
    except Exception as e:
        logger.error(f"Error matching MCP tool pattern: {e}")
    
    return found_mcp_tools

def create_mcp_tool_steps(
    parent_step: Dict[str, Any],
    agent_name: str,
    agent_type: str,
    job_id: str,
    mcp_tool_calls: List[Tuple[str, str]]
) -> List[Dict[str, Any]]:
    """Create virtual tool steps for extracted MCP tool calls.
    
    Creates tool step dictionaries for MCP tool calls that can be added to
    the memory step store as child steps of the original Python interpreter step.
    
    Args:
        parent_step (Dict[str, Any]): The parent Python interpreter step
        agent_name (str): The name of the agent
        agent_type (str): The type of agent (e.g. CodeAgent)
        job_id (str): The job ID
        mcp_tool_calls (List[Tuple[str, str]]): MCP tool calls as (name, args) tuples
        
    Returns:
        List[Dict[str, Any]]: A list of tool step dictionaries
    """
    tool_steps = []
    
    # Get parent step attributes
    parent_step_id = parent_step.get("id")
    step_number = parent_step.get("step_number")
    start_time = parent_step.get("start_time")
    end_time = parent_step.get("end_time")
    duration = parent_step.get("duration")
    
    # Get depth - MCP tools should be one level deeper than Python interpreter
    parent_depth = parent_step.get("depth", 1)
    mcp_tool_depth = parent_depth + 1
    
    # Create a tool step for each MCP tool call
    for idx, (mcp_tool_name, mcp_tool_args) in enumerate(mcp_tool_calls):
        # Generate a unique step ID including the parent step ID and an index
        # Format: mcp-{tool_name}-{parent_step_id}-{index}
        # This ensures each MCP tool call has a unique ID that's linked to the parent
        tool_step_id = f"mcp-{mcp_tool_name}-{agent_name}-{step_number}-{idx}-{job_id}"
        
        # Create the tool step 
        tool_step = {
            "id": tool_step_id,
            "tool_name": mcp_tool_name,
            "tool_id": mcp_tool_name,  # Use the name as the ID
            "agent_name": agent_name,
            "agent_type": agent_type,
            "step_number": f"{step_number}.{idx+1}",  # Use parent step # with a sub-step index
            "depth": mcp_tool_depth,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
            "timestamp": datetime.datetime.now().isoformat(),
            "arguments": mcp_tool_args,
            "observation": parent_step.get("observations"),  # Share observation with parent
            "step_type": "mcp_tool",  # Special step type to distinguish from regular tool calls
            "parent_step_id": parent_step_id,  # Link back to the parent Python interpreter step
            "job_id": job_id
        }
        
        tool_steps.append(tool_step)
    
    return tool_steps

def register_mcp_tool_steps(
    memory_store, 
    parent_step: Dict[str, Any],
    agent_name: str,
    agent_type: str,
    job_id: str
) -> None:
    """Register MCP tool steps from a Python interpreter step.
    
    Extracts MCP tool calls from Python interpreter code, creates tool steps,
    and registers them in the memory store.
    
    Args:
        memory_store: The memory step store instance
        parent_step (Dict[str, Any]): The parent Python interpreter step
        agent_name (str): The name of the agent
        agent_type (str): The type of agent (e.g. CodeAgent)
        job_id (str): The job ID
    """
    # Extract MCP tool calls from any Python interpreter step
    if parent_step.get("step_type") == "agent" and parent_step.get("tool_calls"):
        # Look for Python interpreter tool calls
        for tc in parent_step.get("tool_calls", []):
            if tc.get("name") == "python_interpreter":
                code = tc.get("arguments")
                if not isinstance(code, str):
                    continue
                    
                # Extract MCP tool calls from the Python code
                mcp_tool_calls = extract_mcp_tool_calls(code)
                if not mcp_tool_calls:
                    continue
                    
                # Create tool steps for each MCP tool call
                mcp_tool_steps = create_mcp_tool_steps(
                    parent_step, 
                    agent_name, 
                    agent_type, 
                    job_id, 
                    mcp_tool_calls
                )
                
                # Register each MCP tool step in the memory store
                for tool_step in mcp_tool_steps:
                    try:
                        # Add each tool step to the memory store
                        memory_store.tool_steps.append(tool_step)
                        
                        # Add the MCP tool step ID to the parent's child steps
                        if "child_step_ids" not in parent_step:
                            parent_step["child_step_ids"] = []
                        parent_step["child_step_ids"].append(tool_step["id"])
                        
                        # Log successful registration
                        logger.info(f"Registered MCP tool step for {tool_step['tool_name']} as child of {parent_step['id']}")
                    except Exception as e:
                        logger.error(f"Error registering MCP tool step: {str(e)}")

# Public exports
__all__ = [
    'extract_mcp_tool_calls',
    'create_mcp_tool_steps',
    'register_mcp_tool_steps'
]