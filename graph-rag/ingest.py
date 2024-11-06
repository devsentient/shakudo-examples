import os
from langchain_community.graphs import Neo4jGraph
from neo4j import GraphDatabase
from glob import glob
from tqdm import tqdm
from langchain_core.documents import Document
from langchain_community.embeddings.ollama import OllamaEmbeddings
from langchain_community.chat_models.ollama import ChatOllama

from langchain_text_splitters import RecursiveCharacterTextSplitter
from prompts import PROMPT_QUESTION


def uniform_grab_value(x):
  if hasattr(x, "content"):
    value = x.content
  else:
    value = x
  return value

neo4j_params = {
  "URL": os.environ.get('NEO4J_URL', "neo4j://neo4j.hyperplane-neo4j.svc.cluster.local:7687"),
  "user": os.environ.get('NEO4J_USER', "neo4j"),
  "password": os.environ.get('NEO4J_PASSWORD', "Shakudo312!")
}

graph = Neo4jGraph(
  url=neo4j_params['URL'],
  username=neo4j_params['user'],
  password=neo4j_params['password']
)

driver = GraphDatabase.driver(
  f"{neo4j_params['URL']}",
  auth=(neo4j_params['user'], neo4j_params['password'])
)

try: 
  graph.query("RETURN 1;")
  print("Connection to neo4j is successful.")
except Exception as e:
  print("Connection to neo4j is unsuccessful. Please check your configurations. Trace: \n")
  raise Exception(str(e))
  


OLLAMA_EMBEDDING_MODEL='nomic-embed-text:latest'
OLLAMA_EMBEDDING_ENDPOINT="http://ollama-nomic.hyperplane-ollama.svc.cluster.local:11434"

OLLAMA_LLM = 'qwen2.5:14b-instruct-q4_K_M'
OLLAMA_LLM_ENDPOINT = "http://ollama.hyperplane-ollama.svc.cluster.local:11434"

embedding_model = OllamaEmbeddings(base_url=OLLAMA_EMBEDDING_ENDPOINT, model=OLLAMA_EMBEDDING_MODEL, num_ctx=8192)
llm_model = ChatOllama(base_url=OLLAMA_LLM_ENDPOINT, model=OLLAMA_LLM, num_ctx=8192)

embedding_model = OllamaEmbeddings(base_url=OLLAMA_EMBEDDING_ENDPOINT, 
                                   model=OLLAMA_EMBEDDING_MODEL, 
                                   num_ctx=8196)



files = glob('***')
p_text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=100)
c_text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)

for file_path in tqdm(files):
  filename = file_path.split('/')[-1].split('.')[0]
  print(filename)
  with open(file_path) as fp:
    text = fp.read()

  pages = text.split('\n\n' + '-' * 16 + '\n\n')
  
  parent_docs = []
  for i, page in enumerate(pages):
    parent_docs.append(Document(page_content=page, metadata={'page_number': i + 1}))
  
  p_doc_chunks = p_text_splitter.split_documents(parent_docs)

  for id, p_chunk in enumerate(p_doc_chunks):
    
    p_embedding = embedding_model.embed_query(p_chunk.page_content)
    child_documents = c_text_splitter.split_documents([p_chunk])
    
    formatted_prompt = PROMPT_QUESTION.format_prompt(document=p_chunk.page_content, name=filename)
    responses = uniform_grab_value(llm_model.invoke(formatted_prompt))
    questions = responses.splitlines()
    
    q_nodes = []
    for iq, question in enumerate(questions):
      q_embedding = embedding_model.embed_query(question)
      q_data = {
        'text': question,
        'id': f'{filename}-{id}-q{iq}',
        'embedding': q_embedding
      }
      q_nodes.append(q_data)
    
    children = []
    for ic, c in enumerate(child_documents):
      c_embedding = embedding_model.embed_query(c.page_content)
      child_data = {
        'text': c.page_content,
        'id': f"{filename}-{id}-{ic}",
        'embedding': c_embedding,
      }
      children.append(child_data)

    parent = {
      "text": p_chunk.page_content,
      "page_number": p_chunk.metadata['page_number'],
      "embedding": p_embedding,
      "children": children,
      "id": f'{filename}-{id}',
      "filename": filename,
      "questions": q_nodes,
    }
    
    graph.query(
      f"""
      MERGE (p:Page {{id: $id}})
      SET p.text = $text,
          p.page_number = $page_number,
          p:{filename}
      WITH p
      CALL db.create.setVectorProperty(p, 'embedding', $embedding)
      YIELD node
      WITH p
      UNWIND $children AS chunk
      MERGE (c:Chunk {{id: chunk.id}})
      SET c.text = chunk.text,
          c:{filename}
      MERGE (c)<-[:HAS_CHILD]-(p)
      WITH c, chunk
      CALL db.create.setVectorProperty(c, 'embedding', chunk.embedding)
      YIELD node
      RETURN count(*)
      """,
      parent
    )
  
  graph.query(
      f"""
      MERGE (p:Page {{id: $id}})
      WITH p
      UNWIND $questions as question
      MERGE (q: Question {{id: question.id}})
      SET q.text = question.text,
          q:avenue,
          q:{filename}
      MERGE (q)<-[:HAS_QUESTION]-(p)
      WITH q, question
      CALL db.create.setVectorProperty(q, 'embedding', question.embedding)
      YIELD node
      RETURN count(*)
      """,
      parent
    )
    
graph.query(
  "CALL db.index.vector.createNodeIndex('chunk', 'Chunk', 'embedding', $dimension, 'cosine')",
  {"dimension": 768}
)

graph.query(
  "CALL db.index.vector.createNodeIndex('page', 'Page', 'embedding', $dimension, 'cosine')",
  {"dimension": 768}
)

graph.query(
  "CALL db.index.vector.createNodeIndex('question', 'Question', 'embedding', $dimension, 'cosine')",
  {"dimension": 768}
)