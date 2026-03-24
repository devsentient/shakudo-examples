# Executive Document Studio

A premium Next.js + FastAPI demo app for secure, grounded executive document drafting.

## What this demo shows
- Figma-like enterprise UI with multi-pane drafting workspace
- Private internal document working set with explicit source selection
- Hybrid retrieval using deterministic local embeddings + keyword ranking
- Live SSE draft generation and refinement with staged runtime telemetry
- Grounded provenance / citation panel with score breakdowns
- Seeded George Weston-style mock documents and executive templates
- Persisted draft records in SQLite with version history and audit logs
- Real backend workflows for ingestion, retrieval, refinement, export, and lineage

## Deployment pattern
This project now follows the same deployment shape as the 123Dentist demo:
- one root `run.sh`
- one FastAPI/Uvicorn service
- one exposed port (3000 by default for browser access on Hyperplane)
- frontend pre-built to static assets and served by FastAPI

That means you can run the full demo as a single service instead of managing a separate frontend server.

## Project structure
- `frontend/` — Next.js 14 app and premium studio workspace
- `backend/` — FastAPI backend with ingestion, retrieval, generation, audit, and export APIs
- `run.sh` — single-service launcher in the same style as the 123Dentist demo
- `scripts/` — convenience wrappers for local start/stop/check
- `specs/` — original product and technical specification

## Backend capabilities
- `POST /api/documents/text` — create a document from raw text
- `POST /api/documents/upload` — upload `.txt`, `.pdf`, or `.docx` and extract text
- `GET /api/documents/search` — search across document chunks with hybrid scoring
- `GET /api/documents/audit` — inspect recent audit trail entries
- `GET /api/embeddings/stats` — inspect local vector index coverage
- `POST /api/embeddings/reindex` — rebuild deterministic local embeddings
- `POST /api/drafts/generate` — stream a new draft via SSE
- `POST /api/drafts/{draft_id}/refine` — stream a refined draft version via SSE
- `GET /api/drafts/{draft_id}/versions` — retrieve full draft lineage
- `POST /api/export/{draft_id}?format=markdown|text|html` — export drafts in multiple formats

## Configuration

### Runtime environment
See:
- `backend/.env.example`
- `frontend/.env.example`

Important values:
- `HOST` — bind host, default `0.0.0.0`
- `PORT` — single-service app port, default `8787`
- `STUDIO_DATA_DIR` — data directory for SQLite + uploads, default `backend/data`
- `STUDIO_DB_PATH` — optional explicit override for the SQLite file
- `STUDIO_UPLOADS_DIR` — optional explicit override for the upload directory
- `NEXT_PUBLIC_API_BASE_URL` — API base baked into the frontend build; default `/api` for same-origin single-service deployment

## Run exactly like 123Dentist
From the project root:

```bash
./run.sh
```

What it does:
1. creates/reuses `backend/.venv`
2. installs backend Python dependencies
3. builds the frontend into `frontend/out` if needed
4. starts FastAPI on a single port (`8787` by default)
5. serves the built frontend and the backend API from the same service

Override the port if needed:

```bash
PORT=8787 ./run.sh
```

## Convenience scripts

### Start locally
```bash
./scripts/dev-up.sh
```

### Stop locally
```bash
./scripts/dev-down.sh
```

### Check the stack
```bash
./scripts/stack-check.sh
```

By default these scripts use the same single-port deployment on `3000`.

## Manual local run

### Build frontend
```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=/api npm run build
```

### Start backend + static frontend server
```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
HOST=0.0.0.0 PORT=3000 uvicorn main:app --reload --port 3000
```

Then open: http://localhost:3000

## Validation performed
The current branch has been validated with:
- `npm run build` in `frontend/`
- backend Python compilation
- backend service-level validation for:
  - text ingestion,
  - file upload ingestion,
  - hybrid search,
  - SSE generation,
  - draft refinement,
  - version lineage,
  - HTML export,
- single-service local stack startup via `./run.sh` / `./scripts/dev-up.sh`
- browser-facing checks from the same FastAPI process and port

## Notes
- The current backend uses deterministic retrieval and deterministic section composition to maximize demo reliability.
- The visual design is intentionally premium and enterprise-forward, with runtime telemetry surfaced in the UI.
- The deployment model now mirrors the simpler 123Dentist pattern while keeping the richer Executive Document Studio backend features.
