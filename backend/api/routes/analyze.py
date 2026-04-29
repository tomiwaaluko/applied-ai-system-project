from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from agents.orchestrator import CareerScopeOrchestrator
from core.guardrails import validate_jd_input, validate_pdf_input
from core.models import ProgressEvent
from core.supabase_client import save_report

router = APIRouter()


@router.post("/analyze")
async def analyze_resume(resume: UploadFile = File(...), jd_input: str = Form(...)) -> StreamingResponse:
    if resume.content_type not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(status_code=400, detail="Resume must be a PDF.")

    suffix = Path(resume.filename or "resume.pdf").suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_path = Path(temp_file.name)
        temp_file.write(await resume.read())

    if not validate_pdf_input(str(temp_path)):
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Invalid resume PDF.")

    if not jd_input.lower().startswith(("http://", "https://")) and not validate_jd_input(jd_input):
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Invalid job description input.")

    async def event_stream():
        queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
        orchestrator = CareerScopeOrchestrator(output_dir="outputs")

        async def progress_callback(event: ProgressEvent) -> None:
            await queue.put(event)

        async def run_pipeline() -> None:
            try:
                report = await orchestrator.run(str(temp_path), jd_input, progress_callback=progress_callback)
                report.id = save_report(report)
                await queue.put(
                    ProgressEvent(
                        step=5,
                        total=5,
                        agent="complete",
                        status="done",
                        elapsed_seconds=float(report.metadata.get("processing_time_seconds", 0.0)),
                        message="Report saved.",
                        report_id=report.id,
                    )
                )
            except Exception as exc:
                await queue.put(
                    ProgressEvent(
                        step=5,
                        total=5,
                        agent="error",
                        status="error",
                        elapsed_seconds=0.0,
                        message=str(exc),
                    )
                )
            finally:
                temp_path.unlink(missing_ok=True)
                await queue.put(None)

        task = asyncio.create_task(run_pipeline())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"data: {event.model_dump_json()}\n\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
