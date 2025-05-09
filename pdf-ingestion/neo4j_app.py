"""Context Retrieval FastAPI application."""

import logging
import re
from typing import List, Literal

import uvicorn
from fastapi import FastAPI, HTTPException
from neo4j import GraphDatabase
from pydantic import BaseModel
from llm_provider import llm_embedding
from neo4j_config import NEO4J_PARAMS
from neo4j_query import NEO4J_QUERY_GENERAL, NEO4J_QUERY_SIBLING

# Initialize the FastAPI app with custom docs URLs
app = FastAPI(
    title="Neo4j Context API",
    docs_url="/swagger",
    redoc_url="/redoc-custom",
    openapi_url="/openapi.json",
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("neo4j_fetch_context_api")


# Initialize the Neo4j driver
def initialize_neo4j_driver():
    try:
        return GraphDatabase.driver(
            NEO4J_PARAMS["URL"], auth=(NEO4J_PARAMS["user"], NEO4J_PARAMS["password"])
        )
    except Exception as e:
        logger.error("Failed to initialize the Neo4j driver: %s", e)
        raise RuntimeError("Could not connect to the Neo4j database.") from e


neo4j_driver = initialize_neo4j_driver()


def extract_response_content(response):
    """Extract content from the response object."""
    return getattr(response, "content", response)


def execute_cypher_query(query: str, parameters: dict) -> List[dict]:
    """Run a Cypher query against the Neo4j database."""
    try:
        with neo4j_driver.session() as session:
            return session.read_transaction(
                lambda tx: [record.data() for record in tx.run(query, parameters)]
            )
    except Exception as e:
        logger.error("Neo4j query failed: %s", e)
        raise HTTPException(status_code=500, detail="Database query failed.")



def format_record_to_chunk(record):
    """Format a single database record into a dify-readable(LLM) chunk."""
    print(record)
    chunk_n = int(record['chunk_n'])
    ns = list(range(chunk_n-1,chunk_n+2)) if record["is_last"] == 'False' else list(range(chunk_n-2,chunk_n+1))
    print("ns", ns)
    query_parameters = {
            "file_name": record['file_name'],
            "ns": [str(n) for n in ns],
        }
    results = execute_cypher_query(NEO4J_QUERY_SIBLING, query_parameters)
    print(f"{round(record.get('score'),3)}")
    return ({
        "Score": f"{round(record.get('score'),3)}",
        "Reference": f"{record.get('file_name')}",
        "Content": "".join([r.get('text') for r in results])
     }
    )


async def fetch_contextual_data(
    query: str
) -> str:
    """Fetch contextual data from the database based on the user query."""
    try:
        # Generate embedding for the query
        embedding = llm_embedding(query)
        query_parameters = {
            "prompt_embedding": embedding,
            "inner_K": 3,
        }
        
        # Execute the query and format results
        results = execute_cypher_query(NEO4J_QUERY_GENERAL, query_parameters)
        formatted_chunks = [format_record_to_chunk(record) for record in results]
        return formatted_chunks
    except Exception as e:
        logger.error("Failed to fetch contextual data: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch contextual data.")


class ContextRequestModel(BaseModel):
    """Request model for the /context endpoint."""
    query: str


@app.post("/context")
async def fetch_context(request: ContextRequestModel):
    """Endpoint to handle user queries and return contextual data."""
    try:
        # Normalize input: Replace None or "None" with an empty string

        formatted_context = await fetch_contextual_data(
            query=request.query,
        )
        return {"response": formatted_context}
    except HTTPException as e:
        logger.error("Error in /context endpoint: %s", e.detail)
        raise
    except Exception as e:
        logger.error("Unexpected error in /context endpoint: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error.")


if __name__ == "__main__":
    # For production, consider using Gunicorn with Uvicorn workers:
    # gunicorn -k uvicorn.workers.UvicornWorker -w 4 neo4j_app:app
    uvicorn.run(app, host="0.0.0.0", port=8000)
