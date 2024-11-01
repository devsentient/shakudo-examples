import os
from neo4j import GraphDatabase
from langchain_community.embeddings import OllamaEmbeddings

OLLAMA_EMBEDDING_MODEL='nomic-embed-text:latest'
OLLAMA_EMBEDDING_ENDPOINT="http://ollama-nomic.hyperplane-ollama.svc.cluster.local:11434"

embedding_model = OllamaEmbeddings(base_url=OLLAMA_EMBEDDING_ENDPOINT, 
                                   model=OLLAMA_EMBEDDING_MODEL, num_ctx=8196)

neo4j_params = {
  "URL": os.environ.get('NEO4J_URL', "neo4j://neo4j.hyperplane-neo4j.svc.cluster.local:7687"),
  "user": os.environ.get('NEO4J_USER', "neo4j"),
  "password": os.environ.get('NEO4J_PASSWORD', "Shakudo312!")
}

driver = GraphDatabase.driver(
    f"{neo4j_params['URL']}",
    auth=(neo4j_params['user'], neo4j_params['password'])
)

neo4j_query = """
  CALL {
    match (page_node: Page)
    where (
      $filename in labels(page_node)
    )
    with page_node,
        vector.similarity.cosine(page_node.embedding, $prompt_embedding) as score
    order by score desc
    limit $inner_K
    return page_node, score
    
    union all
    
    match (chunk_node: Chunk)-[:HAS_CHILD]->(page_node:Page)
    where (
      $filename in labels(chunk_node)
    )
    with page_node, vector.similarity.cosine(chunk_node.embedding, $prompt_embedding) as score
    order by score desc
    limit $inner_K
    return page_node, score
  }
  
  with page_node, avg(score) as avg_score
  return page_node.text as text,
        page_node.page_number as page_number,
        avg_score as score
  order by avg_score desc
  limit $K
"""


def run_query(tx, neo4j_query, parameters):
  result = tx.run(neo4j_query, parameters)
  return [record.data() for record in result]

with driver.session() as sess:
  question = "give me sale revenue"
  embedding = embedding_model.embed_query(question)
  parameters = {
    'prompt_embedding': embedding,
    'K': 5,
    'inner_K': 5,
    'filename': 'QuarterlyActivitiesJun2023'
  }
  result = sess.execute_read(run_query, neo4j_query, parameters)
result = sorted(result, key=lambda x: x['score'], reverse=True)

print(result)