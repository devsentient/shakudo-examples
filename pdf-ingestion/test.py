from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from typing import List, Dict, Tuple
from langchain_community.embeddings import OpenAIEmbeddings
import logging

# Logger setup
logger = logging.getLogger(__name__)

NEO4J_PARAMS = {
    "URL": os.environ.get(
        "NEO4J_URL", "neo4j://neo4j.hyperplane-neo4j.svc.cluster.local:7687"
    ),
    "user": os.environ.get("NEO4J_USER", "neo4j"),
    "password": os.environ.get("NEO4J_PASSWORD", "Shakudo312!"),
}

driver = GraphDatabase.driver(
    NEO4J_PARAMS["URL"], auth=(NEO4J_PARAMS["user"], NEO4J_PARAMS["password"])
)


def get_all_chunks_with_parent_info():
    query = """
    MATCH (f:File)-[:HAS_CHUNK]->(c:Chunk)
    RETURN c.id AS chunk_id, f.company_name AS company_name, f.company_code AS company_code
    """
    with driver.session() as session:
        result = session.run(query)
        chunks_info = []
        for record in result:
            chunks_info.append(
                {
                    "chunk_id": record["chunk_id"],
                    "company_name": record["company_name"],
                    "company_code": record["company_code"],
                }
            )
        return chunks_info


# OpenAI API Key (make sure it is loaded from your environment)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set up OpenAI embedding model (text-embedding-ada-002)
embeddings = OpenAIEmbeddings(
    model="text-embedding-ada-002", openai_api_key=OPENAI_API_KEY
)


def embed_text_with_gpt(text: str) -> List[float]:
    """
    Embeds text using OpenAI embeddings.
    """
    try:
        return embeddings.embed_query(text)
    except Exception as e:
        logger.error(f"Error embedding text: {e}")
        return []


def generate_prompt_embedding(prompt: str) -> List[float]:
    """
    Generates the embedding for a given prompt using OpenAI's embeddings.
    """
    try:
        prompt_embedding = embeddings.embed_query(prompt)
        return prompt_embedding
    except Exception as e:
        logger.error(f"Error generating prompt embedding: {e}")
        return []


# Neo4j query to fetch chunks and calculate cosine similarity between chunk embedding and prompt embedding

NEO4J_QUERY_GENERAL = """
    MATCH (f:File)-[:HAS_CHUNK]->(c:Chunk)
    WHERE 
        (
            $company_name = "" OR 
            toLower(f.company_name) CONTAINS toLower($company_name) OR
            apoc.text.fuzzyMatch(
                toLower(f.company_name), 
                toLower($company_name)
            ) > 0.8
        ) OR
        (
            $company_code = "" OR 
            toLower(f.company_code) CONTAINS toLower($company_code) OR
            apoc.text.fuzzyMatch(
                toLower(f.company_code), 
                toLower($company_code)
            ) > 0.8
        )
    WITH c, vector.similarity.cosine(c.embedding, $prompt_embedding) AS score
    ORDER BY score DESC
    LIMIT $inner_K 
    WITH c, score
    MATCH (f:File)-[:HAS_CHUNK]->(c)
    WITH f, MAX(score) AS max_score ,c
    RETURN c.text AS text, c.file_name AS file_name, max_score AS score
    ORDER BY score DESC
"""


def run_query(
    session, company_name: str, company_code: str, prompt: str, inner_K: int = 5
):
    """
    Runs the general query to match chunks based on cosine similarity with the prompt.
    """
    try:
        prompt_embedding = generate_prompt_embedding(prompt)

        if not prompt_embedding:
            logger.info("Error generating prompt embedding. Exiting.")
            return []

        # Prepare the parameters to run the query
        params = {
            "company_name": company_name,
            "company_code": company_code,
            "prompt_embedding": prompt_embedding,
            "inner_K": inner_K,
        }

        # Execute the query
        result = session.run(NEO4J_QUERY_GENERAL, params)
        return result

    except Exception as e:
        logger.info(f"Error running the query: {e}")
        return []


# Example function to process and match using a prompt
def process_and_match_files(
    prompt: str, company_name: str = "", company_code: str = ""
):
    """
    Process the files in the database and return matches based on the given prompt.
    """

    with driver.session() as session:
        matches = run_query(session, company_name, company_code, prompt)
        logger.info((matches.to_df()))
        if matches:
            for match in matches:
                logger.info(
                    f"Found match: {match['file_name']} with score {match['score']}"
                )
        else:
            logger.info("No matches found.")


# # # Example usage
# chunks_info = get_all_chunks_with_parent_info()
# for chunk in chunks_info:
#     if chunk['company_code'] == "":
#         logger.info(f"Chunk ID: {chunk['chunk_id']}")
#         logger.info(f"Company Name: {chunk['company_name']}")
#         logger.info(f"Company Code: {chunk['company_code']}")

# Example usage
if __name__ == "__main__":
    prompt = "Do you know about united airlines?"
    process_and_match_files(prompt, company_name="", company_code="")
