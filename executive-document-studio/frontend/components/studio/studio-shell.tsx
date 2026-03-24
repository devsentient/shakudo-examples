'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import {
  ArrowDownToLine,
  ArrowRight,
  BookOpen,
  Bot,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Database,
  FileSearch,
  Files,
  FolderKanban,
  History,
  Layers3,
  Loader2,
  Lock,
  MessageSquareText,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
  WandSparkles,
} from 'lucide-react'

import {
  createTextDocument,
  downloadDraftExport,
  getAuditLogs,
  getDocuments,
  getDraftVersions,
  getEmbeddingStats,
  getRecentDrafts,
  getTemplates,
  refineDraft,
  searchDocuments,
  streamDraft,
  uploadDocument,
} from '@/lib/api'
import type {
  AuditLog,
  Citation,
  DocumentType,
  ExportFormat,
  SearchResult,
  StreamEvent,
  StudioDocument,
  StudioDraft,
  StudioTemplate,
} from '@/lib/types'
import { cn } from '@/lib/utils'

const defaultPrompt =
  'Draft a board memo evaluating the acquisition of a regional organic food distributor. Incorporate lessons from prior acquisitions, current market positioning, and a more conservative risk stance.'

const defaultRefinePrompt =
  'Tighten the recommendation, sharpen the board voice, and emphasize integration execution risk.'

const navItems = [
  { label: 'Studio', href: '/', icon: Layers3, active: true },
  { label: 'Library', href: '/library', icon: Files },
  { label: 'Templates', href: '/templates', icon: FolderKanban },
]

const promptPresets = [
  'Board-ready tone',
  'Conservative risk framing',
  'Acquisition precedent',
  'Investor summary',
]

const corpusModes = [
  { id: 'search', label: 'Search', icon: Search },
  { id: 'text', label: 'Paste', icon: MessageSquareText },
  { id: 'upload', label: 'Upload', icon: Upload },
] as const

const documentTypes: Array<{ value: DocumentType; label: string }> = [
  { value: 'annual_report', label: 'Annual report' },
  { value: 'acquisition_case_study', label: 'Acquisition case study' },
  { value: 'strategic_plan', label: 'Strategic plan' },
  { value: 'market_analysis', label: 'Market analysis' },
  { value: 'esg_report', label: 'ESG report' },
  { value: 'board_presentation', label: 'Board presentation' },
  { value: 'other', label: 'Other' },
]

type CorpusMode = (typeof corpusModes)[number]['id']
type StreamMode = 'generate' | 'refine' | null

type ActivityItem = {
  id: string
  kind: 'system' | 'stage' | 'retrieval' | 'status' | 'error'
  message: string
  stage?: string
  progress?: number
  mode?: string
  timestamp: string
}

function createActivity(
  message: string,
  kind: ActivityItem['kind'] = 'system',
  extra: Omit<ActivityItem, 'id' | 'kind' | 'message' | 'timestamp'> = {},
): ActivityItem {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    kind,
    message,
    timestamp: new Date().toISOString(),
    ...extra,
  }
}

function humanize(value: string) {
  return value
    .replaceAll('.', ' ')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (match) => match.toUpperCase())
}

function formatDateTime(value?: string | null) {
  if (!value) return '—'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(parsed)
}

function formatScore(value?: number | null) {
  return typeof value === 'number' ? value.toFixed(2) : '0.00'
}

function shortId(value?: string | null) {
  return value ? value.slice(0, 14) : 'pending'
}

