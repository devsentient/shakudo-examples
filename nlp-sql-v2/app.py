"""
NLP-to-SQL Microservice v2 using Vanna AI and Claude Sonnet 4.5

This service provides:
1. Text-to-SQL conversion using Vanna AI with Claude as the LLM
2. SQL execution against Supabase/PostgreSQL
3. Conversational memory for follow-up questions
4. OpenWebUI-compatible API for integration
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional
import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from utils.vanna_client import get_vanna_client, VannaClient
from utils.database import execute_sql, get_table_metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan management for the FastAPI application."""
    # Initialize Vanna client on startup
    logger.info("Initializing Vanna AI client...")
    app.state.vanna = get_vanna_client()
    app.state.conversation_history = {}  # Store conversation history by session
    yield
    # Cleanup on shutdown
    logger.info("Shutting down NLP-SQL service...")


app = FastAPI(
    docs_url=os.environ.get("DOCS_URL", "/nlp-sql-v2/docs"),
    openapi_url=os.environ.get("OPENAPI_URL", "/nlp-sql-v2/openapi.json"),
    redoc_url=None,
    title="NLP-SQL v2 with Vanna AI",
    description="Text-to-SQL service using Vanna AI and Claude Sonnet 4.5",
    summary="Shakudo NLP-SQL v2 microservice",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    expose_headers=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================


class AskQuestionRequest(BaseModel):
    """Request model for asking a natural language question."""

    question: str = Field(
        ..., description="Natural language question to convert to SQL"
    )
    session_id: Optional[str] = Field(
        None, description="Session ID for conversation continuity"
    )
    execute: bool = Field(True, description="Whether to execute the generated SQL")
    schema_name: Optional[str] = Field(
        None, description="Specific schema to query (optional)"
    )


class AskQuestionResponse(BaseModel):
    """Response model for ask question endpoint."""

    question: str
    sql: str
    results: Optional[list] = None
    error: Optional[str] = None
    session_id: str
    follow_up_suggestions: Optional[list] = None


class TrainRequest(BaseModel):
    """Request model for training Vanna with DDL or documentation."""

    ddl: Optional[str] = Field(None, description="DDL statement to train on")
    documentation: Optional[str] = Field(None, description="Documentation to train on")
    sql: Optional[str] = Field(None, description="Example SQL query")
    question: Optional[str] = Field(None, description="Example question for the SQL")


class OpenWebUIRequest(BaseModel):
    """Request model compatible with OpenWebUI pipeline format."""

    messages: list = Field(..., description="List of messages in OpenWebUI format")
    model: str = Field("vanna-sql", description="Model identifier")
    stream: bool = Field(False, description="Whether to stream response")


# ============================================================================
# Core Functions
# ============================================================================


def extract_sql_from_response(text: str) -> str:
    """Extract SQL from potential markdown code blocks."""
    # Try to extract from code block
    sql_match = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return sql_match.group(1).strip()

    # Try generic code block
    code_match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()

    # Return as-is if no code blocks
    return text.strip()


async def generate_sql(
    vanna: VannaClient,
    question: str,
    session_id: str,
    conversation_history: dict,
    schema_name: Optional[str] = None,
) -> str:
    """Generate SQL from natural language question using Vanna AI."""

    # Build context from conversation history
    history = conversation_history.get(session_id, [])
    context = ""
    if history:
        context = "Previous conversation context:\n"
        for entry in history[-5:]:  # Last 5 turns
            context += f"Q: {entry['question']}\n"
            if entry.get("sql"):
                context += f"SQL: {entry['sql']}\n"
        context += "\nCurrent question:\n"

    full_question = context + question if context else question

    try:
        sql = vanna.generate_sql(full_question)
        sql = extract_sql_from_response(sql)

        # Add schema prefix if specified and not already present
        if schema_name and not f"{schema_name}." in sql:
            # Simple heuristic: add schema to table names
            # This is a basic implementation - Vanna should handle this better with proper training
            pass

        return sql
    except Exception as e:
        logger.error(f"Error generating SQL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate SQL: {str(e)}")


def suggest_follow_ups(question: str, results: list) -> list:
    """Generate follow-up question suggestions based on the query and results."""
    suggestions = []

    # Common follow-up patterns
    if results and len(results) > 0:
        if "total" not in question.lower() and "sum" not in question.lower():
            suggestions.append("What is the total amount?")
        if "group" not in question.lower():
            suggestions.append("Can you group these by year?")
        if len(results) > 5:
            suggestions.append("Show me just the top 5 results")

    # Context-specific suggestions
    if "donor" in question.lower() or "donation" in question.lower():
        suggestions.extend(
            [
                "What campaigns did they donate to?",
                "Show their contact information",
                "What is their donation history?",
            ]
        )
    elif "membership" in question.lower():
        suggestions.extend(
            ["When is the expiration date?", "List all payments for this account"]
        )

    return suggestions[:3]  # Return max 3 suggestions


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "service": "nlp-sql-v2",
        "llm": "claude-sonnet-4-5-20250514",
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    try:
        # Check database connectivity
        metadata = await get_table_metadata()
        return {
            "status": "healthy",
            "database": "connected",
            "tables_available": len(metadata) if metadata else 0,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.post("/ask", response_model=AskQuestionResponse)
async def ask_question(request: AskQuestionRequest):
    """
    Main endpoint for asking natural language questions.

    Converts the question to SQL using Vanna AI + Claude,
    optionally executes it, and returns results.
    """
    import uuid

    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())[:8]

    # Initialize conversation history for this session
    if session_id not in app.state.conversation_history:
        app.state.conversation_history[session_id] = []

    try:
        # Generate SQL
        sql = await generate_sql(
            app.state.vanna,
            request.question,
            session_id,
            app.state.conversation_history,
            request.schema_name,
        )

        results = None
        error = None
        follow_ups = None

        # Execute SQL if requested
        if request.execute:
            try:
                results = await execute_sql(sql)
                follow_ups = suggest_follow_ups(request.question, results)
            except Exception as e:
                error = f"SQL execution error: {str(e)}"
                logger.error(f"SQL execution error: {e}")

        # Store in conversation history
        app.state.conversation_history[session_id].append(
            {"question": request.question, "sql": sql, "success": error is None}
        )

        return AskQuestionResponse(
            question=request.question,
            sql=sql,
            results=results,
            error=error,
            session_id=session_id,
            follow_up_suggestions=follow_ups,
        )

    except Exception as e:
        logger.error(f"Error processing question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/openwebui")
async def openwebui_endpoint(request: OpenWebUIRequest):
    """
    OpenWebUI-compatible endpoint for integration with the chat interface.

    This endpoint accepts the standard OpenWebUI message format and
    returns results in a format that OpenWebUI can display.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    # Get the last user message
    last_message = None
    for msg in reversed(request.messages):
        if msg.get("role") == "user":
            last_message = msg.get("content", "")
            break

    if not last_message:
        raise HTTPException(status_code=400, detail="No user message found")

    # Generate SQL and execute
    try:
        sql = await generate_sql(
            app.state.vanna,
            last_message,
            "openwebui",
            app.state.conversation_history,
            None,
        )

        results = await execute_sql(sql)

        # Format response for OpenWebUI
        response_text = f"**Generated SQL:**\n```sql\n{sql}\n```\n\n"

        if results:
            response_text += "**Results:**\n"
            # Format as markdown table
            if isinstance(results, list) and len(results) > 0:
                if isinstance(results[0], dict):
                    headers = list(results[0].keys())
                    response_text += "| " + " | ".join(headers) + " |\n"
                    response_text += "| " + " | ".join(["---"] * len(headers)) + " |\n"
                    for row in results[:50]:  # Limit to 50 rows
                        response_text += (
                            "| "
                            + " | ".join(str(row.get(h, "")) for h in headers)
                            + " |\n"
                        )
                    if len(results) > 50:
                        response_text += f"\n*Showing 50 of {len(results)} results*"
                else:
                    response_text += str(results)
        else:
            response_text += "*No results returned*"

        # Store in history
        if "openwebui" not in app.state.conversation_history:
            app.state.conversation_history["openwebui"] = []
        app.state.conversation_history["openwebui"].append(
            {"question": last_message, "sql": sql, "success": True}
        )

        return {
            "model": request.model,
            "message": {"role": "assistant", "content": response_text},
        }

    except Exception as e:
        logger.error(f"OpenWebUI endpoint error: {e}")
        return {
            "model": request.model,
            "message": {
                "role": "assistant",
                "content": f"Error processing your question: {str(e)}\n\nPlease try rephrasing your question or be more specific about the data you're looking for.",
            },
        }


@app.post("/train")
async def train_vanna(request: TrainRequest):
    """
    Train Vanna AI with DDL, documentation, or example queries.

    This helps Vanna understand your database schema and business context.
    """
    vanna = app.state.vanna
    trained_items = []

    try:
        if request.ddl:
            vanna.train(ddl=request.ddl)
            trained_items.append("ddl")

        if request.documentation:
            vanna.train(documentation=request.documentation)
            trained_items.append("documentation")

        if request.sql and request.question:
            vanna.train(question=request.question, sql=request.sql)
            trained_items.append("question-sql pair")

        return {"status": "success", "trained": trained_items}
    except Exception as e:
        logger.error(f"Training error: {e}")
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@app.get("/schema")
async def get_schema():
    """Get the current database schema information."""
    try:
        metadata = await get_table_metadata()
        return {"schema": metadata}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clear-history")
async def clear_history(session_id: Optional[str] = None):
    """Clear conversation history for a session or all sessions."""
    if session_id:
        if session_id in app.state.conversation_history:
            del app.state.conversation_history[session_id]
            return {"status": "cleared", "session_id": session_id}
        return {"status": "not_found", "session_id": session_id}
    else:
        app.state.conversation_history = {}
        return {"status": "all_cleared"}


@app.get("/training-data")
async def get_training_data():
    """Get the current training data stored in Vanna."""
    try:
        vanna = app.state.vanna
        training_data = vanna.get_training_data()
        return {"training_data": training_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
