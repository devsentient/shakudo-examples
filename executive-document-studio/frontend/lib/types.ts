export type DocumentType =
  | 'annual_report'
  | 'acquisition_case_study'
  | 'strategic_plan'
  | 'market_analysis'
  | 'esg_report'
  | 'board_presentation'
  | 'other'

export type ExportFormat = 'markdown' | 'text' | 'html' | 'docx' | 'pdf'

export interface StudioDocument {
  id: string
  title: string
  type: DocumentType
  tags: string[]
  date?: string | null
  summary?: string | null
  content?: string | null
  source_name?: string | null
  source_kind?: string | null
  created_at: string
  updated_at: string
}

export interface TemplateSection {
  id: string
  title: string
  instructions?: string | null
}

export interface StudioTemplate {
  id: string
  name: string
  description?: string | null
  sections: TemplateSection[]
}

export interface Citation {
  section: string
  document_id: string
  chunk_id: string
  document_title?: string | null
  snippet?: string | null
  score?: number | null
  keyword_score?: number | null
  vector_score?: number | null
  matched_terms: string[]
}

export interface SearchResult {
  chunk_id: string
  document_id: string
  document_title: string
  text: string
  score: number
  keyword_score: number
  vector_score: number
  matched_terms: string[]
  metadata: Record<string, unknown>
}

export interface SearchResponse {
  query: string
  summary: Record<string, unknown>
  results: SearchResult[]
}

export interface AuditLog {
  id: string
  action: string
  entity_type: string
  entity_id: string
  metadata: Record<string, unknown>
  created_at: string
}

export interface EmbeddingStats {
  dimension: number
  indexed_chunks: number
  total_chunks: number
  indexed_documents: number
}

export interface StudioDraft {
  id: string
  template_id: string
  title: string
  content: Record<string, string>
  citations: Citation[]
  working_set: string[]
  version: number
  root_draft_id?: string | null
  parent_draft_id?: string | null
  created_at: string
  updated_at: string
}

export interface StatusEvent {
  type: 'status'
  message?: string
  mode?: 'generate' | 'refine' | string
}

export interface StageEvent {
  type: 'stage'
  stage: string
  status: string
  message?: string
  progress?: number
  mode?: 'generate' | 'refine' | string
  section?: string
  section_title?: string
  draft_id?: string
  version?: number
  section_ids?: string[]
}

export interface RetrievalEvent {
  type: 'retrieval'
  mode?: 'generate' | 'refine' | string
  summary?: Record<string, unknown>
  results?: SearchResult[]
}

export interface CitationsEvent {
  type: 'citations'
  mode?: 'generate' | 'refine' | string
  citations?: Citation[]
}

export interface ContentEvent {
  type: 'content'
  mode?: 'generate' | 'refine' | string
  section?: string
  section_title?: string
  text?: string
}

export interface DoneEvent {
  type: 'done'
  mode?: 'generate' | 'refine' | string
  draft_id?: string
  version?: number
  title?: string
}

export interface ErrorEvent {
  type: 'error'
  mode?: 'generate' | 'refine' | string
  message?: string
}

export type StreamEvent =
  | StatusEvent
  | StageEvent
  | RetrievalEvent
  | CitationsEvent
  | ContentEvent
  | DoneEvent
  | ErrorEvent
