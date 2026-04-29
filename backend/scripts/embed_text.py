"""Gemini embedding helper for CareerScope corpus scripts."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv


EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMENSIONS = 768
MAX_EMBED_TOKENS = 512


def _truncate_text(text: str, max_tokens: int = MAX_EMBED_TOKENS) -> str:
    tokens = text.split()
    return " ".join(tokens[:max_tokens])


@lru_cache(maxsize=1)
def _get_client():
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required to generate embeddings.")

    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "google-genai is required. Install dependencies with `pip install -r requirements.txt`."
        ) from exc

    return genai.Client(api_key=api_key)


def _extract_values(response) -> list[float]:
    if hasattr(response, "embeddings") and response.embeddings:
        embedding = response.embeddings[0]
        values = getattr(embedding, "values", None)
        if values is not None:
            return list(values)

    if hasattr(response, "embedding") and response.embedding is not None:
        embedding = response.embedding
        values = getattr(embedding, "values", None)
        if values is not None:
            return list(values)

    if isinstance(response, dict):
        embedding = response.get("embedding")
        if isinstance(embedding, dict) and "values" in embedding:
            return list(embedding["values"])

        embeddings = response.get("embeddings")
        if embeddings:
            first = embeddings[0]
            if isinstance(first, dict) and "values" in first:
                return list(first["values"])

    raise RuntimeError("Gemini embedding response did not include embedding values.")


def get_embedding(text: str) -> list[float]:
    """Embed non-empty text with Gemini text-embedding-004."""
    if not isinstance(text, str):
        raise TypeError("text must be a string.")

    chunk = _truncate_text(text.strip())
    if not chunk:
        raise ValueError("text must not be empty.")

    client = _get_client()
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=chunk,
        config={"output_dimensionality": EMBEDDING_DIMENSIONS},
    )

    vector = _extract_values(response)
    if len(vector) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Expected {EMBEDDING_DIMENSIONS}-dimensional embedding, got {len(vector)}."
        )

    return [float(value) for value in vector]
