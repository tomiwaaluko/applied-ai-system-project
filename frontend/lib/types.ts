export type Industry = "fintech" | "big_tech" | "ai_ml" | "startup" | "general_swe";

export interface ParsedResume {
  raw_text: string;
  name: string | null;
  skills: string[];
  projects: Record<string, unknown>[];
  experience: Record<string, unknown>[];
  education: Record<string, unknown>[];
  inferred_level: string;
  inferred_industry: Industry;
}

export interface ParsedJD {
  raw_text: string;
  company: string | null;
  role_title: string;
  required_skills: string[];
  preferred_skills: string[];
  experience_years: number | null;
  industry: Industry;
  key_responsibilities: string[];
}

export interface RetrievedContext {
  similar_jds: Record<string, unknown>[];
  benchmarks: Record<string, unknown>[];
  industry_context: string;
}

export interface SkillGap {
  skill: string;
  gap_type: "missing" | "partial" | "strong" | string;
  confidence: number;
  evidence: string;
}

export interface GapAnalysis {
  match_score: number;
  skill_gaps: SkillGap[];
  strengths: string[];
  critical_gaps: string[];
  confidence: number;
  reasoning_trace: string;
}

export interface RoadmapItem {
  timeframe: string;
  action: string;
  rationale: string;
  resource: string | null;
}

export interface Roadmap {
  thirty_day: RoadmapItem[];
  sixty_day: RoadmapItem[];
  ninety_day: RoadmapItem[];
  project_ideas: Record<string, unknown>[];
}

export interface OutreachDraft {
  linkedin_dm: string;
  cold_email_subject: string;
  cold_email_body: string;
  tone: string;
}

export interface CareerReport {
  id: string;
  resume: ParsedResume;
  jd: ParsedJD;
  retrieved_context: RetrievedContext;
  gap_analysis: GapAnalysis;
  roadmap: Roadmap;
  outreach: OutreachDraft;
  metadata: Record<string, unknown>;
}

export interface ProgressEvent {
  step: number;
  total: number;
  agent: string;
  status: string;
  elapsed_seconds: number;
  message: string;
  report_id?: string | null;
}

export interface ReportSummary {
  id: string;
  created_at: string;
  role_title: string | null;
  match_score: number | null;
}
