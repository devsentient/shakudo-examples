from glob import glob
from tqdm import tqdm
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from common import graph, embedding_model
import os

DATADIR = os.path.join(sys.argv[1], 'txt')
files = glob(f"{DATADIR}*.txt")
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
      "filename": filename
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
  "CALL db.index.vector.createNodeIndex('chunk', 'Chunk', 'embedding', $dimension, 'cosine')",
  {"dimension": 768}
)

graph.query(
  "CALL db.index.vector.createNodeIndex('page', 'Page', 'embedding', $dimension, 'cosine')",
  {"dimension": 768}
)