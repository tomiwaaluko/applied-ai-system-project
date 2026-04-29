"""Seed local JD and benchmark text files into the Supabase corpus table."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.embed_text import MAX_EMBED_TOKENS, get_embedding


DATA_DIRS = (
    (REPO_ROOT / "data" / "jds", "jd"),
    (REPO_ROOT / "data" / "benchmarks", "benchmark"),
)
CORPUS_TABLE = "corpus"


def chunk_text(text: str, max_tokens: int = MAX_EMBED_TOKENS) -> list[str]:
    tokens = text.split()
    return [
        " ".join(tokens[index : index + max_tokens])
        for index in range(0, len(tokens), max_tokens)
    ]


def discover_text_files() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    for directory, doc_type in DATA_DIRS:
        if not directory.exists():
            continue
        files.extend((path, doc_type) for path in sorted(directory.glob("*.txt")))
    return files


def _load_core_helper(name: str) -> Callable[..., Any] | None:
    try:
        import core.supabase_client as supabase_client
    except ImportError:
        return None

    helper = getattr(supabase_client, name, None)
    return helper if callable(helper) else None


def _core_file_exists(source_file: str) -> bool | None:
    for helper_name in (
        "is_source_file_seeded",
        "document_exists",
        "source_file_exists",
        "corpus_document_exists",
        "is_document_seeded",
    ):
        helper = _load_core_helper(helper_name)
        if helper is None:
            continue
        return bool(helper(source_file))
    return None


def _core_upsert_document(
    content: str,
    embedding: list[float],
    source_file: str,
    doc_type: str,
    metadata: dict[str, Any],
) -> bool:
    helper = _load_core_helper("upsert_document")
    if helper is None:
        return False

    helper(
        content=content,
        embedding=embedding,
        source_file=source_file,
        doc_type=doc_type,
        metadata=metadata,
    )
    return True


def _get_supabase_client():
    load_dotenv()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required to seed the corpus."
        )

    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError(
            "supabase is required. Install dependencies with `pip install -r requirements.txt`."
        ) from exc

    return create_client(url, key)


_DIRECT_SUPABASE_CLIENT = None


def _direct_supabase_client():
    global _DIRECT_SUPABASE_CLIENT
    if _DIRECT_SUPABASE_CLIENT is None:
        _DIRECT_SUPABASE_CLIENT = _get_supabase_client()
    return _DIRECT_SUPABASE_CLIENT


def file_already_seeded(source_file: str) -> bool:
    core_result = _core_file_exists(source_file)
    if core_result is not None:
        return core_result

    response = (
        _direct_supabase_client()
        .table(CORPUS_TABLE)
        .select("id")
        .eq("source_file", source_file)
        .limit(1)
        .execute()
    )
    return bool(getattr(response, "data", None))


def upsert_document(
    content: str,
    embedding: list[float],
    source_file: str,
    doc_type: str,
    metadata: dict[str, Any],
) -> None:
    if _core_upsert_document(content, embedding, source_file, doc_type, metadata):
        return

    payload = {
        "content": content,
        "embedding": embedding,
        "source_file": source_file,
        "doc_type": doc_type,
        "metadata": metadata,
    }
    _direct_supabase_client().table(CORPUS_TABLE).upsert(payload).execute()


def seed_file(path: Path, doc_type: str) -> int:
    source_file = path.name
    if file_already_seeded(source_file):
        print(f"[SKIP] Already seeded: {source_file}")
        return 0

    text = path.read_text(encoding="utf-8").strip()
    chunks = [chunk for chunk in chunk_text(text) if chunk.strip()]
    if not chunks:
        print(f"[SKIP] Empty file: {source_file}")
        return 0

    for index, chunk in enumerate(chunks, start=1):
        embedding = get_embedding(chunk)
        upsert_document(
            content=chunk,
            embedding=embedding,
            source_file=source_file,
            doc_type=doc_type,
            metadata={
                "chunk_index": index,
                "chunk_count": len(chunks),
                "relative_path": str(path.relative_to(REPO_ROOT)),
            },
        )

    print(f"[OK] Seeded: {source_file} ({len(chunks)} chunks)")
    return len(chunks)


def main() -> None:
    files = discover_text_files()
    seeded_documents = 0
    seeded_chunks = 0

    for path, doc_type in files:
        chunk_count = seed_file(path, doc_type)
        if chunk_count:
            seeded_documents += 1
            seeded_chunks += chunk_count

    print(f"Total documents seeded: {seeded_documents}")
    print(f"Total chunks seeded: {seeded_chunks}")


if __name__ == "__main__":
    main()
