from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import DraftCreate, DraftManualSave, DraftRefine
from app.services.draft_service import draft_service

router = APIRouter()


@router.get('')
async def list_recent_drafts(limit: int = 20):
    return await draft_service.list_recent_drafts(limit=limit)


@router.post('/generate')
async def generate_draft(payload: DraftCreate):
    generator = draft_service.generate_draft_stream(
        template_id=payload.template_id,
        doc_ids=payload.doc_ids,
        instruction=payload.instruction,
    )
    return StreamingResponse(generator, media_type='text/event-stream')


@router.post('/{draft_id}/refine')
async def refine_draft(draft_id: str, payload: DraftRefine):
    generator = draft_service.refine_draft_stream(
        draft_id=draft_id,
        instruction=payload.instruction,
        section_ids=payload.section_ids,
    )
    return StreamingResponse(generator, media_type='text/event-stream')


@router.post('/{draft_id}/manual-save')
async def save_manual_draft(draft_id: str, payload: DraftManualSave):
    draft = await draft_service.save_manual_edit(draft_id, payload)
    if draft is None:
        raise HTTPException(status_code=404, detail='Draft not found')
    return draft


@router.get('/{draft_id}')
async def get_draft(draft_id: str):
    draft = await draft_service.get_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail='Draft not found')
    return draft


@router.get('/{draft_id}/versions')
async def get_draft_versions(draft_id: str):
    return await draft_service.list_draft_versions(draft_id)
