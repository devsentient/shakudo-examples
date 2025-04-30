"""Core modules for the multi-agent system."""

from .memory import MEMORY_STEP_STORE, OUTPUT_REGISTRY

# Import telemetry with fallback if modules are missing
try:
    from .telemetry import setup_telemetry, TelemetrySpanExporter
    TELEMETRY_AVAILABLE = True
except ImportError as e:
    import logging
    logging.warning(f"Telemetry imports failed: {e}. Telemetry will be disabled.")
    # Create dummy implementations
    def setup_telemetry():
        """Dummy implementation when telemetry is unavailable."""
        return None
    
    class TelemetrySpanExporter:
        """Dummy exporter when telemetry is unavailable."""
        def __init__(self, *args, **kwargs):
            pass
            
        def export(self, *args, **kwargs):
            return type('obj', (object,), {'SUCCESS': True})()
            
    TELEMETRY_AVAILABLE = False
from .tools import ServiceTool, TOOLS, TOOL_NAME_TO_ID, NORMALIZED_TOOL_IDS
from .models import (
    MessageRequest, 
    AgentResponse, 
    StepResponse
)
# Import job-related models and shared state from api.job
from api.job import (
    JobStatus,
    JobRequest,
    JobResponse,
    ACTIVE_JOB_IDS,
    ACTIVE_JOB_IDS_LOCK
)
from .agents import (
    initialize_agents,
    MANAGER,
    MANAGER_AGENTS,
    WORKER_AGENTS,
    AGENT_RELATIONSHIPS,
    ACTIVE_AGENT_CALLS,
    ACTIVE_AGENT_CALLS_LOCK,
    ACTIVE_JOB_IDS,
    ACTIVE_JOB_IDS_LOCK,
    step_callback,
    output_tracking_callback,
    create_initial_step
)
from .utils import (
    convert_timestamp_to_iso,
    get_database_connection,
    create_step_relationships
)