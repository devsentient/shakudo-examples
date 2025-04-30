"""Custom MCP Adapter for preserving full structured responses.

This module provides a custom adapter for MCP tools that preserves the full
response structure including both content and data fields, allowing agents
to access complete structured data instead of just text previews.

⚠️ IMPORTANT IMPLEMENTATION NOTE ⚠️
----------------------------------
This adapter must be used consistently across the codebase. To ensure this:

1. MCP tools should ONLY be accessed through the agent's tools list, never directly.
2. MCP tools are intentionally NOT registered in the Python executor state.
3. This guarantees that all MCP tool calls go through this adapter.

If tools were registered directly in the Python executor state, they might
bypass this adapter, leading to inconsistent behavior and potential data loss.

Example Usage with Mattermost MCP:
---------------------------------
```python
# Search for messages mentioning "yevgeniy"
# ✅ CORRECT: Use the tool directly through the agent's tool calling mechanism
result = mattermost_search_posts({
    "team_id": "your_team_id",
    "terms": "yevgeniy"
})

# Access full message content instead of truncated content
posts = result['data']['posts']
full_messages = []

for post_id in result['data']['order']:
    post = posts[post_id]
    # Access full message from either field
    full_content = post.get('full_message') or post.get('message')
    full_messages.append(full_content)
    
# Full messages contain complete content, not truncated with "..."
for message in full_messages:
    print(message)
```

The difference between standard adapter and this custom adapter:
Standard adapter: Only returns text content (truncated with "...")
Custom adapter: Returns complete response with structured data

Response Structure:
------------------
All MCP tools return responses with this structure:
{
    "content": [{"type": "text", "text": "Preview text (might be truncated)"}],
    "data": {
        # Full structured data from the original MCP response
        # This varies by tool but contains the complete response
    }
}

By accessing the 'data' field, agents can work with the complete structured
response rather than just the text preview in the 'content' field.
"""

from typing import Any, Callable, Dict, List, Optional, Type, Union
import logging
import json
import sys
from smolagents import Tool

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Ensure DEBUG level is enabled

# Define server parameter types for custom adapter
# These match the expected parameters from main.py
ServerParameters = Union[Dict[str, Any], 'StdioServerParameters', 'SSEServerParameters']

# Import MCP classes if available, or define placeholder types
try:
    # First, try to import from mcp package directly (current pattern)
    from mcp import StdioServerParameters
    logger.info("✅ Successfully imported StdioServerParameters from mcp package")
    
    # Try to import SSEServerParameters from mcp
    try:
        from mcp import SSEServerParameters
        logger.info("✅ Successfully imported SSEServerParameters from mcp package")
    except ImportError:
        # SSEServerParameters not in mcp - we'll use dict-based fallback
        logger.warning("⚠️ SSEServerParameters not available in mcp package, using custom fallback class")
        
        # Define a placeholder class for compatibility
        class SSEServerParameters:
            """Placeholder for SSEServerParameters."""
            def __init__(self, url: str, **kwargs):
                self.url = url
                self.__dict__.update(kwargs)
                logger.info(f"Created placeholder SSEServerParameters with url: {url}")
        
except ImportError as e:
    # Failed to import from mcp - provide fallback classes
    logger.warning(f"⚠️ Failed to import from mcp package: {e}")
    
    # Define placeholder classes for compatibility
    class StdioServerParameters:
        """Placeholder for StdioServerParameters."""
        def __init__(self, command: str, args: List[str] = None, env: Dict[str, str] = None):
            import os
            
            # Process the command based on whether it's a path or a command name
            if '/' in command or '\\' in command:
                # This is a file path, process it
                # Determine if we need an interpreter
                if command.lower().endswith('.py'):
                    # Python script - use python interpreter
                    if args is None:
                        args = []
                    args = [command] + list(args)
                    command = 'python3'
                    logger.info(f"Using Python interpreter for file: {command} {args[0]}")
                elif command.lower().endswith('.js'):
                    # JavaScript file - use node
                    if args is None:
                        args = []
                    args = [command] + list(args)
                    command = 'node'
                    logger.info(f"Using Node.js for file: {command} {args[0]}")
                else:
                    # Direct executable path
                    logger.info(f"Using direct executable path: {command}")
            else:
                # This is a command name - use as is
                logger.info(f"Using command from system PATH: {command}")
                
            self.command = command
            self.args = args or []
            self.env = env or {}
            logger.info(f"Created StdioServerParameters with command: {command}, args: {self.args}")
    
    class SSEServerParameters:
        """Placeholder for SSEServerParameters."""
        def __init__(self, url: str, **kwargs):
            self.url = url
            self.__dict__.update(kwargs)
            logger.info(f"Created placeholder SSEServerParameters with url: {url}")
            
    logger.warning("Using placeholder classes for MCP server parameters")

