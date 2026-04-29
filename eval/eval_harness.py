from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap
from typing import TYPE_CHECKING

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if TYPE_CHECKING:
    from agents.orchestrator import CareerScopeOrchestrator
    from core.models import CareerReport


FIXTURE_ROOT = PROJECT_ROOT / "data" / "test_fixtures"
RESUME_DIR = FIXTURE_ROOT / "resumes"
JD_DIR = FIXTURE_ROOT / "jds"


TEST_CASES = [
    {
        "id": "TC-001",
        "description": "Entry-level SWE resume vs. Bloomberg data engineering JD",
        "resume": "data/test_fixtures/resumes/entry_swe.pdf",
        "jd": "data/test_fixtures/jds/bloomberg_data_engineer.txt",
        "expected_match_score_range": (0.40, 0.70),
        "expected_critical_gaps_min": 2,
        "expected_critical_gaps_max": 6,
        "expected_skills_present": ["Python", "SQL"],
    },
    {
        "id": "TC-002",
        "description": "Strong ML resume vs. NVIDIA ML engineer JD",
        "resume": "data/test_fixtures/resumes/strong_ml.pdf",
        "jd": "data/test_fixtures/jds/nvidia_ml_engineer.txt",
        "expected_match_score_range": (0.60, 0.90),
        "expected_critical_gaps_min": 0,
        "expected_critical_gaps_max": 4,
        "expected_skills_present": ["PyTorch", "CUDA"],
    },
    {
        "id": "TC-003",
        "description": "Finance-focused resume vs. Goldman Sachs analyst JD",
        "resume": "data/test_fixtures/resumes/finance_analyst.pdf",
        "jd": "data/test_fixtures/jds/goldman_analyst.txt",
        "expected_match_score_range": (0.45, 0.75),
        "expected_critical_gaps_min": 1,
        "expected_critical_gaps_max": 5,
        "expected_skills_present": ["Excel", "Python"],
    },
    {
        "id": "TC-004",
        "description": "Guardrail test - blank/minimal resume",
        "resume": "data/test_fixtures/resumes/minimal.pdf",
        "jd": "data/test_fixtures/jds/generic_swe.txt",
        "expected_match_score_range": (0.0, 0.35),
        "expected_critical_gaps_min": 3,
        "expected_critical_gaps_max": 15,
        "expected_skills_present": [],
        "expect_low_confidence_warning": True,
    },
    {
        "id": "TC-005",
        "description": "Consistency test - same input run twice, scores within 0.10",
        "resume": "data/test_fixtures/resumes/entry_swe.pdf",
        "jd": "data/test_fixtures/jds/bloomberg_data_engineer.txt",
        "is_consistency_test": True,
        "consistency_tolerance": 0.10,
    },
]


RESUME_FIXTURES = {
    "entry_swe.pdf": """Alex Rivera
Entry-Level Software Engineer

Education
B.S. Computer Science, State University, expected May 2026

Skills
Python, SQL, JavaScript, React, Flask, REST APIs, Git, Linux, pytest, basic Docker

Projects
Campus Course Planner: built a Flask and React web app backed by PostgreSQL for searching
classes and saving schedules. Wrote SQL queries, REST endpoints, and pytest coverage.
Personal Finance Tracker: created Python ETL scripts to clean CSV transactions and visualize
monthly spending trends.

Experience
Software Engineering Intern, City Library Technology Team
Built small internal tools in Python and JavaScript, fixed UI bugs, and wrote documentation.
""",
    "strong_ml.pdf": """Maya Chen
Machine Learning Engineer

Education
M.S. Computer Science, Machine Learning concentration

Skills
Python, PyTorch, TensorFlow, CUDA, C++, NumPy, pandas, scikit-learn, Docker, Kubernetes,
MLflow, distributed training, model evaluation, data pipelines, Linux

Projects
GPU Image Classifier: implemented convolutional neural networks in PyTorch with custom CUDA
kernels for preprocessing and benchmarked inference latency on NVIDIA GPUs.
Recommendation System: trained ranking models, tracked experiments in MLflow, and deployed
a FastAPI inference service in Docker.

Experience
ML Research Assistant
Built deep learning models for computer vision, optimized batch training jobs, and reported
precision, recall, and latency metrics.
""",
    "finance_analyst.pdf": """Jordan Patel
Finance and Data Analyst

Education
B.B.A. Finance, minor in Data Analytics

Skills
Excel, financial modeling, valuation, PowerPoint, Python, pandas, SQL, Tableau, statistics,
market research, accounting fundamentals

Projects
Equity Research Model: built an Excel DCF model with sensitivity tables and comparable
company analysis for a public technology company.
Portfolio Analytics: used Python and pandas to calculate returns, volatility, drawdown, and
Sharpe ratios from historical price data.

Experience
Finance Intern, Regional Bank
Prepared weekly KPI reports, reconciled loan portfolio data, and presented findings to the
commercial banking team.
""",
    "minimal.pdf": """Candidate Name

Resume
Interested in software jobs.
""",
}


