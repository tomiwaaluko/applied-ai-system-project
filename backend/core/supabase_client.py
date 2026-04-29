"""Supabase pgvector helpers for the CareerScope corpus and reports.

SQL setup to run in Supabase SQL editor or a migration:

```sql
create table reports (
  id uuid primary key default gen_random_uuid(),
  report_data jsonb not null,
  created_at timestamp default now()
);

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

create unique index if not exists corpus_source_doc_content_idx
  on public.corpus (source_file, doc_type, md5(content));

create index if not exists corpus_embedding_ivfflat_idx
  on public.corpus using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

create or replace function public.match_corpus(
  query_embedding vector(768),
  match_doc_type text,
  match_count int default 5
)
returns table (
  content text,
  similarity_score float,
  source_file text,
  doc_type text,
  metadata jsonb
)
language sql
stable
as $$
  select
    corpus.content,
    1 - (corpus.embedding <=> query_embedding) as similarity_score,
    corpus.source_file,
    corpus.doc_type,
    corpus.metadata
  from public.corpus
  where corpus.doc_type = match_doc_type
  order by corpus.embedding <=> query_embedding
  limit match_count;
$$;
```
"""

from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING, Any

from core.logger import get_logger
from core.models import CareerReport

if TYPE_CHECKING:
    from supabase import Client
else:
    Client = Any


EMBEDDING_DIMENSIONS = 768
VALID_DOC_TYPES = {"jd", "benchmark"}

logger = get_logger("supabase_client")

_anon_client: Client | None = None
_service_client: Client | None = None


SETUP_SQL = """
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

create unique index if not exists corpus_source_doc_content_idx
  on public.corpus (source_file, doc_type, md5(content));

create index if not exists corpus_embedding_ivfflat_idx
  on public.corpus using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

create or replace function public.match_corpus(
  query_embedding vector(768),
  match_doc_type text,
  match_count int default 5
)
returns table (
  content text,
  similarity_score float,
  source_file text,
  doc_type text,
  metadata jsonb
)
language sql
stable
as $$
  select
    corpus.content,
    1 - (corpus.embedding <=> query_embedding) as similarity_score,
    corpus.source_file,
    corpus.doc_type,
    corpus.metadata
  from public.corpus
  where corpus.doc_type = match_doc_type
  order by corpus.embedding <=> query_embedding
  limit match_count;
$$;
"""


def _get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        logger.error("missing_environment_variable", variable=name)
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_supabase_client(use_service_role: bool = False) -> Client:
    """Create and cache a Supabase client lazily."""
    global _anon_client, _service_client

    try:
        from supabase import create_client
    except ImportError as exc:
        logger.error("supabase_dependency_missing", package="supabase")
        raise RuntimeError("Missing dependency: install supabase-py with `pip install supabase`.") from exc

    url = _get_env("SUPABASE_URL")
    if use_service_role:
        if _service_client is None:
            _service_client = create_client(url, _get_env("SUPABASE_SERVICE_ROLE_KEY"))
        return _service_client

    if _anon_client is None:
        _anon_client = create_client(url, _get_env("SUPABASE_ANON_KEY"))
    return _anon_client


def _validate_doc_type(doc_type: str) -> None:
    if doc_type not in VALID_DOC_TYPES:
        logger.error("invalid_doc_type", doc_type=doc_type, valid_doc_types=sorted(VALID_DOC_TYPES))
        raise ValueError(f"doc_type must be one of {sorted(VALID_DOC_TYPES)}")


def _validate_embedding(embedding: list[float], field_name: str = "embedding") -> None:
    if not isinstance(embedding, list) or len(embedding) != EMBEDDING_DIMENSIONS:
        logger.error(
            "invalid_embedding_dimensions",
            field_name=field_name,
            expected=EMBEDDING_DIMENSIONS,
            actual=len(embedding) if isinstance(embedding, list) else None,
        )
        raise ValueError(f"{field_name} must be a list with {EMBEDDING_DIMENSIONS} dimensions")


