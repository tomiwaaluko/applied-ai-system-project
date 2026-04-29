from __future__ import annotations

from unittest.mock import Mock

import pytest

from agents.parser_agent import ParseError, ParserAgent
from core.models import ParsedResume


class _FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _FakePdf:
    def __init__(self, pages: list[_FakePage]) -> None:
        self.pages = pages

    def __enter__(self) -> "_FakePdf":
        return self

    def __exit__(self, *args: object) -> None:
        return None


@pytest.mark.asyncio
async def test_parse_resume_with_mocked_pdf_and_gemini(monkeypatch: pytest.MonkeyPatch, parsed_resume: ParsedResume) -> None:
    monkeypatch.setattr(
        "agents.parser_agent.pdfplumber.open",
        Mock(return_value=_FakePdf([_FakePage("Ada Lovelace\nPython FastAPI SQL")])),
    )
    monkeypatch.setattr(ParserAgent, "_generate_json", Mock(return_value=parsed_resume.model_dump(mode="json")))

    result = await ParserAgent().parse_resume("resume.pdf")

    assert isinstance(result, ParsedResume)
    assert result.skills
    assert result.inferred_level in {"entry", "mid", "senior"}


@pytest.mark.asyncio
async def test_parse_resume_empty_pdf_text_raises_parse_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "agents.parser_agent.pdfplumber.open",
        Mock(return_value=_FakePdf([_FakePage("   "), _FakePage("")])),
    )
    generate_json = Mock()
    monkeypatch.setattr(ParserAgent, "_generate_json", generate_json)

    with pytest.raises(ParseError, match="did not contain extractable text"):
        await ParserAgent().parse_resume("empty.pdf")

    generate_json.assert_not_called()
