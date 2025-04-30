"""Agent initialization and management for the multi-agent system.

This module handles the initialization and orchestration of a hierarchical multi-agent system,
including:

1. Agent creation, configuration, and relationship management
2. Step tracking and lineage recording
3. Agent output management
4. Parent-child relationship tracking between agent steps
5. Job context management for agents

The module sets up a three-tier agent hierarchy:
- A single top-level manager agent (MANAGER)
- A set of intermediate manager agents (MANAGER_AGENTS) 
- A set of worker agents (WORKER_AGENTS) that perform specific tasks
"""

import os
import json
import datetime
import threading
import logging
from typing import Dict, Any, Optional, List, Tuple, Callable, TypedDict, Union, Set, cast

# Helper function to convert string parameter values to appropriate Python types
def convert_param_value(key: str, value: str) -> Any:
    """Convert string parameter values to appropriate Python types."""
    if value.lower() in ['true', 'yes', '1']:
        return True
    if value.lower() in ['false', 'no', '0']:
        return False
    try:
        # Try to convert to int or float if appropriate
        if '.' in value:
            return float(value)
        return int(value)
    except ValueError:
        # Keep as string if not a numeric value
        return value

# Default model configuration
DEFAULT_MODEL_CONFIG = {
    "model_id": os.getenv("LLM_MODEL_ID", "openrouter/anthropic/claude-3.5-sonnet"),
    "api_base": os.getenv("LLM_API_BASE", "http://litellm.hyperplane-litellm.svc.cluster.local:4000"),
    "litellm_api_base": os.getenv("LITELLM_API_BASE", "http://litellm.hyperplane-litellm.svc.cluster.local:4000"),
    "use_litellm": os.getenv("USE_LITELLM", "true").lower() in ["true", "1", "yes"],
    "extra_headers": {
        "HTTP-Referer": os.getenv("LLM_HTTP_REFERER", "http://localhost:8787"),
        "X-Title": os.getenv("LLM_X_TITLE", "Agent Flow Service")
    },
    # Additional model parameters from the UI with type conversion
    "model_params": {
        
    }
}

# Extract any parameters from the model ID (provider/model?param=value format)
model_id_with_params = os.getenv("LLM_MODEL_ID", "openrouter/anthropic/claude-3.5-sonnet")
print(f"Processing model ID with params: {model_id_with_params}")

# Extract base model ID without parameters
base_model_id = model_id_with_params.split('?')[0] if '?' in model_id_with_params else model_id_with_params
print(f"Extracted base model ID: {base_model_id}")

# Override the model_id to use just the base part without parameters
DEFAULT_MODEL_CONFIG["model_id"] = base_model_id
print(f"Model parameters: {DEFAULT_MODEL_CONFIG['model_params']}")

# Set drop_params to True to handle unsupported parameters gracefully
import litellm
litellm.drop_params = True
print("Set litellm.drop_params = True to handle unsupported parameters")

# Ensure API base URLs are properly formatted to prevent URL construction errors
def fix_api_url(url):
    """Fix common URL formatting issues that can cause errors in HTTP clients."""
    if not url:
        return url
    
    # Remove trailing slashes for consistency
    url = url.rstrip("/")
    
    # Fix malformed port specifications (often cause "Invalid port" errors)
    # Pattern: ":port:" should be ":port/"
    import re
    port_pattern = re.compile(r':(\d+):')
    if port_pattern.search(url):
        url = port_pattern.sub(r':\1/', url)
        logger = logging.getLogger(__name__)
        logger.info(f"Fixed malformed port in URL: {url}")
    
    # Ensure URL has protocol if needed
    if ":" in url and "://" not in url:
        url = "http://" + url
        
    return url

# Apply URL fixes to API base URLs
DEFAULT_MODEL_CONFIG["litellm_api_base"] = fix_api_url(DEFAULT_MODEL_CONFIG["litellm_api_base"])
DEFAULT_MODEL_CONFIG["api_base"] = fix_api_url(DEFAULT_MODEL_CONFIG["api_base"])

# Agent framework imports
from smolagents import CodeAgent, ToolCallingAgent, MultiStepAgent, Tool
from smolagents.memory import ActionStep

# Import from local modules
from .memory import MEMORY_STEP_STORE
from .common import OUTPUT_REGISTRY, create_model_for_provider
from .tools import TOOLS, TOOL_NAME_TO_ID, ServiceTool, MCP_TOOLS

# Configure module logger
logger = logging.getLogger(__name__)

# Helper function to safely get a tool
def get_tool_safely(tool_id):
    """Safely get a tool by ID, creating a placeholder if it doesn't exist."""
    try:
        return TOOLS[tool_id]
    except KeyError:
        # If the tool is missing from the TOOLS dictionary, create a placeholder tool
        logger.warning(f"Tool with ID {tool_id} referenced but not found in TOOLS dictionary. Creating placeholder.")
        url = "http://service-not-found.example.com"
        # For some known tool IDs, we can provide better defaults
        if "dremio" in tool_id.lower():
            url = "http://hyperplane-service-dremio.hyperplane-pipelines.svc.cluster.local:8787"
            
        placeholder = ServiceTool(
            name=f"placeholder_{tool_id}",
            description=f"Placeholder for missing tool {tool_id}",
            service_name=f"placeholder_{tool_id}",
            url=url,
            inputs={
                "query": {
                    "type": "string",
                    "description": "The query to execute"
                }
            }
        )
        # Add to TOOLS dictionary so it's available for future references
        TOOLS[tool_id] = placeholder
        return placeholder

# Custom type definitions
class AgentRelationship(TypedDict):
    """Type definition for agent relationship information."""
    parent_agent: str
    is_worker: bool

class AgentStepContext(TypedDict, total=False):
    """Type definition for agent step tracking context."""
    timestamp: str
    agent_id: str
    job_id: str
    metadata: Dict[str, Any]

class AgentConfig(TypedDict, total=False):
    """Type definition for agent configuration parameters."""
    name: str
    description: str 
    tools: List[Tool]
    max_steps: int
    is_output_node: bool

# Global dictionary to track agent relationships (pre-computed from graph at generation time)
# Static mapping of agent names to their parent agent information
AGENT_RELATIONSHIPS: Dict[str, AgentRelationship] = {
    
    
}

# Global dictionary to track agents actively being called 
# We use this to establish parent-child relationships between steps
# The structure is: {agent_name: (parent_agent_name, parent_step_number, context_dict)}
ACTIVE_AGENT_CALLS: Dict[str, Tuple[str, int, Dict[str, Any]]] = {}
# Lock to manage concurrent updates to the ACTIVE_AGENT_CALLS dictionary
ACTIVE_AGENT_CALLS_LOCK: threading.Lock = threading.Lock()

# Dictionary to track job IDs for step callbacks, keyed by thread ID
# The structure is: {thread_id: job_id}
# Import these from api.job to ensure we use the same instances
try:
    from api.job import ACTIVE_JOB_IDS, ACTIVE_JOB_IDS_LOCK
except ImportError:
    # Fallback if not yet imported (for circular import prevention)
    ACTIVE_JOB_IDS: Dict[int, str] = {}
    ACTIVE_JOB_IDS_LOCK: threading.Lock = threading.Lock()

