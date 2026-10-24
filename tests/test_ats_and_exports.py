"""Tests for the ATS scanner, rule-based resume parser, document exports and follow-up drafts."""

import io
from datetime import UTC, datetime

import pytest
from docx import Document
from httpx import ASGITransport, AsyncClient
from pypdf import PdfReader

from apps.api.main import app
from packages.core.services.ats import (
    UnsupportedFileError,
    analyze_resume,
    extract_text,
    heuristic_parse,
    verify_rewrite,
)
from packages.core.services.followups import template_follow_up
from packages.documents.export import (
    build_resume_document,
    cover_letter_pdf_bytes,
    resume_docx_bytes,
    resume_pdf_bytes,
)

WEAK = """Priya Sharma
priya@example.com
Experience
Frontend Developer at Acme
- Responsible for working on the website
- Helped with various tasks in the team
Education
B.Tech Computer Science, COEP
"""

STRONG = (
    """Priya Sharma | priya@example.com | +91 98765 43210 | Pune, India | linkedin.com/in/priya
Summary
Frontend engineer with 3 years building React and TypeScript apps for 200k users.
Skills
React, TypeScript, Next.js, Node.js, AWS, Jest, Figma, SQL, Git, Docker, GraphQL, Tailwind
Experience
Frontend Engineer, Acme (Jan 2022 - Present)
- Built a design system in React used by 6 product teams, cutting UI build time by 30%
- Reduced bundle size by 40% with code splitting, improving LCP from 4.1s to 2.3s
- Led migration of 120 pages from JavaScript to TypeScript with zero production incidents
Projects
Expense tracker: Next.js app with 2k monthly users
Education
B.Tech Computer Science, COEP Pune (2021) - 8.4 CGPA
"""
    + " Additional context about scaling frontend systems." * 25
)

SNAPSHOT = {
    "profile": {"full_name": "Priya Sharma", "email": "p@x.com", "city": "Pune", "summary": "Frontend engineer – ₹ “quotes”"},
    "experiences": [
        {"id": "e1", "title": "Frontend Engineer", "company": "Acme", "start_date": "Jan 2022", "is_current": True,
         "bullets": [{"id": "b1", "text": "Built a design system used by 6 teams"}]}
    ],
    "educations": [{"degree": "B.Tech", "field": "CS", "institution": "COEP", "grade": "8.4"}],
    "skills": [{"name": "React"}, {"name": "TypeScript"}],
    "projects": [],
    "certifications": [],
}


def test_weak_resume_scores_low_with_actionable_issues() -> None:
    r = analyze_resume(WEAK, jd_text="Frontend Engineer with React, TypeScript and AWS")
    assert r["score"] < 50
    assert r["grade"] == "needs_work"
    titles = {i["title"] for i in r["issues"]}
    assert "No phone number found" in titles
    assert "Weak phrasing" in titles
    assert {"React", "TypeScript", "AWS"} <= set(r["keywords"]["missing"])
    assert r["issues"][0]["severity"] == "high"  # sorted most severe first


def test_strong_resume_scores_high() -> None:
    r = analyze_resume(STRONG, jd_text="We need React, TypeScript, GraphQL and AWS.")
    assert r["score"] >= 85
    assert r["keywords"]["missing"] == []
    assert sum(c["max"] for c in r["categories"]) == 100


def test_rewrite_verification_blocks_invented_facts() -> None:
    assert verify_rewrite("Helped with the website", "Built the website, improving speed by 40%", []) is not None
    assert "tools" in (verify_rewrite("Worked on the dashboard", "Built the dashboard in GraphQL", []) or "")
    assert verify_rewrite("Worked on React dashboard", "Built a React dashboard for internal teams", ["React"]) is None


def test_heuristic_parse_reads_real_text() -> None:
    parsed = heuristic_parse(
        "Priya Sharma\npriya@example.com | +91 98765 43210 | Pune | linkedin.com/in/priya-s | github.com/priya\nExperience\n"
        "Frontend Engineer at Acme (Jan 2022 - Present)\n- Built a design system in React\nSkills\nReact, AWS\n"
    )
    assert parsed["full_name"] == "Priya Sharma"
    assert parsed["email"] == "priya@example.com"
    assert parsed["city"] == "Pune"
    exp = parsed["experiences"][0]
    assert (exp["title"], exp["company"], exp["is_current"]) == ("Frontend Engineer", "Acme", True)
    assert exp["bullets"][0]["text"] == "Built a design system in React"
    assert {"React", "AWS"} <= {s["name"] for s in parsed["skills"]}
    assert parsed["links"] == {"linkedin": "https://linkedin.com/in/priya-s", "github": "https://github.com/priya"}


def test_extract_text_formats() -> None:
    d = Document()
    d.add_paragraph("Priya Sharma " * 20)
    buf = io.BytesIO()
    d.save(buf)
    assert "Priya Sharma" in extract_text("cv.docx", buf.getvalue())
    with pytest.raises(UnsupportedFileError):
        extract_text("cv.png", b"x" * 500)
    with pytest.raises(UnsupportedFileError):
        extract_text("cv.txt", b"too short")


def test_pdf_and_docx_exports_contain_resume_text() -> None:
    doc = build_resume_document(SNAPSHOT)
    pdf_text = PdfReader(io.BytesIO(resume_pdf_bytes(doc))).pages[0].extract_text()
    assert "Priya Sharma" in pdf_text
    assert "Built a design system used by 6 teams" in pdf_text
    assert "EXPERIENCE" in pdf_text
    docx = Document(io.BytesIO(resume_docx_bytes(doc)))
    assert any("Frontend Engineer" in p.text for p in docx.paragraphs)
    assert cover_letter_pdf_bytes("Priya", ["p@x.com"], "Dear team,\n\nHello.").startswith(b"%PDF")


