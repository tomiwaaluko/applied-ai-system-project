from __future__ import annotations

import asyncio
import json
import os
import re
import statistics
import time
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from pydantic import ValidationError

from core.logger import get_logger
from core.models import GapAnalysis, ParsedJD, ParsedResume, RetrievedContext


GAP_ANALYZER_MODEL = os.getenv("GEMINI_GAP_ANALYZER_MODEL", "gemini-2.0-flash")


class GapAnalysisError(Exception):
    pass


@lru_cache(maxsize=1)
def _get_gemini_client() -> Any:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required for gap analysis.")

    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("google-genai is required. Install dependencies from requirements.txt.") from exc

    return genai.Client(api_key=api_key)


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(stripped[start : end + 1])


class GapAnalyzerAgent:
    def __init__(self, model: str = GAP_ANALYZER_MODEL) -> None:
        self.model = model
        self.logger = get_logger("gap_analyzer_agent")

    async def analyze(
        self,
        resume: ParsedResume,
        jd: ParsedJD,
        retrieved_context: RetrievedContext,
    ) -> GapAnalysis:
        start = time.perf_counter()
        prompt = self._prompt(resume, jd, retrieved_context)
        payload = await asyncio.to_thread(self._generate_json, prompt)

        try:
            analysis = GapAnalysis.model_validate(payload)
        except ValidationError as exc:
            raise GapAnalysisError(f"Gap analysis JSON failed schema validation: {exc}") from exc

        if analysis.match_score > 0.95:
            self.logger.warning(
                "match_score_capped",
                original_match_score=analysis.match_score,
                capped_match_score=0.95,
            )
            analysis.match_score = 0.95

        confidences = [gap.confidence for gap in analysis.skill_gaps]
        average_confidence = statistics.fmean(confidences) if confidences else 0.0
        elapsed = time.perf_counter() - start

        self.logger.info(
            "gap_analysis_complete",
            agent="gap_analyzer_agent",
            model=self.model,
            match_score=analysis.match_score,
            critical_gaps=len(analysis.critical_gaps),
            average_skill_confidence=round(average_confidence, 3),
            confidence=analysis.confidence,
            reasoning_trace_excerpt=analysis.reasoning_trace[:240],
            processing_time_seconds=round(elapsed, 3),
        )
        return analysis

    def _generate_json(self, prompt: str) -> dict[str, Any]:
        client = _get_gemini_client()
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0.15,
            },
        )
        text = getattr(response, "text", None)
        if not text and hasattr(response, "candidates"):
            text = str(response.candidates[0].content.parts[0].text)
        if not text:
            raise GapAnalysisError("Gemini gap analysis response was empty.")
        return _extract_json(text)

    def _prompt(self, resume: ParsedResume, jd: ParsedJD, retrieved_context: RetrievedContext) -> str:
        schema = json.dumps(GapAnalysis.model_json_schema(), indent=2)
        context_payload = {
            "resume": resume.model_dump(mode="json"),
            "job_description": jd.model_dump(mode="json"),
            "retrieved_context": retrieved_context.model_dump(mode="json"),
        }
        return f"""You are a senior technical recruiter and career coach specializing in early-career software engineering.
You will be given:
1. A candidate's parsed resume
2. A target job description
3. Industry context from similar roles

Your task: perform a rigorous, evidence-based skill gap analysis.

Scoring rules:
- match_score: 0.0-1.0 representing overall fit. Base this on skill overlap, experience level match,
  and project relevance. Do NOT inflate. A typical new grad applying to a mid-level role should score 0.45-0.60.
- For each skill gap:
  - gap_type "missing": skill not mentioned anywhere in resume
  - gap_type "partial": mentioned but at surface level (e.g., "familiar with" vs. "built production systems in")
  - gap_type "strong": resume clearly demonstrates this skill
  - confidence: 0.0-1.0 - your certainty in this classification
  - evidence: cite the specific resume text OR absence of it

IMPORTANT: Be honest. Students improve from accurate feedback, not flattery.
Be specific. Generic gaps ("improve your communication skills") are useless.
Only flag skills that appear in required_skills or preferred_skills of the JD.

critical_gaps: list ONLY required_skills that are missing or partial.
reasoning_trace: write 2-3 concise sentences explaining your overall assessment process. Do not reveal private chain-of-thought.

Return ONLY valid JSON matching this GapAnalysis schema:
{schema}

Input data:
{json.dumps(context_payload, indent=2)}
"""


async def analyze_gaps(
    resume: ParsedResume,
    jd: ParsedJD,
    retrieved_context: RetrievedContext,
) -> GapAnalysis:
    return await GapAnalyzerAgent().analyze(resume, jd, retrieved_context)
