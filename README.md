# CareerScope AI

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Next.js 14](https://img.shields.io/badge/Next.js-14-black)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Built for CodePath AI110](https://img.shields.io/badge/built%20for-CodePath%20AI110-orange)

CareerScope is a full-stack multi-agent AI system that analyzes a resume against any job description and returns an evidence-based gap analysis, 30/60/90-day roadmap, and recruiter-ready outreach drafts.

## Demo

> [Watch the full demo walkthrough](LOOM_LINK_HERE)

Live app placeholder: VERCEL_URL_HERE

## Architecture

![CareerScope architecture diagram](assets/architecture_diagram.png)

The monorepo contains a Next.js 14 frontend, a FastAPI backend, and the existing Python multi-agent pipeline. The frontend uploads a PDF resume and job description input to `/api/analyze`; the FastAPI backend streams Server-Sent Events while the parser, retriever, gap analyzer, roadmap, outreach, and report-writer steps complete. Reports are saved to Supabase and can be reopened through `/api/reports/{id}`.

## Repository Layout

```text
backend/
  agents/      Gemini-powered parser, retriever, gap, roadmap, outreach, orchestrator
  api/         FastAPI app with health, analyze, and reports routes
  core/        Pydantic models, guardrails, logging, Gemini, Supabase helpers
  data/        Deterministic test fixtures
  eval/        Evaluation harness
  scripts/     Corpus embedding and seeding scripts
  tests/       Unit and API integration tests
frontend/
  app/         Next.js App Router pages
  components/  Upload form, progress tracker, report dashboard
  lib/         API client and TypeScript model mirrors
assets/        Architecture diagram and screenshots
```

## Local Setup

Use Python 3.11 or 3.12 for the backend. The current local Python 3.14 environment can run tests, but some Supabase transitive dependencies are more reliable on 3.11/3.12.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Required backend environment variables:

```env
GEMINI_API_KEY=your_gemini_key_here
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
FRONTEND_URL=http://localhost:3000
```

Run the backend:

```powershell
cd backend
uvicorn api.main:app --reload --port 8000
```

Run the frontend:

```powershell
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## Supabase SQL

Run this in the Supabase SQL editor:

```sql
create extension if not exists vector;

create table if not exists public.corpus (
  id uuid primary key default gen_random_uuid(),
  content text not null,
  embedding vector(768) not null,
  source_file text,
  doc_type text not null check (doc_type in ('jd', 'benchmark')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table reports (
  id uuid primary key default gen_random_uuid(),
  report_data jsonb not null,
  created_at timestamp default now()
);
```

The implementation uses Google Gemini only through `google-genai`. Embeddings use `text-embedding-004` and Supabase `vector(768)`.

## Backend CLI

The original CLI still works from inside `backend/`:

```powershell
python main.py --resume data/test_fixtures/resumes/entry_swe.pdf --jd-text "Software Engineer role requiring Python, FastAPI, PostgreSQL, React, and production API experience."
```

Generated JSON and Markdown reports are written to `backend/outputs/`.

## Deployment

Railway backend:

```text
Root directory: backend
Start command: uvicorn api.main:app --host 0.0.0.0 --port $PORT
Environment: GEMINI_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, FRONTEND_URL
```

Vercel frontend:

```text
Root repository deploy using vercel.json
Set NEXT_PUBLIC_API_URL to the Railway backend URL
Replace REPLACE_WITH_RAILWAY_URL in vercel.json before production deployment
```

## Testing

Current backend verification:

```text
python -m pytest tests/ -v --tb=short
11 passed in 0.30s
```

Backend startup verification:

```text
uvicorn api.main:app --port 8000
GET /api/health -> {"status":"ok","version":"1.0.0"}
```

Frontend verification:

```text
npm run build
Compiled successfully with Next.js 14.2.35
```

The live eval harness still depends on Gemini quota. Earlier live eval attempts reached Gemini `429 RESOURCE_EXHAUSTED`; unit and API tests mock external calls.

## Base Project

CareerScope extends PawPal+ from CodePath AI110 Module 1-3. PawPal+ introduced the applied-AI pattern of structured prompting, retrieval-backed context, and recommendation generation. CareerScope evolves that foundation into a deployed career intelligence product with RAG-grounded retrieval, typed agent handoffs, SSE progress streaming, and a report dashboard.

## Design Decisions

- Supabase over ChromaDB: managed Postgres, pgvector persistence, deployment-friendly data access, and a straightforward reports table.
- Direct Gemini SDK over LangChain: explicit prompts, schemas, retries, model choices, and no hidden orchestration abstraction.
- Pydantic models across agents: every agent produces validated structures that the next stage can consume safely.
- SSE for progress: the frontend receives observable pipeline progress without waiting for the full report.

## Reflection

See `model_card.md` for system limitations, misuse risks, testing surprises, and the AI collaboration log.

## License

MIT
