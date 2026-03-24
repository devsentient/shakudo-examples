from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / 'data'
DATA_DIR = Path(os.getenv('STUDIO_DATA_DIR', str(DEFAULT_DATA_DIR))).expanduser().resolve()
UPLOADS_DIR = Path(os.getenv('STUDIO_UPLOADS_DIR', str(DATA_DIR / 'uploads'))).expanduser().resolve()
DB_PATH = Path(os.getenv('STUDIO_DB_PATH', str(DATA_DIR / 'studio.db'))).expanduser().resolve()


def _row_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


async def _ensure_column(db: aiosqlite.Connection, table: str, column: str, definition: str) -> None:
    cursor = await db.execute(f'PRAGMA table_info({table})')
    rows = await cursor.fetchall()
    await cursor.close()
    columns = {row[1] for row in rows}
    if column not in columns:
        await db.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')


async def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            '''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                type TEXT NOT NULL,
                tags TEXT NOT NULL,
                date TEXT,
                summary TEXT,
                content TEXT,
                source_name TEXT,
                source_kind TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                sections TEXT NOT NULL,
                system_prompt TEXT
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                document_title TEXT NOT NULL,
                text TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0,
                metadata TEXT NOT NULL,
                embedding TEXT
            );

            CREATE TABLE IF NOT EXISTS drafts (
                id TEXT PRIMARY KEY,
                template_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                citations TEXT NOT NULL,
                working_set TEXT NOT NULL,
                version INTEGER NOT NULL,
                root_draft_id TEXT,
                parent_draft_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                metadata TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            '''
        )

        await _ensure_column(db, 'documents', 'source_name', 'TEXT')
        await _ensure_column(db, 'documents', 'source_kind', 'TEXT')
        await _ensure_column(db, 'chunks', 'position', 'INTEGER NOT NULL DEFAULT 0')
        await _ensure_column(db, 'chunks', 'embedding', 'TEXT')
        await _ensure_column(db, 'drafts', 'root_draft_id', 'TEXT')
        await _ensure_column(db, 'drafts', 'parent_draft_id', 'TEXT')

        await db.commit()


async def fetch_all(query: str, params: tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = _row_factory
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        await cursor.close()
        return rows


async def fetch_one(query: str, params: tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = _row_factory
        cursor = await db.execute(query, params)
        row = await cursor.fetchone()
        await cursor.close()
        return row


async def execute(query: str, params: tuple[Any, ...] = ()) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(query, params)
        await db.commit()


async def insert_many(query: str, rows: list[tuple[Any, ...]]) -> None:
    if not rows:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(query, rows)
        await db.commit()


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads(value: str | None) -> Any:
    if value is None:
        return None
    return json.loads(value)
