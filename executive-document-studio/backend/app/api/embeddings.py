from fastapi import APIRouter

from app.services.embedding_service import embedding_service

router = APIRouter()


@router.get('/stats')
async def embedding_stats():
    return await embedding_service.stats()


@router.post('/reindex')
async def reindex_all_embeddings():
    return await embedding_service.reindex_all()


@router.post('/index/{document_id}')
async def index_document(document_id: str):
    return await embedding_service.index_document(document_id)
