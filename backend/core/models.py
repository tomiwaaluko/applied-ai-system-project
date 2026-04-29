from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Industry(str, Enum):
    FINTECH = "fintech"
    BIG_TECH = "big_tech"
    AI_ML = "ai_ml"
    STARTUP = "startup"
    GENERAL_SWE = "general_swe"


class ParsedResume(BaseModel):
    raw_text: str
    name: Optional[str]
    skills: list[str]
    projects: list[dict]
    experience: list[dict]
    education: list[dict]
    inferred_level: str
    inferred_industry: Industry


class ParsedJD(BaseModel):
    raw_text: str
    company: Optional[str]
    role_title: str
    required_skills: list[str]
    preferred_skills: list[str]
    experience_years: Optional[int]
    industry: Industry
    key_responsibilities: list[str]


class RetrievedContext(BaseModel):
    similar_jds: list[dict]
    benchmarks: list[dict]
    industry_context: str


class SkillGap(BaseModel):
    skill: str
    gap_type: str
    confidence: float
    evidence: str


class GapAnalysis(BaseModel):
    match_score: float
    skill_gaps: list[SkillGap]
    strengths: list[str]
    critical_gaps: list[str]
    confidence: float
    reasoning_trace: str


class RoadmapItem(BaseModel):
    timeframe: str
    action: str
    rationale: str
    resource: Optional[str]


class Roadmap(BaseModel):
    thirty_day: list[RoadmapItem]
    sixty_day: list[RoadmapItem]
    ninety_day: list[RoadmapItem]
    project_ideas: list[dict]


class OutreachDraft(BaseModel):
    linkedin_dm: str
    cold_email_subject: str
    cold_email_body: str
    tone: str


class CareerReport(BaseModel):
    resume: ParsedResume
    jd: ParsedJD
    retrieved_context: RetrievedContext
    gap_analysis: GapAnalysis
    roadmap: Roadmap
    outreach: OutreachDraft
    metadata: dict