def test_tailored_content_overrides_master_bullets() -> None:
    tailored = {
        "summary": "Tailored summary",
        "skills_ordered": ["TypeScript", "React"],
        "experiences": [{"experience_id": "e1", "company": "Acme", "title": "Frontend Engineer",
                         "bullets": [{"source_bullet_id": "b1", "text": "Built a React design system for 6 teams"}]}],
    }
    doc = build_resume_document(SNAPSHOT, tailored)
    assert doc["summary"] == "Tailored summary"
    assert doc["skills"] == ["TypeScript", "React"]
    assert doc["experiences"][0]["bullets"] == ["Built a React design system for 6 teams"]
    assert doc["experiences"][0]["dates"] == "Jan 2022 - Present"


def test_follow_up_template() -> None:
    draft = template_follow_up("Priya Sharma", "Frontend Engineer", "Razorfin", datetime(2026, 10, 1, tzinfo=UTC), "Built a design system")
    assert "Frontend Engineer" in draft["subject"]
    assert "1 October" in draft["body"] and "Razorfin" in draft["body"]
    assert "Recently, I built a design system." in draft["body"]
    assert draft["body"].rstrip().endswith("Priya Sharma")


@pytest.mark.asyncio
async def test_resume_upload_rejects_unsupported_files() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/v1/resumes/upload",
            headers={"X-Dev-User-Id": "dev-user-1"},
            files={"file": ("photo.png", b"\x89PNG" + b"0" * 400, "image/png")},
        )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "UNSUPPORTED_RESUME"


def test_gemini_schema_has_no_refs_or_titles() -> None:
    import json

    from packages.ai.client import to_gemini_schema
    from packages.ai.schemas import ParsedResumeOutput, TailoredResumeOutput

    def schema_keys(node: object) -> set[str]:
        """Keywords used by schema nodes (property names are skipped)."""
        if not isinstance(node, dict):
            return set()
        keys = set(node)
        for k, v in node.items():
            children = v.values() if k == "properties" else ([v] if isinstance(v, dict) else v if isinstance(v, list) else [])
            for child in children:
                keys |= schema_keys(child)
        return keys

    for model in (ParsedResumeOutput, TailoredResumeOutput):
        converted = to_gemini_schema(model.model_json_schema())
        assert "$ref" not in json.dumps(converted)
        assert not schema_keys(converted) & {"$defs", "title", "default"}
    schema = to_gemini_schema(ParsedResumeOutput.model_json_schema())
    exp = schema["properties"]["experiences"]["items"]
    assert exp["properties"]["end_date"]["nullable"] is True  # str | None -> nullable


@pytest.mark.asyncio
async def test_resume_parse_falls_back_to_rules_when_ai_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.api.routers import resumes
    from packages.ai.client import AIUnavailableError, gemini_client

    async def boom(**_: object) -> None:
        raise AIUnavailableError("down")

    monkeypatch.setattr(gemini_client, "api_key", "real-looking-key")
    monkeypatch.setattr(gemini_client, "generate_structured", boom)
    parsed = await resumes._parse_resume_text("Priya Sharma\npriya@example.com\nExperience\nEngineer at Acme (2022 - Present)\n- Built things\n")
    assert parsed["full_name"] == "Priya Sharma"  # real text, never mock data


def test_follow_up_highlight_skips_weak_bullets() -> None:
    from packages.core.services.followups import pick_highlight

    bullets = ["Responsible for working on the dashboard", "Built a React app", "Cut load time by 40% with caching."]
    assert pick_highlight(bullets) == "Cut load time by 40% with caching"
    assert pick_highlight(bullets[:2]) == "Built a React app"
    assert pick_highlight(bullets[:1]) is None


def test_jd_keywords_ignore_levels_and_domains() -> None:
    r = analyze_resume(STRONG, jd_text="SDE II at HevoData.com. You will use React, Neo4J and Kafka to go live fast.")
    assert set(r["keywords"]["missing"]) == {"Neo4J", "Kafka"}  # no "Go", "SDE", "II" or the domain


def test_tidy_removes_grade_repeated_in_institution() -> None:
    from apps.api.routers.resumes import _tidy

    parsed = {"educations": [{"institution": "RV College of Engineering, Bengaluru 8.2 CGPA", "grade": "8.2 CGPA"}]}
    assert _tidy(parsed)["educations"][0]["institution"] == "RV College of Engineering, Bengaluru"


def test_experience_months_come_from_resume_dates() -> None:
    from apps.api.routers.resumes import _tidy

    parsed = {
        "total_experience_months": 360,  # what the model claimed
        "experiences": [
            {"title": "Frontend Engineer", "start_date": "Jan 2022", "end_date": "Dec 2024", "is_current": False},
            {"title": "Software Engineer Intern", "start_date": "Jun 2021", "end_date": "Dec 2021", "is_current": False},
        ],
    }
    assert 34 <= _tidy(parsed)["total_experience_months"] <= 36  # internship not counted


def test_recognised_skills_exclude_degrees_and_initials() -> None:
    r = analyze_resume(STRONG + "\nB.Tech, RV College of Engineering, 8.2 CGPA. Built AI and ML features.", jd_text="AI, ML")
    keywords = set(r["keywords"]["matched"]) | set(r["keywords"]["missing"])
    assert not keywords & {"B.Tech", "RV", "CGPA"}
    assert {"AI", "ML"} <= set(r["keywords"]["matched"])
