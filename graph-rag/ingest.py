from glob import glob
from tqdm import tqdm
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from common import graph, embedding_model, chat_model
from prompts import PROMPT_QU_QWEN
import os, sys

import logging
logging.getLogger("neo4j").setLevel(logging.ERROR)

PROJECT_TAG = 'financial10k'
DATADIR = os.path.join(sys.argv[1], 'txt')
files = glob(f"{DATADIR}/*.txt")
p_text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=100)
c_text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)

def uniform_grab_value(x):
  """Fetch the content/answer from the LLM model response."""
  return x.content if hasattr(x, "content") else x

for file_path in tqdm(files):
  filename = file_path.split('/')[-1].split('.')[0]
  filename = filename.lower().replace(" ", "_").replace("-", "_")
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
    
    # children
    children = []
    for ic, c in enumerate(child_documents):
      c_embedding = embedding_model.embed_query(c.page_content)
      child_data = {
        'text': c.page_content,
        'id': f"{filename}-{id}-{ic}",
        'embedding': c_embedding,
      }
      children.append(child_data)

    # questions
    formatted_prompt = PROMPT_QU_QWEN.format(
      document=p_chunk.page_content
    )
    questions = uniform_grab_value(chat_model.invoke(formatted_prompt)).splitlines()
    questions = [q for q in questions if q != '' and q.split('.')[0].isdigit()]

    if len(questions) != 5:
      questions = [""] * 5

    q_nodes = []
    q_embeddings = embedding_model.embed_documents(questions)
    for iq, (question, q_embedding) in enumerate(zip(questions, q_embeddings)):
      q_nodes.append({
        "text": question,
        "id": f"{filename}-{id}-q{iq}",
        "embedding": q_embedding,
      })
    
    # parent
    parent = {
      "text": p_chunk.page_content,
      "page_number": p_chunk.metadata['page_number'],
      "embedding": p_embedding,
      "children": children,
      "questions": q_nodes,
      "id": f'{filename}-{id}',
      "filename": filename, 
      "project": PROJECT_TAG
    }
    
    graph.query(
      """
      MERGE (p:Page {id: $id})
      SET p.text = $text,
          p.page_number = $page_number,
          p.filename = $filename,
          p.project = $project
      WITH p
      CALL db.create.setVectorProperty(p, 'embedding', $embedding)
      YIELD node
      WITH p
      UNWIND $children AS chunk
      MERGE (c:Chunk {id: chunk.id})
      SET c.text = chunk.text,
          c.filename = $filename,
          c.project = $project
      MERGE (c)<-[:HAS_CHILD]-(p)
      WITH c, chunk
      CALL db.create.setVectorProperty(c, 'embedding', chunk.embedding)
      YIELD node
      RETURN count(*)
      """,
      parent
    )

    graph.query(
      """
      MERGE (p:Page {id: $id})
      WITH p
      UNWIND $questions as question
      MERGE (q:Question {id: question.id})
      SET q.text = question.text,
          q.project = $project
      MERGE (q)<-[:HAS_QUESTION]-(p)
      WITH q, question
      CALL db.create.setVectorProperty(q, 'embedding', question.embedding)
      YIELD node
      RETURN count(*)
      """,
      parent,
    )

    print(f"Ingested page {id+1}/{len(p_doc_chunks)}")

    
# graph.query(
#   "CALL db.index.vector.createNodeIndex('chunk', 'Chunk', 'embedding', $dimension, 'cosine')",
#   {"dimension": 768}
# )

# graph.query(
#   "CALL db.index.vector.createNodeIndex('page', 'Page', 'embedding', $dimension, 'cosine')",
#   {"dimension": 768}
# )

# graph.query(
#   "CALL db.index.vector.createNodeIndex('question', 'Question', 'embedding', $dimension, 'cosine')",
#   {"dimension": 768}
# )