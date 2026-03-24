# Executive Document Studio — Full Product & Technical Specification

## Demo Objectives
- Demonstrate secure, private AI-powered document drafting for executives
- Show live retrieval from a pre-indexed corpus of internal documents
- Show live LLM generation with streaming output
- Make the "real AI" nature unmistakable via process visibility and provenance
- Align with the use case requested by Anita and Daniel: combining 10 years of internal data

## Target Audience
- George Weston Limited leadership and innovation team
- Primary personas: corporate development executives, board-facing communicators

## Success Criteria for Demo
- User can select a template and drag in relevant documents in under 30 seconds
- Live draft generation completes in under 15 seconds with visible streaming
- Inline citations prove the output is grounded in the provided documents
- Refinements are intelligently applied, not cosmetic
- UI clearly conveys that data stays private and processing is local
- Backend can be redeployed on George Weston's own Azure tenant post-demo

---

## Product Overview

### Core Value Proposition
A secure, private AI workspace where executives can synthesize years of internal documents into polished board memos, investor presentations, and strategic communications—without data leaving their environment.

### Key Capabilities
1. Document Library with semantic search
2. Template-based document creation
3. Live AI drafting with retrieval-augmented generation (RAG)
4. Inline citations showing provenance
5. Iterative refinement via natural language
6. Version history and export options
7. Security and audit visibility

---

## User Flows

### Flow 1: Generate a Board Memo

1. User lands on home dashboard
2. Sees pre-loaded Document Library with annual reports, acquisition case studies, strategic plans
3. Clicks "New Document" → selects "Board Memo" template
4. Drags 4–6 relevant documents into working set
5. Types instruction: "Draft a board memo evaluating the acquisition of a regional organic food distributor"
6. Observes live process: retrieval → context building → streaming generation
7. Reviews draft with inline citations
8. Requests refinements via natural language
9. Exports to Word or PDF

### Flow 2: Semantic Search Before Drafting
1. User opens Document Library
2. Types query: "past acquisition challenges"
3. System returns relevant document excerpts with similarity scores
4. User clicks "Use in new draft" → auto-populates working set

### Flow 3: Refinement via AI Chat
1. User opens existing draft
2. Opens AI Chat sidebar
3. Types: "Add a section on regulatory considerations"
4. System retrieves relevant mentions and inserts new section with citations

---

## Demo "Wow" Moments

### Moment 1: Speed of Context Assembly
- Status: "Retrieving relevant passages…" with document names scrolling
- Then: "Found 47 relevant passages from 6 documents" in under 3 seconds

### Moment 2: Streaming Generation
- Text appears progressively, not all at once
- Section headers appear first, then content fills in section by section

### Moment 3: Inline Citations
- Hover over any paragraph → see which document(s) it came from
- Click citation → opens side panel with source snippet and metadata
- Proves output is grounded in actual documents

### Moment 4: Intelligent Refinement
- Ask: "Make the risk section more conservative"
- Observe: only risk section updates, not the whole document
- Shows model understands document structure

### Moment 5: Security Indicators
- Persistent banner: "🔒 All data processed within your private environment"
- Expandable panel: "View processing details"
- Audit log: timestamped record of operations

### Moment 6: Export with Provenance
- Export to Word includes appendix: "Sources Used"
- Lists all documents that contributed to the draft

---

## Technical Architecture

### High-Level

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Document     │  │ Template     │  │ Draft Workspace      │  │
│  │ Library      │  │ Selector     │  │ • Editor + AI Chat   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │ REST + SSE
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI Python)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Document     │  │ RAG Engine   │  │ Draft Generation     │  │
│  │ Service      │  │ • Embedding  │  │ • LLM Client         │  │
│  │              │  │ • Retrieval  │  │ • Template Engine    │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Vector DB (ChromaDB)  │  Doc Storage (SeaweedFS)  │  SQLite    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture

### Technology Stack
- Framework: Next.js 14 (App Router)
- Language: TypeScript
- Styling: Tailwind CSS + shadcn/ui
- Rich Text Editor: TipTap
- State: Zustand
- Streaming: Server-Sent Events (EventSource)

### Key Routes

| Route | Purpose |
|-------|---------|
| `/` | Dashboard with quick actions |
| `/library` | Document Library with search |
| `/templates` | Template browser |
| `/drafts/new` | New draft wizard |
| `/drafts/[id]` | Draft workspace with editor |

### Core Components
- **DocumentLibrary**: Grid view, semantic search, drag to working set
- **TemplateSelector**: Card grid of templates with preview
- **DraftWorkspace**: Two-column layout, editor + AI chat
- **AIProcessPanel**: Real-time status, retrieval details
- **DocumentCitations**: Sources used, hover for snippets

