import os
from langchain_community.graphs import Neo4jGraph
from neo4j import GraphDatabase

from langchain_community.embeddings.ollama import OllamaEmbeddings
from langchain_community.chat_models.ollama import ChatOllama
from langchain_community.embeddings.openai import OpenAIEmbeddings
from langchain_community.chat_models.openai import ChatOpenAI

OLLAMA_EMBEDDING_MODEL=os.environ.get("OLLAMA_EMBEDDING_MODEL", 'nomic-embed-text:latest')
OLLAMA_EMBEDDING_ENDPOINT=os.environ.get("OLLAMA_EMBEDDING_ENDPOINT", "http://ollama.hyperplane-ollama.svc.cluster.local:11434")
OLLAMA_CHAT_MODEL=os.environ.get("OLLAMA_CHAT_MODEL", 'qwen2.5:14b-instruct-q4_K_M')
OLLAMA_CHAT_ENDPOINT=os.environ.get("OLLAMA_CHAT_ENDPOINT", "http://ollama.hyperplane-ollama.svc.cluster.local:11434")
#=========================|
#  Configure Neo4j        |
#=========================|

neo4j_params = {
  "URL": os.environ.get('NEO4J_URL', "neo4j://neo4j.hyperplane-neo4j.svc.cluster.local:7687"),
  "user": os.environ.get('NEO4J_USER', "neo4j"),
  "password": os.environ.get('NEO4J_PASSWORD', "") # SET THIS
}

driver = GraphDatabase.driver(
    f"{neo4j_params['URL']}",
    auth=(neo4j_params['user'], neo4j_params['password'])
)


graph = Neo4jGraph(
  url=neo4j_params['URL'],
  username=neo4j_params['user'],
  password=neo4j_params['password']
)

#=========================|
#  Configure Ollama       |
#=========================|

embedding_model = OllamaEmbeddings(base_url=OLLAMA_EMBEDDING_ENDPOINT, 
                                   model=OLLAMA_EMBEDDING_MODEL, 
                                   num_ctx=8196)
chat_model = ChatOllama(base_url=OLLAMA_CHAT_ENDPOINT,
                        model=OLLAMA_CHAT_MODEL,
                        num_ctx=8196)


#=========================|
#  Configure OpenAI       |
#=========================|

### For OpenAI user, please set OPENAI_API_KEY as your environment variable and uncomment the following lines
#   embedding_model = OpenAIEmbeddings(model='text-embedding-ada-002')
#   chat_model = ChatOpenAI(model='gpt-4o')
