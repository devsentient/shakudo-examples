"""Custom model implementations for improved compatibility.

This module contains custom model implementations for improved compatibility with various
LLM providers, including:

1. GeminiLiteLLMModel: A specialized model for Gemini models accessed through LiteLLM proxy

Special handling for Gemini models:
- Gemini models don't understand 'tool-call' and 'tool-response' roles used by smolagents
- This implementation converts these roles to 'assistant' and 'user' roles respectively
- Adds proper tool handling and response parsing for Gemini's function calling API
- Bypasses LiteLLM Python SDK to use direct HTTP requests with proper formatting
"""
import json
import logging
import os
import requests
from typing import Dict, List, Optional, Any, Union

from smolagents.models import ApiModel, ChatMessage, MessageRole, tool_role_conversions

# Setup logger
logger = logging.getLogger(__name__)

class GeminiLiteLLMModel(ApiModel):
    """A specialized model for Gemini models accessed through LiteLLM proxy.
    
    This model bypasses the LiteLLM Python SDK and directly uses HTTP requests to
    the LiteLLM proxy, ensuring proper handling of Gemini model formats and parameters.
    
    Key features:
    1. Handles special message roles like 'tool-call' and 'tool-response' that Gemini doesn't support
    2. Converts these to standard 'assistant' and 'user' roles for Gemini compatibility
    3. Properly formats tool specifications for Gemini's function calling API
    4. Properly parses and converts tool calls in responses back to the smolagents format
    
    Parameters:
        model_id (`str`):
            The Gemini model identifier (e.g., "gemini/gemini-2.0-flash").
        api_base (`str`):
            The base URL of the LiteLLM proxy (without /chat/completions).
        api_key (`str`, *optional*):
            The API key to use for authentication.
        **kwargs:
            Additional keyword arguments to pass to the API request.
    """
    
    def __init__(
        self,
        model_id: str,
        api_base: str,
        api_key: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.model_id = model_id
        # Ensure api_base doesn't end with a slash and doesn't include /chat/completions
        self.api_base = api_base.rstrip('/')
        if self.api_base.endswith('/chat/completions'):
            self.api_base = self.api_base[:-len('/chat/completions')]
        self.api_key = api_key

    def process_messages_for_gemini(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Convert messages to a format compatible with Gemini models.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List of processed message dictionaries in Gemini-compatible format
        
        Gemini-specific processing:
        1. Handles special roles like 'tool-call' and 'tool-response'
        2. Reformats content with proper structure for Gemini
        3. Converts multipart messages to appropriate format
        4. Adds examples for code generation if needed
        """
        processed_messages = []
        
        # For Gemini models ONLY: Check if this is likely a CodeAgent pattern
        # Other models don't need this special handling for CodeAgent
        is_code_agent = False
        # Only apply these adjustments for the GeminiLiteLLMModel class (not for other models)
        if messages and messages[0]["role"] == MessageRole.SYSTEM and isinstance(self, GeminiLiteLLMModel):
            content = messages[0]["content"] 
            # Check if this appears to be a CodeAgent prompt by looking for code-related terms
            if isinstance(content, str) and ("```python" in content or "Code:" in content or "Think step by step" in content):
                is_code_agent = True
        
        for message in messages:
            # Handle special roles - Gemini doesn't understand 'tool-call' or 'tool-response'
            role = message["role"]
            
            # Apply role conversions (tool-call -> assistant, tool-response -> user)
            if role in tool_role_conversions:
                logger.debug(f"Converting role {role} to {tool_role_conversions[role]}")
                role = tool_role_conversions[role]
                
            # For system messages in CodeAgent patterns, enhance with examples
            if is_code_agent and role == MessageRole.SYSTEM and processed_messages == []:
                content = message["content"]
                if isinstance(content, str):
                    # Add example of proper code generation for Gemini
                    example = "\n\nExample of properly formatted code execution:\n```python\n# I need to call the browser_agent to check a website\nfinal_answer(browser_agent(\"Go to the shakudo website and tell me what it's all about\"))\n```"
                    message["content"] = content + example
            
            # Process content based on type
            if isinstance(message.get("content"), list):
                # Handle content with multiple parts (text, images, etc.)
                processed_content = []
                for item in message["content"]:
                    if item["type"] == "text":
                        processed_content.append({"type": "text", "text": item["text"]})
                    # Add handling for other content types as needed (images, etc.)
                
                processed_messages.append({"role": role, "content": processed_content})
            else:
                # Simple text message
                processed_messages.append({"role": role, "content": message["content"]})
        
        return processed_messages
        
    def __call__(
        self,
        messages: List[Dict[str, str]],
        stop_sequences: Optional[List[str]] = None,
        grammar: Optional[str] = None,
        tools_to_call_from: Optional[List[Any]] = None,
        **kwargs
    ) -> ChatMessage:
        """Process the input messages and return the model's response using direct HTTP requests.
        
        This bypasses the LiteLLM Python SDK to ensure proper handling of Gemini models.
        """
        # Log incoming messages to help with debugging
        logger.debug(f"Original messages before processing: {json.dumps(messages, indent=2)}")
        
        # Convert messages to the format expected by Gemini
        processed_messages = self.process_messages_for_gemini(messages)
        
        logger.debug(f"Processed messages for Gemini: {json.dumps(processed_messages, indent=2)}")
        
        # Prepare request data
        request_data = {
            "model": self.model_id,
            "messages": processed_messages,
        }
        
        # Add tools if provided
        if tools_to_call_from:
            from smolagents.models import get_tool_json_schema
            
            # Format tools in a way Gemini understands
            tools = [get_tool_json_schema(tool) for tool in tools_to_call_from]
            
            # For Gemini models ONLY with CodeAgent pattern, add explicit examples 
            is_code_agent = False
            # Only apply for GeminiLiteLLMModel class with CodeAgent patterns
            if processed_messages and processed_messages[0]["role"] == "system" and isinstance(self, GeminiLiteLLMModel):
                content = processed_messages[0]["content"]
                if isinstance(content, str) and ("```python" in content or "Code:" in content):
                    is_code_agent = True
                    
                    # For CodeAgent with tools, add specific tool usage examples
                    if is_code_agent and len(tools) > 0:
                        tool_names = [tool["function"]["name"] for tool in tools]
                        tool_example = f"\n\nWhen using tools, always use proper Python function calls. Available tools: {', '.join(tool_names)}."
                        
                        # Add example of tool usage
                        if len(tool_names) > 0:
                            example_tool = tool_names[0]
                            tool_example += f"\n\nExample usage:\n```python\n# Call the tool and use the result\nresult = {example_tool}(parameter=\"value\")\nfinal_answer(result)\n```"
                        
                        processed_messages[0]["content"] += tool_example
            
            # Add tools to request
            request_data["tools"] = tools
            request_data["tool_choice"] = "auto"  # Let Gemini decide when to use tools
            
            logger.debug(f"Added tools to request: {json.dumps(tools, indent=2)}")
        
        # Add optional parameters
        if stop_sequences:
            request_data["stop"] = stop_sequences
        
        # Add temperature and other parameters if provided
        # For Gemini models with CodeAgent, use a lower default temperature
        # This helps with structured code outputs and deterministic behavior
        if "temperature" not in kwargs and isinstance(self, GeminiLiteLLMModel):
            # Only set this for CodeAgent patterns with Gemini
            if any(("```python" in msg.get("content", "") or "Code:" in msg.get("content", "")) 
                   for msg in processed_messages if isinstance(msg.get("content"), str)):
                request_data["temperature"] = 0.3
        
        for param in ["temperature", "max_tokens", "top_p", "top_k"]:
            if param in kwargs:
                request_data[param] = kwargs[param]
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json"
        }
        
        # Add authorization if API key is provided
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Make the HTTP request to the LiteLLM proxy
        endpoint = f"{self.api_base}/chat/completions"
        logger.info(f"Making request to LiteLLM proxy at {endpoint} for model {self.model_id}")
        
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                data=json.dumps(request_data)
            )
            response.raise_for_status()
            
            # Parse the response
            try:
                response_data = response.json()
                logger.debug(f"Raw response from LiteLLM proxy: {json.dumps(response_data, indent=2)}")
            except Exception as json_error:
                logger.error(f"Error parsing JSON response: {json_error}")
                # Provide a fallback response data structure
                response_data = {"choices": [{"message": {"content": "Error parsing model response"}}]}
                
            # Validate response structure to prevent NoneType errors
            if not isinstance(response_data, dict):
                logger.warning(f"Response data is not a dictionary: {type(response_data)}")
                response_data = {"choices": [{"message": {"content": "Invalid response format"}}]}
            
            # Extract usage information if available
            if "usage" in response_data:
                self.last_input_token_count = response_data["usage"].get("prompt_tokens", 0)
                self.last_output_token_count = response_data["usage"].get("completion_tokens", 0)
            
            # Extract response elements
            content = None
            tool_calls = None
            
            if response_data.get("choices") and len(response_data["choices"]) > 0:
                message = response_data["choices"][0].get("message", {})
                content = message.get("content", "")
                
                # Check for tool calls in the response
                if message.get("tool_calls"):
                    from smolagents.models import ChatMessageToolCall, ChatMessageToolCallDefinition
                    
                    # Convert tool calls to smolagents format
                    tool_calls = []
                    for tc in message["tool_calls"]:
                        try:
                            # Handle potential None values carefully
                            function_data = tc.get("function", {}) or {}
                            
                            # Ensure arguments is a valid JSON string
                            arguments = function_data.get("arguments", "{}")
                            if arguments is None:
                                arguments = "{}"
                                
                            # Use safe fallbacks for all values to prevent NoneType errors
                            tool_call = ChatMessageToolCall(
                                id=tc.get("id", str(len(tool_calls))),
                                type=tc.get("type", "function"),
                                function=ChatMessageToolCallDefinition(
                                    name=function_data.get("name", ""),
                                    arguments=arguments
                                )
                            )
                            tool_calls.append(tool_call)
                        except Exception as tc_error:
                            # Log the error but continue processing other tool calls
                            logger.warning(f"Error processing tool call: {tc_error}. Raw tool call data: {tc}")
            
            # Create and return a ChatMessage object
            chat_message = ChatMessage(
                role=MessageRole.ASSISTANT,
                content=content,
                tool_calls=tool_calls,
                raw=response_data
            )
            
            # Only run postprocess_message if we don't already have tool_calls
            if tools_to_call_from and not tool_calls:
                return self.postprocess_message(chat_message, tools_to_call_from)
            
            return chat_message
            
        except Exception as e:
            import traceback
            error_type = type(e).__name__
            error_trace = traceback.format_exc()
            
            # Log detailed error information
            logger.error(f"Error calling Gemini model via LiteLLM proxy: {error_type}: {e}")
            logger.debug(f"Error traceback: {error_trace}")
            
            # Check specifically for the NoneType error we're trying to fix
            if error_type == "AttributeError" and "NoneType" in str(e) and "find" in str(e):
                logger.warning("Detected NoneType attribute error with 'find' method - this is likely related to response parsing")
                
            # Return a fallback message with error type for easier debugging
            error_message = f"Model response error ({error_type}): {str(e)}"
            
            # Return a ChatMessage with the error
            return ChatMessage(
                role=MessageRole.ASSISTANT,
                content=error_message
            )

# Public exports from this module
__all__ = [
    'GeminiLiteLLMModel',  # Specialized model for Gemini models accessed through LiteLLM proxy
]