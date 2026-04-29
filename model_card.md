# Model Card - CareerScope

## System Limitations and Biases

CareerScope's recommendations are only as representative as the job descriptions and benchmark resumes seeded into its Supabase pgvector corpus. If the corpus over-represents large technology companies, finance firms, U.S.-based employers, or entry-level software roles, the retrieved context and gap analysis will treat those patterns as the baseline. That can make legitimate nontraditional paths, smaller-company expectations, public-sector roles, international hiring norms, or interdisciplinary backgrounds look weaker than they are.

Resume parsing can degrade when a PDF uses unusual formatting such as dense columns, graphics-heavy templates, embedded icons, tables, sidebars, scanned images, or nonstandard section labels. The parser may omit skills, merge unrelated sections, or misread dates when the extracted text order differs from the visual layout. Because later agents depend on the parsed `ParsedResume` and `ParsedJD` objects, early extraction errors can propagate into retrieval, scoring, roadmap generation, and outreach drafts.

The system is not able to directly evaluate soft skills, communication ability, leadership, interview performance, workplace behavior, or culture fit. It can infer signals from resume text and job descriptions, but those inferences are incomplete and should not be treated as evidence of a student's actual collaboration style or potential. CareerScope is therefore better suited for identifying document-level gaps than judging a person's employability.

Match scores and confidence scores are model-generated signals, not calibrated probabilities. A score of 0.70 should be read as a rough ranking aid, not a 70% chance of getting an interview or offer. The system is also optimized for English-language resumes and English-language job descriptions, so multilingual users or non-English postings may receive lower-quality parsing, retrieval, and feedback.

## Misuse Potential and Mitigations

The main misuse risk is that an employer or recruiter could invert CareerScope into a candidate filter, using the match score or gap list to reject applicants automatically. That would be inappropriate because the score is uncalibrated, the corpus may be biased, and the system does not measure many real hiring factors such as interviews, references, growth trajectory, or accommodations. It would also amplify parsing errors and corpus skew into high-stakes decisions.

CareerScope mitigates this by framing outputs as development coaching for students rather than screening judgments for employers. The generated report emphasizes skill gaps, evidence, learning priorities, and outreach support so the user can improve their materials and plan next steps. The intended user is the student evaluating their own resume against a target role, not a hiring team ranking a candidate pool.

The code also includes privacy-oriented guardrails. `core/guardrails.py` validates resume PDFs and job description inputs, checks low confidence thresholds, and sanitizes generated text by redacting common email and U.S. phone-number patterns before logging. This does not remove every possible identifier, but it reduces accidental leakage of direct contact information in logs and reinforces that CareerScope is designed for self-use, not employer-side screening.

## Testing Surprises

The most likely edge cases are not exotic model failures; they are ordinary document and input failures. Resumes with two-column layouts, tables, icons, or PDF text extraction artifacts can cause missing or reordered skills. Very short job descriptions do not provide enough signal for retrieval, while overly broad descriptions can lead the gap analyzer to produce generic gaps that are technically plausible but not well grounded in the target role.

TC-005 is the consistency test for this risk: it runs the same resume and job description twice and expects the match scores to remain within 0.10. That tolerance is useful because Gemini outputs can vary even with structured JSON prompts. If TC-005 fails, the score should not be presented as stable enough for comparison across roles or iterations without additional controls such as lower temperature, stricter schemas, or post-processing.

Hallucination risk is highest when retrieved corpus matches are weak or when the resume lacks detail. In those cases the gap analyzer may overstate missing skills, infer experience level from thin evidence, or recommend roadmap items that are reasonable for the industry but not directly supported by the user's inputs. The retriever's low-match warning and the report's evidence fields are important safeguards because they make weak grounding easier to detect.

## AI Collaboration Log

A helpful AI-assisted moment was using AI to turn the project handoff into a concrete multi-agent implementation plan: parser, retriever, gap analyzer, roadmap, outreach, orchestrator, eval harness, and documentation. That helped keep the system modular and made it easier to test each component independently.

An incorrect AI suggestion was an earlier recommendation to use a different provider stack and 1536-dimensional embeddings. That conflicted with the actual project override and implementation, which use Google Gemini through `google-genai`, `text-embedding-004`, and Supabase `vector(768)`. The correction was to align the agents, embedding utility, database schema, tests, and documentation around the Gemini-only architecture.

Overall, AI was used as a drafting and implementation partner rather than as an unchecked source of truth. The workflow was to ask AI for scaffolding, compare the output against the project constraints and codebase, reject suggestions that introduced unsupported dependencies, and then verify behavior with unit tests and the eval harness design. Human review remained necessary for provider choices, privacy framing, bias discussion, and deciding which outputs were appropriate for student self-use.
