import os, re
from fastapi import FastAPI, Request
from neo4j import GraphDatabase
from langchain_community.embeddings.ollama import OllamaEmbeddings
from langchain_community.chat_models.ollama import ChatOllama
from langchain_community.embeddings.openai import OpenAIEmbeddings
from langchain_community.chat_models.openai import ChatOpenAI
from prompts import PROMPT_QWEN, PROMPT_OPENAI

app = FastAPI()




neo4j_params = {
  "URL": os.environ.get('NEO4J_URL', "neo4j://neo4j.hyperplane-neo4j.svc.cluster.local:7687"),
  "user": os.environ.get('NEO4J_USER', "neo4j"),
  "password": os.environ.get('NEO4J_PASSWORD', "Shakudo312!")
}


driver = GraphDatabase.driver(
    f"{neo4j_params['URL']}",
    auth=(neo4j_params['user'], neo4j_params['password'])
)


OLLAMA_EMBEDDING_MODEL='nomic-embed-text:latest'
OLLAMA_EMBEDDING_ENDPOINT="http://ollama-cpu.hyperplane-ollama.svc.cluster.local:11434"

embedding_model = OllamaEmbeddings(base_url=OLLAMA_EMBEDDING_ENDPOINT, 
                                   model=OLLAMA_EMBEDDING_MODEL, 
                                   num_ctx=8196)
chat_model = ChatOllama(base_url='http://ollama.hyperplane-ollama.svc.cluster.local:11434',
                        model='qwen2.5:14b-instruct-q4_K_M',
                        num_ctx=8196)

### For OpenAI users, please set the value for `OPENAI_API_KEY` environment variable and uncomment these following lines:
#   embedding_model = OpenAIEmbeddings(model='text-embedding-ada-002')
#   chat_model = ChatOpenAI(model='gpt-4o')


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


async def retrieve_context(query, document):
  embedding = await embedding_model.aembed_query(query)
  parameters = {
    'prompt_embedding': embedding,
    'K': 5,
    'inner_K': 5,
    'filename': document
  }
  
  with driver.session() as sess:
    result = sess.run(neo4j_query, parameters)
  
  result = sorted(result, key=lambda x: x['score'], reverse=True)
  
  matched_texts =  "  \n\n---\n\n  ".join([
              f" ON PAGE {pl['page_number']}: \n"
              + re.sub(r' {3,}', ' ', pl["text"]) +
              f"\n ON PAGE: {pl['page_number']}"
              for pl in result])
  return matched_texts
  


@app.get('/answer')
async def get_answer(req: Request, query: str, document: str):
  contexts = await retrieve_context(query, document)
  
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