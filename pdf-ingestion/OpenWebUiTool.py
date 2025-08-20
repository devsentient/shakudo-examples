"""
title: Query Graph Rag
author: Shakudo
author_url: https://github.com/shakudo
version: 0.1.0
"""

import os
import requests

### SHAKUDO RAG TOOL EXAMPLE ###

# Note: This is a proof-of-concept (POC) tool designed to demonstrate the 
# potential of the GraphRag tool. Please be aware that the script provides 
# basic functionality and should not be used as a performance benchmark.

# GraphRag's performance may vary significantly depending on factors such as 
# document type, the choice of LLM model, and the relation logic used. 
# These aspects can be easily optimized through fine-tuning and adaptation to 
# specific document categories.

###

class Tools:
    def __init__(self):
        self.citation = True
        self.microsvc = "http://hyperplane-service-e85664.hyperplane-pipelines.svc.cluster.local:8787" # TODO REPLACE WITH INTERNAL URL

    async def query_dataset(self, user_query: str, __event_emitter__=None) -> str:
        """
        Query with the user question, always use this function.
        :param user_query: the query by the user.
        """
        body = {"query": user_query}
        await __event_emitter__(
            {
                "type": "status",  # We set the type here
                "data": {
                    "description": "Query sent to GraphRAG backend...",
                    "done": False,
                    "hidden": False,
                },
                # Note done is False here indicating we are still emitting statuses
            }
        )
        headers = {"Content-Type": "application/json"}
        URL = self.microsvc + "/context"
        response = requests.post(URL, headers=headers, json=body)
        await __event_emitter__(
            {
                "type": "status",  # We set the type here
                "data": {
                    "description": "Invoking Graph Rag Backend ...",
                    "done": False,
                    "hidden": False,
                },
                # Note done is False here indicating we are still emitting statuses
            }
        )
        if response.status_code == 200:
            result = response.json()["response"]
            # Parse the JSON response and pretty print it
            await __event_emitter__(
                {
                    "type": "status",  # We set the type here
                    "data": {
                        "description": "Graph RAG Result parsed",
                        "done": True,
                        "hidden": False,
                    },
                    # Note done is False here indicating we are still emitting statuses
                }
            )

            return "\n".join([x["Content"] for x in result])
        else:
            await __event_emitter__(
                {
                    "type": "status",  # We set the type here
                    "data": {
                        "description": "Graph RAG Tool having an Error",
                        "done": True,
                        "hidden": False,
                    },
                    # Note done is False here indicating we are still emitting statuses
                }
            )
            return f"Error: {response.status_code} - {response.text}"