JD_FIXTURES = {
    "bloomberg_data_engineer.txt": """Bloomberg is hiring a Data Engineer to build reliable market data pipelines for
analytics teams. Required skills include Python, SQL, data modeling, ETL pipeline design,
distributed systems, cloud data platforms, testing, and Linux. The engineer will design
batch and streaming workflows, partner with product teams, monitor data quality, and
improve performance of large datasets. Preferred skills include Spark, Kafka, Airflow,
Docker, Kubernetes, and experience supporting production data infrastructure. Candidates
should communicate clearly with stakeholders and be comfortable debugging complex systems.""",
    "nvidia_ml_engineer.txt": """NVIDIA is hiring a Machine Learning Engineer for accelerated AI systems. Required skills
include Python, PyTorch, CUDA, deep learning, C++, model optimization, data pipelines, Linux,
and rigorous model evaluation. Responsibilities include training neural networks, optimizing
GPU inference performance, collaborating with research and platform teams, and deploying
reproducible ML workflows. Preferred qualifications include TensorFlow, distributed training,
Kubernetes, MLflow, computer vision, recommender systems, and experience benchmarking
latency and throughput on NVIDIA hardware.""",
    "goldman_analyst.txt": """Goldman Sachs is hiring an Analyst for a finance and analytics team. Required skills include
Excel, financial modeling, accounting fundamentals, valuation, market research, Python,
SQL, and clear written communication. Responsibilities include building models, analyzing
business performance, preparing client-ready presentations, validating data quality, and
summarizing risks and opportunities for senior stakeholders. Preferred skills include
Tableau, statistics, PowerPoint, capital markets knowledge, and experience with portfolio
analytics or banking datasets.""",
    "generic_swe.txt": """We are hiring a Software Engineer to build and maintain production web services. Required
skills include Python, JavaScript, SQL, data structures, algorithms, REST APIs, Git, testing,
debugging, and basic cloud deployment. Responsibilities include implementing features,
reviewing code, writing unit tests, diagnosing defects, maintaining documentation, and
collaborating with product and design partners. Preferred skills include React, Docker,
PostgreSQL, CI/CD, Linux, observability, and experience shipping a project used by real users.""",
}


@dataclass
class EvalResult:
    case_id: str
    description: str
    match_score_display: str
    match_score_value: float | None
    confidence: float | None
    gaps: int | None
    passed: bool
    notes: str


def generate_fixtures() -> None:
    RESUME_DIR.mkdir(parents=True, exist_ok=True)
    JD_DIR.mkdir(parents=True, exist_ok=True)

    for filename, text in RESUME_FIXTURES.items():
        path = RESUME_DIR / filename
        if not path.exists():
            _write_pdf(path, text)

    for filename, text in JD_FIXTURES.items():
        path = JD_DIR / filename
        if not path.exists():
            path.write_text(text.strip() + "\n", encoding="utf-8")


def _write_pdf(path: Path, text: str) -> None:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise RuntimeError("reportlab is required to generate PDF fixtures.") from exc

    pdf = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    left_margin = 72
    y = height - 72
    pdf.setFont("Helvetica", 10)

    for raw_line in text.strip().splitlines():
        lines = wrap(raw_line, width=92) if raw_line else [""]
        for line in lines:
            if y < 72:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y = height - 72
            pdf.drawString(left_margin, y, line)
            y -= 14

    pdf.save()


async def run_eval() -> int:
    from agents.orchestrator import CareerScopeOrchestrator

    load_dotenv(PROJECT_ROOT / ".env")
    generate_fixtures()

    results: list[EvalResult] = []
    with tempfile.TemporaryDirectory(prefix="careerscope_eval_") as output_dir:
        orchestrator = CareerScopeOrchestrator(output_dir=Path(output_dir))
        for case in TEST_CASES:
            result = await _run_case(orchestrator, case)
            results.append(result)

    _print_results(results)
    return 0 if all(result.passed for result in results) else 1


async def _run_case(
    orchestrator: "CareerScopeOrchestrator",
    case: dict,
) -> EvalResult:
    try:
        if case.get("is_consistency_test"):
            return await _run_consistency_case(orchestrator, case)
        return await _run_standard_case(orchestrator, case)
    except Exception as exc:
        return EvalResult(
            case_id=case["id"],
            description=case["description"],
            match_score_display="-",
            match_score_value=None,
            confidence=None,
            gaps=None,
            passed=False,
            notes=f"Error: {exc}",
        )