---

## Backend Architecture

### Technology Stack
- Framework: FastAPI (Python 3.11+)
- LLM: OpenAI SDK (streaming)
- Embeddings: text-embedding-3-small
- Vector DB: ChromaDB (embedded)
- Storage: SeaweedFS S3
- Metadata: SQLite

### Service Modules

#### DocumentService
- Upload, list, get, delete documents
- Store in SeaweedFS S3

#### EmbeddingService
- Embed text → vector
- Index documents in ChromaDB
- Query similar chunks

#### RetrievalService
- Retrieve relevant chunks from specified documents
- Build context string with metadata

#### DraftService
- Generate draft (SSE stream)
- Refine draft (SSE stream)
- Version history

#### TemplateService
- List and get templates

#### ExportService
- Export to Word/PDF/Markdown

---

## Data Models

### Document
```json
{
  "id": "doc_001",
  "title": "Annual Report 2023",
  "type": "annual_report",
  "tags": ["finance", "strategy"],
  "date": "2023-12-31",
  "chunk_ids": ["chunk_001", "chunk_002"]
}
```

### Chunk
```json
{
  "id": "chunk_001",
  "document_id": "doc_001",
  "text": "In 2023, George Weston Limited...",
  "embedding": [0.123, -0.456, ...],
  "metadata": {"page": 5, "section": "Financial Highlights"}
}
```

### Draft
```json
{
  "id": "draft_001",
  "template_id": "template_board_memo",
  "title": "Board Memo - Acquisition",
  "content": {"executive_summary": "...", "background": "..."},
  "citations": [{"section": "executive_summary", "document_id": "doc_003"}],
  "working_set": ["doc_001", "doc_003"]
}
```

### Template
```json
{
  "id": "template_board_memo",
  "name": "Board Memo",
  "sections": [
    {"id": "executive_summary", "title": "Executive Summary"},
    {"id": "background", "title": "Background"},
    {"id": "analysis", "title": "Analysis"},
    {"id": "recommendation", "title": "Recommendation"},
    {"id": "risk_assessment", "title": "Risk Assessment"}
  ]
}
```

---

## Retrieval + Generation Pipeline

### Step-by-Step

1. **User submits instruction**
   - POST /api/drafts/generate with template_id, doc_ids, instruction

2. **Backend initiates SSE stream**
   - Returns Content-Type: text/event-stream

3. **Retrieval phase**
   - Embed user instruction
   - Query ChromaDB for top-k chunks
   - Emit: `{"type": "status", "message": "Retrieved 47 passages from 6 documents"}`
   - Emit: `{"type": "citations", "citations": [...]}`

4. **Context assembly**
   - Concatenate chunks with metadata
   - Truncate to max tokens (e.g., 15k)
   - Emit: `{"type": "status", "message": "Building context (12,340 tokens)"}`

5. **LLM generation**
   - Build prompt: system + template + context + instruction
   - Call OpenAI with stream=True
   - For each chunk: `{"type": "content", "section": "...", "text": "..."}`

6. **Finalization**
   - Store draft and citations
   - Emit: `{"type": "done", "draft_id": "..."}`

---

## API Specifications

### REST Endpoints

```
POST   /api/documents/upload
GET    /api/documents
GET    /api/documents/{id}
DELETE /api/documents/{id}
GET    /api/documents/search?q={query}

POST   /api/embeddings/index/{document_id}
POST   /api/embeddings/query

POST   /api/drafts/generate          → SSE stream
POST   /api/drafts/refine/{id}       → SSE stream
GET    /api/drafts/{id}
GET    /api/drafts/{id}/versions

GET    /api/templates
GET    /api/templates/{id}

POST   /api/export/{draft_id}?format={word|pdf|markdown}
```

### SSE Event Types

| Type | Payload | Purpose |
|------|---------|---------|
| `status` | `{message: string}` | Progress updates |
| `citations` | `{citations: Citation[]}` | Sources retrieved |
| `content` | `{section: string, text: string}` | Streaming text |
| `error` | `{message: string}` | Error notification |
| `done` | `{draft_id: string}` | Completion |

---

## Security Model

### Data Privacy
- All document storage on SeaweedFS S3 within Shakudo cluster
- All embeddings in ChromaDB (local, no external calls)
- LLM calls use OpenAI API (can swap for Azure OpenAI for air-gap)
- No data logged to external services

### Authentication
- Demo mode: No auth (single user)
- Production: OIDC integration with George Weston's Azure AD

### Provenance & Audit
- Every draft includes citations mapping sections to source chunks
- Every operation logged with timestamp, user, action
- Exported documents include "Sources Used" appendix