export function StudioShell() {
  const [documents, setDocuments] = useState<StudioDocument[]>([])
  const [templates, setTemplates] = useState<StudioTemplate[]>([])
  const [recentDrafts, setRecentDrafts] = useState<StudioDraft[]>([])
  const [versions, setVersions] = useState<StudioDraft[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState('template_board_memo')
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([])
  const [instruction, setInstruction] = useState(defaultPrompt)
  const [refineInstruction, setRefineInstruction] = useState(defaultRefinePrompt)
  const [selectedRefineSectionIds, setSelectedRefineSectionIds] = useState<string[]>([])
  const [draftSections, setDraftSections] = useState<Record<string, string>>({})
  const [citations, setCitations] = useState<Citation[]>([])
  const [retrievedResults, setRetrievedResults] = useState<SearchResult[]>([])
  const [manualSearchResults, setManualSearchResults] = useState<SearchResult[]>([])
  const [manualSearchSummary, setManualSearchSummary] = useState<Record<string, unknown> | null>(null)
  const [runtimeActivity, setRuntimeActivity] = useState<ActivityItem[]>([
    createActivity('Studio ready. Curate a working set, inspect retrieval, then generate a board-ready draft.'),
  ])
  const [draftId, setDraftId] = useState<string | null>(null)
  const [draftVersion, setDraftVersion] = useState<number | null>(null)
  const [draftTitle, setDraftTitle] = useState('Executive Draft')
  const [embeddingStats, setEmbeddingStats] = useState<{ indexed_chunks: number; total_chunks: number; indexed_documents: number; dimension: number } | null>(null)
  const [corpusMode, setCorpusMode] = useState<CorpusMode>('search')
  const [manualSearchQuery, setManualSearchQuery] = useState('board memo integration risk and premium category growth')
  const [activeStreamMode, setActiveStreamMode] = useState<StreamMode>(null)
  const [progress, setProgress] = useState(0)
  const [isBootstrapping, setIsBootstrapping] = useState(true)
  const [isSearching, setIsSearching] = useState(false)
  const [isCreatingTextDoc, setIsCreatingTextDoc] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [isExporting, setIsExporting] = useState<ExportFormat | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [textDocForm, setTextDocForm] = useState({
    title: '',
    type: 'other' as DocumentType,
    tags: 'internal, strategy',
    date: '',
    summary: '',
    content: '',
  })
  const [uploadForm, setUploadForm] = useState({
    type: 'other' as DocumentType,
    tags: 'internal',
    date: '',
    file: null as File | null,
  })

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.id === selectedTemplateId) ?? templates[0],
    [selectedTemplateId, templates],
  )

  const selectedDocuments = useMemo(
    () => documents.filter((document) => selectedDocIds.includes(document.id)),
    [documents, selectedDocIds],
  )

  const versionList = useMemo(
    () => [...versions].sort((left, right) => right.version - left.version),
    [versions],
  )

  const isStreaming = activeStreamMode !== null
  const progressPercent = Math.max(4, Math.round(progress * 100))

  useEffect(() => {
    void bootstrap()
  }, [])

  useEffect(() => {
    if (!selectedTemplate) return
    setSelectedRefineSectionIds((current) => {
      const valid = current.filter((sectionId) => selectedTemplate.sections.some((section) => section.id === sectionId))
      if (valid.length > 0) return valid
      return selectedTemplate.sections.map((section) => section.id)
    })
  }, [selectedTemplate])

  async function bootstrap() {
    setIsBootstrapping(true)
    setError(null)
    try {
      const [docs, templateData, drafts, audits, stats] = await Promise.all([
        getDocuments(),
        getTemplates(),
        getRecentDrafts(8),
        getAuditLogs(10),
        getEmbeddingStats(),
      ])
      setDocuments(docs)
      setTemplates(templateData)
      setRecentDrafts(drafts)
      setAuditLogs(audits)
      setEmbeddingStats(stats)
      setSelectedDocIds((current) => {
        const valid = current.filter((id) => docs.some((document) => document.id === id))
        return valid.length > 0 ? valid : docs.slice(0, 4).map((document) => document.id)
      })
      setSelectedTemplateId((current) =>
        templateData.some((template) => template.id === current)
          ? current
          : (templateData[0]?.id ?? current),
      )
    } catch (bootstrapError) {
      setError(
        bootstrapError instanceof Error
          ? bootstrapError.message
          : 'Unable to load studio resources',
      )
    } finally {
      setIsBootstrapping(false)
    }
  }

  function appendActivity(item: ActivityItem) {
    setRuntimeActivity((current) => [...current.slice(-19), item])
  }

  async function refreshDocumentsState(preferredId?: string) {
    const docs = await getDocuments()
    setDocuments(docs)
    setSelectedDocIds((current) => {
      const valid = current.filter((id) => docs.some((document) => document.id === id))
      const next = preferredId ? Array.from(new Set([preferredId, ...valid])) : valid
      return next.length > 0 ? next : docs.slice(0, 4).map((document) => document.id)
    })
  }

  async function refreshTelemetry() {
    const [drafts, audits, stats] = await Promise.all([
      getRecentDrafts(8),
      getAuditLogs(10),
      getEmbeddingStats(),
    ])
    setRecentDrafts(drafts)
    setAuditLogs(audits)
    setEmbeddingStats(stats)
  }

  function applyDraftState(draft: StudioDraft) {
    setDraftId(draft.id)
    setDraftVersion(draft.version)
    setDraftTitle(draft.title)
    setDraftSections(draft.content)
    setCitations(draft.citations)
    setSelectedTemplateId(draft.template_id)
    setSelectedDocIds(draft.working_set)
  }

  async function syncAfterDraft(nextDraftId: string) {
    const [nextVersions] = await Promise.all([
      getDraftVersions(nextDraftId),
      refreshTelemetry(),
    ])
    setVersions(nextVersions)
    const persisted = nextVersions.find((item) => item.id === nextDraftId)
    if (persisted) {
      applyDraftState(persisted)
    }
  }

  function toggleDocument(documentId: string) {
    setSelectedDocIds((current) =>
      current.includes(documentId)
        ? current.filter((id) => id !== documentId)
        : [...current, documentId],
    )
  }

  function toggleRefineSection(sectionId: string) {
    setSelectedRefineSectionIds((current) =>
      current.includes(sectionId)
        ? current.filter((id) => id !== sectionId)
        : [...current, sectionId],
    )
  }

  function handleStreamEvent(event: StreamEvent) {
    if (event.type === 'status' && event.message) {
      appendActivity(createActivity(event.message, 'status', { mode: event.mode }))
      return
    }

    if (event.type === 'stage') {
      if (typeof event.progress === 'number') {
        setProgress(event.progress)
      }
      appendActivity(
        createActivity(event.message ?? humanize(event.stage), 'stage', {
          stage: event.stage,
          progress: event.progress,
          mode: event.mode,
        }),
      )
      return
    }

    if (event.type === 'retrieval') {
      setRetrievedResults(event.results ?? [])
      const total = Number(event.summary?.total_chunks ?? event.results?.length ?? 0)
      const docsHit = Number(event.summary?.documents_hit ?? 0)
      appendActivity(
        createActivity(`Retrieval ready: ${total} passages from ${docsHit} documents`, 'retrieval', {
          mode: event.mode,
        }),
      )
      return
    }

    if (event.type === 'citations' && event.citations) {
      setCitations(event.citations)
      return
    }

    if (event.type === 'content' && event.section && event.text) {
      setDraftSections((current) => ({
        ...current,
        [event.section as string]: `${current[event.section as string] ?? ''}${event.text ?? ''}`,
      }))
      return
    }

    if (event.type === 'done') {
      setProgress(1)
      setActiveStreamMode(null)
      setDraftId(event.draft_id ?? null)
      setDraftVersion(event.version ?? null)
      setDraftTitle(event.title ?? draftTitle)
      appendActivity(
        createActivity(
          `${event.mode === 'refine' ? 'Refinement' : 'Generation'} complete. Draft ${shortId(event.draft_id)} is ready.`,
        ),
      )
      if (event.draft_id) {
        void syncAfterDraft(event.draft_id)
      }
      return
    }

    if (event.type === 'error') {
      setError(event.message ?? 'Streaming error')
      setActiveStreamMode(null)
      appendActivity(createActivity(event.message ?? 'Streaming error', 'error', { mode: event.mode }))
    }
  }

  async function handleGenerate() {
    if (!selectedTemplate || selectedDocIds.length === 0 || !instruction.trim()) return

    setActiveStreamMode('generate')
    setError(null)
    setProgress(0.04)
    setDraftId(null)
    setDraftVersion(null)
    setDraftTitle('Generating board-ready draft')
    setDraftSections({})
    setCitations([])
    setRetrievedResults([])
    appendActivity(createActivity('Generation run started. Hybrid retrieval and live section drafting are in progress...', 'system', { mode: 'generate' }))

    await streamDraft(
      {
        template_id: selectedTemplate.id,
        doc_ids: selectedDocIds,
        instruction,
      },
      {
        onEvent: handleStreamEvent,
        onError: (message) => {
          setError(message)
          setActiveStreamMode(null)
          appendActivity(createActivity(message, 'error', { mode: 'generate' }))
        },
      },
    )
  }

  async function handleRefine() {
    if (!draftId || !selectedTemplate || !refineInstruction.trim()) return

    const targetSections =
      selectedRefineSectionIds.length > 0
        ? selectedRefineSectionIds
        : selectedTemplate.sections.map((section) => section.id)

    setActiveStreamMode('refine')
    setError(null)
    setProgress(0.04)
    setRetrievedResults([])
    setDraftSections((current) => {
      const next = { ...current }
      for (const sectionId of targetSections) {
        next[sectionId] = ''
      }
      return next
    })
    appendActivity(createActivity(`Refinement run started for ${targetSections.length} section(s).`, 'system', { mode: 'refine' }))

    await refineDraft(
      draftId,
      {
        instruction: refineInstruction,
        section_ids: targetSections,
      },
      {
        onEvent: handleStreamEvent,
        onError: (message) => {
          setError(message)
          setActiveStreamMode(null)
          appendActivity(createActivity(message, 'error', { mode: 'refine' }))
        },
      },
    )
  }

  async function handleManualSearch(event?: { preventDefault(): void }) {
    event?.preventDefault()
    if (!manualSearchQuery.trim()) return

    setIsSearching(true)
    setError(null)
    try {
      const response = await searchDocuments(manualSearchQuery, {
        docIds: selectedDocIds,
        limit: 8,
      })
      setManualSearchResults(response.results)
      setManualSearchSummary(response.summary)
      appendActivity(
        createActivity(
          `Manual search returned ${response.results.length} ranked passages using ${String(response.summary.mode ?? 'hybrid')} retrieval.`,
          'retrieval',
        ),
      )
    } catch (searchError) {
      setError(searchError instanceof Error ? searchError.message : 'Unable to run semantic search')
    } finally {
      setIsSearching(false)
    }
  }

  async function handleCreateTextIngest() {
    if (!textDocForm.title.trim() || !textDocForm.content.trim()) return

    setIsCreatingTextDoc(true)
    setError(null)
    try {
      const created = await createTextDocument({
        title: textDocForm.title.trim(),
        type: textDocForm.type,
        tags: textDocForm.tags.split(',').map((item) => item.trim()).filter(Boolean),
        date: textDocForm.date || null,
        content: textDocForm.content,
        summary: textDocForm.summary || null,
      })
      await refreshDocumentsState(created.id)
      await refreshTelemetry()
      setCorpusMode('search')
      setTextDocForm({
        title: '',
        type: 'other',
        tags: 'internal, strategy',
        date: '',
        summary: '',
        content: '',
      })
      appendActivity(createActivity(`Added text source “${created.title}” and indexed it for retrieval.`))
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Unable to create text document')
    } finally {
      setIsCreatingTextDoc(false)
    }
  }

  async function handleUploadDocument() {
    if (!uploadForm.file) return

    setIsUploading(true)
    setError(null)
    try {
      const created = await uploadDocument({
        file: uploadForm.file,
        type: uploadForm.type,
        tags: uploadForm.tags.split(',').map((item) => item.trim()).filter(Boolean),
        date: uploadForm.date || null,
      })
      await refreshDocumentsState(created.id)
      await refreshTelemetry()
      setCorpusMode('search')
      setUploadForm({
        type: 'other',
        tags: 'internal',
        date: '',
        file: null,
      })
      appendActivity(createActivity(`Uploaded “${created.title}” and indexed its chunks for the live retrieval stack.`))
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'Unable to upload document')
    } finally {
      setIsUploading(false)
    }
  }

  async function handleExport(format: ExportFormat) {
    if (!draftId) return

    setIsExporting(format)
    setError(null)
    try {
      const { blob, filename } = await downloadDraftExport(draftId, format)
      const url = URL.createObjectURL(blob)
      const anchor = window.document.createElement('a')
      anchor.href = url
      anchor.download = filename
      window.document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
      appendActivity(createActivity(`Exported ${shortId(draftId)} as ${format.toUpperCase()}.`))
      await refreshTelemetry()
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : 'Unable to export draft')
    } finally {
      setIsExporting(null)
    }
  }

  async function handleLoadDraft(draft: StudioDraft) {
    setError(null)
    applyDraftState(draft)
    const lineage = await getDraftVersions(draft.id)
    setVersions(lineage)
    appendActivity(createActivity(`Loaded draft version ${draft.version} for review.`))
  }

  return (
    <div className="min-h-screen bg-studio-950 text-white">
      <div className="pointer-events-none absolute inset-0 bg-noise opacity-100" />
      <div className="pointer-events-none absolute inset-0 bg-grid bg-[size:64px_64px] opacity-[0.06]" />

      <div className="relative mx-auto flex min-h-screen max-w-[1880px] gap-6 px-5 py-6 sm:px-8 sm:py-8 xl:px-12 xl:py-10 2xl:px-20 2xl:py-16">
        <aside className="sticky top-10 hidden h-fit w-[92px] shrink-0 flex-col gap-4 rounded-[30px] px-4 py-5 text-white shadow-float obsidian-glass xl:flex">
          <div className="flex h-12 w-12 items-center justify-center rounded-[1rem] bg-studio-820/95 shadow-float">
            <Sparkles className="h-5 w-5 text-primary" />
          </div>

          <div className="flex flex-col gap-3">
            {navItems.map((item) => {
              const Icon = item.icon
              return (
                <Link
                  key={item.label}
                  href={item.href}
                  className={cn(
                    'flex h-12 w-12 items-center justify-center rounded-[1rem] transition duration-200 ease-in-out',
                    item.active
                      ? 'bg-studio-780/96 text-white shadow-glow'
                      : 'bg-studio-850/70 text-studio-200/70 hover:bg-studio-820/95 hover:text-white',
                  )}
                >
                  <Icon className="h-5 w-5" />
                </Link>
              )
            })}
          </div>

          <div className="mt-auto flex flex-col gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-[1rem] bg-studio-850/70 text-secondary shadow-float">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-[1rem] bg-studio-850/70 text-primary shadow-float">
              <Bot className="h-4 w-4" />
            </div>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col gap-6">
          <header className="rounded-[2rem] px-6 py-6 text-white shadow-float obsidian-glass sm:px-8 sm:py-7">
            <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
              <div className="max-w-4xl">
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-studio-200/55">
                  <span>George Weston Limited</span>
                  <ChevronRight className="h-3.5 w-3.5 text-studio-200/35" />
                  <span>GWL Memo Creation Studio</span>
                </div>
                <h1 className="mt-4 text-[2.15rem] font-semibold tracking-[-0.03em] text-studio-100 sm:text-[2.8rem]">
                  GWL Memo Creation Studio
                </h1>
                <p className="mt-4 max-w-3xl text-sm leading-7 text-studio-200/80 sm:text-[15px]">
                  A calm, editorial drafting environment for executive writing—where live retrieval, provenance, and refinement feel less like a dashboard and more like a precision instrument.
                </p>
              </div>

              <div className="flex flex-col items-start gap-3 xl:items-end">
                <div className="flex flex-wrap gap-2">
                  <span className="obsidian-chip-muted obsidian-chip">
                    <BookOpen className="h-3.5 w-3.5 text-primary" />
                    {selectedTemplate?.name ?? 'Loading template'}
                  </span>
                  <span className="obsidian-status-chip">
                    <Lock className="h-3.5 w-3.5" />
                    Private runtime
                  </span>
                  <span className="obsidian-chip-muted obsidian-chip">
                    <Database className="h-3.5 w-3.5 text-secondary" />
                    {embeddingStats?.indexed_chunks ?? 0} indexed chunks
                  </span>
                </div>

                <button
                  type="button"
                  onClick={handleGenerate}
                  disabled={isStreaming || !selectedTemplate || selectedDocIds.length === 0 || isBootstrapping}
                  className="obsidian-primary-button disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {activeStreamMode === 'generate' ? <Loader2 className="h-4 w-4 animate-spin" /> : <WandSparkles className="h-4 w-4" />}
                  {activeStreamMode === 'generate' ? 'Generating live draft…' : 'Generate live draft'}
                </button>
              </div>
            </div>
          </header>

          <div className="grid min-h-0 flex-1 gap-6 xl:grid-cols-[340px,minmax(0,1.08fr),390px]">
            <aside className="obsidian-panel-low p-5 sm:p-6">
              <div className="space-y-8">
                <div className="space-y-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="obsidian-kicker">Working set</p>
                      <h2 className="mt-3 text-2xl font-semibold text-studio-100">Data Sources</h2>
                    </div>
                    <span className="obsidian-chip-muted obsidian-chip">
                      {selectedDocIds.length}/{documents.length} selected
                    </span>
                  </div>

                  <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-2">
                    <div className="obsidian-subpanel p-3">
                      <div className="flex items-center gap-2 text-studio-200/70">
                        <Database className="h-3.5 w-3.5 text-primary" />
                        <span className="text-[11px] font-medium uppercase tracking-[0.18em]">Indexed chunks</span>
                      </div>
                      <div className="mt-2 flex items-end justify-between gap-3">
                        <p className="text-lg font-semibold text-studio-100">{embeddingStats?.indexed_chunks ?? 0}</p>
                        <p className="text-right text-[11px] leading-4 text-studio-200/55">
                          {embeddingStats?.indexed_documents ?? 0} docs · {embeddingStats?.dimension ?? 0} dims
                        </p>
                      </div>
                    </div>
                    <div className="obsidian-subpanel p-3">
                      <div className="flex items-center gap-2 text-studio-200/70">
                        <ShieldCheck className="h-3.5 w-3.5 text-secondary" />
                        <span className="text-[11px] font-medium uppercase tracking-[0.18em]">Private corpus</span>
                      </div>
                      <div className="mt-2 flex items-end justify-between gap-3">
                        <p className="text-lg font-semibold text-studio-100">100%</p>
                        <p className="text-right text-[11px] leading-4 text-studio-200/55">Source selection required</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  {documents.map((document) => {
                    const selected = selectedDocIds.includes(document.id)
                    return (
                      <button
                        key={document.id}
                        type="button"
                        onClick={() => toggleDocument(document.id)}
                        className={cn(
                          'w-full rounded-[1rem] p-4 text-left transition duration-200 ease-in-out',
                          selected
                            ? 'bg-studio-780/96 text-white shadow-glow'
                            : 'bg-studio-820/94 text-white shadow-panel hover:bg-studio-780/96',
                        )}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className="text-[11px] uppercase tracking-[0.2em] text-studio-200/55">
                              {humanize(document.type)}
                            </p>
                            <h3 className="mt-3 text-base font-semibold text-studio-100">{document.title}</h3>
                            <p className="mt-3 text-sm leading-7 text-studio-200/78">{document.summary}</p>
                          </div>
                          <span className={selected ? 'obsidian-status-chip' : 'obsidian-chip-muted obsidian-chip'}>
                            {selected ? 'Live' : 'Ready'}
                          </span>
                        </div>
                        <div className="mt-5 flex flex-wrap gap-2">
                          {document.tags.map((tag) => (
                            <span key={tag} className="obsidian-chip-muted obsidian-chip">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </button>
                    )
                  })}
                </div>

                <div className="obsidian-panel p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="obsidian-kicker">Corpus operations</p>
                      <h2 className="mt-3 text-xl font-semibold text-studio-100">Search, paste, or upload</h2>
                    </div>
                    <span className="obsidian-status-chip">
                      <ArrowRight className="h-3.5 w-3.5" />
                      Live backend
                    </span>
                  </div>

                  <div className="mt-5 flex gap-2 rounded-[1rem] bg-studio-850/96 p-1.5 shadow-float">
                    {corpusModes.map((mode) => {
                      const Icon = mode.icon
                      const active = corpusMode === mode.id
                      return (
                        <button
                          key={mode.id}
                          type="button"
                          onClick={() => setCorpusMode(mode.id)}
                          className={cn(
                            'flex flex-1 items-center justify-center gap-2 rounded-[0.9rem] px-3 py-2.5 text-sm transition duration-200 ease-in-out',
                            active
                              ? 'bg-studio-780/96 text-white shadow-glow'
                              : 'text-studio-200/65 hover:bg-studio-820/96 hover:text-white',
                          )}
                        >
                          <Icon className="h-4 w-4" />
                          {mode.label}
                        </button>
                      )
                    })}
                  </div>

                  {corpusMode === 'search' ? (
                    <div className="mt-5 space-y-4">
                      <form onSubmit={(event) => void handleManualSearch(event)} className="obsidian-subpanel p-4">
                        <div className="flex items-start gap-3">
                          <Search className="mt-3 h-4 w-4 text-primary" />
                          <textarea
                            value={manualSearchQuery}
                            onChange={(event) => setManualSearchQuery(event.target.value)}
                            className="obsidian-textarea min-h-[108px] border-0 bg-transparent px-0 py-1 shadow-none"
                            placeholder="Search the selected corpus for a grounded argument or evidence cluster..."
                          />
                        </div>
                        <button
                          type="submit"
                          disabled={isSearching || selectedDocIds.length === 0}
                          className="obsidian-secondary-button mt-4 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {isSearching ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSearch className="h-4 w-4" />}
                          Run hybrid search
                        </button>
                      </form>

                      {manualSearchSummary ? (
                        <div className="obsidian-subpanel p-4 text-sm text-studio-200/80">
                          <div className="flex flex-wrap gap-2 text-xs text-studio-200/60">
                            <span>{String(manualSearchSummary.mode ?? 'hybrid')} retrieval</span>
                            <span>·</span>
                            <span>{String(manualSearchSummary.returned ?? manualSearchResults.length)} hits</span>
                            <span>·</span>
                            <span>{String(manualSearchSummary.documents_hit ?? 0)} docs hit</span>
                          </div>
                        </div>
                      ) : null}

                      <div className="space-y-3">
                        {manualSearchResults.slice(0, 4).map((result) => (
                          <div key={result.chunk_id} className="obsidian-subpanel p-4">
                            <div className="flex items-center justify-between gap-3">
                              <span className="text-sm font-medium text-studio-100">{result.document_title}</span>
                              <span className="obsidian-chip-muted obsidian-chip">{formatScore(result.score)} overall</span>
                            </div>
                            <p className="mt-4 text-sm leading-7 text-studio-200/78">{result.text}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {corpusMode === 'text' ? (
                    <div className="mt-5 space-y-3">
                      <input
                        value={textDocForm.title}
                        onChange={(event) => setTextDocForm((current) => ({ ...current, title: event.target.value }))}
                        className="obsidian-input"
                        placeholder="Document title"
                      />
                      <div className="grid gap-3 sm:grid-cols-2">
                        <select
                          value={textDocForm.type}
                          onChange={(event) => setTextDocForm((current) => ({ ...current, type: event.target.value as DocumentType }))}
                          className="obsidian-select"
                        >
                          {documentTypes.map((type) => (
                            <option key={type.value} value={type.value}>
                              {type.label}
                            </option>
                          ))}
                        </select>
                        <input
                          value={textDocForm.date}
                          onChange={(event) => setTextDocForm((current) => ({ ...current, date: event.target.value }))}
                          className="obsidian-input"
                          placeholder="Date"
                        />
                      </div>
                      <input
                        value={textDocForm.tags}
                        onChange={(event) => setTextDocForm((current) => ({ ...current, tags: event.target.value }))}
                        className="obsidian-input"
                        placeholder="Tags (comma separated)"
                      />
                      <textarea
                        value={textDocForm.content}
                        onChange={(event) => setTextDocForm((current) => ({ ...current, content: event.target.value }))}
                        className="obsidian-textarea min-h-[190px]"
                        placeholder="Paste a board note, diligence memo, or strategy excerpt to index it in the local runtime..."
                      />
                      <button
                        type="button"
                        onClick={() => void handleCreateTextIngest()}
                        disabled={isCreatingTextDoc}
                        className="obsidian-primary-button disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isCreatingTextDoc ? <Loader2 className="h-4 w-4 animate-spin" /> : <MessageSquareText className="h-4 w-4" />}
                        Create text source
                      </button>
                    </div>
                  ) : null}

                  {corpusMode === 'upload' ? (
                    <div className="mt-5 space-y-3">
                      <div className="grid gap-3 sm:grid-cols-2">
                        <select
                          value={uploadForm.type}
                          onChange={(event) => setUploadForm((current) => ({ ...current, type: event.target.value as DocumentType }))}
                          className="obsidian-select"
                        >
                          {documentTypes.map((type) => (
                            <option key={type.value} value={type.value}>
                              {type.label}
                            </option>
                          ))}
                        </select>
                        <input
                          value={uploadForm.date}
                          onChange={(event) => setUploadForm((current) => ({ ...current, date: event.target.value }))}
                          className="obsidian-input"
                          placeholder="Date"
                        />
                      </div>
                      <input
                        value={uploadForm.tags}
                        onChange={(event) => setUploadForm((current) => ({ ...current, tags: event.target.value }))}
                        className="obsidian-input"
                        placeholder="Tags (comma separated)"
                      />
                      <label className="obsidian-subpanel block cursor-pointer px-4 py-8 text-center text-sm text-studio-200/72 transition duration-200 ease-in-out hover:bg-studio-720/96 hover:text-white">
                        <Upload className="mx-auto mb-3 h-5 w-5 text-primary" />
                        <span>{uploadForm.file ? uploadForm.file.name : 'Select a .txt, .pdf, or .docx file'}</span>
                        <input
                          type="file"
                          accept=".txt,.pdf,.docx"
                          className="hidden"
                          onChange={(event) => setUploadForm((current) => ({ ...current, file: event.target.files?.[0] ?? null }))}
                        />
                      </label>
                      <button
                        type="button"
                        onClick={() => void handleUploadDocument()}
                        disabled={isUploading || !uploadForm.file}
                        className="obsidian-secondary-button disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                        Upload and index
                      </button>
                    </div>
                  ) : null}
                </div>
              </div>
            </aside>

            <section className="flex min-w-0 flex-col gap-6">
              <div className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
                <div className="obsidian-panel p-6 sm:p-7">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="obsidian-kicker">Prompt orchestration</p>
                      <h2 className="mt-3 text-[1.55rem] font-semibold text-studio-100">Live drafting brief</h2>
                    </div>
                    <span className="obsidian-chip-muted obsidian-chip">
                      {selectedDocIds.length} source docs selected
                    </span>
                  </div>

                  <div className="mt-6 rounded-[1rem] bg-studio-760/96 p-4 shadow-float">
                    <textarea
                      value={instruction}
                      onChange={(event) => setInstruction(event.target.value)}
                      className="obsidian-textarea min-h-[190px] border-0 bg-transparent px-1 py-1 shadow-none"
                      placeholder="Describe the memo you want the system to generate..."
                    />
                  </div>

                  <div className="mt-5 flex flex-wrap gap-2">
                    {promptPresets.map((preset) => (
                      <button
                        key={preset}
                        type="button"
                        onClick={() => setInstruction((current) => `${current.trim()} ${preset}.`.trim())}
                        className="obsidian-chip-filter"
                      >
                        + {preset}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="relative overflow-hidden rounded-[1rem] bg-studio-820/95 p-6 text-white shadow-panel sm:p-7">
                  <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-[radial-gradient(circle_at_top,rgba(173,198,255,0.12),transparent_70%)]" />
                  <div className="relative">
                    <p className="obsidian-kicker">Refinement + exports</p>
                    <h2 className="mt-3 text-[1.55rem] font-semibold text-studio-100">Operational controls</h2>

                    <div className="mt-6 space-y-4 rounded-[1rem] bg-studio-760/96 p-4 shadow-float">
                      <p className="text-[11px] uppercase tracking-[0.2em] text-studio-200/55">Refinement instruction</p>
                      <textarea
                        value={refineInstruction}
                        onChange={(event) => setRefineInstruction(event.target.value)}
                        className="obsidian-textarea min-h-[126px] border-0 bg-transparent px-0 py-0 shadow-none"
                        placeholder="Describe how the current draft should be tightened or reframed..."
                      />
                      <div className="flex flex-wrap gap-2">
                        {(selectedTemplate?.sections ?? []).map((section) => {
                          const selected = selectedRefineSectionIds.includes(section.id)
                          return (
                            <button
                              key={section.id}
                              type="button"
                              onClick={() => toggleRefineSection(section.id)}
                              className={cn(
                                'rounded-md px-3 py-1.5 text-[11px] font-medium transition duration-200 ease-in-out',
                                selected
                                  ? 'bg-studio-780/96 text-white shadow-glow'
                                  : 'bg-studio-850/96 text-studio-200/68 hover:bg-studio-780/96 hover:text-white',
                              )}
                            >
                              {section.title}
                            </button>
                          )
                        })}
                      </div>
                      <button
                        type="button"
                        onClick={handleRefine}
                        disabled={isStreaming || !draftId || !selectedTemplate}
                        className="obsidian-secondary-button disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {activeStreamMode === 'refine' ? <Loader2 className="h-4 w-4 animate-spin" /> : <History className="h-4 w-4" />}
                        {activeStreamMode === 'refine' ? 'Refining…' : 'Refine current draft'}
                      </button>
                    </div>

                    <div className="mt-5 grid gap-3 sm:grid-cols-3">
                      {(['markdown', 'text', 'html'] as ExportFormat[]).map((format) => (
                        <button
                          key={format}
                          type="button"
                          onClick={() => void handleExport(format)}
                          disabled={!draftId || isStreaming}
                          className="obsidian-secondary-button justify-center disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {isExporting === format ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowDownToLine className="h-4 w-4" />}
                          {format.toUpperCase()}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-[1.5rem] bg-studio-850/96 p-6 text-white shadow-chrome sm:p-8">
                <div className="space-y-5">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <p className="obsidian-kicker">Draft canvas</p>
                      <h2 className="mt-3 text-[1.7rem] font-semibold tracking-[-0.02em] text-studio-100">{draftTitle}</h2>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <span className="obsidian-chip-muted obsidian-chip">{draftId ? shortId(draftId) : 'Unsaved draft'}</span>
                      <span className="obsidian-chip-muted obsidian-chip">Version {draftVersion ?? 0}</span>
                      {selectedDocuments.map((document) => (
                        <span key={document.id} className="obsidian-chip-muted obsidian-chip">
                          {document.title}
                        </span>
                      ))}
                    </div>
                  </div>

                  {error ? (
                    <div className="rounded-[1rem] bg-rose-400/10 px-4 py-4 text-sm text-rose-100 shadow-[inset_0_-2px_0_0_rgba(255,180,171,0.85)]">
                      {error}
                    </div>
                  ) : null}

                  <div className="grid gap-4">
                    {(selectedTemplate?.sections ?? []).map((section) => {
                      const content = draftSections[section.id] ?? ''
                      return (
                        <article
                          key={section.id}
                          className="rounded-[1rem] bg-studio-820/95 p-5 shadow-panel transition duration-200 ease-in-out hover:bg-studio-780/96 sm:p-6"
                        >
                          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <p className="text-[11px] uppercase tracking-[0.2em] text-studio-200/55">Section</p>
                              <h3 className="mt-2 text-xl font-semibold text-studio-100">{section.title}</h3>
                              {section.instructions ? (
                                <p className="mt-3 text-sm leading-7 text-studio-200/68">{section.instructions}</p>
                              ) : null}
                            </div>
                            <span className={content ? 'obsidian-status-chip' : 'obsidian-chip-muted obsidian-chip'}>
                              {content ? 'Grounded' : isStreaming ? 'Drafting' : 'Ready'}
                            </span>
                          </div>
                          <div className="mt-5 min-h-[140px] rounded-[1rem] bg-studio-760/96 px-4 py-4 text-[15px] leading-7 text-studio-100 shadow-float">
                            {content ? (
                              <p className="whitespace-pre-wrap">{content}</p>
                            ) : (
                              <p className="text-studio-200/56">
                                {isStreaming
                                  ? 'Live content is streaming into this section…'
                                  : 'Generate or refine a draft to populate this section with cited executive-ready language.'}
                              </p>
                            )}
                          </div>
                        </article>
                      )
                    })}
                  </div>
                </div>
              </div>
            </section>

            <aside className="flex flex-col gap-6">
              <div className="obsidian-panel p-5 sm:p-6">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="obsidian-kicker">AI runtime</p>
                    <h2 className="mt-3 text-[1.5rem] font-semibold text-studio-100">Generation activity</h2>
                  </div>
                  <span className={isStreaming ? 'obsidian-status-chip' : 'obsidian-chip-muted obsidian-chip'}>
                    {isStreaming ? `${activeStreamMode} live` : 'Standing by'}
                  </span>
                </div>

                <div className="mt-6 rounded-[1rem] bg-studio-760/96 p-4 shadow-float">
                  <div className="flex items-center justify-between text-sm text-studio-200/78">
                    <span>Pipeline progress</span>
                    <span>{progressPercent}%</span>
                  </div>
                  <div className="obsidian-track mt-4">
                    <div
                      className="obsidian-progress h-full rounded-full transition-all duration-300"
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>
                </div>

                <div className="mt-5 space-y-3">
                  {runtimeActivity.slice(-8).reverse().map((item) => (
                    <div key={item.id} className="obsidian-subpanel flex gap-3 p-3.5">
                      <div className="mt-1 flex h-8 w-8 items-center justify-center rounded-[0.75rem] bg-studio-820/90 text-primary">
                        <MessageSquareText className="h-3.5 w-3.5" />
                      </div>
                      <div>
                        <p className="text-sm leading-7 text-studio-200/82">{item.message}</p>
                        <p className="mt-2 text-[11px] uppercase tracking-[0.18em] text-studio-200/50">
                          {item.stage ? humanize(item.stage) : humanize(item.kind)} · {formatDateTime(item.timestamp)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="obsidian-panel-high p-5 sm:p-6">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="obsidian-kicker">Provenance</p>
                    <h2 className="mt-3 text-[1.5rem] font-semibold text-studio-100">Retrieved evidence</h2>
                  </div>
                  <span className="obsidian-chip-muted obsidian-chip">{retrievedResults.length} passages</span>
                </div>

                <div className="mt-5 space-y-3">
                  {retrievedResults.length === 0 ? (
                    <div className="obsidian-subpanel p-4 text-sm leading-7 text-studio-200/56">
                      Once generation or refinement starts, top-ranked passages and score breakdowns will appear here.
                    </div>
                  ) : (
                    retrievedResults.slice(0, 5).map((result) => (
                      <div key={result.chunk_id} className="obsidian-subpanel p-4">
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-sm font-medium text-studio-100">{result.document_title}</span>
                          <span className="obsidian-chip-muted obsidian-chip">{formatScore(result.score)} overall</span>
                        </div>
                        <div className="mt-4 flex flex-wrap gap-2 text-[11px] text-studio-200/60">
                          <span>keyword {formatScore(result.keyword_score)}</span>
                          <span>·</span>
                          <span>vector {formatScore(result.vector_score)}</span>
                          {result.matched_terms.length > 0 ? (
                            <>
                              <span>·</span>
                              <span>{result.matched_terms.join(', ')}</span>
                            </>
                          ) : null}
                        </div>
                        <p className="mt-4 text-sm leading-7 text-studio-200/80">{result.text}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="obsidian-panel p-5 sm:p-6">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="obsidian-kicker">Draft lineage</p>
                    <h2 className="mt-3 text-[1.5rem] font-semibold text-studio-100">Versions + activity</h2>
                  </div>
                  <History className="mt-1 h-4 w-4 text-studio-200/50" />
                </div>

                <div className="mt-5 space-y-3">
                  {versionList.length === 0 ? (
                    <div className="obsidian-subpanel p-4 text-sm leading-7 text-studio-200/56">
                      Generate a draft to start a version history.
                    </div>
                  ) : (
                    versionList.map((version) => (
                      <button
                        key={version.id}
                        type="button"
                        onClick={() => void handleLoadDraft(version)}
                        className={cn(
                          'w-full rounded-[1rem] p-4 text-left transition duration-200 ease-in-out',
                          version.id === draftId
                            ? 'bg-studio-780/96 text-white shadow-glow'
                            : 'bg-studio-760/96 text-white shadow-float hover:bg-studio-720/96',
                        )}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-sm font-medium text-studio-100">Version {version.version}</span>
                          <span className="text-[11px] uppercase tracking-[0.18em] text-studio-200/50">
                            {formatDateTime(version.updated_at)}
                          </span>
                        </div>
                        <p className="mt-3 text-sm leading-7 text-studio-200/76">{version.title}</p>
                      </button>
                    ))
                  )}
                </div>

                <div className="mt-6 space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-studio-100">Recent drafts</p>
                    <Clock3 className="h-4 w-4 text-studio-200/45" />
                  </div>
                  <div className="space-y-3">
                    {recentDrafts.slice(0, 4).map((draft) => (
                      <button
                        key={draft.id}
                        type="button"
                        onClick={() => void handleLoadDraft(draft)}
                        className="w-full rounded-[1rem] bg-studio-760/96 p-3.5 text-left shadow-float transition duration-200 ease-in-out hover:bg-studio-720/96"
                      >
                        <p className="text-sm font-medium text-studio-100">{draft.title}</p>
                        <p className="mt-2 text-xs text-studio-200/55">v{draft.version} · {formatDateTime(draft.updated_at)}</p>
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="relative overflow-hidden rounded-[1rem] bg-studio-820/95 p-5 text-white shadow-panel sm:p-6">
                <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(78,222,163,0.16),transparent_55%)]" />
                <div className="relative">
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-[1rem] bg-secondary/18 text-secondary shadow-float">
                      <ShieldCheck className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="obsidian-kicker">Trust surface</p>
                      <h2 className="mt-3 text-[1.5rem] font-semibold text-studio-100">Security & auditability</h2>
                      <p className="mt-4 text-sm leading-7 text-studio-200/78">
                        Documents stay inside the private environment, provenance is preserved, and each run is logged as part of the demo narrative.
                      </p>
                    </div>
                  </div>

                  <div className="mt-5 grid gap-3">
                    {auditLogs.slice(0, 4).map((entry) => (
                      <div key={entry.id} className="obsidian-subpanel px-4 py-3.5">
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-sm text-studio-100">{humanize(entry.action)}</span>
                          <span className="text-[11px] uppercase tracking-[0.18em] text-studio-200/45">
                            {formatDateTime(entry.created_at)}
                          </span>
                        </div>
                        <p className="mt-2 text-xs text-studio-200/56">{entry.entity_type} · {shortId(entry.entity_id)}</p>
                      </div>
                    ))}
                    {auditLogs.length === 0 ? (
                      <div className="obsidian-subpanel px-4 py-3.5 text-sm text-studio-200/70">
                        Audit records will appear here after generation, refinement, export, or ingestion.
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            </aside>
          </div>
        </div>
      </div>
    </div>
  )
}