async def _run_standard_case(
    orchestrator: "CareerScopeOrchestrator",
    case: dict,
) -> EvalResult:
    report = await _run_pipeline(orchestrator, case)
    analysis = report.gap_analysis
    notes = _check_standard_expectations(report, case)
    passed = not notes

    return EvalResult(
        case_id=case["id"],
        description=case["description"],
        match_score_display=f"{analysis.match_score:.2f}",
        match_score_value=analysis.match_score,
        confidence=analysis.confidence,
        gaps=len(analysis.critical_gaps),
        passed=passed,
        notes="OK" if passed else "; ".join(notes),
    )


async def _run_consistency_case(
    orchestrator: "CareerScopeOrchestrator",
    case: dict,
) -> EvalResult:
    first = await _run_pipeline(orchestrator, case)
    second = await _run_pipeline(orchestrator, case)
    first_score = first.gap_analysis.match_score
    second_score = second.gap_analysis.match_score
    delta = abs(first_score - second_score)
    tolerance = case["consistency_tolerance"]
    passed = delta <= tolerance
    notes = f"Delta {delta:.2f} within tolerance" if passed else f"Delta {delta:.2f} > {tolerance:.2f}"
    avg_score = statistics.fmean([first_score, second_score])
    avg_confidence = statistics.fmean([first.gap_analysis.confidence, second.gap_analysis.confidence])

    return EvalResult(
        case_id=case["id"],
        description=case["description"],
        match_score_display=f"diff {delta:.2f}",
        match_score_value=avg_score,
        confidence=avg_confidence,
        gaps=None,
        passed=passed,
        notes=notes,
    )


async def _run_pipeline(orchestrator: "CareerScopeOrchestrator", case: dict) -> "CareerReport":
    resume_path = PROJECT_ROOT / case["resume"]
    jd_text = (PROJECT_ROOT / case["jd"]).read_text(encoding="utf-8")
    return await orchestrator.run(str(resume_path), jd_text)


def _check_standard_expectations(report: "CareerReport", case: dict) -> list[str]:
    analysis = report.gap_analysis
    notes: list[str] = []
    min_score, max_score = case["expected_match_score_range"]
    gap_count = len(analysis.critical_gaps)

    if not min_score <= analysis.match_score <= max_score:
        notes.append(f"score {analysis.match_score:.2f} outside {min_score:.2f}-{max_score:.2f}")

    min_gaps = case["expected_critical_gaps_min"]
    max_gaps = case["expected_critical_gaps_max"]
    if not min_gaps <= gap_count <= max_gaps:
        notes.append(f"gaps {gap_count} outside {min_gaps}-{max_gaps}")

    missing_skills = _missing_expected_skills(report, case.get("expected_skills_present", []))
    if missing_skills:
        notes.append(f"missing expected skills in gap analysis: {', '.join(missing_skills)}")

    if case.get("expect_low_confidence_warning") and analysis.confidence >= 0.4:
        notes.append(f"expected low confidence, got {analysis.confidence:.2f}")

    return notes


def _missing_expected_skills(report: "CareerReport", expected_skills: list[str]) -> list[str]:
    if not expected_skills:
        return []

    analysis = report.gap_analysis
    searchable_values = [
        *(gap.skill for gap in analysis.skill_gaps),
        *analysis.critical_gaps,
        *analysis.strengths,
    ]
    haystack = "\n".join(searchable_values).lower()
    return [skill for skill in expected_skills if skill.lower() not in haystack]


def _print_results(results: list[EvalResult]) -> None:
    headers = ["ID", "Description", "Match Score", "Gaps", "PASS/FAIL", "Notes"]
    rows = [
        [
            result.case_id,
            result.description,
            result.match_score_display,
            "-" if result.gaps is None else str(result.gaps),
            "PASS" if result.passed else "FAIL",
            result.notes,
        ]
        for result in results
    ]
    widths = [
        max(len(str(row[index])) for row in [headers, *rows])
        for index in range(len(headers))
    ]

    def fmt(row: list[str]) -> str:
        return " | ".join(value.ljust(widths[index]) for index, value in enumerate(row))

    print()
    print(fmt(headers))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(fmt(row))

    passed_count = sum(result.passed for result in results)
    result_scores = [result.match_score_value for result in results if result.match_score_value is not None]
    result_confidences = [result.confidence for result in results if result.confidence is not None]
    avg_score = statistics.fmean(result_scores) if result_scores else 0.0
    avg_confidence = statistics.fmean(result_confidences) if result_confidences else 0.0
    print()
    print(f"Summary: {passed_count}/{len(TEST_CASES)} tests passed. Average match score: {avg_score:.2f}. Average confidence: {avg_confidence:.2f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CareerScope eval harness.")
    parser.add_argument(
        "--prepare-fixtures",
        action="store_true",
        help="Generate missing test fixtures and exit without running the orchestrator.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.prepare_fixtures:
        generate_fixtures()
        print(f"Fixtures ready under {FIXTURE_ROOT}")
        return

    raise SystemExit(asyncio.run(run_eval()))


if __name__ == "__main__":
    main()
