from __future__ import annotations

import asyncio
import json
import os
import re
import time
from functools import lru_cache
from typing import Any

import httpx
import pdfplumber
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pydantic import ValidationError

from core.logger import get_logger
from core.models import Industry, ParsedJD, ParsedResume


PARSER_MODEL = os.getenv("GEMINI_PARSER_MODEL", "gemini-2.0-flash")


class ParseError(Exception):
    def __init__(self, message: str, raw_text: str | None = None) -> None:
        super().__init__(message)
        self.raw_text = raw_text


@lru_cache(maxsize=1)
def _get_gemini_client() -> Any:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required for parser agent calls.")

    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("google-genai is required. Install dependencies from requirements.txt.") from exc

    return genai.Client(api_key=api_key)


def _clean_text(text: str) -> str:
    normalized = text.replace("\x00", " ").replace("\uFFFD", " ")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


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


def _schema_for(model: type[ParsedResume] | type[ParsedJD]) -> str:
    return json.dumps(model.model_json_schema(), indent=2)


class ParserAgent:
    def __init__(self, model: str = PARSER_MODEL) -> None:
        self.model = model
        self.logger = get_logger("parser_agent")

    async def parse_resume(self, pdf_path: str) -> ParsedResume:
        start = time.perf_counter()
        raw_text = await asyncio.to_thread(self._extract_pdf_text, pdf_path)
        if not raw_text:
            raise ParseError("Resume PDF did not contain extractable text.", raw_text=raw_text)

        prompt = self._resume_prompt(raw_text)
        payload = await self._call_json_model(prompt)

        try:
            parsed = ParsedResume.model_validate(payload)
        except ValidationError as exc:
            raise ParseError(f"Resume JSON failed schema validation: {exc}", raw_text=raw_text) from exc

        elapsed = time.perf_counter() - start
        self.logger.info(
            "resume_parsed",
            agent="parser_agent",
            model=self.model,
            input_length=len(raw_text),
            skills=len(parsed.skills),
            projects=len(parsed.projects),
            experience=len(parsed.experience),
            education=len(parsed.education),
            processing_time_seconds=round(elapsed, 3),
        )
        return parsed

    async def parse_jd(self, jd_input: str) -> ParsedJD:
        start = time.perf_counter()
        raw_text = await self._get_jd_text(jd_input)
        if not raw_text:
            raise ParseError("Job description input did not contain extractable text.", raw_text=raw_text)

        prompt = self._jd_prompt(raw_text)
        payload = await self._call_json_model(prompt)

        try:
            parsed = ParsedJD.model_validate(payload)
        except ValidationError as exc:
            raise ParseError(f"Job description JSON failed schema validation: {exc}", raw_text=raw_text) from exc

        elapsed = time.perf_counter() - start
        self.logger.info(
            "jd_parsed",
            agent="parser_agent",
            model=self.model,
            input_length=len(raw_text),
            required_skills=len(parsed.required_skills),
            preferred_skills=len(parsed.preferred_skills),
            responsibilities=len(parsed.key_responsibilities),
            processing_time_seconds=round(elapsed, 3),
        )
        return parsed

    def _extract_pdf_text(self, pdf_path: str) -> str:
        parts: list[str] = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        parts.append(page_text)
        except Exception as exc:
            raise ParseError(f"Failed to extract resume PDF text: {exc}") from exc
        return _clean_text("\n".join(parts))

    async def _get_jd_text(self, jd_input: str) -> str:
        value = jd_input.strip()
        if value.lower().startswith(("http://", "https://")):
            return await self._fetch_jd_url(value)
        return _clean_text(value)

    async def _fetch_jd_url(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": "CareerScopeBot/1.0"})
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ParseError(f"Failed to fetch job description URL: {exc}") from exc

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()

        selectors = [
            "article",
            "main",
            "div.job-description",
            "div[class*='job-description']",
            "section[class*='description']",
            "div[class*='description']",
        ]
        for selector in selectors:
            node = soup.select_one(selector)
            if node:
                text = _clean_text(node.get_text("\n"))
                if len(text) > 100:
                    return text

        return _clean_text(soup.get_text("\n"))

    async def _call_json_model(self, prompt: str) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                return await asyncio.to_thread(self._generate_json, prompt)
            except Exception as exc:
                last_error = exc
                if attempt == 0:
                    self.logger.warning("parser_model_retry", model=self.model, error=str(exc))
                    await asyncio.sleep(1)

        raise ParseError(f"Gemini parser call failed after retry: {last_error}") from last_error

    def _generate_json(self, prompt: str) -> dict[str, Any]:
        client = _get_gemini_client()
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        )
        text = getattr(response, "text", None)
        if not text and hasattr(response, "candidates"):
            text = str(response.candidates[0].content.parts[0].text)
        if not text:
            raise ParseError("Gemini parser response was empty.")
        return _extract_json(text)

    def _resume_prompt(self, raw_text: str) -> str:
        industries = ", ".join(industry.value for industry in Industry)
        return f"""You are a precise resume parser. Extract structured information from the resume text provided.
Return ONLY valid JSON matching this schema:
{_schema_for(ParsedResume)}

Rules:
- skills: extract ALL technical skills, tools, frameworks, languages mentioned anywhere
- inferred_level: base this on years of experience and role seniority
- inferred_industry: choose the best fit from [{industries}]
- Do not hallucinate. If a field is not present, return null or empty list.
- For projects, extract tech_stack as a flat list of all technologies mentioned.

Resume text:
{raw_text}
"""

    def _jd_prompt(self, raw_text: str) -> str:
        industries = ", ".join(industry.value for industry in Industry)
        return f"""You are a precise job description parser. Extract structured information from the job description text provided.
Return ONLY valid JSON matching this schema:
{_schema_for(ParsedJD)}

Rules:
- required_skills: extract explicit must-have skills, tools, languages, frameworks, and qualifications.
- preferred_skills: extract nice-to-have skills and bonus qualifications.
- experience_years: infer the minimum years only if stated or strongly implied; otherwise return null.
- industry: choose the best fit from [{industries}].
- key_responsibilities: extract concrete role responsibilities, not generic company descriptions.
- Do not hallucinate. If a field is not present, return null or empty list.

Job description text:
{raw_text}
"""


async def parse_resume(pdf_path: str) -> ParsedResume:
    return await ParserAgent().parse_resume(pdf_path)


async def parse_jd(jd_input: str) -> ParsedJD:
    return await ParserAgent().parse_jd(jd_input)
