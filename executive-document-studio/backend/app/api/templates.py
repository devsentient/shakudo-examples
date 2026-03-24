from fastapi import APIRouter, HTTPException

from app.services.template_service import template_service

router = APIRouter()


@router.get('')
async def list_templates():
    return await template_service.list_templates()


@router.get('/{template_id}')
async def get_template(template_id: str):
    template = await template_service.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail='Template not found')
    return template
