from __future__ import annotations

import math
import re
from collections import Counter
from hashlib import sha256

from app.models.schemas import EmbeddingStats
from app.services import database


class EmbeddingService:
    def __init__(self, dimension: int = 96):
        self.dimension = dimension

    def embed_text(self, text: str) -> list[float]:
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * self.dimension

        counts = Counter(tokens)
        vector = [0.0] * self.dimension
        for token, count in counts.items():
            index = self._stable_index(token)
            weight = 1.0 + math.log(count)
            vector[index] += weight

        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        return sum(a * b for a, b in zip(left, right))

    async def index_document(self, document_id: str) -> dict[str, object]:
        document = await database.fetch_one('SELECT id FROM documents WHERE id = ?', (document_id,))
        if document is None:
            return {'status': 'missing', 'document_id': document_id}

        rows = await database.fetch_all(
            'SELECT id, text FROM chunks WHERE document_id = ? ORDER BY position ASC, id ASC',
            (document_id,),
        )
        if not rows:
            return {'status': 'empty', 'document_id': document_id, 'indexed_chunks': 0, 'dimension': self.dimension}

        updates = [(database.dumps(self.embed_text(row['text'])), row['id']) for row in rows]
        await database.insert_many('UPDATE chunks SET embedding = ? WHERE id = ?', updates)
        return {
            'status': 'indexed',
            'document_id': document_id,
            'indexed_chunks': len(updates),
            'dimension': self.dimension,
        }

    async def reindex_all(self) -> EmbeddingStats:
        rows = await database.fetch_all('SELECT id FROM documents ORDER BY id ASC')
        for row in rows:
            await self.index_document(row['id'])
        return await self.stats()

    async def stats(self) -> EmbeddingStats:
        totals = await database.fetch_one(
            'SELECT COUNT(*) AS total_chunks, SUM(CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END) AS indexed_chunks FROM chunks'
        )
        docs = await database.fetch_one(
            'SELECT COUNT(DISTINCT document_id) AS indexed_documents FROM chunks WHERE embedding IS NOT NULL'
        )
        return EmbeddingStats(
            dimension=self.dimension,
            indexed_chunks=int(totals['indexed_chunks'] or 0),
            total_chunks=int(totals['total_chunks'] or 0),
            indexed_documents=int(docs['indexed_documents'] or 0),
        )

    def _stable_index(self, token: str) -> int:
        digest = sha256(token.encode('utf-8')).digest()
        value = int.from_bytes(digest[:8], byteorder='big', signed=False)
        return value % self.dimension

    def _tokenize(self, text: str) -> list[str]:
        return [token.lower() for token in re.findall(r'[A-Za-z0-9]+', text)]


embedding_service = EmbeddingService()
