from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    annual_report = 'annual_report'
    acquisition_case_study = 'acquisition_case_study'
    strategic_plan = 'strategic_plan'
    market_analysis = 'market_analysis'
    esg_report = 'esg_report'
    board_presentation = 'board_presentation'
    other = 'other'


class Document(BaseModel):
    id: str
    title: str
    type: DocumentType
    tags: List[str] = Field(default_factory=list)
    date: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    source_name: Optional[str] = None
    source_kind: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentCreateText(BaseModel):
    title: str
    type: DocumentType = DocumentType.other
    tags: List[str] = Field(default_factory=list)
    date: Optional[str] = None
    content: str
    summary: Optional[str] = None


class DocumentCreateUrl(BaseModel):
    url: str
    title: Optional[str] = None
    type: DocumentType = DocumentType.other
    tags: List[str] = Field(default_factory=list)
    date: Optional[str] = None


class Chunk(BaseModel):
    id: str
    document_id: str
    document_title: str
    text: str
    position: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None


class Citation(BaseModel):
    section: str
    document_id: str
    chunk_id: str
    document_title: Optional[str] = None
    snippet: Optional[str] = None
    score: Optional[float] = None
    keyword_score: Optional[float] = None
    vector_score: Optional[float] = None
    matched_terms: List[str] = Field(default_factory=list)


class TemplateSection(BaseModel):
    id: str
    title: str
    instructions: Optional[str] = None


class Template(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    sections: List[TemplateSection] = Field(default_factory=list)
    system_prompt: Optional[str] = None


class Draft(BaseModel):
    id: str
    template_id: str
    title: str
    content: Dict[str, str] = Field(default_factory=dict)
    citations: List[Citation] = Field(default_factory=list)
    working_set: List[str] = Field(default_factory=list)
    version: int = 1
    root_draft_id: Optional[str] = None
    parent_draft_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DraftCreate(BaseModel):
    template_id: str
    doc_ids: List[str]
    instruction: str


class DraftRefine(BaseModel):
    instruction: str
    section_ids: Optional[List[str]] = None


class DraftManualSave(BaseModel):
    title: Optional[str] = None
    content: Dict[str, str] = Field(default_factory=dict)


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    text: str
    score: float
    keyword_score: float = 0.0
    vector_score: float = 0.0
    matched_terms: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    summary: Dict[str, Any] = Field(default_factory=dict)
    results: List[SearchResult] = Field(default_factory=list)


class EmbeddingStats(BaseModel):
    dimension: int
    indexed_chunks: int
    total_chunks: int
    indexed_documents: int


class AuditLog(BaseModel):
    id: str
    action: str
    entity_type: str
    entity_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
