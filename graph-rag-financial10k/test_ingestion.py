
from common import embedding_model, driver

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