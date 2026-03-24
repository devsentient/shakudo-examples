from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.models.schemas import DocumentCreateText, DocumentCreateUrl, DocumentType
from app.services.document_service import document_service

router = APIRouter()


@router.get('')
async def list_documents():
    return await document_service.list_documents()


@router.post('/text')
async def create_text_document(payload: DocumentCreateText):
    return await document_service.create_text_document(payload)


@router.post('/url')
async def create_url_document(payload: DocumentCreateUrl):
    try:
        return await document_service.create_url_document(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/upload')
async def upload_document(
    file: UploadFile = File(...),
    type: DocumentType = Form(DocumentType.other),
    tags: str = Form(''),
    date: str | None = Form(None),
):
    try:
        tag_list = [item.strip() for item in tags.split(',') if item.strip()]
        return await document_service.upload_document(file, document_type=type, tags=tag_list, date=date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get('/search')
async def search_documents(q: str = Query(..., min_length=2), limit: int = 10, doc_ids: str | None = None):
    parsed_ids = [item.strip() for item in doc_ids.split(',')] if doc_ids else None
    return await document_service.search(q, limit=limit, doc_ids=parsed_ids)


@router.get('/audit')
async def list_audit_logs(limit: int = 50):
    return await document_service.list_audit_logs(limit=limit)


@router.get('/{document_id}')
async def get_document(document_id: str):
    document = await document_service.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail='Document not found')
    return document
