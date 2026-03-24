from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator
from uuid import uuid4

from app.models.schemas import Citation, Draft, DraftManualSave, SearchResult
from app.services import database
from app.services.audit_service import audit_service
from app.services.document_service import document_service
from app.services.retrieval_service import retrieval_service
from app.services.template_service import template_service


class DraftService:
    async def generate_draft_stream(self, template_id: str, doc_ids: list[str], instruction: str) -> AsyncGenerator[str, None]:
        template = await template_service.get_template(template_id)
        if template is None:
            yield self._sse({'type': 'error', 'message': f'Template {template_id} not found'})
            return

        documents = await document_service.list_documents()
        selected_documents = [doc for doc in documents if doc.id in doc_ids]
        if not selected_documents:
            yield self._sse({'type': 'error', 'message': 'Select at least one source document before generating a draft'})
            return

        message = f'Retrieving relevant passages from {len(selected_documents)} documents'
        yield self._stage('retrieval', message, progress=0.08, mode='generate', status='started')
        await asyncio.sleep(0.08)

        retrieved = await retrieval_service.retrieve_relevant_chunks(instruction, doc_ids, limit=10)
        retrieval_summary = retrieval_service.summarize_retrieval(retrieved)
        yield self._sse(
            {
                'type': 'retrieval',
                'mode': 'generate',
                'summary': retrieval_summary,
                'results': [item.model_dump() for item in retrieved],
            }
        )
        yield self._stage(
            'retrieval',
            f"Retrieved {retrieval_summary['total_chunks']} passages across {retrieval_summary['documents_hit']} documents",
            progress=0.2,
            mode='generate',
            status='completed',
        )

        citations = self._build_citations(template.sections, retrieved)
        yield self._sse({'type': 'citations', 'mode': 'generate', 'citations': [citation.model_dump() for citation in citations]})

        context = retrieval_service.build_context(retrieved)
        yield self._stage(
            'context',
            f'Assembled grounded context package ({len(context.split())} words)',
            progress=0.32,
            mode='generate',
            status='completed',
        )
        await asyncio.sleep(0.06)

        yield self._stage(
            'planning',
            f'Planned {len(template.sections)} board-ready sections',
            progress=0.42,
            mode='generate',
            status='completed',
            sections=[section.model_dump() for section in template.sections],
        )

        generated_sections: dict[str, str] = {}
        total_sections = max(len(template.sections), 1)
        for index, section in enumerate(template.sections, start=1):
            section_progress = 0.42 + ((index - 1) / total_sections) * 0.42
            yield self._stage(
                'drafting',
                f'Drafting {section.title}',
                progress=section_progress,
                mode='generate',
                status='started',
                section=section.id,
                section_title=section.title,
            )
            section_text = self._compose_section(
                section.id,
                section.title,
                instruction,
                selected_documents,
                retrieved,
            )
            generated_sections[section.id] = section_text
            for piece in self._chunk_text(section_text, chunk_size=140):
                yield self._sse(
                    {
                        'type': 'content',
                        'mode': 'generate',
                        'section': section.id,
                        'section_title': section.title,
                        'text': piece,
                    }
                )
                await asyncio.sleep(0.025)
            yield self._stage(
                'drafting',
                f'{section.title} ready',
                progress=section_progress + (0.42 / total_sections),
                mode='generate',
                status='completed',
                section=section.id,
                section_title=section.title,
            )

        yield self._stage('persistence', 'Persisting draft lineage and audit metadata', progress=0.92, mode='generate', status='started')
        draft_id = f'draft_{uuid4().hex[:10]}'
        draft = Draft(
            id=draft_id,
            template_id=template_id,
            title=self._title_from_instruction(instruction),
            content=generated_sections,
            citations=citations,
            working_set=doc_ids,
            version=1,
            root_draft_id=draft_id,
            parent_draft_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await self.save_draft(draft)
        await audit_service.log(
            'draft.generated',
            'draft',
            draft.id,
            {
                'template_id': template_id,
                'document_ids': doc_ids,
                'instruction': instruction,
                'retrieval_summary': retrieval_summary,
            },
        )
        yield self._stage(
            'persistence',
            f'Draft saved as {draft_id}',
            progress=0.99,
            mode='generate',
            status='completed',
            draft_id=draft_id,
            version=1,
        )
        yield self._sse({'type': 'done', 'mode': 'generate', 'draft_id': draft_id, 'version': 1, 'title': draft.title})

    async def refine_draft_stream(self, draft_id: str, instruction: str, section_ids: list[str] | None = None) -> AsyncGenerator[str, None]:
        original = await self.get_draft(draft_id)
        if original is None:
            yield self._sse({'type': 'error', 'message': f'Draft {draft_id} not found'})
            return

        template = await template_service.get_template(original.template_id)
        if template is None:
            yield self._sse({'type': 'error', 'message': 'Template for draft not found'})
            return

        documents = await document_service.list_documents()
        selected_documents = [doc for doc in documents if doc.id in original.working_set]
        if not selected_documents:
            yield self._sse({'type': 'error', 'message': 'Original working set is no longer available'})
            return

        target_sections = section_ids or list(original.content.keys())
        yield self._stage(
            'retrieval',
            f'Retrieving grounded context for {len(target_sections)} section(s)',
            progress=0.08,
            mode='refine',
            status='started',
            section_ids=target_sections,
        )
        retrieved = await retrieval_service.retrieve_relevant_chunks(instruction, original.working_set, limit=8)
        retrieval_summary = retrieval_service.summarize_retrieval(retrieved)
        yield self._sse(
            {
                'type': 'retrieval',
                'mode': 'refine',
                'summary': retrieval_summary,
                'results': [item.model_dump() for item in retrieved],
            }
        )
        yield self._stage(
            'retrieval',
            f"Retrieved {retrieval_summary['total_chunks']} passages to refine the draft",
            progress=0.2,
            mode='refine',
            status='completed',
        )

        citations = self._build_citations(template.sections, retrieved)
        yield self._sse({'type': 'citations', 'mode': 'refine', 'citations': [citation.model_dump() for citation in citations]})
        yield self._stage(
            'planning',
            f'Refinement plan ready for {len(target_sections)} section(s)',
            progress=0.34,
            mode='refine',
            status='completed',
            section_ids=target_sections,
        )

        next_version = original.version + 1
        merged_content = dict(original.content)
        total_sections = max(len(target_sections), 1)
        refined_sections: dict[str, str] = {}
        for index, section in enumerate(template.sections, start=1):
            if section.id not in target_sections:
                continue
            section_rank = list(target_sections).index(section.id) + 1
            section_progress = 0.34 + ((section_rank - 1) / total_sections) * 0.46
            yield self._stage(
                'drafting',
                f'Refining {section.title}',
                progress=section_progress,
                mode='refine',
                status='started',
                section=section.id,
                section_title=section.title,
            )
            section_text = self._compose_section(
                section.id,
                section.title,
                f'Refine the existing draft with this request: {instruction}',
                selected_documents,
                retrieved,
                prior_content=original.content,
            )
            refined_sections[section.id] = section_text
            merged_content[section.id] = section_text
            for piece in self._chunk_text(section_text, chunk_size=140):
                yield self._sse(
                    {
                        'type': 'content',
                        'mode': 'refine',
                        'section': section.id,
                        'section_title': section.title,
                        'text': piece,
                    }
                )
                await asyncio.sleep(0.025)
            yield self._stage(
                'drafting',
                f'{section.title} refinement complete',
                progress=section_progress + (0.46 / total_sections),
                mode='refine',
                status='completed',
                section=section.id,
                section_title=section.title,
            )

        yield self._stage('persistence', 'Saving refined version and audit metadata', progress=0.92, mode='refine', status='started')
        new_draft_id = f'draft_{uuid4().hex[:10]}'
        refined_draft = Draft(
            id=new_draft_id,
            template_id=original.template_id,
            title=original.title,
            content=merged_content,
            citations=citations or original.citations,
            working_set=original.working_set,
            version=next_version,
            root_draft_id=original.root_draft_id or original.id,
            parent_draft_id=original.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await self.save_draft(refined_draft)
        await audit_service.log(
            'draft.refined',
            'draft',
            refined_draft.id,
            {
                'parent_draft_id': original.id,
                'root_draft_id': refined_draft.root_draft_id,
                'instruction': instruction,
                'section_ids': target_sections,
                'retrieval_summary': retrieval_summary,
            },
        )
        yield self._stage(
            'persistence',
            f'Refined draft saved as {new_draft_id}',
            progress=0.99,
            mode='refine',
            status='completed',
            draft_id=new_draft_id,
            version=next_version,
        )
        yield self._sse({'type': 'done', 'mode': 'refine', 'draft_id': new_draft_id, 'version': next_version, 'title': refined_draft.title})

    async def save_draft(self, draft: Draft) -> None:
        await database.execute(
            '''
            INSERT OR REPLACE INTO drafts (id, template_id, title, content, citations, working_set, version, root_draft_id, parent_draft_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                draft.id,
                draft.template_id,
                draft.title,
                json.dumps(draft.content),
                json.dumps([citation.model_dump() for citation in draft.citations]),
                json.dumps(draft.working_set),
                draft.version,
                draft.root_draft_id,
                draft.parent_draft_id,
                draft.created_at.isoformat(),
                draft.updated_at.isoformat(),
            ),
        )

    async def list_draft_versions(self, draft_id: str) -> list[Draft]:
        row = await database.fetch_one('SELECT * FROM drafts WHERE id = ?', (draft_id,))
        if not row:
            return []
        root_id = row.get('root_draft_id') or row['id']
        rows = await database.fetch_all(
            'SELECT * FROM drafts WHERE root_draft_id = ? OR id = ? ORDER BY version ASC, created_at ASC',
            (root_id, root_id),
        )
        return [self._row_to_draft(item) for item in rows]

    async def get_draft(self, draft_id: str) -> Draft | None:
        row = await database.fetch_one('SELECT * FROM drafts WHERE id = ?', (draft_id,))
        if not row:
            return None
        return self._row_to_draft(row)

    async def save_manual_edit(self, draft_id: str, payload: DraftManualSave) -> Draft | None:
        original = await self.get_draft(draft_id)
        if original is None:
            return None

        merged_content = dict(original.content)
        for section_id, value in payload.content.items():
            merged_content[section_id] = value

        next_version = original.version + 1
        new_draft_id = f'draft_{uuid4().hex[:10]}'
        now = datetime.utcnow()
        edited_draft = Draft(
            id=new_draft_id,
            template_id=original.template_id,
            title=(payload.title or original.title).strip() or original.title,
            content=merged_content,
            citations=original.citations,
            working_set=original.working_set,
            version=next_version,
            root_draft_id=original.root_draft_id or original.id,
            parent_draft_id=original.id,
            created_at=now,
            updated_at=now,
        )
        await self.save_draft(edited_draft)
        await audit_service.log(
            'draft.edited',
            'draft',
            edited_draft.id,
            {
                'parent_draft_id': original.id,
                'root_draft_id': edited_draft.root_draft_id,
                'sections_updated': list(payload.content.keys()),
            },
        )
        return edited_draft

    async def list_recent_drafts(self, limit: int = 20) -> list[Draft]:
        rows = await database.fetch_all('SELECT * FROM drafts ORDER BY updated_at DESC LIMIT ?', (limit,))
        return [self._row_to_draft(row) for row in rows]

    def _build_citations(self, template_sections, retrieved: list[SearchResult]) -> list[Citation]:
        if not template_sections:
            return []
        return [
            Citation(
                section=template_sections[min(index, len(template_sections) - 1)].id,
                document_id=item.document_id,
                chunk_id=item.chunk_id,
                document_title=item.document_title,
                snippet=item.text[:220] + ('...' if len(item.text) > 220 else ''),
                score=item.score,
                keyword_score=item.keyword_score,
                vector_score=item.vector_score,
                matched_terms=item.matched_terms,
            )
            for index, item in enumerate(retrieved)
        ]

    def _row_to_draft(self, row) -> Draft:
        return Draft(
            id=row['id'],
            template_id=row['template_id'],
            title=row['title'],
            content=database.loads(row['content']) or {},
            citations=[Citation(**citation) for citation in (database.loads(row['citations']) or [])],
            working_set=database.loads(row['working_set']) or [],
            version=row['version'],
            root_draft_id=row.get('root_draft_id'),
            parent_draft_id=row.get('parent_draft_id'),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )

    def _compose_section(self, section_id: str, section_title: str, instruction: str, documents, retrieved: list[SearchResult], prior_content: dict[str, str] | None = None) -> str:
        doc_titles = ', '.join(document.title for document in documents[:3]) or 'selected internal documents'
        evidence = '; '.join(item.text.split('. ')[0] for item in retrieved[:3]) or 'limited direct evidence was retrieved, so management should review additional supporting material'
        existing_text = ''
        if prior_content and section_id in prior_content:
            existing_text = f" Prior version guidance: {prior_content[section_id][:220]}"

        base = {
            'executive_summary': (
                'We recommend advancing to a focused diligence phase for the proposed regional organic food distributor. '
                'The internal evidence suggests strategic fit with premium food growth priorities, adjacency to existing distribution capabilities, '
                'and a credible path to leadership alignment if management frames the opportunity with disciplined assumptions.'
            ),
            'background': (
                f'The opportunity should be evaluated against precedent materials including {doc_titles}. '
                'Historical transaction reviews show that integrations succeed when category adjacency, operating cadence, and governance design are established before close.'
            ),
            'analysis': (
                'The retrieved internal corpus highlights three decision anchors: category growth exposure, operating margin durability, and execution readiness. '
                f'Across the source material, the strongest corroborating evidence includes: {evidence}.'
            ),
            'recommendation': (
                'Management should authorize a stage-gated diligence plan focused on commercial overlap, distribution complexity, and scenario-based value creation. '
                'A draft board narrative should emphasize optionality, integration discipline, and the ability to defer commitment if leading indicators weaken.'
            ),
            'risk_assessment': (
                'The risk posture should remain conservative. Key watch areas include integration drag, margin compression during transition, regulatory review sensitivity, '
                'and the need for explicit executive sponsorship to avoid diffused accountability.'
            ),
            'situation': 'The current situation should be framed in a concise executive style grounded in the selected internal sources.',
            'implications': 'Leadership implications should emphasize why the issue matters now and what trade-offs are emerging.',
            'actions': 'Recommended actions should be concrete, ordered, and easily reviewable by executives.',
        }
        text = base.get(section_id, f'{section_title} should synthesize the selected internal record into an executive-ready narrative.')
        return f'{text}{existing_text}\n\nRequested brief: {instruction.strip()}'

    def _title_from_instruction(self, instruction: str) -> str:
        cleaned = instruction.strip().rstrip('.')
        return cleaned[:90] if cleaned else 'Executive Draft'

    def _chunk_text(self, text: str, chunk_size: int = 160) -> list[str]:
        return [text[index:index + chunk_size] for index in range(0, len(text), chunk_size)]

    def _stage(self, stage: str, message: str, progress: float, mode: str, status: str, **extra) -> str:
        payload = {
            'type': 'stage',
            'stage': stage,
            'status': status,
            'message': message,
            'progress': round(progress, 3),
            'mode': mode,
        }
        payload.update(extra)
        return self._sse(payload)

    def _sse(self, payload: dict) -> str:
        return f'data: {json.dumps(payload)}\n\n'


draft_service = DraftService()
