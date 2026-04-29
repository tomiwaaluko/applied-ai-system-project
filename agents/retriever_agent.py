from __future__ import annotations

import asyncio
import os
import time
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv

from core.logger import get_logger
from core.models import ParsedJD, ParsedResume, RetrievedContext
from core.supabase_client import similarity_search
from scripts.embed_text import get_embedding


SYNTHESIS_MODEL = os.getenv("GEMINI_RETRIEVER_MODEL", "gemini-2.0-flash-lite")
LOW_MATCH_THRESHOLD = 0.5


@lru_cache(maxsize=1)
def _get_gemini_client() -> Any:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required for retriever synthesis.")

    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("google-genai is required. Install dependencies from requirements.txt.") from exc

    return genai.Client(api_key=api_key)


class RetrieverAgent:
    def __init__(self, model: str = SYNTHESIS_MODEL) -> None:
        self.model = model
        self.logger = get_logger("retriever_agent")

    async def retrieve(self, resume: ParsedResume, jd: ParsedJD) -> RetrievedContext:
        start = time.perf_counter()
        query = self._build_query(jd)
        query_embedding = await asyncio.to_thread(get_embedding, query)

        similar_jds_task = asyncio.to_thread(similarity_search, query_embedding, "jd", 5)
        benchmarks_task = asyncio.to_thread(similarity_search, query_embedding, "benchmark", 3)
        similar_jds, benchmarks = await asyncio.gather(similar_jds_task, benchmarks_task)

        self._log_retrieval_scores("jd", similar_jds)
        self._log_retrieval_scores("benchmark", benchmarks)
        self._warn_if_low_match(similar_jds + benchmarks)

        industry_context = await self._synthesize_context(resume, jd, similar_jds, benchmarks)

        elapsed = time.perf_counter() - start
        self.logger.info(
            "retrieval_complete",
            model=self.model,
            query=query,
            similar_jds=len(similar_jds),
            benchmarks=len(benchmarks),
            processing_time_seconds=round(elapsed, 3),
        )
        return RetrievedContext(
            similar_jds=similar_jds,
            benchmarks=benchmarks,
            industry_context=industry_context,
        )

    def _build_query(self, jd: ParsedJD) -> str:
        skills = " ".join(jd.required_skills[:5])
        return f"{jd.role_title} {jd.industry.value} {skills}".strip()

    def _log_retrieval_scores(self, doc_type: str, records: list[dict[str, Any]]) -> None:
        for record in records:
            self.logger.info(
                "retrieved_document",
                doc_type=doc_type,
                source_file=record.get("source_file"),
                similarity_score=record.get("similarity_score"),
            )

    def _warn_if_low_match(self, records: list[dict[str, Any]]) -> None:
        if not records:
            self.logger.warning(
                "LOW_CORPUS_MATCH",
                reason="no_records",
                message="retrieved context may be unreliable. Consider seeding more relevant JDs.",
            )
            return

        scores = [float(record.get("similarity_score") or 0.0) for record in records]
        if all(score < LOW_MATCH_THRESHOLD for score in scores):
            self.logger.warning(
                "LOW_CORPUS_MATCH",
                max_similarity=max(scores),
                message="retrieved context may be unreliable. Consider seeding more relevant JDs.",
            )

    async def _synthesize_context(
        self,
        resume: ParsedResume,
        jd: ParsedJD,
        similar_jds: list[dict[str, Any]],
        benchmarks: list[dict[str, Any]],
    ) -> str:
        if not similar_jds and not benchmarks:
            return (
                "No relevant corpus documents were retrieved, so this context is limited to the parsed "
                "resume and job description. Seed more role-specific job descriptions and benchmark "
                "resumes to improve RAG grounding."
            )

        prompt = self._synthesis_prompt(resume, jd, similar_jds, benchmarks)
        return await asyncio.to_thread(self._generate_text, prompt)

    def _generate_text(self, prompt: str) -> str:
        client = _get_gemini_client()
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={"temperature": 0.2},
        )
        text = getattr(response, "text", None)
        if not text and hasattr(response, "candidates"):
            text = str(response.candidates[0].content.parts[0].text)
        return (text or "").strip()

    def _synthesis_prompt(
        self,
        resume: ParsedResume,
        jd: ParsedJD,
        similar_jds: list[dict[str, Any]],
        benchmarks: list[dict[str, Any]],
    ) -> str:
        jd_docs = "\n\n".join(
            f"JD {index} (score={doc.get('similarity_score')}):\n{doc.get('content', '')[:2500]}"
            for index, doc in enumerate(similar_jds, start=1)
        )
        benchmark_docs = "\n\n".join(
            f"Benchmark {index} (score={doc.get('similarity_score')}):\n{doc.get('content', '')[:2500]}"
            for index, doc in enumerate(benchmarks, start=1)
        )
        return f"""You are a context synthesis agent. Given retrieved job description and benchmark documents,
synthesize a 2-3 paragraph industry context summary. Focus on:
- What skills and experience levels this industry/role tier typically expects
- Common patterns in strong candidates for this role type
- Any notable trends in the retrieved JDs

Return only the synthesis text. Do not reference specific company names from retrieved docs.

Target role: {jd.role_title}
Target industry: {jd.industry.value}
Candidate inferred level: {resume.inferred_level}
Candidate inferred industry: {resume.inferred_industry.value}
Target required skills: {", ".join(jd.required_skills)}

Retrieved job descriptions:
{jd_docs}

Retrieved benchmark resumes:
{benchmark_docs}
"""


async def retrieve_context(resume: ParsedResume, jd: ParsedJD) -> RetrievedContext:
    return await RetrieverAgent().retrieve(resume, jd)
