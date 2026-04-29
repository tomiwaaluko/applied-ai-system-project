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
from core.models import GapAnalysis, Industry, OutreachDraft, ParsedJD, ParsedResume


OUTREACH_MODEL = os.getenv("GEMINI_OUTREACH_MODEL", "gemini-2.0-flash")
LINKEDIN_DM_MAX_CHARS = 300
COLD_EMAIL_BODY_MAX_WORDS = 150
BANNED_OPENERS = (
    "i hope this message finds you well",
    "hope this message finds you well",
)


class OutreachDraftError(Exception):
    pass


@lru_cache(maxsize=1)
def _get_gemini_client() -> Any:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required for outreach drafting.")

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


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\S+\b", text))


def _normalize_space(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def _remove_banned_openers(text: str) -> str:
    cleaned = text.strip()
    for opener in BANNED_OPENERS:
        pattern = re.compile(rf"^\s*{re.escape(opener)}[,.!\s-]*", re.IGNORECASE)
        cleaned = pattern.sub("", cleaned)
    return cleaned.lstrip(" ,.!-\n\t")


def _truncate_linkedin_dm(text: str) -> str:
    cleaned = _normalize_space(_remove_banned_openers(text))
    if len(cleaned) <= LINKEDIN_DM_MAX_CHARS:
        return cleaned

    limit = LINKEDIN_DM_MAX_CHARS - 1
    truncated = cleaned[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{truncated}."


def _truncate_email_body(text: str) -> str:
    cleaned = _remove_banned_openers(text.strip())
    words = cleaned.split()
    if len(words) <= COLD_EMAIL_BODY_MAX_WORDS:
        return cleaned

    truncated = " ".join(words[:COLD_EMAIL_BODY_MAX_WORDS]).rstrip(" ,;:")
    if not truncated.endswith((".", "!", "?")):
        truncated += "."
    return truncated


def _detect_tone(jd: ParsedJD) -> str:
    context = " ".join(
        [
            jd.company or "",
            jd.role_title,
            jd.raw_text,
            jd.industry.value,
        ]
    ).lower()
    formal_terms = (
        "finance",
        "fintech",
        "bank",
        "capital",
        "investment",
        "insurance",
        "enterprise",
        "compliance",
        "risk",
        "regulated",
        "global",
        "fortune",
    )
    conversational_terms = (
        "startup",
        "founding",
        "seed",
        "series a",
        "series b",
        "fast-paced",
        "tech",
        "developer",
        "ai",
        "ml",
        "product-led",
    )

    if jd.industry in {Industry.FINTECH, Industry.BIG_TECH} or any(term in context for term in formal_terms):
        return "formal"
    if jd.industry in {Industry.STARTUP, Industry.AI_ML} or any(term in context for term in conversational_terms):
        return "conversational"
    return "conversational"


class OutreachAgent:
    def __init__(self, model: str | None = None) -> None:
        load_dotenv()
        self.model = model or os.getenv("GEMINI_OUTREACH_MODEL", OUTREACH_MODEL)
        self.logger = get_logger("outreach_agent")

    async def draft_outreach(
        self,
        resume: ParsedResume,
        jd: ParsedJD,
        gap_analysis: GapAnalysis,
    ) -> OutreachDraft:
        start = time.perf_counter()
        tone = _detect_tone(jd)
        prompt = self._prompt(resume, jd, gap_analysis, tone)
        payload = await asyncio.to_thread(self._generate_json, prompt)

        try:
            draft = OutreachDraft.model_validate(payload)
        except ValidationError as exc:
            raise OutreachDraftError(f"Outreach JSON failed schema validation: {exc}") from exc

        draft = self._enforce_constraints(draft, tone)
        elapsed = time.perf_counter() - start

        self.logger.info(
            "outreach_draft_complete",
            agent="outreach_agent",
            model=self.model,
            detected_tone=tone,
            linkedin_dm_chars=len(draft.linkedin_dm),
            cold_email_subject_chars=len(draft.cold_email_subject),
            cold_email_body_words=_word_count(draft.cold_email_body),
            processing_time_seconds=round(elapsed, 3),
        )
        return draft

    def _generate_json(self, prompt: str) -> dict[str, Any]:
        client = _get_gemini_client()
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0.35,
            },
        )
        text = getattr(response, "text", None)
        if not text and hasattr(response, "candidates"):
            text = str(response.candidates[0].content.parts[0].text)
        if not text:
            raise OutreachDraftError("Gemini outreach response was empty.")
        return _extract_json(text)

    def _enforce_constraints(self, draft: OutreachDraft, tone: str) -> OutreachDraft:
        linkedin_dm = _truncate_linkedin_dm(draft.linkedin_dm)
        cold_email_body = _truncate_email_body(draft.cold_email_body)
        cold_email_subject = _normalize_space(_remove_banned_openers(draft.cold_email_subject))

        return OutreachDraft(
            linkedin_dm=linkedin_dm,
            cold_email_subject=cold_email_subject,
            cold_email_body=cold_email_body,
            tone=tone,
        )

    def _prompt(
        self,
        resume: ParsedResume,
        jd: ParsedJD,
        gap_analysis: GapAnalysis,
        tone: str,
    ) -> str:
        schema = json.dumps(OutreachDraft.model_json_schema(), indent=2)
        input_payload = {
            "resume": resume.model_dump(mode="json"),
            "job_description": jd.model_dump(mode="json"),
            "gap_analysis": gap_analysis.model_dump(mode="json"),
            "detected_tone": tone,
        }
        return f"""You are a recruiter outreach specialist for CareerScope Phase 5.
Write concise, specific outreach drafts for a candidate applying to a target role.

Return ONLY valid JSON matching this OutreachDraft schema:
{schema}

Required output fields:
- linkedin_dm: LinkedIn direct message under 300 characters.
- cold_email_subject: concise subject line tailored to the company and role.
- cold_email_body: cold email body under 150 words.
- tone: exactly "{tone}".

Tone guidance:
- Use formal language for finance, regulated, or enterprise companies.
- Use conversational language for startups, AI/ML teams, and developer-focused tech companies.
- The detected tone for this input is "{tone}".

Content requirements:
- Include a specific hook from the job description or company context.
- Include a specific candidate strength from the resume or gap analysis.
- Include a soft CTA that asks for a quick conversation, advice, or the right contact.
- Do not use a generic opener.
- Do not write "I hope this message finds you well" or any close variant.
- Do not exaggerate gaps or claim skills that the resume/gap analysis does not support.
- Keep the outreach useful even if the match score is imperfect by emphasizing real strengths.

Input data:
{json.dumps(input_payload, indent=2)}
"""


async def draft_outreach(
    resume: ParsedResume,
    jd: ParsedJD,
    gap_analysis: GapAnalysis,
) -> OutreachDraft:
    return await OutreachAgent().draft_outreach(resume, jd, gap_analysis)
