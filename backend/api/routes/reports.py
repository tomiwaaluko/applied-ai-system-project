from __future__ import annotations

from fastapi import APIRouter, HTTPException

from core.supabase_client import get_report, list_reports

router = APIRouter()


@router.get("/reports")
async def recent_reports() -> list[dict]:
    summaries: list[dict] = []
    for record in list_reports():
        report = record.get("report_data") or {}
        summaries.append(
            {
                "id": record.get("id"),
                "created_at": record.get("created_at"),
                "role_title": (report.get("jd") or {}).get("role_title"),
                "match_score": (report.get("gap_analysis") or {}).get("match_score"),
            }
        )
    return summaries


@router.get("/reports/{report_id}")
async def report_detail(report_id: str) -> dict:
    record = get_report(report_id)
    if not record:
        raise HTTPException(status_code=404, detail="Report not found.")
    return record.get("report_data") or {}
