import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple

import colorlog
from langchain_text_splitters import RecursiveCharacterTextSplitter

from llm_provider import async_llm_embedding

from neo4j import GraphDatabase
from neo4j_config import NEO4J_PARAMS
from neo4j_query import chunk_query, create_query


# Configure the color-coded logger
def setup_logger() -> logging.Logger:
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "white",
                "INFO": "cyan",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
    )
    logger = logging.getLogger("IngestionLogger")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger


logger = setup_logger()
# Neo4j driver initialization
driver = GraphDatabase.driver(
    NEO4J_PARAMS["URL"], auth=(NEO4J_PARAMS["user"], NEO4J_PARAMS["password"])
)

# ThreadPool for blocking tasks
executor = ThreadPoolExecutor(max_workers=4)


def split_text_on_boundary(
    text: str, chunk_size: int = 500, chunk_overlap: int = 50
) -> List[str]:
    """
    Splits text into chunks with specified size and overlap, preferring natural boundaries.
    """
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="r50k_base", 
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return splitter.split_text(text)

def create_parent_node(
    file_name: str,
    children: List[Dict],
    content: str,
) -> Dict:
    """
    Creates a parent node dictionary for Neo4j ingestion.
    """
    return {
        "children": children,
        "id": file_name,
        "text": content,
        "file_name": file_name,
    }


def execute_create_query(session, parent: Dict):
    """
    Executes Neo4j queries to create nodes and relationships.
    """
    try:
        session.run(create_query, parent)
        session.run(chunk_query, parent)
    except Exception as e:
        logger.error(f"Error executing queries: {e}")


async def process_chunks(
    chunks: List[str],
    file_name: str,
    session,
    content: str,
):
    """
    Processes and embeds text chunks, creating parent-child relationships.
    """
    try:
        logger.info(f"Ingesting {len(chunks)} chunks..")
        child_embeddings = await asyncio.gather(
            *[async_llm_embedding(chunk, logger=logger) for chunk in chunks]
        )
        logger.info("Embeded chunks.")
        children = [
            {"text": c, "embedding": embedding, 'chunk_n': f'{i}', 'is_last': f'{i==len(chunks)}'}
            for i, (c, embedding) in enumerate(zip(chunks, child_embeddings))
        ]
        parent_node = create_parent_node(
            file_name, children, content
        )
        execute_create_query(session, parent_node)
    except Exception as e:
        logger.error(f"Error processing chunks: {e}")


async def ingest_file(file_path: str):
    """
    Reads and processes a single file for ingestion.
    """
    try:
        with open(file_path, "r") as f:
            content = f.read()

        chunks = split_text_on_boundary(content)
        with driver.session() as session:
            await process_chunks(
                chunks, file_path.replace('.pdf', '').split('/')[-1], session, content
            )
    except Exception as e:
        logger.error(f"Error ingesting file {file_path}: {e}")


async def ingest_folder(folder_path: str):
    """
    Iterates through all files in a folder and ingests them asynchronously.
    """
    tasks = []
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".pdf.md"):
            file_path = os.path.join(folder_path, file_name)
            logger.info(f"Ingesting: {file_path}")
            tasks.append(ingest_file(file_path))

    await asyncio.gather(*tasks)


async def main():
    """
    Main entry point for the ingestion process.
    """
    folder_path = "cleanned_md"
    await ingest_folder(folder_path)


if __name__ == "__main__":
    asyncio.run(main())