def step_callback(step: ActionStep, agent: Optional[Any] = None) -> None:
    """Callback function that records steps from all agents with lineage tracking.
    
    This function is called for each step of agent execution and handles:
    1. Recording the step in the memory store with proper parent-child relationships
    2. Tracking and storing agent outputs
    3. Logging tool calls and observations
    4. Maintaining step lineage for visualization and debugging
    
    Args:
        step (ActionStep): The agent's action step to record
        agent (Optional[Agent]): The agent that executed the step
    """
    # Track the current thread ID for debugging
    thread_id = threading.get_ident()
    
    if agent is None:
        logger.warning(f"[JOB_ID_DEBUG] Agent not provided to callback in thread {thread_id}")
        return
    
    agent_name = getattr(agent, "name", "unnamed_agent")
    logger.warning(f"[JOB_ID_DEBUG] step_callback invoked for agent {agent_name} on thread {thread_id}, step {step.step_number}")
    
    # Get the current job ID from thread context and log it
    with ACTIVE_JOB_IDS_LOCK:
        job_id_in_thread = ACTIVE_JOB_IDS.get(thread_id)
        all_job_ids = {t: j for t, j in ACTIVE_JOB_IDS.items()}
        logger.warning(f"[JOB_ID_DEBUG] Current thread {thread_id} has job_id: {job_id_in_thread}")
        logger.warning(f"[JOB_ID_DEBUG] All job IDs in registry: {all_job_ids}")
    
    # If this agent has an output and is marked as an output node, save to OUTPUT_REGISTRY
    agent_id = getattr(agent, "id", None)
    is_output_node = getattr(agent, "is_output_node", False)
    
    if agent_id and is_output_node and hasattr(step, "action_output") and step.action_output:
        OUTPUT_REGISTRY[agent_id] = str(step.action_output)
        logger.info(f"Agent {agent.name} saved output as designated output node")
    
    agent_type = agent.__class__.__name__
    
    # Get the parent relationship from the pre-registered information
    parent_step_id = None
    
    # Thread-safe access to ACTIVE_AGENT_CALLS
    with ACTIVE_AGENT_CALLS_LOCK:
        parent_step_info = ACTIVE_AGENT_CALLS.get(agent_name)
        logger.warning(f"[JOB_ID_DEBUG] Parent info for {agent_name}: {parent_step_info}")
    
    if parent_step_info:
        # This agent has a parent from the pre-registered relationships
        if isinstance(parent_step_info, tuple) and len(parent_step_info) >= 2:
            parent_agent_name, parent_step_number = parent_step_info[:2]
            logger.warning(f"[JOB_ID_DEBUG] Found parent agent {parent_agent_name} (step {parent_step_number}) for {agent_name}")
            
            # Extract current job_id for consistent referencing
            current_job_id = None
            with ACTIVE_JOB_IDS_LOCK:
                current_job_id = ACTIVE_JOB_IDS.get(thread_id)
                logger.warning(f"[JOB_ID_DEBUG] Job ID for parent reference: {current_job_id}")
            
            if not current_job_id:
                logger.warning(f"[JOB_ID_DEBUG] No job_id available for parent reference from {agent_name} to {parent_agent_name}, falling back to thread ID")
                # Fall back to current thread ID as job_id in case of error
                current_job_id = f"thread-{thread_id}"
            
            # Use the same format as step_id to ensure consistency: {agent_name}-{step_number}-{job_id}
            parent_step_id = f"{parent_agent_name}-{parent_step_number}-{current_job_id}"
            logger.warning(f"[JOB_ID_DEBUG] Created parent step ID: {parent_step_id}")
            
            # Log the relationship for the first step
            if step.step_number == 1:
                logger.info(f"[LINEAGE] Linking agent {agent_name} to parent agent {parent_agent_name}")
    
    # Log tool calls for visibility
    if hasattr(step, "tool_calls") and step.tool_calls and hasattr(step, "observations"):
        for tc in step.tool_calls:
            tool_name = tc.name
            tool_id = TOOL_NAME_TO_ID.get(tool_name, "unknown_tool_id")
            observation_snippet = str(step.observations)[:150] + "..." if len(str(step.observations)) > 150 else str(step.observations)
            logger.info(f"Tool call: {tool_name} (ID: {tool_id}) - Observation: {observation_snippet}")
            
            # Check if this is an MCP tool
            is_mcp_tool = "mcp" in tool_name.lower()
            if is_mcp_tool:
                logger.info(f"🔍 MCP TOOL CALL: {tool_name}")
                
                # Analyze the response format to check if custom adapter is being used
                try:
                    # Check if the observation is a dictionary with content and data fields
                    observation = step.observations
                    
                    if hasattr(observation, 'get') and callable(observation.get):
                        has_content = 'content' in observation
                        has_data = 'data' in observation
                        
                        if has_content and has_data:
                            logger.info(f"✅ MCP TOOL RESPONSE: Proper structure with content and data fields")
                            
                            # Log data structure
                            data_keys = list(observation.get('data', {}).keys())
                            content_preview = str(observation.get('content', ''))[:100]
                            logger.info(f"📋 MCP DATA KEYS: {data_keys}")
                            logger.debug(f"📋 MCP CONTENT PREVIEW: {content_preview}")
                        else:
                            logger.warning(f"⚠️ MCP TOOL RESPONSE: Missing expected structure!")
                            logger.warning(f"⚠️ Has content field: {has_content}")
                            logger.warning(f"⚠️ Has data field: {has_data}")
                            logger.debug(f"⚠️ Raw response: {str(observation)[:200]}")
                    else:
                        # Observation is not a dict-like object
                        logger.warning(f"⚠️ MCP TOOL RESPONSE: Not a dict-like object!")
                        logger.warning(f"⚠️ Response type: {type(observation).__name__}")
                        logger.debug(f"⚠️ Raw response: {str(observation)[:200]}")
                except Exception as e:
                    logger.error(f"❌ Error analyzing MCP tool response: {str(e)}")
            
            # Check if this is calling a managed agent (additional debugging)
            from_agents = [worker.name for worker in WORKER_AGENTS.values()] + [manager.name for manager in MANAGER_AGENTS.values()]
            if tool_name in from_agents:
                logger.warning(f"[JOB_ID_DEBUG] Detected agent {agent_name} calling managed agent {tool_name} in step {step.step_number}")
    
    # Get the current job ID based on the current thread ID
    thread_id = threading.get_ident()
    current_job_id = None
    
    with ACTIVE_JOB_IDS_LOCK:
        current_job_id = ACTIVE_JOB_IDS.get(thread_id)
        logger.warning(f"[JOB_ID_DEBUG] Job ID for step {step.step_number} of agent {agent_name}: {current_job_id}")
    
    if current_job_id:
        logger.warning(f"[JOB_ID_DEBUG] Associating step {step.step_number} for agent {agent_name} with job {current_job_id} (thread {thread_id})")
    else:
        logger.warning(f"[JOB_ID_DEBUG] No job ID available for step {step.step_number} from agent {agent_name} (thread {thread_id})")
        
        # Try an additional method to get the job_id from Python executor state if available
        if hasattr(agent, 'python_executor') and hasattr(agent.python_executor, 'state') and 'get_current_job_id' in agent.python_executor.state:
            try:
                logger.warning(f"[JOB_ID_DEBUG] Attempting to get job_id from Python executor state for {agent_name}")
                get_current_job_id_func = agent.python_executor.state['get_current_job_id']
                executor_job_id = get_current_job_id_func()
                logger.warning(f"[JOB_ID_DEBUG] Got job_id from executor state: {executor_job_id}")
                if executor_job_id:
                    current_job_id = executor_job_id
            except Exception as e:
                logger.warning(f"[JOB_ID_DEBUG] Error getting job_id from executor state: {e}")
    
    # Add the step with lineage information and job ID
    logger.warning(f"[JOB_ID_DEBUG] Adding step for {agent_name} with job_id: {current_job_id}")
    try:
        MEMORY_STEP_STORE.add_step(step, agent_name, agent_type, parent_step_id=parent_step_id, job_id=current_job_id)
        logger.warning(f"[JOB_ID_DEBUG] Successfully added step {step.step_number} for agent {agent_name}")
    except Exception as e:
        logger.error(f"[JOB_ID_DEBUG] Error adding step: {str(e)}")
    
    logger.info(f"[LINEAGE] Recorded step {step.step_number} for agent {agent_name}")

def output_tracking_callback(step: ActionStep, agent: Optional[Any] = None) -> None:
    """Tracks output from all agents, especially the designated output agents and tools.
    
    This callback focuses specifically on tracking outputs rather than lineage,
    ensuring that agent and tool outputs are properly stored in the OUTPUT_REGISTRY
    for later retrieval. It's particularly important for designated output nodes.
    
    Args:
        step (ActionStep): The agent's action step
        agent (Optional[Agent]): The agent that executed the step
    """
    if agent is None:
        logger.warning("Agent not provided to output_tracking_callback")
        return
        
    agent_name = getattr(agent, "name", "unnamed_agent")
    agent_id = getattr(agent, "id", None)
    
    # Track agent outputs
    if hasattr(step, "action_output") and step.action_output and agent_id:
        # Store the agent's output in the registry
        output_text = str(step.action_output)
        OUTPUT_REGISTRY[agent_id] = output_text
        logger.debug(f"Tracked output from agent {agent_name} (ID: {agent_id})")
        
    # Track tool calls and their observations
    if hasattr(step, "tool_calls") and step.tool_calls and hasattr(step, "observations"):
        for tc in step.tool_calls:
            tool_name = tc.name
            tool_id = TOOL_NAME_TO_ID.get(tool_name, "unknown_tool_id")
            observation = str(step.observations)
            
            # Save tool outputs with multiple ID formats for maximum compatibility
            OUTPUT_REGISTRY[tool_id] = observation
            OUTPUT_REGISTRY[f"tool-{tool_id}"] = observation
            
            # If this tool ID is a designated output node, mark it in the logs
            if tool_id == "agent_1745420716020" or f"tool-{tool_id}" == "agent_1745420716020":
                logger.info(f"Tool {tool_name} (ID: {tool_id}) captured output as designated output node")
            else:
                logger.debug(f"Tracked output from tool {tool_name} (ID: {tool_id})")

# Initialize worker agents (specialized agents for specific tasks)
WORKER_AGENTS: Dict[str, Union[ToolCallingAgent, CodeAgent]] = {
    
}

