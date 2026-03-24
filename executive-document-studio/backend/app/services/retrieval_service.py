from __future__ import annotations

from collections import defaultdict

from app.models.schemas import SearchResult
from app.services.document_service import document_service


class RetrievalService:
    async def retrieve_relevant_chunks(self, query: str, document_ids: list[str], limit: int = 8) -> list[SearchResult]:
        response = await document_service.search(query, limit=max(limit * 3, 12), doc_ids=document_ids)
        base_results = response.results
        if not base_results:
            return []

        doc_frequency: dict[str, int] = defaultdict(int)
        for result in base_results:
            doc_frequency[result.document_id] += 1

        reranked = []
        for result in base_results:
            score = min(
                1.0,
                result.score
                + self._soft_match_bonus(query, result)
                + self._diversity_bonus(doc_frequency[result.document_id]),
            )
            reranked.append(
                SearchResult(
                    chunk_id=result.chunk_id,
                    document_id=result.document_id,
                    document_title=result.document_title,
                    text=result.text,
                    score=round(score, 4),
                    keyword_score=result.keyword_score,
                    vector_score=result.vector_score,
                    matched_terms=result.matched_terms,
                    metadata={
                        **result.metadata,
                        'retrieval_mode': response.summary.get('mode', 'hybrid'),
                    },
                )
            )
        return sorted(reranked, key=lambda item: (item.score, item.vector_score, item.keyword_score), reverse=True)[:limit]

    def build_context(self, chunks: list[SearchResult]) -> str:
        grouped = defaultdict(list)
        for chunk in chunks:
            grouped[chunk.document_title].append(chunk)
        parts = []
        for title, entries in grouped.items():
            parts.append(f'## {title}')
            for entry in entries:
                terms = ', '.join(entry.matched_terms) if entry.matched_terms else 'semantic match'
                parts.append(
                    f"[overall {entry.score:.2f} | keyword {entry.keyword_score:.2f} | vector {entry.vector_score:.2f} | {terms}] {entry.text}"
                )
        return '\n\n'.join(parts)

    def summarize_retrieval(self, chunks: list[SearchResult]) -> dict:
        by_doc: dict[str, int] = defaultdict(int)
        for chunk in chunks:
            by_doc[chunk.document_title] += 1
        average_score = round(sum(chunk.score for chunk in chunks) / len(chunks), 4) if chunks else 0.0
        average_keyword = round(sum(chunk.keyword_score for chunk in chunks) / len(chunks), 4) if chunks else 0.0
        average_vector = round(sum(chunk.vector_score for chunk in chunks) / len(chunks), 4) if chunks else 0.0
        return {
            'total_chunks': len(chunks),
            'documents_hit': len(by_doc),
            'document_hits': dict(by_doc),
            'average_score': average_score,
            'average_keyword_score': average_keyword,
            'average_vector_score': average_vector,
        }

    def _soft_match_bonus(self, query: str, result: SearchResult) -> float:
        text = result.text.lower()
        bonuses = min(len(result.matched_terms) * 0.01, 0.04)
        themes = {
            'acquisition': ['acquisition', 'integration', 'transaction', 'target', 'synergy'],
            'risk': ['risk', 'regulatory', 'supply chain', 'margin', 'execution', 'mitigation'],
            'board': ['board', 'executive', 'leadership', 'memo', 'recommendation'],
            'market': ['market', 'competitor', 'category', 'consumer', 'growth'],
        }
        query_lower = query.lower()
        for trigger, keywords in themes.items():
            if trigger in query_lower and any(keyword in text for keyword in keywords):
                bonuses += 0.04
        return min(bonuses, 0.12)

    def _diversity_bonus(self, same_doc_count: int) -> float:
        return max(0.0, 0.08 - max(0, same_doc_count - 1) * 0.015)


retrieval_service = RetrievalService()
