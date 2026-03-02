# NLP-to-SQL v2 Demo

A natural language to SQL chatbot demo for Reagan Presidential Library CRM data, built on Shakudo platform.

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│   OpenWebUI     │────▶│  Pipeline Filters    │────▶│  Vanna AI       │
│   (Chat UI)     │     │  • Presidio PII      │     │  Microservice   │
│                 │◀────│  • NLP-SQL Router    │◀────│  (Claude 4.5)   │
└─────────────────┘     └──────────────────────┘     └────────┬────────┘
                                                              │
                                                              ▼
                                                     ┌─────────────────┐
                                                     │   Supabase      │
                                                     │   PostgreSQL    │
                                                     │   (reagan_crm)  │
                                                     └─────────────────┘
```

## Components

### 1. Vanna AI Microservice (`app.py`)
FastAPI service that uses Vanna AI with Claude Sonnet 4.5 to convert natural language questions to SQL queries.

**Endpoints:**
- `POST /ask` - Convert natural language to SQL and execute
- `POST /openwebui` - OpenWebUI-compatible endpoint for pipeline integration
- `POST /train` - Train Vanna with new DDL/documentation/Q&A pairs
- `GET /schema` - Get database schema information
- `GET /health` - Health check

### 2. OpenWebUI Pipelines (`pipelines/`)

**Presidio PII Filter** (`presidio_pii_filter.py`)
- Ingress/egress guardrail for PII detection
- Uses regex patterns (no LLM needed) for fast detection (<100ms)
- Detects: credit cards, SSN, emails, phone numbers, names
- Configurable: redact, warn, or block

**NLP-SQL Router** (`nlp_sql_filter.py`)
- Routes database questions to Vanna microservice
- Pattern matching for SQL-related queries
- Falls through to default LLM for non-database questions

### 3. Database Schema (`schema/`)

Reagan CRM schema with three main tables:
- **Account** - Households and Organizations (foundations)
- **Contact** - Individual people (donors, members)
- **Opportunity** - Donations, memberships, grants

## Setup Instructions

### 1. Database Setup

Set environment variables:
```bash
export DATABASE_HOST=supabase-metaflow-postgresql.hyperplane-supabase-metaflow.svc.cluster.local
export DATABASE_PORT=5432
export DATABASE_NAME=postgres
export DATABASE_USER=postgres
export DATABASE_PASSWORD=<your-password>
```

Create schema and seed data:
```bash
python schema/execute_schema.py
```

### 2. Train Vanna AI

After database is set up:
```bash
export ANTHROPIC_API_KEY=<your-api-key>
python schema/003_vanna_training.py
```

### 3. Deploy Microservice on Shakudo

Create a microservice with:
- **Name**: `nlp-sql-v2`
- **Environment**: `basic-ai-tools-small`
- **Git Server**: `demos`
- **Branch**: `main`
- **Working Directory**: `/tmp/git/monorepo/nlp-sql-v2/`
- **Port**: `8787`

Required environment variables:
- `DATABASE_HOST`
- `DATABASE_PORT`
- `DATABASE_NAME`
- `DATABASE_USER`
- `DATABASE_PASSWORD`
- `DATABASE_SCHEMA=reagan_crm`
- `ANTHROPIC_API_KEY`

### 4. Configure OpenWebUI

1. Install the Presidio PII filter in OpenWebUI pipelines
2. Install the NLP-SQL router filter
3. Configure the router to point to your Vanna microservice URL

## Sample Queries

The demo supports these Reagan sample queries:

1. **Membership lookup**: "What is Daniel Garcia's current membership?"
2. **Expiration date**: "When is the expiration date?"
3. **Payment history**: "List all the payments made for this account"
4. **Donor search**: "Search for all donors who donated more than $500 for the last 3 years within Ventura County"
5. **Foundation giving**: "Show all donations made by the Zilkha Foundation"
6. **Recent changes**: "Show me all the records that were modified for the last 2 days"

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_HOST` | PostgreSQL host | `supabase-metaflow-postgresql...` |
| `DATABASE_PORT` | PostgreSQL port | `5432` |
| `DATABASE_NAME` | Database name | `postgres` |
| `DATABASE_USER` | Database user | `postgres` |
| `DATABASE_PASSWORD` | Database password | (required) |
| `DATABASE_SCHEMA` | Schema name | `reagan_crm` |
| `ANTHROPIC_API_KEY` | Claude API key | (required) |
| `VANNA_MODEL` | Vanna model name | `reagan-crm-v1` |

## File Structure

```
nlp-sql-v2/
├── app.py                     # FastAPI microservice
├── run.sh                     # Shakudo startup script
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── pipelines/
│   ├── __init__.py
│   ├── nlp_sql_filter.py      # OpenWebUI NLP-SQL router
│   └── presidio_pii_filter.py # OpenWebUI PII guardrail
├── schema/
│   ├── 001_create_schema.sql  # Database DDL
│   ├── 002_seed_data.sql      # Demo seed data
│   ├── 003_vanna_training.py  # Vanna training script
│   └── execute_schema.py      # Schema setup script
└── utils/
    ├── __init__.py
    ├── database.py            # PostgreSQL utilities
    └── vanna_client.py        # Claude-powered Vanna client
```

## Tech Stack

- **LLM**: Claude Sonnet 4.5 (via Anthropic API)
- **Text-to-SQL**: Vanna AI
- **Database**: PostgreSQL (Supabase)
- **API Framework**: FastAPI
- **Chat UI**: OpenWebUI
- **PII Detection**: Presidio-like regex patterns
- **Platform**: Shakudo