# Initialize manager agents (code agents that can execute Python and coordinate other agents)
MANAGER_AGENTS: Dict[str, CodeAgent] = {

}

# Initialize top-level manager (primary agent that orchestrates the entire flow)
# Use string formatting instead of multi-line strings to avoid syntax issues

# Declare global variables properly
global MANAGER
# Create a placeholder for the manager that will be initialized in initialize_agents()
MANAGER: Optional[CodeAgent] = None

# Define the specification to be used in initialize_agents()
MANAGER_SPEC = {
    "agent_type": "CodeAgent",
    "name": "Main",
    "description": """# Step 1 - Conduct Research on Latest SEC Documents for Dynex

Produce a comprehensive report detailing the most recent filings from Dynex as reported by the Securities and Exchange Commission (SEC). Focus on:
- The latest quarterly or annual reports (Form 10-Q and Form 10-K)
- Any significant event reports (Form 8-K) that have been filed recently
- Recent insider trading activities related to Dynex

Use @agent-webresearcher to conduct research online. Provide it with specific topics and research requests focusing on SEC filings for Dynex. Do as many follow-up requests as needed to construct the report.
Important guidance:
- Make sure to ask @agent-webresearcher to return the links to its sources, not just the research
- Always include source links with every section in your report
- The research should cover documents filed within the last month for a thorough update

# Step 2 - Send Research Report by Email to yijie@shakudo.io

Use the following code to send the compiled report via email to Yijie Ding at Shakudo. Ensure that all relevant details are included in the request sent to the n8n endpoint.
\\`\\`\\`python
import requests
from datetime import datetime, timedelta

def fetch_recent_dates(days_back=30):
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)
    return {'start_date': str(start_date), 'end_date': str(end_date)}

def send_request(service, data):
    url = \"https://n8n-v1.dev.hyperplane.dev/webhook/e6684397-2018-4213-86e0-44dc78f8b951\"
    headers = {\"Content-Type\": \"application/json\"}
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def email_request(request):
    data = {\"service\": \"gmail\", \"request\": request}
    return send_request(service=\"gmail\", data=data)

# Example of how to compile and send the research report
research_report = \"Include detailed summary of Dynex's recent SEC filings here.\"
dates_range = fetch_recent_dates()

email_request({
    'subject': f'Dynex Latest SEC Filings Report for {dates_range[\"start_date\"]} - {dates_range[\"end_date\"]}',
    'to_email': 'yijie@shakudo.io',
    'body': research_report,
})
\\`\\`\\`""",
    "service_tool_ids": [
        
            
                "tool-89fc99d5-b85b-423b-aad9-b372a734b62e",
            
        
    ],
    "max_steps": 10,
    "use_base_tools": False,
    "managed_agent_ids": [
        
        
            
                
            
        
    ],
    
    "additional_authorized_imports": [
        "time", "json", "requests", "requests.exceptions", "nest_asyncio", 
        "urllib", "urllib.request", "urllib.error", "urllib.parse", 
        "pandas", "psycopg2", "http.client", "aiohttp",
        
        
        
    ],
    
}

def setup_agent_relationship_tracking() -> None:
    """Pre-register parent-child relationships based on agent relationships.
    
    This function initializes the ACTIVE_AGENT_CALLS dictionary with information
    about the parent-child relationships between agents, so that when agents execute,
    their steps can be properly linked in the lineage graph.
    """
    logger.info("Initializing agent relationship tracking")
    # For each worker agent, check if it has a parent in AGENT_RELATIONSHIPS
    for worker_id, worker in WORKER_AGENTS.items():
        worker_name = getattr(worker, "name", f"worker-{worker_id}")
        # Get parent information from the pre-computed relationships
        if worker_name in AGENT_RELATIONSHIPS:
            parent_name = AGENT_RELATIONSHIPS[worker_name].get("parent_agent")
            if parent_name:
                # Create a placeholder timestamp for initial registration
                call_timestamp = datetime.datetime.now().isoformat()
                logger.info(f"[LINEAGE] Pre-registering relationship: {parent_name} -> {worker_name}")
                # Safely update the global tracking dictionary with a lock
                with ACTIVE_AGENT_CALLS_LOCK:
                    # Store the parent relationship (use the current timestamp for stable reference)
                    context: Dict[str, Any] = {"timestamp": call_timestamp}
                    ACTIVE_AGENT_CALLS[worker_name] = (parent_name, 0, context)

def create_initial_step(message: str, job_id: str, metadata: Dict[str, Any] = None) -> Tuple[ActionStep, str]:
    """Create an initial step for the top manager to establish lineage tracking.
    
    This function creates a "step 0" for the top-level manager agent, which serves
    as the root of the execution tree for a job. All other steps will link back to
    this initial step either directly or indirectly.
    
    Args:
        message (str): The user's input message/task
        job_id (str): The unique identifier for the job
        metadata (Dict[str, Any], optional): Optional metadata to include with the message
        
    Returns:
        Tuple[ActionStep, str]: The initial action step and the formatted prompt
    """
    thread_id = threading.get_ident()
    logger.warning(f"[JOB_ID_DEBUG] create_initial_step called with job_id {job_id} on thread {thread_id}")
    
    # Ensure the MANAGER is initialized
    global MANAGER
    if MANAGER is None:
        logger.error("Error: MANAGER is None. Calling initialize_agents() to initialize it.")
        initialize_agents()
        if MANAGER is None:
            raise RuntimeError("Failed to initialize MANAGER. Agent processing cannot continue.")
    
    # Make sure this thread has the job_id set in the thread-local storage
    with ACTIVE_JOB_IDS_LOCK:
        ACTIVE_JOB_IDS[thread_id] = job_id
        logger.warning(f"[JOB_ID_DEBUG] Set job_id {job_id} in ACTIVE_JOB_IDS for thread {thread_id} in create_initial_step")
        
        # Log all active job IDs for debugging
        all_job_ids = {tid: jid for tid, jid in ACTIVE_JOB_IDS.items()}
        logger.warning(f"[JOB_ID_DEBUG] All active job IDs after setting: {all_job_ids}")
    
    # Create the formatted prompt that will be sent to the agent
    metadata_section = ""
    if metadata and isinstance(metadata, dict):
        # Format metadata as a JSON string with indentation for readability
        try:
            metadata_json = json.dumps(metadata, indent=2)
            metadata_section = f"\nMetadata:\n```json\n{metadata_json}\n```\n"
            logger.info(f"Including metadata in prompt for job {job_id}")
        except Exception as e:
            logger.warning(f"Failed to serialize metadata for job {job_id}: {e}")
    
    # Check MANAGER again to ensure it's still initialized
    if MANAGER is None:
        raise RuntimeError("MANAGER is None when formatting prompt. Agent processing cannot continue.")
        
    # Generate MCP tool documentation if there are MCP tools
    mcp_docs = get_mcp_tool_usage_documentation()
    mcp_section = f"\n{mcp_docs}\n" if mcp_docs else ""
        
    formatted_prompt = f"""Additional Instructions:\n{MANAGER.description}\n{mcp_section}{metadata_section}\nUser task:\n{message}"""
    logger.warning(f"[JOB_ID_DEBUG] Created formatted prompt for job {job_id}")

    # Create an explicit step 0 for the top manager agent to ensure proper lineage tracking
    # This will serve as the root step that all other steps can connect to
    initial_step = ActionStep(
        step_number=0,
        tool_calls=[],
        start_time=datetime.datetime.now().timestamp(),
        action_output=formatted_prompt,  # Include the input prompt in the initial step
        end_time=None,  # Will be updated when agent completes
        duration=0      # Will be updated when agent completes
    )
    logger.warning(f"[JOB_ID_DEBUG] Created initial step object for job {job_id}")

    # Persist the initial step to the database
    try:
        logger.warning(f"[JOB_ID_DEBUG] About to add initial step to MEMORY_STEP_STORE with job_id {job_id}")
        # Check MANAGER again
        if MANAGER is None:
            raise RuntimeError("MANAGER is None when adding step to memory. Agent processing cannot continue.")
            
        MEMORY_STEP_STORE.add_step(
            initial_step, 
            MANAGER.name, 
            "CodeAgent", 
            parent_step_id=None,  # This is the root step with no parent
            job_id=job_id
        )
        logger.warning(f"[JOB_ID_DEBUG] Successfully added initial step to MEMORY_STEP_STORE with job_id {job_id}")
    except Exception as e:
        logger.error(f"[JOB_ID_DEBUG] Error adding initial step to MEMORY_STEP_STORE: {str(e)}")
        raise

    logger.info(f"Created initial step 0 for manager {MANAGER.name} with job ID {job_id}")
    
    # Log the thread again to make sure it's consistent
    current_thread_id = threading.get_ident()
    if current_thread_id != thread_id:
        logger.warning(f"[JOB_ID_DEBUG] Thread ID changed during create_initial_step: {thread_id} -> {current_thread_id}")
    
    return initial_step, formatted_prompt

