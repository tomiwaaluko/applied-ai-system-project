from __future__ import annotations

import asyncio
import json
import os
import re
import time
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from pydantic import ValidationError

from core.logger import get_logger
from core.models import GapAnalysis, ParsedResume, Roadmap


DEFAULT_ROADMAP_MODEL = "gemini-2.0-flash"


class RoadmapError(Exception):
    pass


@lru_cache(maxsize=1)
def _get_gemini_client() -> Any:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required for roadmap agent calls.")

    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("google-genai is required. Install dependencies from requirements.txt.") from exc

    return genai.Client(api_key=api_key)


def _get_default_model() -> str:
    load_dotenv()
    return os.getenv("GEMINI_ROADMAP_MODEL", DEFAULT_ROADMAP_MODEL)


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


def _response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text:
        return text

    if hasattr(response, "candidates") and response.candidates:
        parts = getattr(response.candidates[0].content, "parts", [])
        if parts:
            part_text = getattr(parts[0], "text", None)
            if part_text:
                return str(part_text)

    return ""


def _output_tokens(response: Any, text: str) -> int:
    usage = getattr(response, "usage_metadata", None)
    if usage:
        for field in ("candidates_token_count", "output_token_count"):
            value = getattr(usage, field, None)
            if value is not None:
                return int(value)

    # Rough approximation used when the SDK/model response omits token usage.
    return max(1, len(text) // 4)


class RoadmapAgent:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or _get_default_model()
        self.logger = get_logger("roadmap_agent")

    async def build_roadmap(
        self,
        resume: ParsedResume,
        gap_analysis: GapAnalysis,
    ) -> Roadmap:
        start = time.perf_counter()
        prompt = self._prompt(resume, gap_analysis)
        payload, output_length, output_tokens = await asyncio.to_thread(self._generate_json, prompt)

        try:
            roadmap = Roadmap.model_validate(payload)
        except ValidationError as exc:
            raise RoadmapError(f"Roadmap JSON failed schema validation: {exc}") from exc

        if len(roadmap.project_ideas) != 2:
            raise RoadmapError(
                f"Roadmap must include exactly 2 project ideas; got {len(roadmap.project_ideas)}."
            )

        action_count = len(roadmap.thirty_day) + len(roadmap.sixty_day) + len(roadmap.ninety_day)
        elapsed = time.perf_counter() - start
        self.logger.info(
            "roadmap_built",
            agent="roadmap_agent",
            model=self.model,
            output_tokens=output_tokens,
            output_length=output_length,
            actions=action_count,
            projects=len(roadmap.project_ideas),
            processing_time_seconds=round(elapsed, 3),
        )
        return roadmap

    def _generate_json(self, prompt: str) -> tuple[dict[str, Any], int, int]:
        client = _get_gemini_client()
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        )
        text = _response_text(response)
        if not text:
            raise RoadmapError("Gemini roadmap response was empty.")
        return _extract_json(text), len(text), _output_tokens(response, text)

    def _prompt(self, resume: ParsedResume, gap_analysis: GapAnalysis) -> str:
        schema = json.dumps(Roadmap.model_json_schema(), indent=2)
        input_payload = {
            "resume": resume.model_dump(mode="json"),
            "gap_analysis": gap_analysis.model_dump(mode="json"),
        }
        return f"""You are a career development coach creating a personalized, actionable roadmap.
You will receive a student's resume and their gap analysis.

Create a structured 30/60/90-day action plan that:
- 30 days: addresses the most critical skill gaps with specific, beginner-accessible actions
- 60 days: builds toward intermediate mastery, includes a portfolio-worthy project idea
- 90 days: positions the candidate for the target role, includes interview prep steps

Rules:
- Every action must be SPECIFIC (not "learn Python" - "complete Python's official asyncio tutorial and build one async CLI tool")
- Every action must be ACHIEVABLE in the timeframe for a full-time student
- Resources should be free or common (LeetCode, official docs, YouTube, GitHub projects)
- project_ideas: propose 2 project ideas that would directly address critical_gaps
  Each project should be completable in 2-3 weekends

Return ONLY valid JSON matching the Roadmap schema.

Roadmap schema:
{schema}

Additional output constraints:
- Use the exact top-level keys from the schema: thirty_day, sixty_day, ninety_day, project_ideas.
- Each RoadmapItem timeframe must be one of: "30_day", "60_day", "90_day".
- Each project idea must be an object with concrete title, description, critical_gaps_addressed, suggested_stack, and weekend_scope fields.
- Do not include markdown, commentary, citations, or text outside the JSON object.

Input data:
{json.dumps(input_payload, indent=2)}
"""


async def build_roadmap(
    resume: ParsedResume,
    gap_analysis: GapAnalysis,
) -> Roadmap:
    return await RoadmapAgent().build_roadmap(resume, gap_analysis)