class FullResponseSmolAgentsAdapter:
    """Custom SmolAgents adapter that preserves the full MCP response structure.
    
    Unlike the default SmolAgentsAdapter which extracts only the text content,
    this adapter preserves the complete MCP response structure, including the
    'data' field that contains full structured data. This allows agents to
    access both the text preview and the complete structured data.
    """
    
    def __init__(self):
        logger.info("🔧 ADAPTER CLASS INIT: FullResponseSmolAgentsAdapter initialized")
        logger.info("This adapter preserves complete structured responses from MCP tools")
    
    def adapt(self, *args, **kwargs) -> Type[Tool]:
        """Adapt an MCP tool to a SmolAgents tool that preserves structured data.
        
        This method is flexible and can handle different argument patterns:
        - When called as adapt(name, description, function, inputs)
        - When called as adapt(function)
        - When called as adapt(partial_function, tool)
        - When called with other patterns from different MCP versions
        
        Returns:
            A Tool class that preserves the full MCP response
        """
        # Handle different calling conventions
        if len(args) == 4:  # Standard pattern (name, description, function, inputs)
            name, description, function, inputs = args
        elif len(args) == 1 and callable(args[0]):  # Function-only pattern (for some MCP versions)
            function = args[0]
            name = getattr(function, "__name__", "unknown_tool")
            description = getattr(function, "__doc__", "No description available")
            inputs = {}
        elif len(args) == 2:  # New pattern in MCP 0.6.0+ (partial_function, tool)
            # This matches the pattern we're seeing in the logs
            partial_fn, tool_obj = args
            
            # Extract information from the tool object
            if hasattr(tool_obj, "name"):
                name = tool_obj.name
            else:
                name = getattr(partial_fn.func, "__name__", "unknown_tool")
                if hasattr(partial_fn, "args") and len(partial_fn.args) > 0:
                    # For partial functions, sometimes the tool name is in args[0]
                    if isinstance(partial_fn.args[0], str):
                        name = partial_fn.args[0]
                        
            # Get description - either from tool or function docstring
            if hasattr(tool_obj, "description") and tool_obj.description:
                description = tool_obj.description
            else:
                description = getattr(partial_fn.func, "__doc__", "No description available")
                
            # Get input schema
            if hasattr(tool_obj, "inputSchema"):
                inputs = tool_obj.inputSchema
            else:
                inputs = {}
                
            # Use the partial function as our function
            function = partial_fn
        elif kwargs and "function" in kwargs:  # Keyword arguments pattern
            function = kwargs["function"]
            name = kwargs.get("name", getattr(function, "__name__", "unknown_tool"))
            description = kwargs.get("description", getattr(function, "__doc__", "No description available"))
            inputs = kwargs.get("inputs", {})
        else:
            # Try one more fallback for handling functools.partial with tuple unpacking
            if len(args) > 0 and hasattr(args[0], "func") and hasattr(args[0], "args"):
                # This looks like a functools.partial object
                function = args[0]
                # Try to extract the name from partial.args[0] if it's a string
                if hasattr(function, "args") and len(function.args) > 0 and isinstance(function.args[0], str):
                    name = function.args[0]
                else:
                    name = getattr(function.func, "__name__", "unknown_tool")
                description = getattr(function.func, "__doc__", "No description available")
                inputs = {}
                logger.warning(f"🔧 ADAPTER FALLBACK: Using functools.partial fallback for {name}")
            else:
                # Log the problematic arguments
                logger.error(f"🔧 ADAPTER ERROR: Invalid arguments to adapt(): args={args}, kwargs={kwargs}")
                raise ValueError(f"Cannot adapt with provided arguments: args={args}, kwargs={kwargs}")
            
        logger.info(f"🔧 ADAPTER INIT: Creating custom MCP adapter for tool '{name}'")
        logger.debug(f"🔧 ADAPTER INIT: Tool description: '{description[:50] if isinstance(description, str) else str(description)[:50]}...'")
        try:
            func_name = function.__name__ if hasattr(function, '__name__') else str(function)
            logger.debug(f"🔧 ADAPTER INIT: Function object: {func_name}")
        except Exception as e:
            logger.error(f"🔧 ADAPTER INIT: Error getting function name: {e}")
            logger.debug(f"🔧 ADAPTER INIT: Function object: {str(function)}")
        
        class MCPFullResponseTool(Tool):
            def __call__(self, *args, **kwargs):
                logger.info(f"🔄 ADAPTER CALL: Invoking MCP tool '{name}' through custom adapter")
                # Handle input: support either a single dict arg or keyword args
                if len(args) == 1 and isinstance(args[0], dict) and not kwargs:
                    mcp_input = args[0]
                else:
                    mcp_input = kwargs
                
                logger.debug(f"🔄 ADAPTER CALL: Input to '{name}': {json.dumps(mcp_input, default=str)[:200]}")
                
                # Call MCP function and capture the full response
                try:
                    logger.debug(f"🔄 ADAPTER CALL: Calling underlying MCP function for '{name}'")
                    
                    # Add specific logging for tool name
                    logger.info(f"🔄 ADAPTER DIAGNOSTIC: Calling tool '{name}' with input {json.dumps(mcp_input, default=str)[:100]}")
                    mcp_output = function(mcp_input)
                    
                    # Log the output structure in detail
                    output_type = type(mcp_output).__name__
                    logger.info(f"🔄 ADAPTER DIAGNOSTIC: Tool '{name}' returned type={output_type}")
                    
                    # Add detailed diagnostic logging for all tools
                    if isinstance(mcp_output, str):
                        # String output - log a sample
                        logger.warning(f"🔄 ADAPTER DIAGNOSTIC: Tool '{name}' returned string output - first 200 chars: {mcp_output[:200]}")
                        
                        # Try to determine if it's in JSON format
                        if mcp_output.strip().startswith('{') and mcp_output.strip().endswith('}'):
                            logger.info(f"🔄 ADAPTER DIAGNOSTIC: Output looks like JSON string, attempting to parse")
                            try:
                                parsed_json = json.loads(mcp_output)
                                logger.info(f"🔄 ADAPTER DIAGNOSTIC: Successfully parsed JSON to dict, keys: {list(parsed_json.keys())}")
                                # Use the parsed JSON instead
                                mcp_output = parsed_json
                                output_type = "dict (parsed from JSON string)"
                                logger.info(f"🔄 ADAPTER DIAGNOSTIC: Using parsed JSON object instead of string")
                            except json.JSONDecodeError as e:
                                logger.warning(f"🔄 ADAPTER DIAGNOSTIC: Failed to parse string as JSON: {e}")
                    
                    # Check and fix response structure if needed
                    if isinstance(mcp_output, dict):
                        # Log all top-level keys in the dictionary
                        dict_keys = list(mcp_output.keys())
                        logger.info(f"🔄 ADAPTER DIAGNOSTIC: Dict keys: {dict_keys}")
                        
                        has_content = 'content' in mcp_output
                        has_data = 'data' in mcp_output
                        
                        if has_content and has_data:
                            # Log content and data structure
                            content_type = type(mcp_output['content']).__name__
                            data_type = type(mcp_output['data']).__name__
                            logger.info(f"🔄 ADAPTER DIAGNOSTIC: content type={content_type}, data type={data_type}")
                            
                            # Correct format, log success
                            content_preview = str(mcp_output.get('content', ''))[:100]
                            data_keys = list(mcp_output.get('data', {}).keys())
                            
                            logger.info(f"✅ ADAPTER OUTPUT: '{name}' returned correct structure with content and data")
                            logger.debug(f"✅ ADAPTER OUTPUT: Content preview: {content_preview}")
                            logger.debug(f"✅ ADAPTER OUTPUT: Data keys: {data_keys}")
                            
                            # Already in correct format, return as is
                            return mcp_output
                        else:
                            # Missing content or data, log warning and fix structure
                            logger.warning(f"⚠️ ADAPTER OUTPUT: '{name}' returned incomplete structure, fixing...")
                            logger.warning(f"⚠️ ADAPTER STRUCTURE CHECK: has_content={has_content}, has_data={has_data}")
                            
                            # Create properly structured response
                            fixed_response = {"content": [], "data": {}}
                            
                            if has_content:
                                fixed_response["content"] = mcp_output["content"]
                            else:
                                # Create content from the output
                                if isinstance(mcp_output, dict):
                                    text_repr = str(mcp_output)[:500]  # Truncate very long outputs
                                else:
                                    text_repr = str(mcp_output)
                                fixed_response["content"] = [{"type": "text", "text": text_repr}]
                                logger.debug(f"⚠️ ADAPTER FIX: Created content from output: {text_repr[:100]}...")
                            
                            if has_data:
                                fixed_response["data"] = mcp_output["data"]
                            else:
                                # Use the whole output as data
                                fixed_response["data"] = mcp_output
                                logger.debug(f"⚠️ ADAPTER FIX: Used output as data field")
                            
                            logger.info(f"⚠️ ADAPTER FIX: Converted malformed response to proper structure")
                            logger.info(f"⚠️ ADAPTER DIAGNOSTIC: Fixed response: content_type={type(fixed_response['content']).__name__}, data_type={type(fixed_response['data']).__name__}")
                            
                            return fixed_response
                    else:
                        # Not a dict, log warning and create proper structure
                        logger.warning(f"⚠️ ADAPTER OUTPUT: '{name}' returned {output_type}, NOT a dict!")
                        logger.warning(f"⚠️ ADAPTER DIAGNOSTIC: Raw non-dict output type={output_type}, preview: {str(mcp_output)[:200]}")
                        
                        # Create a properly structured response
                        if isinstance(mcp_output, str):
                            text_output = mcp_output
                            data_output = {"raw_string": mcp_output}
                        else:
                            text_output = str(mcp_output)
                            data_output = {"raw_output": text_output}
                        
                        fixed_response = {
                            "content": [{"type": "text", "text": text_output}],
                            "data": data_output
                        }
                        
                        logger.info(f"⚠️ ADAPTER FIX: Converted {output_type} to proper structure")
                        return fixed_response
                except Exception as e:
                    logger.error(f"❌ ADAPTER ERROR: Error calling MCP tool '{name}': {e}", exc_info=True)
                    # Return error in a standardized format
                    error_response = {
                        "content": [{"type": "text", "text": f"Error calling tool {name}: {str(e)}"}],
                        "data": {"error": str(e)}
                    }
                    logger.debug(f"❌ ADAPTER ERROR: Returning formatted error response: {error_response}")
                    return error_response
                
            @classmethod
            def get_name(cls):
                return name
                
            @classmethod
            def get_description(cls):
                return description
                
            @classmethod
            def get_input_schema(cls):
                return inputs
                
            @classmethod
            def get_output_schema(cls):
                return {"type": "object", "properties": {
                    "content": {"type": "array", "items": {"type": "object"}},
                    "data": {"type": "object"}
                }}
        
        return MCPFullResponseTool
    
    def async_adapt(self, *args, **kwargs):
        """Async adaptation is not supported by SmolAgents."""
        raise NotImplementedError("async is not supported by the SmolAgents framework.")