def patch_agent_call(agent):
    """
    Monkey patch the agent's __call__ method to propagate job_id to the agent's thread.
    
    This ensures that when a managed agent is called, it has access to the current job_id
    in its thread, so it can properly create and track steps.
    
    Args:
        agent: The agent to patch
    """
    original_call = agent.__call__
    
    def patched_call(*args, **kwargs):
        # Get current job_id from parent thread
        parent_thread_id = threading.get_ident()
        job_id = None
        
        logger.warning(f"[JOB_ID_DEBUG] Patched call entered for {agent.name} on thread {parent_thread_id}")
        
        # Check all active job IDs
        with ACTIVE_JOB_IDS_LOCK:
            job_id = ACTIVE_JOB_IDS.get(parent_thread_id)
            all_jobs = {tid: jid for tid, jid in ACTIVE_JOB_IDS.items()}
            logger.warning(f"[JOB_ID_DEBUG] All active job IDs: {all_jobs}")
            logger.warning(f"[JOB_ID_DEBUG] Current thread {parent_thread_id} has job_id: {job_id}")
        
        if job_id:
            # Preserve the original job_id for restoring later
            original_job_id = job_id
            
            # Monkey patch the run method to set the job_id in the agent's thread
            original_run = agent.run
            logger.warning(f"[JOB_ID_DEBUG] Found job_id {job_id} for {agent.name}, patching run method")
            
            def run_with_job_id(*run_args, **run_kwargs):
                # Inside the managed agent's thread, set the job_id
                agent_thread_id = threading.get_ident()
                logger.warning(f"[JOB_ID_DEBUG] run_with_job_id executed for {agent.name} on thread {agent_thread_id}")
                
                with ACTIVE_JOB_IDS_LOCK:
                    ACTIVE_JOB_IDS[agent_thread_id] = original_job_id
                    logger.warning(f"[JOB_ID_DEBUG] Propagated job ID {original_job_id} from thread {parent_thread_id} to managed agent {agent.name} on thread {agent_thread_id}")
                
                # Check if the ID was actually set
                with ACTIVE_JOB_IDS_LOCK:
                    actual_job_id = ACTIVE_JOB_IDS.get(agent_thread_id)
                    logger.warning(f"[JOB_ID_DEBUG] Verified job_id for thread {agent_thread_id}: {actual_job_id}")
                
                try:
                    # Call the original run method
                    logger.warning(f"[JOB_ID_DEBUG] Calling original run method for {agent.name}")
                    result = original_run(*run_args, **run_kwargs)
                    logger.warning(f"[JOB_ID_DEBUG] Original run method completed for {agent.name}")
                    return result
                finally:
                    # Clean up after run completes to avoid memory leaks
                    with ACTIVE_JOB_IDS_LOCK:
                        if agent_thread_id in ACTIVE_JOB_IDS:
                            logger.warning(f"[JOB_ID_DEBUG] Cleaning up job_id for thread {agent_thread_id}")
                            del ACTIVE_JOB_IDS[agent_thread_id]
            
            # Replace the run method temporarily
            agent.run = run_with_job_id
            logger.warning(f"[JOB_ID_DEBUG] Successfully patched run method for {agent.name}")
            
            try:
                # Call the original __call__ method
                logger.warning(f"[JOB_ID_DEBUG] Calling original __call__ method for {agent.name}")
                result = original_call(*args, **kwargs)
                logger.warning(f"[JOB_ID_DEBUG] Original __call__ completed for {agent.name}")
                return result
            finally:
                # Restore the original run method
                logger.warning(f"[JOB_ID_DEBUG] Restoring original run method for {agent.name}")
                agent.run = original_run
                
                # Also restore the job_id for the current thread, as it may have been cleared by the child agent
                with ACTIVE_JOB_IDS_LOCK:
                    ACTIVE_JOB_IDS[parent_thread_id] = original_job_id
                    logger.warning(f"[JOB_ID_DEBUG] Restored job_id {original_job_id} back to parent thread {parent_thread_id}")
        else:
            # No job_id available, use the original method
            logger.warning(f"[JOB_ID_DEBUG] No job_id available when calling managed agent {agent.name}, proceeding with original method")
            return original_call(*args, **kwargs)
    
    # Replace the __call__ method
    agent.__call__ = patched_call
    return agent

def get_mcp_tool_usage_documentation():
    """Generate documentation for MCP tools to include in agent prompts.
    
    Since tools are now passed through the standard tools argument, smolagents
    automatically includes appropriate descriptions in agent prompts.
    This function returns minimal guidance for agent usage.
    
    Returns:
        str: Markdown formatted documentation for MCP tool usage
    """
    # Minimal documentation since the tool descriptions are handled by smolagents
    docs = [
        "## MCP Tools",
        "",
        "This agent has access to all necessary MCP tools through the standard tool calling mechanism.",
        "Use tools according to their descriptions provided by the agent framework.",
        "",
        "The tools will automatically preserve the full response structure when called."
    ]
    
    return "\n".join(docs)

