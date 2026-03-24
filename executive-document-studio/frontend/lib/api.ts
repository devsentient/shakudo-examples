import type {
  AuditLog,
  DocumentType,
  EmbeddingStats,
  ExportFormat,
  SearchResponse,
  StreamEvent,
  StudioDocument,
  StudioDraft,
  StudioTemplate,
} from '@/lib/types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/api'

async function buildErrorMessage(response: Response): Promise<string> {
  const text = await response.text()
  if (!text) {
    return `Request failed with status ${response.status}`
  }

  try {
    const payload = JSON.parse(text) as { detail?: string }
    if (payload.detail) return payload.detail
  } catch {
    // Fall through to raw text.
  }

  return text
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(await buildErrorMessage(response))
  }
  return response.json() as Promise<T>
}

function parseSseChunk(chunk: string): StreamEvent[] {
  return chunk
    .split('\n\n')
    .map((entry) => entry.trim())
    .filter(Boolean)
    .flatMap((entry) => {
      const dataLine = entry
        .split('\n')
        .find((line) => line.startsWith('data:'))

      if (!dataLine) return []

      try {
        return [JSON.parse(dataLine.replace(/^data:\s*/, '')) as StreamEvent]
      } catch {
        return []
      }
    })
}

function buildDraftStreamHandlers(
  handlers: {
    onEvent: (event: StreamEvent) => void
    onError: (message: string) => void
  },
) {
  return async (response: Response) => {
    if (!response.ok || !response.body) {
      handlers.onError(await buildErrorMessage(response))
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const segments = buffer.split('\n\n')
      buffer = segments.pop() ?? ''

      for (const segment of segments) {
        for (const event of parseSseChunk(`${segment}\n\n`)) {
          handlers.onEvent(event)
        }
      }
    }

    if (buffer.trim()) {
      for (const event of parseSseChunk(buffer)) {
        handlers.onEvent(event)
      }
    }
  }
}

async function streamRequest(
  path: string,
  payload: Record<string, unknown>,
  handlers: {
    onEvent: (event: StreamEvent) => void
    onError: (message: string) => void
  },
) {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  } catch (error) {
    handlers.onError(error instanceof Error ? error.message : 'Unable to reach backend')
    return
  }

  await buildDraftStreamHandlers(handlers)(response)
}

export async function getDocuments(): Promise<StudioDocument[]> {
  const response = await fetch(`${API_BASE_URL}/documents`, { cache: 'no-store' })
  return parseJson<StudioDocument[]>(response)
}

export async function createTextDocument(input: {
  title: string
  type: DocumentType
  tags: string[]
  date?: string | null
  content: string
  summary?: string | null
}): Promise<StudioDocument> {
  const response = await fetch(`${API_BASE_URL}/documents/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  return parseJson<StudioDocument>(response)
}

export async function createUrlDocument(input: {
  url: string
  title?: string | null
  type: DocumentType
  tags: string[]
  date?: string | null
}): Promise<StudioDocument> {
  const response = await fetch(`${API_BASE_URL}/documents/url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  return parseJson<StudioDocument>(response)
}

export async function uploadDocument(input: {
  file: File
  type: DocumentType
  tags: string[]
  date?: string | null
}): Promise<StudioDocument> {
  const formData = new FormData()
  formData.set('file', input.file)
  formData.set('type', input.type)
  formData.set('tags', input.tags.join(','))
  if (input.date) {
    formData.set('date', input.date)
  }

  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: 'POST',
    body: formData,
  })
  return parseJson<StudioDocument>(response)
}

export async function searchDocuments(
  query: string,
  options: { docIds?: string[]; limit?: number } = {},
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query })
  if (options.limit) params.set('limit', String(options.limit))
  if (options.docIds && options.docIds.length > 0) {
    params.set('doc_ids', options.docIds.join(','))
  }

  const response = await fetch(`${API_BASE_URL}/documents/search?${params.toString()}`, {
    cache: 'no-store',
  })
  return parseJson<SearchResponse>(response)
}

export async function getAuditLogs(limit = 12): Promise<AuditLog[]> {
  const response = await fetch(`${API_BASE_URL}/documents/audit?limit=${limit}`, {
    cache: 'no-store',
  })
  return parseJson<AuditLog[]>(response)
}

export async function getTemplates(): Promise<StudioTemplate[]> {
  const response = await fetch(`${API_BASE_URL}/templates`, { cache: 'no-store' })
  return parseJson<StudioTemplate[]>(response)
}

export async function getRecentDrafts(limit = 8): Promise<StudioDraft[]> {
  const response = await fetch(`${API_BASE_URL}/drafts?limit=${limit}`, { cache: 'no-store' })
  return parseJson<StudioDraft[]>(response)
}

export async function getDraft(draftId: string): Promise<StudioDraft> {
  const response = await fetch(`${API_BASE_URL}/drafts/${draftId}`, { cache: 'no-store' })
  return parseJson<StudioDraft>(response)
}

export async function getDraftVersions(draftId: string): Promise<StudioDraft[]> {
  const response = await fetch(`${API_BASE_URL}/drafts/${draftId}/versions`, {
    cache: 'no-store',
  })
  return parseJson<StudioDraft[]>(response)
}

export async function saveManualDraft(
  draftId: string,
  input: { title?: string; content: Record<string, string> },
): Promise<StudioDraft> {
  const response = await fetch(`${API_BASE_URL}/drafts/${draftId}/manual-save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  return parseJson<StudioDraft>(response)
}

export async function getEmbeddingStats(): Promise<EmbeddingStats> {
  const response = await fetch(`${API_BASE_URL}/embeddings/stats`, { cache: 'no-store' })
  return parseJson<EmbeddingStats>(response)
}

export async function streamDraft(
  input: { template_id: string; doc_ids: string[]; instruction: string },
  handlers: {
    onEvent: (event: StreamEvent) => void
    onError: (message: string) => void
  },
) {
  await streamRequest('/drafts/generate', input, handlers)
}

export async function refineDraft(
  draftId: string,
  input: { instruction: string; section_ids?: string[] },
  handlers: {
    onEvent: (event: StreamEvent) => void
    onError: (message: string) => void
  },
) {
  await streamRequest(`/drafts/${draftId}/refine`, input, handlers)
}

function extractFilename(contentDisposition: string | null, fallback: string): string {
  if (!contentDisposition) return fallback
  const match = contentDisposition.match(/filename=([^;]+)/i)
  return match?.[1]?.replaceAll('"', '') ?? fallback
}

export async function downloadDraftExport(
  draftId: string,
  format: ExportFormat,
): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(`${API_BASE_URL}/export/${draftId}?format=${format}`, {
    method: 'POST',
  })
  if (!response.ok) {
    throw new Error(await buildErrorMessage(response))
  }

  return {
    blob: await response.blob(),
    filename: extractFilename(response.headers.get('Content-Disposition'), `${draftId}.${format}`),
  }
}
