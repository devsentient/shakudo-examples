from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.models.schemas import AuditLog
from app.services import database


class AuditService:
    async def log(self, action: str, entity_type: str, entity_id: str, metadata: dict) -> AuditLog:
        entry = AuditLog(
            id=f'audit_{uuid4().hex[:12]}',
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
            created_at=datetime.utcnow(),
        )
        await database.execute(
            '''
            INSERT INTO audit_logs (id, action, entity_type, entity_id, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                entry.id,
                entry.action,
                entry.entity_type,
                entry.entity_id,
                database.dumps(entry.metadata),
                entry.created_at.isoformat(),
            ),
        )
        return entry

    async def list_recent(self, limit: int = 50) -> list[AuditLog]:
        rows = await database.fetch_all(
            'SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?',
            (limit,),
        )
        return [
            AuditLog(
                id=row['id'],
                action=row['action'],
                entity_type=row['entity_type'],
                entity_id=row['entity_id'],
                metadata=database.loads(row['metadata']) or {},
                created_at=row['created_at'],
            )
            for row in rows
        ]


audit_service = AuditService()