def initialize_agents() -> Tuple[Union[CodeAgent, ToolCallingAgent], Dict[str, ToolCallingAgent], Dict[str, CodeAgent]]:
    """Initialize all agents and set up relationship tracking.
    
    This function prepares the agent system by:
    1. Creating the top manager with all MCP tools directly passed in
    2. Adding output tracking callbacks if needed
    3. Setting up agent relationship tracking
    4. Monkey patching managed agents to propagate job_id
    5. Configuring the CodeAgent's Python executor state to include managed agents
    6. Returning the manager and agent dictionaries for use
    
    Returns:
        Tuple[Union[CodeAgent, ToolCallingAgent], Dict[str, ToolCallingAgent], Dict[str, CodeAgent]]: 
            The top manager, worker agents, and manager agents
    """
    # Access the global MANAGER variable
    global MANAGER
    
    # Check if MANAGER is already initialized to avoid duplicate initialization
    if MANAGER is not None:
        logger.info("MANAGER already initialized, returning existing instance")
        return MANAGER, WORKER_AGENTS, MANAGER_AGENTS
    
    # We need to import the MCP tools but ONLY use those explicitly defined in agent-graph.json
    try:
        import sys
        import main
        import re
        
        # Get all available MCP tools
        all_mcp_tools = getattr(main, 'MCP_TOOLS', [])
        logger.info(f"Found {len(all_mcp_tools)} total MCP tools available")
        
        # Only include MCP tools that are explicitly linked in agent-graph.json
        # This ensures tools are only added when specifically configured
        from modules.tools import TOOLS, MCP_TOOLS
        
        # Critical debugging information
        logger.info(f"CRITICAL DEBUG: MCP_TOOLS type: {type(MCP_TOOLS)}")
        logger.info(f"CRITICAL DEBUG: MCP_TOOLS length: {len(MCP_TOOLS) if hasattr(MCP_TOOLS, '__len__') else 'unknown'}")
        
        # Critical debugging for TOOLS dictionary - MCP tools are registered here
        logger.info(f"CRITICAL DEBUG: TOOLS dictionary type: {type(TOOLS)}")
        logger.info(f"CRITICAL DEBUG: TOOLS dictionary length: {len(TOOLS) if hasattr(TOOLS, '__len__') else 'unknown'}")
        
        # Find MCP tools in TOOLS dictionary
        try:
            # Find MCP tools by ID prefix
            mcp_tools_in_dict = {tool_id: tool for tool_id, tool in TOOLS.items() if tool_id.startswith('mcp-')}
            logger.info(f"CRITICAL DEBUG: Found {len(mcp_tools_in_dict)} MCP tools in TOOLS dictionary")
            
            # Log the tool IDs and names of the first few MCP tools
            mcp_tool_info = []
            for i, (tool_id, tool) in enumerate(list(mcp_tools_in_dict.items())[:5]):
                mcp_tool_info.append({
                    "tool_id": tool_id,
                    "type": type(tool).__name__,
                    "has_name": hasattr(tool, "name"),
                    "name": getattr(tool, "name", "unknown") if hasattr(tool, "name") else "unknown"
                })
            logger.info(f"CRITICAL DEBUG: MCP tool details from TOOLS: {mcp_tool_info}")
        except Exception as e:
            logger.error(f"CRITICAL DEBUG: Error enumerating MCP tools in TOOLS: {e}")
        
        # Get service tools and MCP tools separately
        service_tools = []
        mcp_tools = []
        
        # Process each tool ID from the service_tool_ids list
        for tool_id in MANAGER_SPEC["service_tool_ids"]:
            # Check if this is an MCP tool ID
            if tool_id.startswith("mcp-") or "mcp" in tool_id.lower():
                logger.info(f"Found MCP tool ID in agent-graph.json: {tool_id}")
                
                # Check for both formats: "mcp-server-function" and "tool-mcp-uuid-function"
                logger.info(f"Attempting to match MCP tool ID: {tool_id}")
                
                # First try the standard format "mcp-server-function"
                match_standard = re.match(r"mcp-([^-]+)-(.+)", tool_id)
                if match_standard:
                    server_name, function_name = match_standard.groups()
                    logger.info(f"Matched standard format. Server: {server_name}, Function: {function_name}")
                    # Find matching tools
                    matched_tools = [
                        tool for tool in MCP_TOOLS 
                        if ((server_name in tool.name.lower() and function_name in tool.name.lower()) or 
                            tool.name == f"{server_name}_{function_name}")
                    ]
                    logger.info(f"Found {len(matched_tools)} matching tools for server {server_name} and function {function_name}")
                
                # Then try the "tool-mcp-uuid-function" format
                elif tool_id.startswith("tool-mcp-"):
                    logger.info(f"Tool ID appears to be in tool-mcp-uuid-function format: {tool_id}")
                    # Extract the function name (last part after the last dash)
                    parts = tool_id.split("-")
                    if len(parts) > 3:
                        function_name = parts[-1]
                        logger.info(f"Extracted function name: {function_name}")
                        
                        # Add extra logging for clarity during matching
                        logger.info(f"When matching function name '{function_name}' to MCP tools:")
                        logger.info(f"- Will match exact name: '{function_name}'")
                        logger.info(f"- Will match with server prefix: '<server>_{function_name}'")
                        logger.info(f"- Will NOT match if function_name is just a substring: '{function_name}' won't match if its contained in a longer name")
                        
                        # Log available MCP tool names for debugging
                        available_tool_names = []
                        server_prefix_patterns = []
                        
                        # CRITICAL DEBUG: Log the state of TOOLS dictionary with MCP tools
                        logger.info(f"CRITICAL DEBUG (tool match): Looking for MCP tools in TOOLS dictionary")
                        logger.info(f"CRITICAL DEBUG (tool match): TOOLS dictionary type: {type(TOOLS)}")
                        logger.info(f"CRITICAL DEBUG (tool match): TOOLS dictionary length: {len(TOOLS) if hasattr(TOOLS, '__len__') else 'unknown'}")
                        
                        try:
                            # Log MCP tool IDs and references for debugging
                            mcp_tool_ids = []
                            for t_id, mcp_tool in TOOLS.items():
                                if t_id.startswith('mcp-') and not isinstance(mcp_tool, str) and hasattr(mcp_tool, 'name'):
                                    mcp_tool_ids.append({
                                        "tool_id": t_id, 
                                        "name": mcp_tool.name,
                                        "id": id(mcp_tool)
                                    })
                            
                            # Log the IDs of the first few MCP tools
                            logger.info(f"CRITICAL DEBUG (tool match): MCP tool IDs in TOOLS: {mcp_tool_ids[:min(5, len(mcp_tool_ids))]} (total: {len(mcp_tool_ids)})")
                        except Exception as e:
                            logger.error(f"CRITICAL DEBUG (tool match): Error enumerating MCP tools in TOOLS: {e}")
                        
                        # Extract possible server name from tool ID
                        # Format is "tool-mcp-ca5eb76f-8989-4e1e-8d42-1ef4abc75f98-set_auth_token"
                        # We can't reliably get server name here, so we'll use common patterns
                        
                        # Get MCP tools from TOOLS dictionary
                        mcp_tools_from_dict = {t_id: tool for t_id, tool in TOOLS.items() if t_id.startswith('mcp-')}
                        logger.info(f"Found {len(mcp_tools_from_dict)} MCP tools in TOOLS dictionary for server name detection")
                        
                        # Get potential server names from the tools
                        common_server_names = []
                        for tool_id in mcp_tools_from_dict.keys():
                            # Extract potential server name from the tool ID (mcp-{server}-{function})
                            if tool_id.startswith("mcp-") and "-" in tool_id[4:]:
                                server_part = tool_id[4:].split("-", 1)[0]
                                if server_part and server_part not in common_server_names:
                                    common_server_names.append(server_part)
                                    
                        # If no server names were found in tool IDs, use a generic "mcp" as fallback
                        if not common_server_names:
                            common_server_names = ["mcp"]
                            
                        logger.info(f"Detected potential server names from tool IDs: {common_server_names}")
                        
                        # Initialize server_name with a default value to avoid reference error
                        server_name = None
                        
                        # Try to guess the server name based on function name
                        for potential_server in common_server_names:
                            if function_name.startswith(f"{potential_server}_") or function_name.startswith(f"{potential_server}-"):
                                server_name = potential_server
                                logger.info(f"Detected server name '{server_name}' from function name: {function_name}")
                                break
                        
                        # Create variations for all common server names
                        for srv_name in common_server_names:
                            server_prefix_patterns.extend([
                                srv_name + "_",                   # mattermost_
                                srv_name.replace('-', '_') + "_", # mattermost_
                                srv_name.replace('_', '-') + "_", # mattermost_
                                srv_name + "-",                   # mattermost-
                                srv_name.replace('-', '_') + "-", # mattermost-
                                srv_name.replace('_', '-') + "-"  # mattermost-
                            ])
                        logger.info(f"Looking for server prefixes: {server_prefix_patterns[:5]}... (total: {len(server_prefix_patterns)})")
                        
                        # Collect all tool names including different format variations
                        for tool_id, t in mcp_tools_from_dict.items():
                            # Skip if tool is a string (should be rare but defensive check)
                            if isinstance(t, str):
                                logger.warning(f"Found string in TOOLS['{tool_id}']: '{t}', skipping")
                                continue
                                
                            # Get the tool name with proper attribute check
                            if hasattr(t, 'name'):
                                tool_name = t.name
                                available_tool_names.append(tool_name)
                                logger.debug(f"Found tool with name: {tool_name}")
                                
                                # Also store variations of the name for matching flexibility
                                tool_name_underscore = tool_name.replace('-', '_')
                                if tool_name_underscore != tool_name:
                                    available_tool_names.append(tool_name_underscore)
                                    
                                # For tools with server name prefix, also store without prefix
                                for prefix in server_prefix_patterns:
                                    if tool_name.startswith(prefix):
                                        # Add the name without the prefix
                                        name_without_prefix = tool_name[len(prefix):]
                                        available_tool_names.append(name_without_prefix)
                                        logger.debug(f"Added name without prefix: {name_without_prefix}")
                                        
                                        # Add the underscore version of name without prefix
                                        name_without_prefix_underscore = name_without_prefix.replace('-', '_')
                                        if name_without_prefix_underscore != name_without_prefix:
                                            available_tool_names.append(name_without_prefix_underscore)
                            else:
                                logger.warning(f"Found MCP tool without name attribute in TOOLS['{tool_id}']: {type(t).__name__}")
                            
                        # Additional checks for server-specific prefixes
                        if server_name and function_name.startswith(f"{server_name}_"):
                            # Add the full function name
                            available_tool_names.append(function_name)
                            # Also add the version without prefix
                            available_tool_names.append(function_name[len(f"{server_name}_"):])
                        
                        # Add the direct function name for exact matching
                        available_tool_names.append(function_name)
                        # Add with underscore replaced by dash
                        available_tool_names.append(function_name.replace('_', '-'))
                        
                        # Remove duplicates and log for debugging
                        available_tool_names = list(set(available_tool_names))
                        logger.info(f"Available MCP tool names (after normalization): {available_tool_names}")
                        
                        # Log MCP tools from TOOLS dictionary for better debugging
                        mcp_tools_from_dict = {t_id: tool for t_id, tool in TOOLS.items() if t_id.startswith('mcp-')}
                        logger.info(f"Detailed MCP tool inventory from TOOLS dictionary ({len(mcp_tools_from_dict)} tools):")
                        for tool_id, tool in mcp_tools_from_dict.items():
                            if isinstance(tool, str):
                                logger.warning(f"Found string in TOOLS['{tool_id}']: '{tool}'")
                                continue
                                
                            if hasattr(tool, 'name'):
                                logger.info(f"Available MCP tool: {tool.name}, ID: {tool_id}, type: {type(tool).__name__}")
                            else:
                                logger.info(f"MCP tool without name: ID: {tool_id}, type: {type(tool).__name__}")
                        
                        # Find matching tools based on function name with more robust checks
                        matched_tools = []
                        
                        # CRITICAL DEBUG: Log actual function name and all tool names for direct comparison
                        logger.info(f"CRITICAL DEBUG (match detail): Finding matches for function '{function_name}'")
                        all_mcp_tool_info = []
                        for idx, (tool_id, tool) in enumerate(mcp_tools_from_dict.items()):
                            if not isinstance(tool, str) and hasattr(tool, 'name'):
                                all_mcp_tool_info.append({"idx": idx, "tool_id": tool_id, "name": tool.name})
                        logger.info(f"CRITICAL DEBUG (match detail): All tool names: {all_mcp_tool_info}")
                        
                        for tool_id, tool in mcp_tools_from_dict.items():
                            # Skip strings
                            if isinstance(tool, str):
                                continue
                                
                            # Skip tools without name attribute
                            if not hasattr(tool, 'name'):
                                continue
                                
                            tool_name = tool.name.lower()
                            matched = False
                            match_reason = ""
                            
                            # Try every possible matching strategy and log results
                            
                            # 1. Check for exact match
                            if function_name.lower() == tool_name:
                                matched = True
                                match_reason = "exact match"
                            
                            # 2. Check if function name is contained in tool name
                            # but only if it's a standalone word, not just any substring to prevent overly permissive matching
                            elif (
                                function_name.lower() in tool_name and 
                                (
                                    # Only match if this is a full word (with word boundaries)
                                    f"_{function_name.lower()}" in tool_name or
                                    tool_name.endswith(function_name.lower()) or
                                    tool_name.startswith(function_name.lower() + "_") or
                                    tool_name == function_name.lower()  # For completeness
                                )
                            ):
                                matched = True
                                match_reason = "substring match (at word boundary)"
                            
                            # 3. Check if function name with underscores converted to dashes is in tool name
                            elif function_name.replace('_', '-').lower() in tool_name:
                                matched = True
                                match_reason = "dash conversion match"
                            
                            # 4. Check for server-prefixed versions
                            elif any(prefix.lower() + function_name.lower() == tool_name for prefix in [s + "_" for s in common_server_names] + ["mcp_"]):
                                matched = True
                                match_reason = "server prefix match"
                            
                            # 5. Check if tool name without server prefix matches function name
                            else:
                                for prefix in server_prefix_patterns:
                                    prefix_lower = prefix.lower()
                                    if tool_name.startswith(prefix_lower):
                                        name_without_prefix = tool_name[len(prefix_lower):]
                                        if function_name.lower() == name_without_prefix:
                                            matched = True
                                            match_reason = f"exact match without prefix {prefix_lower}"
                                            break
                            
                            # Log matching result for every tool
                            logger.info(f"CRITICAL DEBUG (match detail): Tool '{tool.name}' match={matched}, reason='{match_reason}'")
                            
                            if matched:
                                matched_tools.append(tool)
                                logger.info(f"Found match for {function_name}: {tool_name} ({match_reason})")
                        logger.info(f"Found {len(matched_tools)} matching tools for function '{function_name}'")
                    else:
                        logger.warning(f"Tool ID has unusual format, not enough parts: {tool_id}")
                        matched_tools = []
                else:
                    logger.warning(f"Tool ID has unrecognized format: {tool_id}")
                    matched_tools = []
                
                # Add any matched tools - but track and deduplicate to avoid errors
                if matched_tools:
                    # Track tool names to prevent duplicates
                    added_names = set(tool.name for tool in mcp_tools if hasattr(tool, 'name'))
                    
                    for tool in matched_tools:
                        # Skip tools that are already added (prevent duplicates)
                        if hasattr(tool, 'name') and tool.name in added_names:
                            logger.info(f"Skipping duplicate MCP tool {tool.name} (already added)")
                            continue
                            
                        # Add the tool and track its name
                        mcp_tools.append(tool)
                        if hasattr(tool, 'name'):
                            added_names.add(tool.name)
                            logger.info(f"Added MCP tool {tool.name} to agent's tools (matched {tool_id})")
                else:
                    logger.warning(f"No matching MCP tool found for ID: {tool_id}")
            else:
                # This is a standard service tool
                try:
                    tool = get_tool_safely(tool_id)
                    service_tools.append(tool)
                    logger.info(f"Added service tool {tool_id} to manager's tools")
                except Exception as e:
                    logger.warning(f"Failed to get service tool {tool_id}: {e}")
        
        logger.info(f"Found {len(mcp_tools)} MCP tools and {len(service_tools)} service tools linked in agent-graph.json")
    except (ImportError, AttributeError) as e:
        logger.warning(f"Could not import MCP tools from main module: {e}")
        mcp_tools = []
        service_tools = []
        
        # Fallback: get service tools if MCP import failed
        try:
            from modules.tools import TOOLS
            for tool_id in MANAGER_SPEC["service_tool_ids"]:
                # Skip MCP tools as they can't be handled without MCP module
                if tool_id.startswith("mcp-") or "mcp" in tool_id.lower():
                    continue
                    
                try:
                    tool = get_tool_safely(tool_id)
                    service_tools.append(tool)
                    logger.info(f"Added service tool {tool_id} to manager's tools (fallback mode)")
                except Exception as e:
                    logger.warning(f"Failed to get service tool {tool_id}: {e}")
        except Exception as e:
            logger.warning(f"Failed to import TOOLS dictionary: {e}")
    
    # Get the managed agents
    managed_agents = []
    for agent_id in MANAGER_SPEC.get("managed_agent_ids", []):
        # Check if it's a manager first
        if agent_id in MANAGER_AGENTS:
            managed_agents.append(MANAGER_AGENTS[agent_id])
            logger.info(f"Added manager agent {agent_id} to manager's managed agents")
        # Then check if it's a worker
        elif agent_id in WORKER_AGENTS:
            managed_agents.append(WORKER_AGENTS[agent_id])
            logger.info(f"Added worker agent {agent_id} to manager's managed agents")
    
    # Create the model
    model = create_model_for_provider(
        model_id=DEFAULT_MODEL_CONFIG["model_id"],
        api_base=DEFAULT_MODEL_CONFIG["litellm_api_base"] if DEFAULT_MODEL_CONFIG["use_litellm"] else DEFAULT_MODEL_CONFIG["api_base"],
        api_key=os.getenv("LLM_API_KEY"),
        extra_headers=DEFAULT_MODEL_CONFIG["extra_headers"] if not DEFAULT_MODEL_CONFIG["use_litellm"] else None,
        **DEFAULT_MODEL_CONFIG.get("model_params", {})
    )
    
    # Now create the manager with service tools and only explicitly linked MCP tools
    logger.info(f"Creating manager with {len(service_tools)} service tools and {len(mcp_tools)} MCP tools")
    
    # CRITICAL DEBUG: Final comprehensive check of mcp_tools list
    logger.info(f"CRITICAL DEBUG (final check): mcp_tools type: {type(mcp_tools)}")
    logger.info(f"CRITICAL DEBUG (final check): mcp_tools length: {len(mcp_tools)}")
    
    # Log all available MCP tools one more time for comparison
    try:
        # Count MCP tools in TOOLS dictionary
        mcp_tools_in_dict = {t_id: tool for t_id, tool in TOOLS.items() if t_id.startswith('mcp-')}
        logger.info(f"CRITICAL DEBUG (final check): MCP tools in TOOLS dictionary: {len(mcp_tools_in_dict)}")
        
        # Get tool names from TOOLS dictionary
        available_mcp_tool_names = []
        for t_id, tool in mcp_tools_in_dict.items():
            if not isinstance(tool, str) and hasattr(tool, 'name'):
                available_mcp_tool_names.append(tool.name)
                
        logger.info(f"CRITICAL DEBUG (final check): Available MCP tool names in TOOLS: {available_mcp_tool_names[:min(10, len(available_mcp_tool_names))]} (total: {len(available_mcp_tool_names)})")
        
        # Log which tools were matched and which weren't
        matched_names = [tool.name for tool in mcp_tools if not isinstance(tool, str) and hasattr(tool, 'name')]
        logger.info(f"CRITICAL DEBUG (final check): Matched tool names: {matched_names}")
        
        # Find which tools weren't matched
        unmatched = [name for name in available_mcp_tool_names if name not in matched_names]
        logger.info(f"CRITICAL DEBUG (final check): Unmatched tool names: {unmatched[:min(10, len(unmatched))]} (total: {len(unmatched)})")
    except Exception as e:
        logger.error(f"CRITICAL DEBUG (final check): Error in final tool analysis: {e}")
        
    # Log detailed information about each tool being registered
    logger.info("=== DETAILED TOOL LIST BEFORE MANAGER CREATION ===")
    combined_tools = service_tools + mcp_tools
    for i, tool in enumerate(combined_tools):
        logger.info(f"Tool {i+1}/{len(combined_tools)}: name='{tool.name}', type={type(tool).__name__}")
        logger.info(f"  Description: {getattr(tool, 'description', 'No description')[:100]}...")
        logger.info(f"  Is callable: {callable(tool)}")
        tool_methods = [attr for attr in dir(tool) if not attr.startswith('_') and callable(getattr(tool, attr, None))]
        logger.info(f"  Methods: {tool_methods[:10]}")
        # Check if this is an MCP tool
        from_mcp = i >= len(service_tools)
        logger.info(f"  Is MCP tool: {from_mcp}")
        
        # For each MCP tool, log extra detailed information
        if from_mcp:
            logger.info(f"  MCP TOOL DETAILS: {tool.name}")
            logger.info(f"  Full dir: {dir(tool)}")
            logger.info(f"  Has __call__: {hasattr(tool, '__call__')}")
            logger.info(f"  Input schema: {getattr(tool, 'get_input_schema', lambda: 'No schema')()}")
    logger.info("=== END OF TOOL LIST ===")
    
    # Determine agent type
    agent_class = CodeAgent
    if MANAGER_SPEC.get("agent_type") == "ToolCallingAgent":
        agent_class = ToolCallingAgent
    
    # Create the agent
    MANAGER = agent_class(
        tools=service_tools + mcp_tools,  # Combine service tools with only explicitly linked MCP tools
        name=MANAGER_SPEC["name"],
        description=MANAGER_SPEC["description"],
        managed_agents=managed_agents,
        model=model,
        max_steps=MANAGER_SPEC["max_steps"],
        provide_run_summary=True,
        step_callbacks=[step_callback],
        add_base_tools=MANAGER_SPEC["use_base_tools"],
        **({} if agent_class == ToolCallingAgent else {"additional_authorized_imports": ["time", "json", "requests", "requests.exceptions", "nest_asyncio", "urllib", "urllib.request", "urllib.error", "urllib.parse", "pandas", "psycopg2", "http.client", "aiohttp"]})
    )
    
    # Set additional parameters for CodeAgent
    if agent_class == CodeAgent:
        # Standard imports that should always be authorized for CodeAgents
        standard_imports = [
            "time", "json", "requests", "requests.exceptions", "nest_asyncio", 
            "urllib", "urllib.request", "urllib.error", "urllib.parse", 
            "pandas", "psycopg2", "http.client", "aiohttp"
        ]
        
        # Start with standard imports
        authorized_imports = list(standard_imports)
        
        # Add worker and manager agent names if available in MANAGER_SPEC
        if "additional_authorized_imports" in MANAGER_SPEC:
            # Add any custom imports from MANAGER_SPEC
            for import_name in MANAGER_SPEC["additional_authorized_imports"]:
                if import_name not in authorized_imports:
                    authorized_imports.append(import_name)
        
        # Add managed agent names to authorized imports
        for agent in managed_agents:
            agent_name = getattr(agent, "name", None)
            if agent_name and agent_name not in authorized_imports:
                authorized_imports.append(agent_name)
                
        # Set the complete list of authorized imports
        MANAGER.additional_authorized_imports = authorized_imports
        logger.info(f"Set authorized imports for CodeAgent: {authorized_imports}")
        
    logger.info(f"Created manager agent {MANAGER.name} of type {agent_class.__name__}")
    logger.info(f"Manager has {len(MANAGER.tools)} tools in total")
    
    # Count how many MCP tools were added to verify our fixes worked
    mcp_tool_count = 0
    for tool in MANAGER.tools:
        if not isinstance(tool, str) and hasattr(tool, 'name'):
            tool_name = tool.name.lower()
            # Check if this is an MCP tool using a generic pattern
            if 'mcp' in str(type(tool)).lower() or 'mcp' in tool_name:
                mcp_tool_count += 1
    
    logger.info(f"✅ VERIFICATION: Manager has {mcp_tool_count} MCP tools out of {len(MANAGER.tools)} total tools")
    
    # Log the final tools list in the manager
    logger.info("=== MANAGER FINAL TOOLS LIST ===")
    for i, tool in enumerate(MANAGER.tools):
        try:
            # Add defensive checks for string objects or other non-tool objects
            if isinstance(tool, str):
                logger.warning(f"Tool {i+1}/{len(MANAGER.tools)} is a string: '{tool}'. This will cause errors when trying to access attributes.")
                continue
                
            tool_name = getattr(tool, 'name', f"unnamed_tool_{i}")
            tool_type = type(tool).__name__
            logger.info(f"Tool {i+1}/{len(MANAGER.tools)}: name='{tool_name}', type={tool_type}")
            
            # Only try to access description if tool is not a string
            description = getattr(tool, 'description', 'No description')
            if isinstance(description, str):
                logger.info(f"  Description: {description[:100]}...")
            else:
                logger.info(f"  Description: {type(description).__name__} (not a string)")
                
            # Log detailed information for all tools
            logger.info(f"  Tool implementation details: {tool_name}")
            logger.info(f"  Has __call__: {hasattr(tool, '__call__')}")
            
            if hasattr(tool, 'get_input_schema'):
                try:
                    input_schema = tool.get_input_schema()
                    logger.info(f"  Input schema: {input_schema}")
                except Exception as e:
                    logger.error(f"  Error getting input schema: {e}")
        except Exception as e:
            logger.error(f"  Error inspecting tool at index {i}: {e}")
    logger.info("=== END OF MANAGER TOOLS LIST ===")
    
    # Add the output tracking callback to all agents
    
    
    # Monkey patch all managed agents to propagate job_id
    for worker_id, worker in WORKER_AGENTS.items():
        patch_agent_call(worker)
        
    for manager_id, manager in MANAGER_AGENTS.items():
        patch_agent_call(manager)
    
    # Set up relationship tracking
    setup_agent_relationship_tracking()
    
    # Add managed agents to the Python executor's state
    # This allows direct access in Python code without imports
    # We need to do this for the top manager and all manager agents
    if hasattr(MANAGER, 'python_executor') and hasattr(MANAGER.python_executor, 'state'):
        logger.info("🛠 Configuring MANAGER's Python executor state")
        
        # Add worker agents to the executor state
        for agent_name, agent in WORKER_AGENTS.items():
            MANAGER.python_executor.state[agent.name] = agent
            logger.info(f"✅ Added worker agent {agent.name} to MANAGER's Python executor state")
            
        # Add manager agents to the executor state
        for agent_name, agent in MANAGER_AGENTS.items():
            MANAGER.python_executor.state[agent.name] = agent
            logger.info(f"✅ Added manager agent {agent.name} to MANAGER's Python executor state")
        
        # Add a getter function for the current job_id that the Python code can use
        def get_current_job_id():
            with ACTIVE_JOB_IDS_LOCK:
                return ACTIVE_JOB_IDS.get(threading.get_ident())
        
        # Add the function to the executor's state
        MANAGER.python_executor.state['get_current_job_id'] = get_current_job_id
        
        # Import the job metadata function
        from modules.memory import get_job_metadata
        
        # Add the get_job_metadata function to the executor's state
        MANAGER.python_executor.state['get_job_metadata'] = get_job_metadata
        
        # Log MCP tools that will be used directly by agents
        # This is for diagnostic purposes and improving the frontend prompt editor
        logger.info("=== MCP TOOLS AVAILABLE TO AGENTS ===")
        from modules.tools import TOOLS
        mcp_tool_names = []
        mcp_tool_sources = {}
        
        # First, log MCP tools registered directly with the agent via from_mcp
        for tool in mcp_tools:
            # Skip string objects to prevent AttributeError
            if isinstance(tool, str):
                logger.warning(f"Found string in mcp_tools: '{tool}'. Skipping.")
                continue
            
            try:
                # Get tool attributes with proper checks
                tool_name = getattr(tool, "name", "unknown") if hasattr(tool, "name") else "unnamed_tool"
                tool_desc = getattr(tool, "description", "No description") if hasattr(tool, "description") else "No description"
                
                # Safe object ID access
                try:
                    tool_id = getattr(tool, "id", None) or id(tool)
                except:
                    tool_id = f"unknown_id_{hash(str(tool))}"
                
                logger.info(f"Directly registered MCP tool from from_mcp(): {tool_name}")
                logger.info(f"  Tool ID: {tool_id}")
                
                # Only slice the description if it's a string
                if isinstance(tool_desc, str):
                    desc_preview = tool_desc[:100] + "..." if len(tool_desc) > 100 else tool_desc
                else:
                    desc_preview = f"Non-string description type: {type(tool_desc).__name__}"
                logger.info(f"  Description: {desc_preview}")
                
                # Safe class access
                logger.info(f"  Type: {type(tool).__name__}")
                logger.info(f"  Class: {tool.__class__.__name__}")
                logger.info(f"  Module: {tool.__class__.__module__}")
                
                # Collect names for summary with source
                if tool_name not in mcp_tool_names:
                    mcp_tool_names.append(tool_name)
                    mcp_tool_sources[tool_name] = "from_mcp"
            except Exception as e:
                logger.error(f"Error analyzing MCP tool: {e}")
                logger.error(f"Tool type: {type(tool).__name__}")
                # Try to safely get a string representation for debugging
                try:
                    tool_str = str(tool)[:100]
                    logger.error(f"Tool string representation: {tool_str}...")
                except:
                    logger.error("Unable to get string representation of tool")
                # Continue processing other tools
                continue
        
        # Also check tools in MANAGER
        if hasattr(MANAGER, 'tools'):
            for tool in MANAGER.tools:
                # Skip string objects to prevent AttributeError
                if isinstance(tool, str):
                    logger.warning(f"Found string in MANAGER.tools: '{tool}'. Skipping.")
                    continue
                
                try:
                    # Safe attribute access
                    tool_name = getattr(tool, "name", "unknown") if hasattr(tool, "name") else f"unnamed_tool_{id(tool)}"
                    
                    # Check if it's an MCP tool
                    is_mcp_tool = False
                    try:
                        is_mcp_tool = "mcp" in str(type(tool)).lower() or "mcp" in tool_name.lower()
                    except:
                        # If there's an error checking the type, assume it's not an MCP tool
                        is_mcp_tool = False
                    
                    if is_mcp_tool:
                        logger.info(f"MCP tool from MANAGER.tools: {tool_name}")
                        
                        # Safe class information access
                        try:
                            logger.info(f"  Type: {type(tool).__name__}")
                            logger.info(f"  Class: {tool.__class__.__name__}")
                            logger.info(f"  Module: {tool.__class__.__module__}")
                        except Exception as class_err:
                            logger.error(f"Error getting class info for {tool_name}: {class_err}")
                        
                        # Collect names for summary with source
                        if tool_name not in mcp_tool_names:
                            mcp_tool_names.append(tool_name)
                            mcp_tool_sources[tool_name] = "MANAGER.tools"
                except Exception as e:
                    logger.error(f"Error processing tool in MANAGER.tools: {e}")
                    # Continue processing other tools
                    continue
        
        # Then log tools registered via the TOOLS dictionary 
        for tool_id, tool in TOOLS.items():
            if "mcp-" in tool_id:
                # Make the tool available by its registered ID for logging purposes
                python_safe_id = tool_id.replace("-", "_")
                logger.info(f"MCP tool from TOOLS dictionary: {tool_id}")
                logger.info(f"  Python-safe ID: {python_safe_id}")
                logger.info(f"  Type: {type(tool).__name__}")
                logger.info(f"  Class: {tool.__class__.__name__}")
                logger.info(f"  Module: {tool.__class__.__module__}")
                
                # For the actual tool name
                simple_name = getattr(tool, "name", "")
                if simple_name:
                    underscore_name = simple_name.replace("-", "_")
                    logger.info(f"  Tool name: {simple_name}")
                    logger.info(f"  Underscore name: {underscore_name}")
                    
                    # Collect names for summary with source
                    if simple_name not in mcp_tool_names:
                        mcp_tool_names.append(simple_name)
                        mcp_tool_sources[simple_name] = "TOOLS"
                    if underscore_name not in mcp_tool_names:
                        mcp_tool_names.append(underscore_name)
                        mcp_tool_sources[underscore_name] = "TOOLS (underscore converted)"
        
        # MCP tools are intentionally NOT registered in the Python executor state
        # This ensures tools are only accessed through the agent's tools argument
        # Which guarantees the custom adapter is always used
        if hasattr(MANAGER, 'python_executor') and hasattr(MANAGER.python_executor, 'state'):
            logger.info("=== NOT REGISTERING MCP TOOLS IN PYTHON EXECUTOR STATE ===")
            logger.info("MCP tools are now only available through the agent's tools list")
            logger.info("This ensures the custom adapter is always used")
            
            # Document in the Python executor state why tools aren't directly registered
            MANAGER.python_executor.state['MCP_TOOLS_NOTE'] = """
            MCP tools are intentionally not registered directly in the Python executor state.
            This ensures all tool calls go through the proper adapter which preserves full response structure.
            Use tools through the CodeAgent's standard tool-calling mechanism instead.
            """
        
        # Log a summary of all tool names the agent might try to use
        logger.info("=== MCP TOOL NAMES SUMMARY ===")
        for name in sorted(mcp_tool_names):
            source = mcp_tool_sources.get(name, "unknown source")
            logger.info(f"Tool name: {name} (Source: {source})")
        logger.info("=============================")
        
        logger.info(f"Added managed agents to Python executor state: {list(WORKER_AGENTS.keys()) + list(MANAGER_AGENTS.keys())}")
    
    # Also do this for manager agents that can call other agents
    for manager_id, manager in MANAGER_AGENTS.items():
        if hasattr(manager, 'python_executor') and hasattr(manager.python_executor, 'state'):
            # Add managed agents depending on relationship
            for agent_name, agent_rel in AGENT_RELATIONSHIPS.items():
                if agent_rel["parent_agent"] == manager.name:
                    # Find the agent object by name
                    for agent_obj in list(WORKER_AGENTS.values()) + list(MANAGER_AGENTS.values()):
                        if agent_obj.name == agent_name:
                            manager.python_executor.state[agent_name] = agent_obj
                            break
            
            # Add a getter function for the current job_id that the Python code can use
            def get_current_job_id():
                with ACTIVE_JOB_IDS_LOCK:
                    return ACTIVE_JOB_IDS.get(threading.get_ident())
            
            # Add the function to the executor's state
            manager.python_executor.state['get_current_job_id'] = get_current_job_id
            
            # Import the job metadata function
            from modules.memory import get_job_metadata
            
            # Add the get_job_metadata function to the executor's state
            manager.python_executor.state['get_job_metadata'] = get_job_metadata
            
            # Log MCP tools available to this manager agent
            logger.info(f"=== MCP TOOLS AVAILABLE TO {manager.name} ===")
            from modules.tools import TOOLS
            manager_mcp_tool_names = []
            
            # First, log MCP tools registered directly with the agent via from_mcp
            # These would be available through the agent's tools list
            for agent_tool in manager.tools:
                # Skip string objects to prevent AttributeError
                if isinstance(agent_tool, str):
                    logger.warning(f"Found string in {manager.name}.tools: '{agent_tool}'. Skipping.")
                    continue
                
                try:
                    # Check if it's an MCP tool with safe attribute access
                    has_name = hasattr(agent_tool, "name")
                    is_mcp_tool = False
                    
                    if has_name:
                        try:
                            is_mcp_tool = "mcp" in str(type(agent_tool)).lower()
                        except:
                            # If there's an error in type checking, try a fallback
                            try:
                                tool_name = agent_tool.name
                                is_mcp_tool = "mcp" in tool_name.lower()
                            except:
                                # Both checks failed, skip this tool
                                continue
                                
                        if is_mcp_tool:
                            tool_name = agent_tool.name
                            logger.info(f"Directly registered MCP tool for {manager.name}: {tool_name}")
                            
                            # Collect names for summary
                            if tool_name not in manager_mcp_tool_names:
                                manager_mcp_tool_names.append(tool_name)
                except Exception as e:
                    logger.error(f"Error processing tool in {manager.name}.tools: {e}")
                    # Continue with other tools
                    continue
            
            # Log a summary of all tool names this manager might try to use
            logger.info(f"=== MCP TOOL NAMES SUMMARY FOR {manager.name} ===")
            for name in sorted(manager_mcp_tool_names):
                logger.info(f"Available tool name for {manager.name}: {name}")
            logger.info("==========================================")
            
            # MCP tools are intentionally NOT registered in the Python executor state
            # for consistency and to ensure the custom adapter is always used
            logger.info(f"=== NOT REGISTERING MCP TOOLS IN {manager.name}'s PYTHON EXECUTOR STATE ===")
            logger.info(f"MCP tools are only available through the agent's tools list for {manager.name}")
            
            # Document in the manager's Python executor state why tools aren't directly registered
            manager.python_executor.state['MCP_TOOLS_NOTE'] = """
            MCP tools are intentionally not registered directly in the Python executor state.
            This ensures all tool calls go through the proper adapter which preserves full response structure.
            Use tools through the CodeAgent's standard tool-calling mechanism instead.
            """
            
            logger.info(f"Added managed agents to {manager.name}'s Python executor state")
    
    return MANAGER, WORKER_AGENTS, MANAGER_AGENTS

# Public exports from this module
__all__ = [
    # Main agent exports
    'MANAGER',              # Top-level manager agent
    'MANAGER_AGENTS',       # Dictionary of manager agents
    'WORKER_AGENTS',        # Dictionary of worker agents
    
    # Agent relationship tracking
    'AGENT_RELATIONSHIPS',  # Pre-computed agent relationship map
    'ACTIVE_AGENT_CALLS',   # Current active agent call tracking
    'ACTIVE_JOB_IDS',       # Job ID tracking by thread
    
    # Functions
    'step_callback',        # Main callback for step recording
    'output_tracking_callback',  # Callback for output tracking
    'initialize_agents',    # Function to set up the agent system
    'create_initial_step',  # Creates the root step for a job
    
    # Types
    'AgentRelationship',    # Type for agent relationship data
    'AgentStepContext',     # Type for step context data
    'AgentConfig'           # Type for agent configuration
]