import os
from langchain_community.graphs import Neo4jGraph
from neo4j import GraphDatabase
from glob import glob
from tqdm import tqdm

from langchain_text_splitters import RecursiveCharacterTextSplitter
from prompts import PROMPT_EXTRACT, PROMPT_QU_QWEN



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

def uniform_grab_value(x):
    if hasattr(x, "content"):
        value = x.content
    else:
        value = x
    return value

try: 
    graph.query("RETURN 1;")
    print("Connection to neo4j is successful.")
except Exception as e:
    print("Connection to neo4j is unsuccessful. Please check your configurations. Trace: \n")
    raise Exception(str(e))
  
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.chat_models import ChatOllama

OLLAMA_EMBEDDING_MODEL='nomic-embed-text:latest'
OLLAMA_EMBEDDING_ENDPOINT="http://ollama-nomic.hyperplane-ollama.svc.cluster.local:11434"

OLLAMA_LLM = 'qwen2.5:14b-instruct-q4_K_S'
OLLAMA_LLM_ENDPOINT = "http://ollama-sqlcoder.hyperplane-ollama.svc.cluster.local:11434"

embedding_model = OllamaEmbeddings(base_url=OLLAMA_EMBEDDING_ENDPOINT, 
                                   model=OLLAMA_EMBEDDING_MODEL, 
                                   num_ctx=8196)
llm_model = ChatOllama(base_url=OLLAMA_LLM_ENDPOINT, model=OLLAMA_LLM, num_ctx=32768)

from langchain_core.documents import Document

files = glob('/root/client/extractor_job_v2/md_files/*/*.md')
p_text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
c_text_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=100)

for file_path in tqdm(files):
  filename = file_path.split('/')[-1].split('.')[0]
  
  formatted_prompt = PROMPT_QU_QWEN.format(name=filename)
  date = uniform_grab_value(llm_model.invoke(formatted_prompt))
  
  with open(file_path) as fp:
    text = fp.read()

  pages = text.split('\n\n' + '-' * 16 + '\n\n')
  
  parent_docs = []
  for i, page in enumerate(pages):
    parent_docs.append(Document(page_content=page, metadata={'page_number': i + 1}))
  
  p_doc_chunks = p_text_splitter.split_documents(parent_docs)

  for id, p_chunk in enumerate(p_doc_chunks):
    formatted_prompt = PROMPT_QU_QWEN.format(doument=p_chunk.page_content, name=date)
    questions = uniform_grab_value(llm_model.invoke(formatted_prompt))
    questions = questions.splitlines()
    if len(questions) != 5:
      questions = [''] * 5
      
    q_nodes = []
    q_embeddings = embedding_model.embed_documents(questions)
    for iq, (question, q_embedding) in enumerate(zip([questions, q_embeddings])):
      q_data = {
        'text': question,
        'id': f'{filename}-{id}-q{iq}',
        'embedding': q_embedding
      }
      q_nodes.append(q_data)
      
    p_embedding = embedding_model.embed_query(p_chunk.page_content)
    child_documents = c_text_splitter.split_documents([p_chunk])
    
    children = []
    text_childrens = [c.page_content for c in child_documents]
    c_embeddings = embedding_model.embed_documents(text_childrens)
    for ic, (c_text, c_embedding) in enumerate(zip(text_childrens, c_embeddings)):
      child_data = {
        'text': c_text,
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
      "date": date
    }
    
    graph.query(
      f"""
      MERGE (p:Page {{id: $id}})
      SET p.text = $text,
          p.page_number = $page_number,
          p:{date}
      WITH p
      CALL db.create.setVectorProperty(p, 'embedding', $embedding)
      YIELD node
      WITH p
      UNWIND $children AS chunk
      MERGE (c:Chunk {{id: chunk.id}})
      SET c.text = chunk.text,
          c:{date}
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
          q:{date}
      MERGE (q)<-[:HAS_QUESTION]-(p)
      WITH q, question
      CALL db.create.setVectorProperty(q, 'embedding', question.embedding)
      YIELD node
      RETURN count(*)
      """,
      parent
    )
    print('question done')
    
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