from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.main import app
from core.models import CareerReport, GapAnalysis, OutreachDraft, ParsedJD, ParsedResume, RetrievedContext, Roadmap


@pytest.fixture
def sample_report(
    parsed_resume: ParsedResume,
    parsed_jd: ParsedJD,
    retrieved_context: RetrievedContext,
    gap_analysis: GapAnalysis,
    roadmap: Roadmap,
    outreach_draft: OutreachDraft,
) -> CareerReport:
    return CareerReport(
        id="11111111-1111-1111-1111-111111111111",
        resume=parsed_resume,
        jd=parsed_jd,
        retrieved_context=retrieved_context,
        gap_analysis=gap_analysis,
        roadmap=roadmap,
        outreach=outreach_draft,
        metadata={"processing_time_seconds": 0.1},
    )


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_analyze_stream_starts(monkeypatch: pytest.MonkeyPatch, client: AsyncClient, sample_report: CareerReport) -> None:
    class FakeOrchestrator:
        def __init__(self, output_dir: str) -> None:
            self.output_dir = output_dir

        async def run(self, resume_path: str, jd_input: str, progress_callback=None) -> CareerReport:
            if progress_callback:
                from core.models import ProgressEvent

                await progress_callback(
                    ProgressEvent(
                        step=1,
                        total=5,
                        agent="parser",
                        status="done",
                        elapsed_seconds=0.01,
                        message="Parsed.",
                    )
                )
            return sample_report

    monkeypatch.setattr("api.routes.analyze.CareerScopeOrchestrator", FakeOrchestrator)
    monkeypatch.setattr("api.routes.analyze.save_report", lambda report: report.id)

    response = await client.post(
        "/api/analyze",
        files={"resume": ("resume.pdf", b"%PDF-1.4\nsynthetic", "application/pdf")},
        data={"jd_input": "Python FastAPI SQL AWS backend engineer role. " * 4},
    )

    assert response.status_code == 200
    assert response.text.startswith("data: ")
    assert '"agent":"parser"' in response.text
    assert '"agent":"complete"' in response.text


@pytest.mark.asyncio
async def test_reports_list(monkeypatch: pytest.MonkeyPatch, client: AsyncClient, sample_report: CareerReport) -> None:
    monkeypatch.setattr(
        "api.routes.reports.list_reports",
        lambda: [
            {
                "id": sample_report.id,
                "created_at": "2026-04-29T00:00:00Z",
                "report_data": sample_report.model_dump(mode="json"),
            }
        ],
    )

    response = await client.get("/api/reports")
    assert response.status_code == 200
    assert response.json()[0]["id"] == sample_report.id
    assert response.json()[0]["role_title"] == sample_report.jd.role_title


@pytest.mark.asyncio
async def test_report_not_found(monkeypatch: pytest.MonkeyPatch, client: AsyncClient) -> None:
    monkeypatch.setattr("api.routes.reports.get_report", lambda report_id: None)
    response = await client.get("/api/reports/nonexistent-id")
    assert response.status_code == 404
