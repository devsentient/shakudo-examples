from __future__ import annotations

from typing import List

from app.models.schemas import Template, TemplateSection
from app.services import database


class TemplateService:
    async def list_templates(self) -> List[Template]:
        rows = await database.fetch_all('SELECT * FROM templates ORDER BY name ASC')
        return [
            Template(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                sections=[TemplateSection(**section) for section in database.loads(row['sections'])],
                system_prompt=row['system_prompt'],
            )
            for row in rows
        ]

    async def get_template(self, template_id: str) -> Template | None:
        row = await database.fetch_one('SELECT * FROM templates WHERE id = ?', (template_id,))
        if not row:
            return None
        return Template(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            sections=[TemplateSection(**section) for section in database.loads(row['sections'])],
            system_prompt=row['system_prompt'],
        )


template_service = TemplateService()
