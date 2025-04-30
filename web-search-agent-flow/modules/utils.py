"""Utility functions for the multi-agent system.

This module provides common utility functions used throughout the multi-agent system,
including:

1. Timestamp conversion and formatting
2. Database connection management
3. Database operations for step relationships
4. Shared helper functions for data manipulation

These utilities abstract common operations to maintain consistency and avoid
code duplication across the system.
"""
import os
import logging
import datetime
import asyncio
from typing import Tuple, Optional, Any, Union, Dict, List, TypeVar, Generic, cast

# For database connections
try:
    import psycopg2
    from psycopg2.extensions import connection as PgConnection
    from psycopg2.extensions import cursor as PgCursor
except ImportError:
    # Define placeholder types for when psycopg2 is not available
    PgConnection = Any
    PgCursor = Any

# Setup logger
logger = logging.getLogger(__name__)

# Type aliases
TimestampValue = Union[int, float, str, datetime.datetime]

def convert_timestamp_to_iso(timestamp: TimestampValue) -> str:
    """Converts various timestamp formats to ISO 8601 format string.
    
    This utility function handles various timestamp formats and standardizes them
    to ISO 8601 format for consistency throughout the system. It supports:
    - Integer/float epoch seconds
    - Integer/float epoch milliseconds
    - Datetime objects
    - ISO format strings (which are passed through unchanged)
    
    Args:
        timestamp (TimestampValue): A timestamp value in any supported format
        
    Returns:
        str: ISO 8601 formatted timestamp string (YYYY-MM-DDTHH:MM:SS.mmmmmm)
        
    Examples:
        >>> convert_timestamp_to_iso(1609459200)  # Epoch seconds
        '2021-01-01T00:00:00'
        >>> convert_timestamp_to_iso(1609459200000)  # Epoch milliseconds
        '2021-01-01T00:00:00'
        >>> convert_timestamp_to_iso("2021-01-01T00:00:00")  # Already ISO
        '2021-01-01T00:00:00'
    """
    if isinstance(timestamp, (int, float)):
        # Convert milliseconds or seconds since epoch to datetime object
        try:
            if timestamp > 1e12:  # Likely milliseconds
                dt = datetime.datetime.fromtimestamp(timestamp / 1000.0)
            else:  # Likely seconds
                dt = datetime.datetime.fromtimestamp(timestamp)
            # Format as ISO string
            return dt.isoformat()
        except (ValueError, OverflowError) as e:
            logger.warning(f"Failed to convert numeric timestamp {timestamp}: {e}")
            # Return a fallback timestamp if conversion fails
            return datetime.datetime.now().isoformat()
    elif isinstance(timestamp, datetime.datetime):
        return timestamp.isoformat()
    elif timestamp is None:
        # Return current time for None values
        return datetime.datetime.now().isoformat()
    
    # For string and other types, return as is with str conversion
    return str(timestamp)

def get_database_connection() -> PgConnection:
    """Creates and returns a PostgreSQL database connection if configured.
    
    This function establishes a connection to the PostgreSQL database using the
    connection string from the PG_CONNECTION_STRING environment variable. It returns
    the connection object for use in database operations.
    
    The connection is configured with autocommit set to False to allow for explicit
    transaction management.
    
    Returns:
        PgConnection: The database connection if successful, or None if the connection fails
            or no connection string is provided
            
    Example:
        ```python
        conn = get_database_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM agent_flow_steps LIMIT 10")
                rows = cursor.fetchall()
                # Process rows...
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error: {e}")
            finally:
                conn.close()
        ```
    """
    conn_string = os.getenv('PG_CONNECTION_STRING')
    if not conn_string:
        logger.debug("Skipping database operation: No PG_CONNECTION_STRING environment variable")
        return None
        
    try:
        # Connect to the database
        conn = psycopg2.connect(conn_string)
        conn.autocommit = False  # Ensure explicit transaction control
        logger.debug("Successfully connected to PostgreSQL database")
        return conn
    except ImportError:
        logger.error("psycopg2 module not available - database operations disabled")
        return None
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None

async def create_step_relationships(job_id: str) -> bool:
    """Creates relationships between steps for a completed job.
    
    This function establishes parent-child relationships between steps in the database
    for a specific job. It identifies parent-child relationships from the parent_step_id
    field and creates explicit relationship records in the agent_flow_step_relationships
    table.
    
    This is typically called after all steps for a job have been recorded to ensure
    that the complete lineage graph is captured in the database.
    
    Args:
        job_id (str): The unique identifier of the job for which to create step relationships
        
    Returns:
        bool: True if relationships were successfully created, False if an error occurred
        
    Note:
        This function requires the PG_CONNECTION_STRING environment variable to be set.
        If it's not set, the function will log a debug message and return False.
    """
    if not os.getenv('PG_CONNECTION_STRING'):
        logger.debug(f"Skipping step relationship creation for job {job_id}: No database connection string")
        return False
        
    conn = None
    cursor = None
    try:
        # Connect to the database using the utility function
        conn = get_database_connection()
        if not conn:
            logger.error(f"Failed to connect to database for creating step relationships for job {job_id}")
            return False
        
        cursor = conn.cursor()
        
        # Find all steps for this job
        cursor.execute(
            "SELECT step_id, parent_step_id FROM agent_flow_steps WHERE job_id = %s",
            (job_id,)
        )
        
        steps = cursor.fetchall()
        logger.info(f"Found {len(steps)} steps for job {job_id} to create relationships")
        
        # Create relationships based on parent_step_id values
        relationships_created = 0
        for step in steps:
            step_id = step[0]
            parent_step_id = step[1]
            
            if parent_step_id:
                try:
                    cursor.execute(
                        """
                        INSERT INTO agent_flow_step_relationships (parent_step_id, child_step_id)
                        VALUES (%s, %s)
                        ON CONFLICT (parent_step_id, child_step_id) DO NOTHING
                        """,
                        (parent_step_id, step_id)
                    )
                    if cursor.rowcount > 0:
                        relationships_created += 1
                except Exception as rel_error:
                    logger.warning(f"Error creating relationship from {parent_step_id} to {step_id}: {rel_error}")
        
        conn.commit()
        logger.info(f"Created {relationships_created} step relationships for job {job_id}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to create step relationships for job {job_id}: {e}")
        # Rollback on error
        if conn:
            try:
                conn.rollback()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback transaction: {rollback_error}")
        return False
    finally:
        # Close the database connection
        if conn:
            conn.close()

def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """Safely parse a JSON string with error handling.
    
    This utility function attempts to parse a JSON string and returns a default
    value if parsing fails. This is useful for handling potentially malformed
    JSON input without raising exceptions.
    
    Args:
        json_str (str): The JSON string to parse
        default (Any, optional): The default value to return if parsing fails. 
            Defaults to None.
            
    Returns:
        Any: The parsed JSON object, or the default value if parsing fails
        
    Example:
        ```python
        # Safe parsing with default empty dict
        metadata = safe_json_loads(metadata_str, {})
        # Now use metadata without worrying about exceptions
        user_id = metadata.get('user_id', 'anonymous')
        ```
    """
    import json
    if not json_str:
        return default
        
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning(f"Failed to parse JSON string: {e}")
        return default

# Public exports from this module
__all__ = [
    # Timestamp functions
    'convert_timestamp_to_iso',
    
    # Database functions
    'get_database_connection',
    'create_step_relationships',
    
    # Helper functions
    'safe_json_loads',
    
    # Type definitions
    'TimestampValue',
    'PgConnection',
    'PgCursor'
]