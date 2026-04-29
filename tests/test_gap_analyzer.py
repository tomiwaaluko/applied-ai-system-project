from __future__ import annotations

from unittest.mock import Mock

import pytest

from agents.gap_analyzer_agent import GapAnalyzerAgent
from core.models import GapAnalysis, ParsedJD, ParsedResume, RetrievedContext


@pytest.mark.asyncio
async def test_analyze_returns_valid_gap_analysis(
    monkeypatch: pytest.MonkeyPatch,
    parsed_resume: ParsedResume,
    parsed_jd: ParsedJD,
    retrieved_context: RetrievedContext,
    gap_analysis: GapAnalysis,
) -> None:
    monkeypatch.setattr(GapAnalyzerAgent, "_generate_json", Mock(return_value=gap_analysis.model_dump(mode="json")))

    result = await GapAnalyzerAgent().analyze(parsed_resume, parsed_jd, retrieved_context)

    assert isinstance(result, GapAnalysis)
    assert 0.0 <= result.match_score <= 0.95
    assert 0.0 <= result.confidence <= 1.0
    assert result.skill_gaps
    assert all(0.0 <= gap.confidence <= 1.0 for gap in result.skill_gaps)


@pytest.mark.asyncio
async def test_analyze_caps_overinflated_match_score(
    monkeypatch: pytest.MonkeyPatch,
    parsed_resume: ParsedResume,
    parsed_jd: ParsedJD,
    retrieved_context: RetrievedContext,
    gap_analysis: GapAnalysis,
) -> None:
    payload = gap_analysis.model_copy(update={"match_score": 0.99}).model_dump(mode="json")
    monkeypatch.setattr(GapAnalyzerAgent, "_generate_json", Mock(return_value=payload))

    result = await GapAnalyzerAgent().analyze(parsed_resume, parsed_jd, retrieved_context)

    assert result.match_score == 0.95
