from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.services.audit_service import audit_service
from app.services.draft_service import draft_service
from app.services.export_service import export_service

router = APIRouter()


@router.post('/{draft_id}')
async def export_draft(draft_id: str, format: str = Query('markdown')):
    draft = await draft_service.get_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail='Draft not found')

    if format == 'markdown':
        content = export_service.to_markdown_bytes(draft)
        media_type = 'text/markdown'
        suffix = 'md'
    elif format == 'text':
        content = export_service.to_text_bytes(draft)
        media_type = 'text/plain'
        suffix = 'txt'
    elif format == 'html':
        content = export_service.to_html_bytes(draft)
        media_type = 'text/html'
        suffix = 'html'
    elif format == 'docx':
        content = export_service.to_docx_bytes(draft)
        media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        suffix = 'docx'
    elif format == 'pdf':
        content = export_service.to_pdf_bytes(draft)
        media_type = 'application/pdf'
        suffix = 'pdf'
    else:
        raise HTTPException(status_code=400, detail='Supported export formats: markdown, text, html, docx, pdf')

    await audit_service.log('draft.exported', 'draft', draft_id, {'format': format})
    return Response(
        content=content,
        media_type=media_type,
        headers={'Content-Disposition': f'attachment; filename={draft_id}.{suffix}'},
    )
