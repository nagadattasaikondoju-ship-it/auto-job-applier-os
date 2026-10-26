"""Job-targeted ATS resume: rewrite a profile for one job description without inventing anything.

The AI analyses the job and rewrites the summary, skills and bullets. Every piece it returns is then
checked in code: titles, companies and dates always come from the profile, skills must already be
in the resume, and a bullet that adds numbers, tools or claims falls back to the original wording.
Scores are computed in code (keywords 30, experience 25, achievements 20, structure 15, clarity 10)
so they're comparable between runs. Without the AI, a rules-only version still reorders the resume
around the job.
"""

import json
import logging
import re
from typing import Any

from packages.ai.client import AIUnavailableError, gemini_client
from packages.ai.schemas import AtsResumeOutput, JobDescriptionAnalysis
from packages.core.config import settings
from packages.core.services.ats import (
    _norm,
    evidenced_skills,
    jd_keywords,
    job_fit_score,
    profile_snapshot_to_text,
    verify_rewrite,
)
from packages.documents.export import build_resume_document, document_text

logger = logging.getLogger("applyon.ats_optimizer")

SYSTEM_PROMPT = """You are "ATS Resume Tailor Pro", an expert resume strategist, technical recruiter, ATS specialist \
and hiring manager with 20+ years of experience placing candidates at startups, agencies and global product companies.

Rewrite the candidate's resume for ONE job so it gets shortlisted:
1. Analyse the job: role title and ATS title variants, the top hard skills (max 20), soft skills (max 10), tools, \
must-have and nice-to-have responsibilities, seniority, industry terms.
2. Summary: 2-3 lines tailored to this job, using only facts in the profile.
3. Core skills: ONLY skills the profile already shows, most relevant to the job first.
4. Experience: for each role, rewrite each relevant bullet (and drop clearly irrelevant ones). Start with a strong \
action verb; say the task, tool or method; keep any result, scale or number that the original states. Present tense \
for the current role, past tense for earlier roles. 1-2 lines each. No "responsible for", "worked on", "helped \
with", "involved in", no first person.
5. Use the job's exact keywords ONLY where the original bullet already proves that experience. Never copy \
sentences from the job description.

Truthfulness is non-negotiable. You may rephrase, reorder and highlight transferable skills. You must NOT invent \
jobs, titles, companies, dates, degrees, certifications, tools, metrics, team sizes, leadership, ownership or results. \
If the original has no number, do not add one. If a required skill is missing, do not fake it: list it under \
development_recommendations.

Also return: changes_made (main improvements and why they raise relevance), missing_information (specific questions \
that would let the candidate strengthen the resume: metrics, tools, team size, outcomes), and final_recommendation \
(one or two sentences: ready to apply, needs minor edits, or needs more information).
Every rewritten bullet must reference the id of the original bullet it comes from."""

_STOP = {
    "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "at", "by", "with", "from", "into", "using",
    "used", "that", "which", "as", "its", "their", "our", "my", "across", "per", "via", "while", "was", "were",
    "is", "are", "be", "this", "these",
}


# Leadership/ownership claims the summary may only make if the resume already does (by word root)
_LEADERSHIP_ROOTS = (r"\blead", r"\bled\b", r"\bmanag", r"\bown", r"\bmentor", r"\bspearhead", r"\bheaded\b", r"\bdirect")


def _new_leadership_claim(text: str, master_text: str) -> bool:
    low, master = text.lower(), master_text.lower()
    return any(re.search(r, low) and not re.search(r, master) for r in _LEADERSHIP_ROOTS)


