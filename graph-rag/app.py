import os, re
from fastapi import FastAPI, Request
from prompts import PROMPT_QWEN, PROMPT_OPENAI, PROMPT_EXTRACT2
from common import driver, embedding_model, chat_model

app = FastAPI()

def uniform_grab_value(x):
    if hasattr(x, "content"):
        value = x.content
    else:
        value = x
    return value


neo4j_query = """
  CALL {
    match (page_node: Page)
    where (
      $symbol in labels(page_node) OR
      page_node.symbol = $symbol OR 
      page_node.symbol IS NULL OR 
      page_node.symbol = '' OR 
      $symbol = ''
    )
    with page_node,
        vector.similarity.cosine(page_node.embedding, $prompt_embedding) as score
    order by score desc
    limit $inner_K
    return page_node, score
    
    union all
    
    match (chunk_node: Chunk)-[:HAS_CHILD]->(page_node:Page)
    where (
      $symbol in labels(chunk_node) OR 
      chunk_node.symbol = $symbol OR 
      chunk_node.symbol IS NULL OR 
      chunk_node.symbol = '' OR 
      $symbol = ''
    )
    with page_node, vector.similarity.cosine(chunk_node.embedding, $prompt_embedding) as score
    order by score desc
    limit $inner_K
    return page_node, score

    union all
    
    match (question_node: Question)-[:HAS_QUESTION]->(page_node:Page)
    where (
      $symbol in labels(question_node) OR 
      question_node.symbol = $symbol OR 
      question_node.symbol IS NULL OR 
      question_node.symbol = '' OR 
      $symbol = ''
    )
    with page_node, vector.similarity.cosine(question_node.embedding, $prompt_embedding) as score
    order by score desc
    limit $inner_K
    return page_node, score
  }
  
  with page_node, avg(score) as avg_score
  return page_node.text as text,
        page_node.page_number as page_number,
        avg_score as score,
        page_node.filename as filename
  order by avg_score desc
  limit $K
"""

def run_query(tx, neo4j_query, parameters):
  result = tx.run(neo4j_query, parameters)
  return [record.data() for record in result]


async def retrieve_context(query, symbol):
  embedding = await embedding_model.aembed_query(query)
  parameters = {
    'prompt_embedding': embedding,
    'K': 5,
    'inner_K': 5,
    'symbol': symbol
  }
  
  with driver.session() as sess:
    # results = sess.run(neo4j_query, parameters)
    results = run_query(sess, neo4j_query, parameters)
  result = sorted(results, key=lambda x: x['score'], reverse=True)

  matched_texts = "  \n\n---\n\n  ".join([
              f"FILENAME {pl['filename']} ON PAGE {pl['page_number']}: \n"
              + re.sub(r' {3,}', ' ', pl["text"]) +
              f"\n ON PAGE: {pl['page_number']}"
              for pl in result])
  return matched_texts


@app.get('/answer')
async def get_answer(req: Request, query: str):

  formatted_prompt = PROMPT_EXTRACT2.format(prompt=query)
  symbol = uniform_grab_value(chat_model.invoke(formatted_prompt))
  symbol = str(symbol).upper()
  print(f"Symbol extracted: {symbol}")

  contexts = await retrieve_context(query, symbol)
  formatted_prompt = PROMPT_QWEN.format_prompt(
    document=contexts,
    question=query
  )
  
  ### For OpenAI users, please uncomment these following lines to enable OpenAI Prompt
  #   formatted_prompt = PROMPT_OPENAI.format_prompt(
  #     document=contexts,
  #     question=query
  #   )
  
  response = uniform_grab_value(await chat_model.ainvoke(formatted_prompt))
  
  return {
    'response': response
  }
