"""Common module for shared state and utilities.

This module contains shared state and utilities used across multiple modules in the system.
It helps break circular dependencies by providing a central location for shared resources.

Responsibilities:
1. Maintain shared registries and state
2. Provide utility functions needed by multiple modules
3. Prevent circular dependencies between modules
4. Provide specialized model implementations
"""
# Import standard libraries
import logging
import os
from typing import Dict, Any, Optional

# Setup logger
logger = logging.getLogger(__name__)

# Import custom modules
from .models import GeminiLiteLLMModel



# OUTPUT_REGISTRY: Shared registry for storing outputs from agents and tools
OUTPUT_REGISTRY: Dict[str, Any] = {}

# Tool name to ID mapping - will be initialized by tools.py
TOOL_NAME_TO_ID: Dict[str, str] = {}

def get_tool_id(tool_name: str) -> str:
    """Get tool ID from tool name, safely handling case where mapping is not initialized yet.
    
    Args:
        tool_name (str): The name of the tool to look up
        
    Returns:
        str: The tool ID if found, otherwise "unknown_tool_id"
    """
    return TOOL_NAME_TO_ID.get(tool_name, "unknown_tool_id")

def create_model_for_provider(model_id: str, api_base: str, api_key: Optional[str] = None, **kwargs):
    """Create the appropriate model class based on the model_id.
    
    This function selects the appropriate model implementation based on the model_id:
    - For Gemini models, it uses the specialized GeminiLiteLLMModel
    - For other models, it uses the standard LiteLLMModel from smolagents
    
    Args:
        model_id (str): The model identifier (e.g. "gemini/gemini-2.0-flash")
        api_base (str): The API base URL
        api_key (str, optional): The API key to use
        **kwargs: Additional arguments to pass to the model constructor
        
    Returns:
        Union[GeminiLiteLLMModel, LiteLLMModel]: The appropriate model instance
    """
    # Check if this is a Gemini model
    if "gemini" in model_id.lower():
        logger.info(f"Using specialized GeminiLiteLLMModel for {model_id}")
        return GeminiLiteLLMModel(
            model_id=model_id,
            api_base=api_base,
            api_key=api_key,
            **kwargs
        )
    else:
        # Otherwise use the standard LiteLLMModel from smolagents
        from smolagents.models import LiteLLMModel
        logger.info(f"Using standard LiteLLMModel for {model_id}")
        return LiteLLMModel(
            model_id=model_id,
            api_base=api_base,
            api_key=api_key,
            **kwargs
        )

# Public exports from this module
__all__ = [
    'OUTPUT_REGISTRY',      # Registry for storing outputs from agents and tools
    'TOOL_NAME_TO_ID',      # Mapping from tool names to IDs (initialized by tools.py)
    'get_tool_id',          # Function to safely get tool ID from name
    'GeminiLiteLLMModel',   # Specialized model for Gemini models
    'create_model_for_provider', # Factory function to create appropriate model instance
    
]