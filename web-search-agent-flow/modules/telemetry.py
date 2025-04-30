"""Telemetry instrumentation for multi-agent system.

This module provides OpenTelemetry integration for the multi-agent system, allowing for:
1. Distributed tracing of agent execution across the system
2. Custom span exporting to the Shakudo telemetry service
3. Detailed instrumentation of agent operations
4. Performance and behavior monitoring

The telemetry system captures agent operations, tool usage, and key events,
enabling observability into the multi-agent workflow execution.
"""
import os
import re
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Sequence, Union, Callable, TypedDict, cast

# OpenTelemetry imports
from opentelemetry.sdk.trace import TracerProvider, Span
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult, BatchSpanProcessor
from opentelemetry import trace
from openinference.instrumentation.smolagents import SmolagentsInstrumentor

# Setup logger
logger = logging.getLogger(__name__)

# Type definitions for telemetry components
class SpanEvent(TypedDict, total=False):
    """Type definition for an OpenTelemetry span event."""
    name: str
    timestamp: Union[int, float]
    attributes: Dict[str, Any]

class SpanData(TypedDict, total=False):
    """Type definition for exported span data."""
    name: str
    trace_id: str
    span_id: str
    parent_id: Optional[str]
    start_time: Union[int, float]
    end_time: Union[int, float]
    attributes: Dict[str, Any]
    events: List[SpanEvent]
    kind: Optional[str]
    status: Dict[str, str]
    agent_name: Optional[str]
    tool_name: Optional[str]

class TelemetryPayload(TypedDict):
    """Type definition for telemetry server payload."""
    type: str
    data: Union[SpanData, Dict[str, Any]]