### UI Security Indicators
- Banner: "🔒 All data processed within your private environment"
- Expandable "Processing Details" panel
- Audit log viewer in settings

---

## Deployment on Shakudo

### Container Image
- Multi-stage Dockerfile: Build Next.js + FastAPI
- Single container running both (ports 3000, 8000)

### Kubernetes Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: executive-document-studio
  namespace: hyperplane-jhub
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: app
        image: your-registry/exec-doc-studio:v1
        ports:
        - containerPort: 3000
          name: frontend
        - containerPort: 8000
          name: backend
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-credentials
              key: openai-api-key
        - name: S3_ENDPOINT
          value: http://seaweedfs-s3.hyperplane-jhub.svc.cluster.local:8333
        volumeMounts:
        - name: data
          mountPath: /app/data
```

---

## Mock Data Requirements

### Documents to Create (10-15 total)

1. **Annual Reports (2015-2024)** - 5-7 mock reports
2. **Acquisition Case Studies** - Shoppers Drug Mart learnings, hypothetical smaller acquisition
3. **Strategic Plans** - 2025 Strategic Plan, 2023 ESG Report
4. **Market Analyses** - Canadian Grocery Retail Landscape, Competitive Intelligence
5. **Board Presentation Templates** - Sample deck with standard sections

### Document Format
- Store as PDFs for realism
- Extract text for indexing
- Generate chunk metadata: page, section

---

## Implementation Phases

### Phase 1: Backend Core (Day 1)
- FastAPI project structure
- DocumentService (upload, list, get)
- SeaweedFS S3 integration
- ChromaDB setup
- EmbeddingService

### Phase 2: Retrieval + Generation (Day 1-2)
- RetrievalService
- DraftService with streaming
- OpenAI integration
- Prompt templates

### Phase 3: Frontend Foundation (Day 2)
- Next.js project with Tailwind + shadcn/ui
- DocumentLibrary component
- TemplateSelector
- DraftWorkspace with TipTap editor

### Phase 4: Streaming Integration (Day 2-3)
- SSE client in frontend
- AIProcessPanel with live status
- Streaming text to editor
- Citations panel

### Phase 5: Refinement + Export (Day 3)
- Refinement flow
- AI Chat sidebar
- Export to Word/PDF
- Version history

### Phase 6: Polish + Deploy (Day 3)
- Create and load mock documents
- Pre-index embeddings
- Security indicators
- Deploy to Shakudo
- Demo rehearsals

---

## Demo Script (5 Minutes)

### Minute 1: Setup & Context
- Open app, show Dashboard
- Document Library with pre-loaded corpus
- Semantic search demo: "past acquisition challenges"

### Minute 2: Select Template & Documents
- "New Document" → Board Memo template
- Drag in 5 documents: Annual Report, Acquisition Case Study, Market Analysis, etc.

### Minute 3: Generate Draft
- Type instruction
- Watch process: retrieval → context → streaming generation
- Text streams section by section

### Minute 4: Review & Refine
- Hover to see citations
- Click citation to see source
- AI Chat: "Make risk section more conservative"
- Watch targeted update

### Minute 5: Export & Security
- Export to Word with "Sources Used" appendix
- Point to security banner
- Mention Azure OpenAI deployment option

---

## Success Metrics

- Draft generation: < 15 seconds
- Retrieval: < 3 seconds
- Citation accuracy: 90%+ grounded in documents
- Refinement quality: Non-trivial, contextually appropriate changes
- User feedback: "This is impressive" or "Can we pilot this?"

---

## Open Questions

1. LLM Provider: OpenAI API (simpler) or Azure OpenAI (production-ready)?
2. Auth for Demo: Single-user or OIDC integration?
3. Mock Data: Fictional or request sanitized real data?
4. Refinement Granularity: Section-level or paragraph-level?
5. Export Formats: Word + PDF, or also PowerPoint?

---

## Post-Demo Next Steps

1. Collect feedback from Anita and Daniel
2. Discuss deployment options: Azure tenant, self-hosted LLM
3. Integration with George Weston document systems
4. Security review and compliance
5. Pilot program scope and timeline

---

## Conclusion

This specification provides a complete blueprint for building a demo web app that will showcase secure, private, AI-powered executive document drafting for George Weston Limited. The design emphasizes:

- **Live AI**: Real retrieval and generation with streaming
- **Provenance**: Inline citations proving output is grounded in documents
- **Security**: Visible indicators and audit trail
- **Professional UX**: Enterprise-grade interface
- **Deployability**: Ready for Shakudo and future Azure tenant migration

Ready to proceed with implementation upon approval.
