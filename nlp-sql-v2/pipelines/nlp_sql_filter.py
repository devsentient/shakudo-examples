"""
OpenWebUI Pipeline Filter for NLP-to-SQL Routing

This filter intercepts messages that look like database queries
and routes them to the Vanna AI microservice for SQL generation
and execution.

To install in OpenWebUI:
1. Go to Admin Panel > Pipelines
2. Create a new pipeline
3. Paste this code
4. Configure the VANNA_API_URL valve
"""

import os
import re
import httpx
from typing import Optional, Callable, Awaitable, Any
from pydantic import BaseModel, Field


class Pipeline:
    """
    NLP-to-SQL Pipeline Filter for OpenWebUI.

    This pipeline detects database-related queries and routes them
    to the Vanna AI microservice for SQL generation and execution.
    """

    class Valves(BaseModel):
        """Configuration valves for the pipeline."""

        pipelines: list = Field(
            default=["*"], description="List of pipelines to apply this filter to"
        )
        priority: int = Field(
            default=0, description="Priority of this filter (lower = higher priority)"
        )
        vanna_api_url: str = Field(
            default="http://nlp-sql-v2.hyperplane-pipelines.svc.cluster.local:8787",
            description="URL of the Vanna AI microservice",
        )
        enable_sql_routing: bool = Field(
            default=True, description="Enable routing SQL-like queries to Vanna"
        )
        sql_keywords: list = Field(
            default=[
                "show",
                "list",
                "find",
                "search",
                "get",
                "what",
                "how many",
                "count",
                "total",
                "sum",
                "average",
                "who",
                "which",
                "where",
                "donation",
                "donor",
                "membership",
                "account",
                "contact",
                "payment",
                "campaign",
                "database",
                "table",
                "record",
                "field",
            ],
            description="Keywords that trigger SQL routing",
        )

    def __init__(self):
        self.name = "NLP-to-SQL Router"
        self.valves = self.Valves()

    def _is_sql_query(self, message: str) -> bool:
        """
        Determine if a message should be routed to the SQL service.

        Uses keyword matching and pattern detection to identify
        database-related queries.
        """
        if not self.valves.enable_sql_routing:
            return False

        message_lower = message.lower()

        # Check for explicit SQL request
        if "sql" in message_lower or "query" in message_lower:
            return True

        # Check for database-related keywords
        keyword_count = sum(
            1 for kw in self.valves.sql_keywords if kw.lower() in message_lower
        )

        # If 2+ keywords match, likely a database query
        if keyword_count >= 2:
            return True

        # Check for common question patterns about data
        data_patterns = [
            r"how many .*(donor|account|contact|payment|member)",
            r"list .*(all|the) .*(donor|account|contact|payment|member)",
            r"show .*(donor|account|contact|payment|member)",
            r"what is .*(membership|donation|payment|balance)",
            r"search for .*(donor|account|contact)",
            r"find .*(donor|account|contact|payment)",
            r"who .*(donated|gave|contributed)",
        ]

        for pattern in data_patterns:
            if re.search(pattern, message_lower):
                return True

        return False

    async def _call_vanna(self, question: str, session_id: str) -> dict:
        """Call the Vanna AI microservice to generate and execute SQL."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.valves.vanna_api_url}/ask",
                json={"question": question, "session_id": session_id, "execute": True},
            )
            response.raise_for_status()
            return response.json()

    def _format_results(self, data: dict) -> str:
        """Format the Vanna response for display in OpenWebUI."""
        response_text = ""

        # Show the SQL
        if data.get("sql"):
            response_text += f"**Generated SQL:**\n```sql\n{data['sql']}\n```\n\n"

        # Show results
        if data.get("error"):
            response_text += f"**Error:** {data['error']}\n"
        elif data.get("results"):
            results = data["results"]
            response_text += "**Results:**\n"

            if isinstance(results, list) and len(results) > 0:
                if isinstance(results[0], dict):
                    # Format as markdown table
                    headers = list(results[0].keys())
                    response_text += "| " + " | ".join(headers) + " |\n"
                    response_text += "| " + " | ".join(["---"] * len(headers)) + " |\n"

                    for row in results[:50]:  # Limit to 50 rows
                        values = [
                            str(row.get(h, ""))[:50] for h in headers
                        ]  # Truncate long values
                        response_text += "| " + " | ".join(values) + " |\n"

                    if len(results) > 50:
                        response_text += f"\n*Showing 50 of {len(results)} results*\n"

                    response_text += f"\n*Total: {len(results)} records*\n"
                else:
                    response_text += str(results)
            else:
                response_text += "*No results found*\n"

        # Show follow-up suggestions
        if data.get("follow_up_suggestions"):
            response_text += "\n**Suggested follow-up questions:**\n"
            for suggestion in data["follow_up_suggestions"]:
                response_text += f"- {suggestion}\n"

        return response_text

    async def inlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[Any], Awaitable[None]]] = None,
    ) -> dict:
        """
        Inlet filter - processes messages before they reach the LLM.

        If the message looks like a database query, route it to Vanna
        and return the results directly instead of sending to the LLM.
        """
        messages = body.get("messages", [])

        if not messages:
            return body

        # Get the last user message
        last_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break

        if not last_message:
            return body

        # Check if this is a SQL-related query
        if self._is_sql_query(last_message):
            try:
                # Generate session ID from user
                session_id = (
                    __user__.get("id", "default")[:8] if __user__ else "default"
                )

                # Emit status
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": "Generating SQL query...",
                                "done": False,
                            },
                        }
                    )

                # Call Vanna
                result = await self._call_vanna(last_message, session_id)

                # Format response
                formatted = self._format_results(result)

                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {"description": "Query complete", "done": True},
                        }
                    )

                # Replace the last message with the formatted result
                # This will make OpenWebUI display our result instead of
                # sending to the LLM
                body["__sql_result__"] = formatted

            except Exception as e:
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": f"SQL Error: {str(e)}",
                                "done": True,
                            },
                        }
                    )

        return body

    async def outlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[Any], Awaitable[None]]] = None,
    ) -> dict:
        """
        Outlet filter - processes the response before it's sent to the user.

        If we have a SQL result from inlet, inject it into the response.
        """
        if "__sql_result__" in body:
            # We handled this in inlet - inject our result
            body["messages"] = body.get("messages", [])
            body["messages"].append(
                {"role": "assistant", "content": body.pop("__sql_result__")}
            )

        return body
