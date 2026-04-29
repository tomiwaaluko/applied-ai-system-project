from __future__ import annotations

import math
import re
from pathlib import Path

from core.logger import get_logger


MAX_PDF_BYTES = 10 * 1024 * 1024
MIN_JD_CHARS = 100
MAX_JD_CHARS = 50_000

logger = get_logger("guardrails")

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(
    r"""
    (?<!\d)
    (?:\+?1[\s.-]?)?
    (?:\(?\d{3}\)?[\s.-]?)
    \d{3}[\s.-]?\d{4}
    (?!\d)
    """,
    re.VERBOSE,
)


def validate_pdf_input(file_path: str) -> bool:
    """Validate resume PDF path, extension, and size."""
    path = Path(file_path)

    if not path.exists():
        logger.error("pdf_validation_failed", reason="file_not_found", file_path=file_path)
        return False

    if not path.is_file():
        logger.error("pdf_validation_failed", reason="not_a_file", file_path=file_path)
        return False

    if path.suffix.lower() != ".pdf":
        logger.error("pdf_validation_failed", reason="invalid_extension", file_path=file_path)
        return False

    try:
        size = path.stat().st_size
    except OSError as exc:
        logger.error("pdf_validation_failed", reason="stat_failed", file_path=file_path, error=str(exc))
        return False

    if size >= MAX_PDF_BYTES:
        logger.error("pdf_validation_failed", reason="file_too_large", file_path=file_path, size_bytes=size)
        return False

    return True


def validate_jd_input(text: str) -> bool:
    """Validate a job description text payload."""
    if not isinstance(text, str):
        logger.error("jd_validation_failed", reason="not_text")
        return False

    stripped = text.strip()
    if not stripped:
        logger.error("jd_validation_failed", reason="empty")
        return False

    char_count = len(stripped)
    if char_count <= MIN_JD_CHARS:
        logger.error("jd_validation_failed", reason="too_short", char_count=char_count)
        return False

    if char_count >= MAX_JD_CHARS:
        logger.error("jd_validation_failed", reason="too_long", char_count=char_count)
        return False

    return True


def sanitize_output(text: str) -> str:
    """Remove common email and US phone-number patterns from generated output."""
    if not isinstance(text, str):
        return ""

    sanitized = EMAIL_PATTERN.sub("[email redacted]", text)
    return PHONE_PATTERN.sub("[phone redacted]", sanitized)


def check_confidence_threshold(score: float, threshold: float = 0.4) -> bool:
    """Return whether a confidence score is valid and above the threshold."""
    if not isinstance(score, (int, float)) or not math.isfinite(score):
        logger.warning("confidence_check_failed", reason="invalid_score", score=score, threshold=threshold)
        return False

    if not isinstance(threshold, (int, float)) or not math.isfinite(threshold):
        logger.warning("confidence_check_failed", reason="invalid_threshold", score=score, threshold=threshold)
        return False

    if score < threshold:
        logger.warning("confidence_below_threshold", score=score, threshold=threshold)
        return False

    return True