def _stems(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-z0-9+#/]+", text.lower()) if w not in _STOP}


# Where an added purpose or result usually starts: "..., improving X", "... to evaluate Y"
_CLAUSE = re.compile(
    r",\s|\s(?:to|in order to|by|while|which|resulting in|leading to|improving|enhancing|ensuring|driving|enabling)\s"
)


def _passes(text: str, src: str, skills: list[str], master_stems: set[str]) -> bool:
    return not verify_rewrite(src, text, skills) and len(_stems(text) - _stems(src) - master_stems) <= 2


def _salvage(text: str, src: str, skills: list[str], master_stems: set[str]) -> str | None:
    """The rewrite if it adds nothing; else the rewrite with an invented trailing clause cut off; else None."""
    if _passes(text, src, skills, master_stems):
        return text
    cuts = sorted({m.start() for m in _CLAUSE.finditer(text)}, reverse=True)
    for cut in cuts:
        # drop what would dangle after the cut ("..., significantly", "... and")
        head = re.sub(r"(?:[,;]?\s+(?:\w+ly|and|or|thereby|further|also|while))+$", "", text[:cut]).rstrip(" ,;")
        if len(head.split()) >= 4 and _passes(head, src, skills, master_stems):
            return head
    return None


def _relevance(text: str, jd_terms: set[str]) -> int:
    low = text.lower()
    return sum(1 for t in jd_terms if re.search(rf"(?<![\w]){re.escape(t)}(?![\w])", low))


def build_targeted_content(
    snapshot: dict[str, Any], ai: AtsResumeOutput | None, jd_text: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resume content (ResumeVersion.content_json shape) plus a record of what the guards changed."""
    master_text = profile_snapshot_to_text(snapshot)
    master_stems = _stems(master_text)
    skills = evidenced_skills(snapshot)
    skill_norms = {_norm(s) for s in skills}
    jd_terms = {k.lower() for k in jd_keywords(jd_text)}
    guard: dict[str, Any] = {"reverted_bullets": [], "removed_skills": [], "summary_kept_original": False, "rejected_summary": None}

    # Skills: only genuine ones, the job's first
    core: list[str] = []
    for s in (ai.core_skills if ai else []):
        if _norm(s) in skill_norms:
            match = next((x for x in skills if _norm(x) == _norm(s)), s)
            if match not in core:
                core.append(match)
        else:
            guard["removed_skills"].append(s)
    rest = sorted((s for s in skills if s not in core), key=lambda s: -_relevance(s, jd_terms))
    skills_ordered = (core + rest)[:30]

    # Summary: AI version unless it adds facts
    original_summary = (snapshot.get("profile") or {}).get("summary") or ""
    summary = (ai.summary.strip() if ai else "") or original_summary
    if ai and summary != original_summary:
        new_words = _stems(summary) - master_stems
        claims_leadership = _new_leadership_claim(summary, master_text)
        if verify_rewrite(master_text, summary, skills) or claims_leadership or len(new_words) > 7:
            guard["rejected_summary"] = summary
            summary = original_summary
            guard["summary_kept_original"] = True

    # Experience: titles, companies and dates always from the profile
    ai_bullets = {e.experience_id: e.bullets for e in (ai.experiences if ai else [])}
    experiences = []
    for exp in snapshot.get("experiences", []):
        exp_id = str(exp.get("id"))
        sources = {str(b.get("id")): b.get("text", "") for b in exp.get("bullets", []) if isinstance(b, dict)}
        bullets: list[dict[str, str]] = []
        for b in ai_bullets.get(exp_id, []):
            src = sources.get(str(b.source_bullet_id))
            if src is None or any(x["source_bullet_id"] == str(b.source_bullet_id) for x in bullets):
                continue  # unknown or duplicate source
            proposed = b.text.strip()
            text = _salvage(proposed, src, skills, master_stems)
            if text is None:
                guard["reverted_bullets"].append({"original": src, "rejected": proposed})
                text = src
            if not src.rstrip().endswith(".") and text.endswith("."):
                text = text.rstrip(".")
            bullets.append({"source_bullet_id": str(b.source_bullet_id), "text": text})
        if not bullets:  # AI unavailable or dropped them all: originals, most relevant first
            ordered = sorted(sources.items(), key=lambda kv: -_relevance(kv[1], jd_terms))
            bullets = [{"source_bullet_id": k, "text": v} for k, v in ordered if v]
        experiences.append(
            {"experience_id": exp_id, "company": exp.get("company", ""), "title": exp.get("title", ""), "bullets": bullets}
        )

    changes: list[str] = list(ai.changes_made) if ai else [
        "Ordered your skills and bullets so the ones this job asks for come first (AI was unavailable, so "
        "wording is unchanged)."
    ]
    if guard["reverted_bullets"]:
        changes.append(f"Kept your original wording for {len(guard['reverted_bullets'])} bullet(s) where the rewrite added facts")
    content = {
        "summary": summary,
        "skills_ordered": skills_ordered,
        "experiences": experiences,
        "keywords_used": [k for k in sorted(jd_keywords(jd_text), key=str.lower) if _norm(k) in skill_norms],
        "changes_made": changes,
    }
    return content, guard


async def optimize_resume_for_job(
    snapshot: dict[str, Any],
    jd_text: str,
    job_title: str = "",
    company: str = "",
    seniority: str = "",
    target_role: str = "",
    location: str = "",
) -> dict[str, Any]:
    """Before/after job-fit scores, keyword report and a guarded, job-targeted resume."""
    master_text = profile_snapshot_to_text(snapshot)
    before = job_fit_score(master_text, jd_text, job_title)

    ai: AtsResumeOutput | None = None
    if not gemini_client.is_mock:
        prompt = (
            f"JOB_TITLE: {job_title}\nTARGET_COMPANY: {company}\nCANDIDATE_TARGET_ROLE: {target_role}\n"
            f"CANDIDATE_SENIORITY: {seniority}\nLOCATION: {location}\n\nJOB_DESCRIPTION:\n{jd_text[:6000]}\n\n"
            f"CANDIDATE_PROFILE (the only source of truth; bullet ids in each experience):\n"
            f"{json.dumps(_profile_for_prompt(snapshot), ensure_ascii=False)}"
        )
        try:
            ai = await gemini_client.generate_structured(
                model_name=settings.gemini_model_smart,
                system_instruction=SYSTEM_PROMPT,
                prompt=prompt,
                response_model=AtsResumeOutput,
                prompt_version="v1_ats_job_resume",
                timeout_seconds=90.0,  # a whole resume is a long answer
            )
        except AIUnavailableError as e:
            logger.info("ATS optimizer falling back to rules: %s", e)

    content, guard = build_targeted_content(snapshot, ai, jd_text)
    doc = build_resume_document(snapshot, content)
    after = job_fit_score(document_text(doc), jd_text, job_title)

    development = list(ai.development_recommendations) if ai else []
    for k in after["keywords"]["missing"]:
        if not any(k.lower() in d.lower() for d in development):
            development.append(f"{k}: the job asks for it and your resume doesn't show it. Add it only if you've used it.")

    verdict = (
        "ready" if after["score"] >= 85 and after["keywords"]["coverage"] >= 70
        else "minor_edits" if after["score"] >= 70
        else "needs_info"
    )
    analysis = ai.job_analysis if ai else JobDescriptionAnalysis(role_title=job_title)
    if not analysis.hard_skills:  # smaller models sometimes leave the analysis thin
        analysis.hard_skills = sorted(jd_keywords(jd_text), key=str.lower)
    final = (ai.final_recommendation.strip() if ai else "") or {
        "ready": "Ready to apply: it covers the job's key skills and every line is backed by your experience.",
        "minor_edits": "Nearly there: apply, or first add metrics or the missing skills you genuinely have.",
        "needs_info": "Needs more information: the job asks for skills your resume doesn't show yet. See the gaps below.",
    }[verdict]
    return {
        "ai_used": ai is not None,
        "job_analysis": analysis.model_dump(),
        "before": {k: before[k] for k in ("score", "categories", "reason")},
        "after": {k: after[k] for k in ("score", "categories", "reason")},
        "keywords": after["keywords"],
        "content": content,
        "resume": doc,
        "changes_made": content["changes_made"],
        "missing_information": list(ai.missing_information) if ai else [],
        "development_recommendations": development[:12],
        "final_recommendation": final,
        "verdict": verdict,
        "guard": guard,
    }


def _profile_for_prompt(snapshot: dict[str, Any]) -> dict[str, Any]:
    p = snapshot.get("profile") or {}
    return {
        "name": p.get("full_name"),
        "headline": p.get("headline"),
        "summary": p.get("summary"),
        "skills": [s.get("name") for s in snapshot.get("skills", [])],
        "experiences": [
            {
                "id": str(e.get("id")),
                "title": e.get("title"),
                "company": e.get("company"),
                "dates": f"{e.get('start_date') or ''} - {'Present' if e.get('is_current') else e.get('end_date') or ''}",
                "current": bool(e.get("is_current")),
                "bullets": [{"id": str(b.get("id")), "text": b.get("text")} for b in e.get("bullets", []) if isinstance(b, dict)],
            }
            for e in snapshot.get("experiences", [])
        ],
        "projects": [{"title": x.get("title"), "description": x.get("description")} for x in snapshot.get("projects", [])],
        "education": [
            {"degree": x.get("degree"), "field": x.get("field"), "institution": x.get("institution")}
            for x in snapshot.get("educations", [])
        ],
        "certifications": [x.get("name") for x in snapshot.get("certifications", [])],
    }
