from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, TypeVar

from agents.gap_analyzer_agent import GapAnalyzerAgent
from agents.outreach_agent import OutreachAgent
from agents.parser_agent import ParserAgent
from agents.retriever_agent import RetrieverAgent
from agents.roadmap_agent import RoadmapAgent
from core.guardrails import validate_jd_input, validate_pdf_input
from core.logger import get_logger
from core.models import CareerReport, GapAnalysis, OutreachDraft, ProgressEvent, RetrievedContext, Roadmap


T = TypeVar("T")


class CareerScopeOrchestrator:
    def __init__(self, output_dir: str | Path = "outputs") -> None:
        self.logger = get_logger("orchestrator")
        self.parser = ParserAgent()
        self.retriever = RetrieverAgent()
        self.gap_analyzer = GapAnalyzerAgent()
        self.roadmap = RoadmapAgent()
        self.outreach = OutreachAgent()
        self.output_dir = Path(output_dir)

    async def run(
        self,
        resume_path: str,
        jd_input: str,
        progress_callback: Callable[[ProgressEvent], Awaitable[None]] | None = None,
    ) -> CareerReport:
        start = time.perf_counter()
        self._validate_inputs(resume_path, jd_input)

        parse_started = time.perf_counter()
        resume, jd = await asyncio.gather(
            self._retry("parse_resume", lambda: self.parser.parse_resume(resume_path)),
            self._retry("parse_jd", lambda: self.parser.parse_jd(jd_input)),
        )
        parse_seconds = time.perf_counter() - parse_started
        print(f"[1/5] Parsing resume + job description... OK ({parse_seconds:.1f}s)")
        await self._emit_progress(
            progress_callback,
            step=1,
            agent="parser",
            elapsed_seconds=parse_seconds,
            message="Parsed resume and job description.",
        )

        retrieval_started = time.perf_counter()
        retrieved_context = await self._retry(
            "retrieve_context",
            lambda: self.retriever.retrieve(resume, jd),
            fallback=lambda error: self._fallback_retrieved_context(error),
        )
        retrieval_seconds = time.perf_counter() - retrieval_started
        print(f"[2/5] Retrieving context... OK ({retrieval_seconds:.1f}s)")
        await self._emit_progress(
            progress_callback,
            step=2,
            agent="retriever",
            elapsed_seconds=retrieval_seconds,
            message="Retrieved role context from the corpus.",
        )

        gap_started = time.perf_counter()
        gap_analysis = await self._retry(
            "analyze_gaps",
            lambda: self.gap_analyzer.analyze(resume, jd, retrieved_context),
            fallback=lambda error: self._fallback_gap_analysis(error),
        )
        gap_seconds = time.perf_counter() - gap_started
        print(f"[3/5] Analyzing skill gaps... OK ({gap_seconds:.1f}s)")
        await self._emit_progress(
            progress_callback,
            step=3,
            agent="gap_analyzer",
            elapsed_seconds=gap_seconds,
            message="Completed evidence-based gap analysis.",
        )

        build_started = time.perf_counter()
        roadmap, outreach = await asyncio.gather(
            self._retry(
                "build_roadmap",
                lambda: self.roadmap.build_roadmap(resume, gap_analysis),
                fallback=lambda error: self._fallback_roadmap(error),
            ),
            self._retry(
                "draft_outreach",
                lambda: self.outreach.draft_outreach(resume, jd, gap_analysis),
                fallback=lambda error: self._fallback_outreach(error),
            ),
        )
        build_seconds = time.perf_counter() - build_started
        print(f"[4/5] Building roadmap + outreach... OK ({build_seconds:.1f}s)")
        await self._emit_progress(
            progress_callback,
            step=4,
            agent="roadmap_outreach",
            elapsed_seconds=build_seconds,
            message="Generated roadmap and outreach drafts.",
        )

        report = CareerReport(
            id=str(uuid.uuid4()),
            resume=resume,
            jd=jd,
            retrieved_context=retrieved_context,
            gap_analysis=gap_analysis,
            roadmap=roadmap,
            outreach=outreach,
            metadata={
                "created_at": datetime.now(timezone.utc).isoformat(),
                "processing_time_seconds": round(time.perf_counter() - start, 3),
                "models": {
                    "parser": self.parser.model,
                    "retriever": self.retriever.model,
                    "gap_analyzer": self.gap_analyzer.model,
                    "roadmap": self.roadmap.model,
                    "outreach": self.outreach.model,
                },
            },
        )
        json_path, markdown_path = self._write_report(report)
        print(f"[5/5] Writing report... OK")
        print(
            f"Report complete -> {markdown_path}\n"
            f"   Match Score: {report.gap_analysis.match_score:.2f} | "
            f"Critical Gaps: {len(report.gap_analysis.critical_gaps)} | "
            f"Confidence: {report.gap_analysis.confidence:.2f}"
        )
        self.logger.info("report_written", json_path=str(json_path), markdown_path=str(markdown_path))
        await self._emit_progress(
            progress_callback,
            step=5,
            agent="report_writer",
            elapsed_seconds=time.perf_counter() - start,
            message="Assembled and wrote the report.",
            report_id=report.id,
        )
        return report

    async def _emit_progress(
        self,
        progress_callback: Callable[[ProgressEvent], Awaitable[None]] | None,
        *,
        step: int,
        agent: str,
        elapsed_seconds: float,
        message: str,
        report_id: str | None = None,
    ) -> None:
        if progress_callback is None:
            return
        await progress_callback(
            ProgressEvent(
                step=step,
                total=5,
                agent=agent,
                status="done",
                elapsed_seconds=round(elapsed_seconds, 3),
                message=message,
                report_id=report_id,
            )
        )

    def _validate_inputs(self, resume_path: str, jd_input: str) -> None:
        if not validate_pdf_input(resume_path):
            raise ValueError(f"Invalid resume PDF input: {resume_path}")
        if not jd_input.lower().startswith(("http://", "https://")) and not validate_jd_input(jd_input):
            raise ValueError("Invalid job description text input.")

    async def _retry(
        self,
        name: str,
        operation: Callable[[], Awaitable[T]],
        fallback: Callable[[Exception], T] | None = None,
        max_attempts: int = 2,
        delay_seconds: float = 2.0,
    ) -> T:
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                return await operation()
            except Exception as exc:
                last_error = exc
                self.logger.warning("agent_attempt_failed", agent=name, attempt=attempt, error=str(exc))
                if attempt < max_attempts:
                    await asyncio.sleep(delay_seconds)

        assert last_error is not None
        self.logger.error("agent_failed", agent=name, error=str(last_error))
        if fallback is not None:
            return fallback(last_error)
        raise last_error

    def _write_report(self, report: CareerReport) -> tuple[Path, Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        json_path = self.output_dir / f"{timestamp}_report.json"
        markdown_path = self.output_dir / f"{timestamp}_report.md"

        json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        markdown_path.write_text(self._format_markdown_report(report), encoding="utf-8")
        return json_path, markdown_path

    def _format_markdown_report(self, report: CareerReport) -> str:
        candidate = report.resume.name or "Candidate"
        match_pct = round(report.gap_analysis.match_score * 100)
        gaps = "\n".join(
            f"| {gap.skill} | {gap.gap_type} | {gap.confidence:.2f} | {gap.evidence} |"
            for gap in report.gap_analysis.skill_gaps
        )
        roadmap = self._format_roadmap(report.roadmap)
        projects = "\n".join(
            f"### {project.get('title', 'Project idea')}\n\n"
            f"{project.get('description', '')}\n\n"
            f"Skills addressed: {', '.join(project.get('skills_addressed', project.get('critical_gaps_addressed', [])))}"
            for project in report.roadmap.project_ideas
        )
        return f"""# CareerScope Report: {candidate}

Target role: **{report.jd.role_title}**  
Company: **{report.jd.company or "Not specified"}**  
Match score: **{match_pct}%**

## Executive Summary

{report.retrieved_context.industry_context}

## Strengths

{self._bullet_list(report.gap_analysis.strengths)}

## Critical Gaps

{self._bullet_list(report.gap_analysis.critical_gaps)}

## Gap Analysis

| Skill | Gap Type | Confidence | Evidence |
|---|---|---:|---|
{gaps}

## 30/60/90 Day Roadmap

{roadmap}

## Project Ideas

{projects}

## Outreach Drafts

### LinkedIn DM

```text
{report.outreach.linkedin_dm}
```

### Cold Email

Subject: {report.outreach.cold_email_subject}

```text
{report.outreach.cold_email_body}
```

<details>
<summary>Reasoning trace</summary>

{report.gap_analysis.reasoning_trace}

</details>
"""

    def _format_roadmap(self, roadmap: Roadmap) -> str:
        sections = [
            ("30 Days", roadmap.thirty_day),
            ("60 Days", roadmap.sixty_day),
            ("90 Days", roadmap.ninety_day),
        ]
        output: list[str] = []
        for title, items in sections:
            output.append(f"### {title}")
            output.extend(
                f"- [ ] {item.action}  \n  Rationale: {item.rationale}  \n  Resource: {item.resource or 'TBD'}"
                for item in items
            )
            output.append("")
        return "\n".join(output).strip()

    def _bullet_list(self, values: list[str]) -> str:
        if not values:
            return "- None identified"
        return "\n".join(f"- {value}" for value in values)

    def _fallback_retrieved_context(self, error: Exception) -> RetrievedContext:
        return RetrievedContext(similar_jds=[], benchmarks=[], industry_context=f"Retriever failed: {error}")

    def _fallback_gap_analysis(self, error: Exception) -> GapAnalysis:
        return GapAnalysis(
            match_score=0.0,
            skill_gaps=[],
            strengths=[],
            critical_gaps=[],
            confidence=0.0,
            reasoning_trace=f"Gap analyzer failed: {error}",
        )

    def _fallback_roadmap(self, error: Exception) -> Roadmap:
        return Roadmap(thirty_day=[], sixty_day=[], ninety_day=[], project_ideas=[{"error": str(error)}])

    def _fallback_outreach(self, error: Exception) -> OutreachDraft:
        return OutreachDraft(
            linkedin_dm=f"Outreach agent failed: {error}",
            cold_email_subject="Outreach draft unavailable",
            cold_email_body=f"Outreach agent failed: {error}",
            tone="conversational",
        )
