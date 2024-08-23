import logging

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import SearchParams

from fastapi import FastAPI, APIRouter, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from constants import ROOT_PATH, OPENAI_API_KEY, QDRANT_URL, TEMPERATURE, SEED


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(
    docs_url=ROOT_PATH + "/api/docs",
    openapi_url=ROOT_PATH + "/api/openapi.json",
    redoc_url=None,
    title="RAG Tutorial Backend Module",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
router = APIRouter(prefix="/api")

openai_client = OpenAI(api_key=OPENAI_API_KEY)
qdrant_client = QdrantClient(url=QDRANT_URL)


class InputTemplate(BaseModel):
    user_query: str
    collection_name: str
    llm_model: str
    embedding_model: str
    limit: int


@router.post("/answer")
async def answer_question(input: InputTemplate):
    """
    Search for relevant information from the Qdrant collection and answer user query with a large language model of the user's choice.
    """
    try:
        query = input.user_query
        collection_name = input.collection_name
        llm_model = input.llm_model
        embedding_model = input.embedding_model
        limit = input.limit

        query_vector = openai_client.embeddings.create(model=embedding_model, input=query)

        search_results = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_vector.data[0].embedding,
            limit=limit,
        )
        search_results_text = '\n'.join([result.payload['text'] for result in search_results])

        prompt = [
            {"role": "system", "content": 'You are a Kubernetes expert more than happy to answer the user\'s question'},
            {"role": "user", "content": query + '\n\nRetrieved contexts:\n\n' + search_results_text},
        ]
        response = openai_client.chat.completions.create(
            model=llm_model,
            messages=prompt,
            temperature=TEMPERATURE,
            seed=SEED,
        )
        answer = response.choices[0].message.content

        context = [
            {
                'score': result.score,
                'text': result.payload['text'],
                'filepath': result.payload['_ab_source_file_url'],
            }
            for result in search_results
        ]

        return JSONResponse(
            content={
                "answer": answer,
                "context": context,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.error(str(e))
        return JSONResponse(
            content={
                "answer": "Sorry, the backend API encountered some error and hence couldn't generate an answer for you.",
                "context": "",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

app.include_router(router=router)