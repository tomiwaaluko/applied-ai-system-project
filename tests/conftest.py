from __future__ import annotations

import sys
import types

import pytest

# Keep parser imports testable when optional PDF dependencies are absent locally.
pdfplumber_stub = types.SimpleNamespace(
    open=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("pdfplumber.open must be mocked"))
)
sys.modules.setdefault("pdfplumber", pdfplumber_stub)

bs4_stub = types.ModuleType("bs4")
bs4_stub.BeautifulSoup = lambda *_args, **_kwargs: None
sys.modules.setdefault("bs4", bs4_stub)

from core.models import (
    GapAnalysis,
    Industry,
    OutreachDraft,
    ParsedJD,
    ParsedResume,
    RetrievedContext,
    Roadmap,
    RoadmapItem,
)


@pytest.fixture
def parsed_resume() -> ParsedResume:
    return ParsedResume(
        raw_text="Ada Lovelace built Python APIs with FastAPI, SQL, and React projects.",
        name="Ada Lovelace",
        skills=["Python", "FastAPI", "SQL", "React"],
        projects=[
            {
                "name": "CareerScope",
                "description": "Built a resume analysis app.",
                "tech_stack": ["Python", "FastAPI", "React"],
            }
        ],
        experience=[{"title": "Software Engineering Intern", "years": 1}],
        education=[{"school": "CodePath University", "degree": "BS Computer Science"}],
        inferred_level="entry",
        inferred_industry=Industry.AI_ML,
    )


@pytest.fixture
def parsed_jd() -> ParsedJD:
    return ParsedJD(
        raw_text="We need a backend engineer with Python, FastAPI, SQL, AWS, and production API experience.",
        company="ExampleAI",
        role_title="Backend Software Engineer",
        required_skills=["Python", "FastAPI", "SQL", "AWS"],
        preferred_skills=["React", "Docker"],
        experience_years=2,
        industry=Industry.AI_ML,
        key_responsibilities=["Build APIs", "Improve data pipelines"],
    )


@pytest.fixture
def retrieved_context() -> RetrievedContext:
    return RetrievedContext(
        similar_jds=[
            {
                "content": "Backend role requiring Python and FastAPI.",
                "similarity_score": 0.82,
                "source_file": "jd.md",
                "doc_type": "jd",
                "metadata": {},
            }
        ],
        benchmarks=[
            {
                "content": "Strong entry-level candidates show deployed API projects.",
                "similarity_score": 0.74,
                "source_file": "benchmark.md",
                "doc_type": "benchmark",
                "metadata": {},
            }
        ],
        industry_context="Backend AI roles emphasize API depth, SQL, and cloud deployment.",
    )


@pytest.fixture
def gap_analysis() -> GapAnalysis:
    return GapAnalysis(
        match_score=0.72,
        skill_gaps=[
            {
                "skill": "AWS",
                "gap_type": "missing",
                "confidence": 0.91,
                "evidence": "AWS is required by the JD but absent from the resume.",
            },
            {
                "skill": "FastAPI",
                "gap_type": "strong",
                "confidence": 0.88,
                "evidence": "Resume lists FastAPI project work.",
            },
        ],
        strengths=["Python", "FastAPI"],
        critical_gaps=["AWS"],
        confidence=0.86,
        reasoning_trace="Compared required skills against resume evidence and retrieved benchmarks.",
    )


@pytest.fixture
def roadmap() -> Roadmap:
    return Roadmap(
        thirty_day=[
            RoadmapItem(
                timeframe="30 days",
                action="Deploy one FastAPI service to AWS.",
                rationale="Addresses the top missing cloud skill.",
                resource="AWS Free Tier",
            )
        ],
        sixty_day=[
            RoadmapItem(
                timeframe="60 days",
                action="Add CI and containerization.",
                rationale="Improves production readiness.",
                resource="Docker docs",
            )
        ],
        ninety_day=[
            RoadmapItem(
                timeframe="90 days",
                action="Publish a case study.",
                rationale="Makes project impact visible to recruiters.",
                resource=None,
            )
        ],
        project_ideas=[
            {
                "title": "Cloud Resume Analyzer",
                "description": "Deploy a FastAPI service using AWS.",
                "skills_addressed": ["AWS", "FastAPI"],
            },
            {
                "title": "SQL Benchmark Dashboard",
                "description": "Build a dashboard over benchmark resume data.",
                "skills_addressed": ["SQL", "React"],
            },
        ],
    )


@pytest.fixture
def outreach_draft() -> OutreachDraft:
    return OutreachDraft(
        linkedin_dm="Hi, I built FastAPI projects and would value your perspective on ExampleAI backend roles.",
        cold_email_subject="Backend engineer interest at ExampleAI",
        cold_email_body="I am interested in the Backend Software Engineer role and have built FastAPI and SQL projects.",
        tone="conversational",
    )
