

from langchain_community.embeddings import OllamaEmbeddings, OpenAIEmbeddings
from langchain_community.chat_models import ChatOpenAI, ChatOllama
from langchain.schema import HumanMessage
import os
import requests

def llm_invoke(context, force_json=False):
    if LLM_PROVIDER == 'OPENAI':
        llm = ChatOpenAI(
            openai_api_key=OPENAI_API_KEY,
            model_name=GENERATION_MODEL,
            model_kwargs={
                'response_format': {
                    'type': 'json_object',
                }
            } if force_json else {}
        )
    else: 
        llm = ChatOllama(
            base_url=OLLAMA_ENDPOINT, 
            model=GENERATION_MODEL)
    return llm.invoke(context)

def llm_embedding(text, force_json=False, logger=None):
    try:
        if LLM_PROVIDER == 'OPENAI':
            embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=OPENAI_API_KEY)
        else:
            embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_ENDPOINT)
        vector =  embeddings.embed_query(text)
        # if  logger:
            # logger.info("Embeded")
        return vector
    except Exception as e:
        print(f"Error embedding text: {e}")
        return []

async def async_llm_embedding(text, force_json=False, logger=None):
    try:
        if LLM_PROVIDER == 'OPENAI':
            embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=OPENAI_API_KEY)
        else:
            embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_ENDPOINT)
        vector =  embeddings.embed_query(text)
        # if  logger:
        #     logger.info("Embeded")
        return vector
    except Exception as e:
        print(f"Error embedding text: {e}")
        return []

 


def pull_ollama_model(model_name):
    """
    Pull an Ollama model via its local API.
    Ensure 'ollama serve' is running in your cluster first.
    """
    url = OLLAMA_ENDPOINT + '/api/pull'
    print(f'pulling {model_name}')
    payload = {"model": model_name}

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"Successfully pulled model: {model_name}")
        else:
            print(f"Error pulling model (status {response.status_code}):\n{response.text}")
    except requests.exceptions.RequestException as e:
        print("An error occurred while making the request:", str(e))


LLM_PROVIDER = os.environ.get("LLM_PROVIDER", 'OPENAI')
if LLM_PROVIDER == 'OPENAI':
    print("Using OPENAI.")
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '') # Reqired
    GENERATION_MODEL = os.environ.get('GENERATION_MODEL', 'gpt-4o')
    EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'text-embedding-3-small')
    assert OPENAI_API_KEY
else:
    print("Using Ollama")
    OLLAMA_ENDPOINT = os.environ.get("OLLAMA_ENDPOINT", 'http://ollama.hyperplane-ollama:11434')
    GENERATION_MODEL = os.environ.get('GENERATION_MODEL','llama3.2') # Required
    EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'nomic-embed-text') # Required
    print("Pulling model")
    pull_ollama_model(GENERATION_MODEL)
    pull_ollama_model(EMBEDDING_MODEL)


def check():
    print("Testing generation")
    # Initialize LangChain with OpenAI model


    # Construct the query
    query = [
        HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Tell me a joke",
                }
            ]
        )
    ]
    response = llm_invoke(query)
    print( response.content) 
    vector = llm_embedding("text")
    if vector:
        print(f"Embedding tested {len(vector)} size.")
    else:
        print("Embedding failed.")

if __name__ == '__main__':
    print('Done')
    check()