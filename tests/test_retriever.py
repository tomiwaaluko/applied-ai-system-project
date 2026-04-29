from __future__ import annotations

from unittest.mock import Mock

import pytest

from agents.retriever_agent import RetrieverAgent
from core.models import ParsedJD, ParsedResume, RetrievedContext


@pytest.mark.asyncio
async def test_retrieve_searches_jds_and_benchmarks(
    monkeypatch: pytest.MonkeyPatch,
    parsed_resume: ParsedResume,
    parsed_jd: ParsedJD,
) -> None:
    embedding = [0.1] * 768
    similarity_search = Mock(
        side_effect=[
            [{"content": "similar jd", "similarity_score": 0.8, "source_file": "jd.md", "doc_type": "jd"}],
            [{"content": "benchmark", "similarity_score": 0.7, "source_file": "bench.md", "doc_type": "benchmark"}],
        ]
    )
    monkeypatch.setattr("agents.retriever_agent.get_embedding", Mock(return_value=embedding))
    monkeypatch.setattr("agents.retriever_agent.similarity_search", similarity_search)
    monkeypatch.setattr(RetrieverAgent, "_generate_text", Mock(return_value="Synthesized industry context."))

    result = await RetrieverAgent().retrieve(parsed_resume, parsed_jd)

    assert isinstance(result, RetrievedContext)
    assert result.similar_jds
    assert result.benchmarks
    assert {call.args[1] for call in similarity_search.call_args_list} == {"jd", "benchmark"}
    similarity_search.assert_any_call(embedding, "jd", 5)
    similarity_search.assert_any_call(embedding, "benchmark", 3)


@pytest.mark.asyncio
async def test_retrieve_low_similarity_returns_context_and_logs_warning(
    monkeypatch: pytest.MonkeyPatch,
    parsed_resume: ParsedResume,
    parsed_jd: ParsedJD,
) -> None:
    low_records = [
        {"content": "weak match", "similarity_score": 0.12, "source_file": "low.md", "doc_type": "jd"},
    ]
    monkeypatch.setattr("agents.retriever_agent.get_embedding", Mock(return_value=[0.2] * 768))
    monkeypatch.setattr("agents.retriever_agent.similarity_search", Mock(side_effect=[low_records, []]))
    monkeypatch.setattr(RetrieverAgent, "_generate_text", Mock(return_value="Low-confidence synthesized context."))

    agent = RetrieverAgent()
    warning = Mock()
    monkeypatch.setattr(agent.logger, "warning", warning)

    result = await agent.retrieve(parsed_resume, parsed_jd)

    assert isinstance(result, RetrievedContext)
    assert result.similar_jds == low_records
    assert result.industry_context == "Low-confidence synthesized context."
    warning.assert_called_once()
    assert warning.call_args.args[0] == "LOW_CORPUS_MATCH"
