import logging
import os

from fastapi import FastAPI, APIRouter, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


ROOT_PATH = os.environ.get('ROOT_PATH', '')

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


class InputTemplate(BaseModel):
    point: str
    params: Any


@router.post("/answer")
async def answer_question(
    request: Request,
    input: InputTemplate):
    logger.info(f"Headers: {request.headers} Request: {input}")

    if input.point == 'ping':
        return JSONResponse(content={"result": "pong" }, status_code=status.HTTP_200_OK)


    return JSONResponse(
        content={
            "result": "echo",
        },
        status_code=status.HTTP_200_OK,
    )

app.include_router(router=router)