class TelemetrySpanExporter(SpanExporter):
    """Custom OpenTelemetry exporter that sends spans to the telemetry server.
    
    This exporter captures OpenTelemetry spans and forwards them to the Shakudo telemetry
    service for storage and visualization. It handles conversion of span data to a
    telemetry-compatible format, data sanitization, error handling, and both synchronous
    and asynchronous transmission methods.
    
    The exporter is designed to be resilient to network issues and gracefully handle
    data formatting problems to prevent agent execution from being disrupted by
    telemetry operations.
    """
    
    def __init__(self, telemetry_server_url: str = os.getenv("TELEMETRY_SERVER_URL", "http://hyperplane-service-89a509.hyperplane-pipelines.svc.cluster.local:8787")):
        """Initialize the exporter with the telemetry server URL.
        
        Args:
            telemetry_server_url (str): The URL of the telemetry server that will
                receive the span data. Defaults to the value from the TELEMETRY_SERVER_URL
                environment variable, or a default service name if not set.
        """
        self.telemetry_server_url: str = telemetry_server_url.rstrip("/")
        self.session: Optional[Any] = None  # Will be aiohttp.ClientSession when created
    
    async def _get_session(self) -> Any:  # Can't properly type aiohttp.ClientSession due to jinja2
        """Get or create an aiohttp session for asynchronous HTTP requests.
        
        This method lazily initializes an aiohttp ClientSession when needed
        to avoid creating sessions that might not be used.
        
        Returns:
            aiohttp.ClientSession: A session object for making HTTP requests.
        """
        import aiohttp
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
        
    def _convert_span_to_dict(self, span: Span) -> SpanData:
        """Convert an OpenTelemetry span to a structured dictionary format.
        
        This method transforms an OpenTelemetry Span object into a standardized
        dictionary format suitable for transmission to the telemetry service.
        It includes:
        - Basic span metadata (ID, trace ID, timestamps)
        - Span attributes with proper sanitization
        - Events with timestamps and attributes
        - Agent and tool identification for easier filtering
        
        Args:
            span (Span): The OpenTelemetry span to convert
            
        Returns:
            SpanData: A dictionary containing the formatted span data
        """
        context = span.get_span_context()
        parent = span.parent
        
        # Helper function to sanitize values for JSON serialization
        def sanitize_for_json(obj, depth=0, max_depth=10):
            """Make sure objects can be properly serialized to JSON."""
            # Prevent infinite recursion
            if depth > max_depth:
                return "<max recursion depth reached>"
                
            if obj is None:
                return None
            elif isinstance(obj, (int, float, bool)):
                return obj
            elif isinstance(obj, str):
                # Ensure the string is valid Unicode and doesn't contain control characters
                try:
                    # Replace any problematic characters
                    clean_str = obj.encode('utf-8', errors='replace').decode('utf-8')
                    # Remove control characters that might break JSON
                    clean_str = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', clean_str)
                    # Truncate long strings
                    if len(clean_str) > 5000:
                        return clean_str[:5000] + "...[truncated]"
                    return clean_str
                except Exception:
                    return "<invalid string>"
            elif isinstance(obj, dict):
                # Handle empty dictionaries
                if not obj:
                    return {}
                
                # Create a new sanitized dictionary
                result = {}
                # Process at most 100 items to prevent excessively large objects
                items = list(obj.items())[:100]
                
                for k, v in items:
                    # Skip None keys or non-string keys
                    if k is None:
                        continue
                    
                    # Convert non-string keys to strings
                    if not isinstance(k, str):
                        try:
                            k = str(k)
                        except Exception:
                            k = "<unserializable key>"
                    
                    # Recurse on the value
                    result[k] = sanitize_for_json(v, depth + 1, max_depth)
                
                # Add a note if we truncated the dictionary
                if len(obj) > 100:
                    result["_truncated"] = f"{len(obj) - 100} additional items not shown"
                
                return result
            elif isinstance(obj, (list, tuple)):
                # Handle empty lists
                if not obj:
                    return []
                
                # Truncate lists to prevent excessively large payloads
                items = list(obj)[:100]
                result = [sanitize_for_json(item, depth + 1, max_depth) for item in items]
                
                # Add a note if we truncated the list
                if len(obj) > 100:
                    result.append(f"{len(obj) - 100} additional items not shown")
                
                return result
            else:
                # Try to convert to string, with fallback for any errors
                try:
                    return str(obj)
                except Exception:
                    return "<unserializable object>"
        
        # Convert span events to a serializable format
        events = []
        for event in span.events:
            try:
                attributes = dict(event.attributes) if event.attributes else {}
                # Sanitize attributes to ensure serializability
                sanitized_attributes = sanitize_for_json(attributes)
                
                event_dict = {
                    'name': event.name,
                    'timestamp': event.timestamp,
                    'attributes': sanitized_attributes
                }
                events.append(event_dict)
            except Exception as e:
                logger.warning(f"Error processing event in span: {e}")
                # Include a simplified event instead
                events.append({
                    'name': str(getattr(event, 'name', 'unknown')),
                    'timestamp': str(getattr(event, 'timestamp', 0)),
                    'attributes': {'error': 'Error processing event attributes'}
                })

        # Sanitize attributes to ensure serializability
        attributes = dict(span.attributes) if span.attributes else {}
        sanitized_attributes = sanitize_for_json(attributes)
        
        # Build the span data dictionary with safe values
        span_data = {
            'name': str(span.name),
            'trace_id': format(context.trace_id, '032x'),  # Convert to 32-char hex string
            'span_id': format(context.span_id, '016x'),    # Convert to 16-char hex string
            'parent_id': format(parent.span_id, '016x') if parent else None,
            'start_time': span.start_time,
            'end_time': span.end_time,
            'attributes': sanitized_attributes,
            'events': events,
            'kind': span.kind.name if span.kind else None,
            'status': {
                'status_code': span.status.status_code.name,
                'description': str(span.status.description or '')
            }
        }

        # Add agent-specific attributes for easier filtering
        if 'agent.name' in span_data['attributes']:
            span_data['agent_name'] = str(span_data['attributes']['agent.name'])
        if 'tool.name' in span_data['attributes']:
            span_data['tool_name'] = str(span_data['attributes']['tool.name'])
        
        return span_data

    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        """Export spans by sending them to the telemetry server.
        
        This is the main entry point called by the OpenTelemetry BatchSpanProcessor
        to export spans. It processes each span individually, converting it to
        a compatible format and sending it to the telemetry server.
        
        Args:
            spans (Sequence[Span]): A sequence of OpenTelemetry spans to export
            
        Returns:
            SpanExportResult: SUCCESS if all spans were exported successfully,
                FAILURE if there was an error with any span
        """
        try:
            for span in spans:
                span_data = self._convert_span_to_dict(span)
                
                # Send synchronously to avoid asyncio issues
                self._send_span_sync(span_data)
            
            return SpanExportResult.SUCCESS
        except Exception as e:
            logger.error(f"Error exporting spans: {e}")
            return SpanExportResult.FAILURE
            
    def _send_span_sync(self, span_data: SpanData) -> None:
        """Send a span to the telemetry server using synchronous HTTP requests.
        
        This method uses the requests library to send telemetry data synchronously,
        which avoids potential issues with asyncio event loops. It includes robustness
        features like string truncation, payload validation, and error handling.
        
        Args:
            span_data (SpanData): The span data dictionary to send to the telemetry server
        """
        try:
            import requests
            import json
            
            # Function to truncate long strings in the payload
            def truncate_strings(obj, max_length=10000):
                """Recursively truncate long strings in nested objects."""
                if isinstance(obj, dict):
                    return {k: truncate_strings(v, max_length) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [truncate_strings(item, max_length) for item in obj]
                elif isinstance(obj, str) and len(obj) > max_length:
                    return obj[:max_length] + "...[truncated]"
                else:
                    return obj
            
            # Apply truncation to span_data to avoid excessively long strings
            truncated_span_data = truncate_strings(span_data)
            
            # Remove any attributes that might cause JSON encoding issues
            if "attributes" in truncated_span_data:
                # Remove any attributes with excessively long values
                problematic_keys = []
                for key, value in truncated_span_data["attributes"].items():
                    if isinstance(value, str) and len(value) > 10000:
                        problematic_keys.append(key)
                
                # Remove problematic attributes
                for key in problematic_keys:
                    del truncated_span_data["attributes"][key]
            
            # Simplify events if there are too many
            if "events" in truncated_span_data and len(truncated_span_data["events"]) > 50:
                truncated_span_data["events"] = truncated_span_data["events"][:50]
                truncated_span_data["events"].append({
                    "name": "events_truncated",
                    "timestamp": 0,
                    "attributes": {"message": f"Additional events truncated"}
                })
            
            payload = {
                "type": "telemetry.spans",
                "data": truncated_span_data
            }
            
            # Try to serialize the payload to validate it's JSON-compatible
            try:
                json_data = json.dumps(payload)
                
                # Check if the JSON is too large (30MB max)
                if len(json_data) > 30 * 1024 * 1024:
                    logger.warning(f"JSON payload too large: {len(json_data)} bytes")
                    # Use a minimal payload instead
                    simplified_payload = {
                        "type": "telemetry.spans",
                        "data": {
                            "name": str(truncated_span_data.get("name", "unknown")),
                            "trace_id": truncated_span_data.get("trace_id", "unknown"),
                            "span_id": truncated_span_data.get("span_id", "unknown"),
                            "error": "Payload too large for transmission"
                        }
                    }
                    json_data = json.dumps(simplified_payload)
            except (TypeError, ValueError) as e:
                logger.warning(f"JSON serialization error: {e}")
                # Attempt to create a simplified payload
                simplified_payload = {
                    "type": "telemetry.spans",
                    "data": {
                        "name": str(truncated_span_data.get("name", "unknown")),
                        "trace_id": truncated_span_data.get("trace_id", "unknown"),
                        "span_id": truncated_span_data.get("span_id", "unknown"),
                        "error": "Failed to serialize span data"
                    }
                }
                json_data = json.dumps(simplified_payload)
            
            # Send with validated JSON payload
            response = requests.post(
                f"{self.telemetry_server_url}/submit",
                data=json_data,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to send telemetry: {response.status_code} - {response.text}")
        except Exception as e:
            logger.warning(f"Error sending telemetry: {e}")
    
    async def _send_span(self, span_data: SpanData) -> None:
        """Send a span to the telemetry server using asynchronous HTTP requests.
        
        This method uses aiohttp to send telemetry data asynchronously. It's an
        alternative to the synchronous method but is currently not used in the
        main export path to avoid potential issues with asyncio event loops.
        
        Args:
            span_data (SpanData): The span data dictionary to send to the telemetry server
        """
        try:
            import aiohttp
            session = await self._get_session()
            
            payload: TelemetryPayload = {
                "type": "telemetry.spans",
                "data": span_data
            }
            
            async with session.post(
                f"{self.telemetry_server_url}/submit",
                json=payload,
                timeout=5
            ) as response:
                if response.status != 200:
                    response_text = await response.text()
                    logger.warning(f"Failed to send telemetry: {response.status} - {response_text}")
        except Exception as e:
            logger.warning(f"Error sending telemetry: {e}")

    def force_flush(self, timeout_millis: float = 30000) -> bool:
        """Force flush any pending spans.
        
        This is required by the SpanExporter interface but is a no-op in our implementation
        as we send spans immediately upon receipt.
        
        Args:
            timeout_millis (float): Maximum time to wait for flush to complete (not used)
            
        Returns:
            bool: Always returns True to indicate success
        """
        return True

    def shutdown(self) -> None:
        """Shutdown the exporter and close any open resources.
        
        This method is called when the application is shutting down to ensure that
        all resources are properly cleaned up. It closes the aiohttp session if one
        was created.
        """
        if self.session and not self.session.closed:
            asyncio.create_task(self.session.close())
            self.session = None

def setup_telemetry() -> TracerProvider:
    """Set up OpenTelemetry with the telemetry server exporter.
    
    This function initializes the OpenTelemetry tracing system with our custom
    TelemetrySpanExporter. It:
    1. Creates the custom exporter
    2. Sets up the TracerProvider with a BatchSpanProcessor
    3. Initializes the global tracer provider
    4. Instruments the smolagents library to capture agent operations
    
    Returns:
        TracerProvider: The configured tracer provider for use in the application
    """
    # Check for opentelemetry packages
    try:
        import opentelemetry
        logger.info(f"OpenTelemetry version: {opentelemetry.__version__}")
    except ImportError:
        logger.warning("OpenTelemetry not installed. Telemetry will be disabled.")
        # Return a dummy tracer provider that doesn't do anything
        return TracerProvider()
    
    try:
        # Create the custom exporter
        exporter = TelemetrySpanExporter()
        
        # Create and set TracerProvider
        tracer_provider = TracerProvider()
        processor = BatchSpanProcessor(exporter)
        tracer_provider.add_span_processor(processor)
        
        # Initialize the global tracer provider
        trace.set_tracer_provider(tracer_provider)
        
        # Import smolagents models directly to ensure classes are available
        try:
            from smolagents.models import ApiModel, HfApiModel
            # Check if SmolagentsInstrumentor is available
            try:
                # Instrument smolagents to use our tracer
                SmolagentsInstrumentor().instrument(tracer_provider=tracer_provider)
                logger.info("Successfully instrumented smolagents for telemetry")
            except (ImportError, AttributeError, NameError) as e:
                logger.warning(f"Error instrumenting smolagents: {e}")
                logger.warning("Telemetry for smolagents will not be available")
        except ImportError as e:
            logger.warning(f"Smolagents models not available: {e}")
        
        return tracer_provider
    except Exception as e:
        logger.error(f"Failed to initialize telemetry: {e}")
        # Return a dummy tracer provider that doesn't do anything
        return TracerProvider()

# Public exports from this module
__all__ = [
    'TelemetrySpanExporter',   # The custom span exporter class
    'setup_telemetry',         # Function to initialize telemetry
    'SpanData',                # Type definition for span data
    'SpanEvent',               # Type definition for span events
    'TelemetryPayload'         # Type definition for telemetry payloads
]