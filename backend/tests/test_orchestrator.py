from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from agents.orchestrator import CareerScopeOrchestrator
from core.models import CareerReport, GapAnalysis, OutreachDraft, ParsedJD, ParsedResume, RetrievedContext, Roadmap


@pytest.mark.asyncio
async def test_orchestrator_full_pipeline_returns_report_and_writes_markdown(
    tmp_path,
    parsed_resume: ParsedResume,
    parsed_jd: ParsedJD,
    retrieved_context: RetrievedContext,
    gap_analysis: GapAnalysis,
    roadmap: Roadmap,
    outreach_draft: OutreachDraft,
) -> None:
    resume_path = tmp_path / "resume.pdf"
    resume_path.write_bytes(b"%PDF-1.4\n% test pdf")
    jd_input = " ".join([parsed_jd.raw_text] * 4)

    output_dir = tmp_path / "outputs"
    orchestrator = CareerScopeOrchestrator(output_dir=output_dir)
    orchestrator.parser.parse_resume = AsyncMock(return_value=parsed_resume)
    orchestrator.parser.parse_jd = AsyncMock(return_value=parsed_jd)
    orchestrator.retriever.retrieve = AsyncMock(return_value=retrieved_context)
    orchestrator.gap_analyzer.analyze = AsyncMock(return_value=gap_analysis)
    orchestrator.roadmap.build_roadmap = AsyncMock(return_value=roadmap)
    orchestrator.outreach.draft_outreach = AsyncMock(return_value=outreach_draft)

    report = await orchestrator.run(str(resume_path), jd_input)

    assert isinstance(report, CareerReport)
    assert report.resume == parsed_resume
    assert report.jd == parsed_jd
    assert report.retrieved_context == retrieved_context
    assert report.gap_analysis == gap_analysis
    assert report.roadmap == roadmap
    assert report.outreach == outreach_draft
    markdown_files = list(output_dir.glob("*_report.md"))
    assert len(markdown_files) == 1
    assert "CareerScope Report" in markdown_files[0].read_text(encoding="utf-8")