def _document_id(source_file: str, doc_type: str, content: str) -> str:
    seed = f"{source_file}:{doc_type}:{content}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def create_corpus_table() -> Any:
    """Run the corpus setup SQL through a project-provided SQL execution RPC.

    Supabase's Python Data API does not expose arbitrary SQL execution by default.
    If your project has an RPC such as `exec_sql` or `execute_sql`, this helper
    will use it; otherwise run SETUP_SQL manually in Supabase SQL editor.
    """
    client = get_supabase_client(use_service_role=True)
    last_error: Exception | None = None

    for rpc_name in ("exec_sql", "execute_sql"):
        for params in ({"sql": SETUP_SQL}, {"query": SETUP_SQL}):
            try:
                response = client.rpc(rpc_name, params).execute()
                logger.info("corpus_table_setup_complete", rpc=rpc_name)
                return response
            except Exception as exc:  # pragma: no cover - depends on project RPCs.
                last_error = exc

    logger.error("corpus_table_setup_failed", error=str(last_error))
    raise RuntimeError(
        "Unable to run setup SQL through Supabase RPC. Run SETUP_SQL manually "
        "or create an exec_sql/execute_sql RPC."
    ) from last_error


def upsert_document(
    content: str,
    embedding: list[float],
    source_file: str,
    doc_type: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Insert or update one corpus document."""
    if not content or not content.strip():
        logger.error("empty_document_content", source_file=source_file, doc_type=doc_type)
        raise ValueError("content must be non-empty")

    _validate_doc_type(doc_type)
    _validate_embedding(embedding)

    document = {
        "id": _document_id(source_file, doc_type, content),
        "content": content,
        "embedding": embedding,
        "source_file": source_file,
        "doc_type": doc_type,
        "metadata": metadata or {},
    }

    response = get_supabase_client(use_service_role=True).table("corpus").upsert(document).execute()
    data = response.data
    logger.info("document_upserted", source_file=source_file, doc_type=doc_type)

    if isinstance(data, list):
        return data[0] if data else None
    return data


def similarity_search(query_embedding: list[float], doc_type: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Search the corpus using the `match_corpus` RPC and normalize result records."""
    _validate_doc_type(doc_type)
    _validate_embedding(query_embedding, field_name="query_embedding")

    if top_k < 1:
        logger.error("invalid_top_k", top_k=top_k)
        raise ValueError("top_k must be at least 1")

    response = (
        get_supabase_client()
        .rpc(
            "match_corpus",
            {
                "query_embedding": query_embedding,
                "match_doc_type": doc_type,
                "match_count": top_k,
            },
        )
        .execute()
    )

    records = response.data or []
    normalized: list[dict[str, Any]] = []
    for record in records:
        score = record.get("similarity_score", record.get("similarity", record.get("score")))
        normalized.append(
            {
                "content": record.get("content", ""),
                "similarity_score": float(score or 0.0),
                "source_file": record.get("source_file"),
                "doc_type": record.get("doc_type", doc_type),
                "metadata": record.get("metadata") or {},
            }
        )

    logger.info("similarity_search_complete", doc_type=doc_type, top_k=top_k, results=len(normalized))
    return normalized


def is_source_file_seeded(source_file: str, doc_type: str | None = None) -> bool:
    """Return True if at least one corpus row exists for a source file."""
    query = get_supabase_client(use_service_role=True).table("corpus").select("id").eq("source_file", source_file).limit(1)
    if doc_type is not None:
        _validate_doc_type(doc_type)
        query = query.eq("doc_type", doc_type)

    response = query.execute()
    return bool(response.data)


def save_report(report: CareerReport) -> str:
    """Persist a CareerReport JSON payload and return its report id."""
    if not report.id:
        report.id = str(uuid.uuid4())

    payload = {"id": report.id, "report_data": report.model_dump(mode="json")}
    response = get_supabase_client(use_service_role=True).table("reports").insert(payload).execute()
    data = response.data or []
    logger.info("report_saved", report_id=report.id)

    if data and data[0].get("id"):
        return str(data[0]["id"])
    return report.id


def get_report(report_id: str) -> dict[str, Any] | None:
    """Fetch one saved report by id."""
    response = (
        get_supabase_client(use_service_role=True)
        .table("reports")
        .select("id, report_data, created_at")
        .eq("id", report_id)
        .limit(1)
        .execute()
    )
    data = response.data or []
    return data[0] if data else None


def list_reports(limit: int = 20) -> list[dict[str, Any]]:
    """Return recent saved reports."""
    response = (
        get_supabase_client(use_service_role=True)
        .table("reports")
        .select("id, report_data, created_at")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data or []
