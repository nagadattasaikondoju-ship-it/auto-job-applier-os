"""ATS-friendly PDF and DOCX export built in pure Python (fpdf2 + python-docx).

Both formats use one column, standard headings, real text and no tables or images,
which is what applicant tracking systems parse most reliably.
"""

import io
from typing import Any

from docx import Document
from docx.shared import Pt
from fpdf import FPDF

# Characters outside Latin-1 that commonly appear in resumes, mapped to safe equivalents
# for the PDF core fonts.
_REPLACEMENTS = {
    "–": "-",
    "—": "-",
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "•": "-",
    "…": "...",
    "₹": "Rs ",
    " ": " ",
}


def _latin1(text: str) -> str:
    for src, dst in _REPLACEMENTS.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "ignore").decode("latin-1")


def _bullet_text(bullet: Any) -> str:
    if isinstance(bullet, dict):
        return str(bullet.get("text", "")).strip()
    return str(bullet).strip()


def _dates(start: str | None, end: str | None, is_current: bool = False) -> str:
    end_label = "Present" if is_current else (end or "")
    return " - ".join(p for p in [start or "", end_label] if p)


def build_resume_document(
    snapshot: dict[str, Any], tailored: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Merge a profile snapshot with optional tailored content into one printable structure.

    Tailored content only reorders and rewrites existing facts; anything it doesn't cover
    falls back to the master profile.
    """
    profile = snapshot.get("profile", {})
    links = profile.get("links") or {}
    contact = [
        profile.get("email"),
        profile.get("phone"),
        ", ".join(p for p in [profile.get("city"), profile.get("country")] if p),
        *[v for v in links.values() if v],
    ]

    experiences_by_id = {str(e.get("id")): e for e in snapshot.get("experiences", [])}
    experiences: list[dict[str, Any]] = []
    if tailored and tailored.get("experiences"):
        for t in tailored["experiences"]:
            src = experiences_by_id.get(str(t.get("experience_id")), {})
            experiences.append(
                {
                    "title": t.get("title") or src.get("title", ""),
                    "company": t.get("company") or src.get("company", ""),
                    "dates": _dates(src.get("start_date"), src.get("end_date"), bool(src.get("is_current"))),
                    "location": src.get("location") or "",
                    "bullets": [_bullet_text(b) for b in t.get("bullets", []) if _bullet_text(b)],
                }
            )
    else:
        for e in snapshot.get("experiences", []):
            experiences.append(
                {
                    "title": e.get("title", ""),
                    "company": e.get("company", ""),
                    "dates": _dates(e.get("start_date"), e.get("end_date"), bool(e.get("is_current"))),
                    "location": e.get("location") or "",
                    "bullets": [_bullet_text(b) for b in e.get("bullets", []) if _bullet_text(b)],
                }
            )

    skills = (tailored or {}).get("skills_ordered") or [s.get("name", "") for s in snapshot.get("skills", [])]

    return {
        "name": profile.get("full_name") or "Candidate",
        "headline": profile.get("headline") or profile.get("current_title") or "",
        "contact": [c for c in contact if c],
        "summary": (tailored or {}).get("summary") or profile.get("summary") or "",
        "skills": [s for s in skills if s],
        "experiences": experiences,
        "educations": [
            {
                "line": ", ".join(p for p in [e.get("degree"), e.get("field")] if p),
                "institution": e.get("institution", ""),
                "dates": _dates(e.get("start_date"), e.get("end_date")),
                "grade": e.get("grade") or "",
            }
            for e in snapshot.get("educations", [])
        ],
        "projects": [
            {
                "title": p.get("title", ""),
                "description": p.get("description") or "",
                "skills": p.get("skills") or [],
            }
            for p in snapshot.get("projects", [])
        ],
        "certifications": [
            ", ".join(x for x in [c.get("name"), c.get("issuer"), c.get("issue_date")] if x)
            for c in snapshot.get("certifications", [])
        ],
    }


class _ResumePDF(FPDF):
    def section(self, title: str) -> None:
        self.ln(3)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 6, _latin1(title.upper()), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(180, 180, 180)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(1.5)

    def para(self, text: str, size: float = 10, style: str = "") -> None:
        self.set_font("Helvetica", style, size)
        self.multi_cell(0, 5, _latin1(text), new_x="LMARGIN", new_y="NEXT")

    def bullet(self, text: str) -> None:
        self.set_font("Helvetica", "", 10)
        x = self.get_x()
        self.cell(5, 5, "-")
        self.multi_cell(0, 5, _latin1(text), new_x="LMARGIN", new_y="NEXT")
        self.set_x(x)


def resume_pdf_bytes(doc: dict[str, Any]) -> bytes:
    pdf = _ResumePDF(format="A4")
    pdf.set_margins(16, 14, 16)
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 9, _latin1(doc["name"]), new_x="LMARGIN", new_y="NEXT")
    if doc["headline"]:
        pdf.para(doc["headline"], 11)
    if doc["contact"]:
        pdf.para(" | ".join(doc["contact"]), 9)

    if doc["summary"]:
        pdf.section("Summary")
        pdf.para(doc["summary"])
    if doc["skills"]:
        pdf.section("Skills")
        pdf.para(", ".join(doc["skills"]))
    if doc["experiences"]:
        pdf.section("Experience")
        for e in doc["experiences"]:
            pdf.para(" - ".join(p for p in [e["title"], e["company"]] if p), 10.5, "B")
            meta = " | ".join(p for p in [e["dates"], e["location"]] if p)
            if meta:
                pdf.para(meta, 9)
            for b in e["bullets"]:
                pdf.bullet(b)
            pdf.ln(1.5)
    if doc["projects"]:
        pdf.section("Projects")
        for p in doc["projects"]:
            pdf.para(p["title"], 10.5, "B")
            if p["description"]:
                pdf.para(p["description"])
            if p["skills"]:
                pdf.para("Tools: " + ", ".join(p["skills"]), 9)
    if doc["educations"]:
        pdf.section("Education")
        for e in doc["educations"]:
            pdf.para(" - ".join(p for p in [e["line"], e["institution"]] if p), 10.5, "B")
            meta = " | ".join(p for p in [e["dates"], e["grade"]] if p)
            if meta:
                pdf.para(meta, 9)
    if doc["certifications"]:
        pdf.section("Certifications")
        for c in doc["certifications"]:
            pdf.bullet(c)

    return bytes(pdf.output())


def resume_docx_bytes(doc: dict[str, Any]) -> bytes:
    d = Document()
    style = d.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    d.add_heading(doc["name"], level=0)
    if doc["headline"]:
        d.add_paragraph(doc["headline"])
    if doc["contact"]:
        d.add_paragraph(" | ".join(doc["contact"]))

    def heading(text: str) -> None:
        d.add_heading(text, level=1)

    if doc["summary"]:
        heading("Summary")
        d.add_paragraph(doc["summary"])
    if doc["skills"]:
        heading("Skills")
        d.add_paragraph(", ".join(doc["skills"]))
    if doc["experiences"]:
        heading("Experience")
        for e in doc["experiences"]:
            p = d.add_paragraph()
            p.add_run(" - ".join(x for x in [e["title"], e["company"]] if x)).bold = True
            meta = " | ".join(x for x in [e["dates"], e["location"]] if x)
            if meta:
                d.add_paragraph(meta)
            for b in e["bullets"]:
                d.add_paragraph(b, style="List Bullet")
    if doc["projects"]:
        heading("Projects")
        for pr in doc["projects"]:
            p = d.add_paragraph()
            p.add_run(pr["title"]).bold = True
            if pr["description"]:
                d.add_paragraph(pr["description"])
    if doc["educations"]:
        heading("Education")
        for e in doc["educations"]:
            p = d.add_paragraph()
            p.add_run(" - ".join(x for x in [e["line"], e["institution"]] if x)).bold = True
            meta = " | ".join(x for x in [e["dates"], e["grade"]] if x)
            if meta:
                d.add_paragraph(meta)
    if doc["certifications"]:
        heading("Certifications")
        for c in doc["certifications"]:
            d.add_paragraph(c, style="List Bullet")

    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def cover_letter_pdf_bytes(name: str, contact: list[str], body: str) -> bytes:
    pdf = _ResumePDF(format="A4")
    pdf.set_margins(22, 20, 22)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, _latin1(name), new_x="LMARGIN", new_y="NEXT")
    if contact:
        pdf.para(" | ".join(contact), 9)
    pdf.ln(6)
    for para in [p.strip() for p in body.split("\n\n") if p.strip()]:
        pdf.para(para, 10.5)
        pdf.ln(2)
    return bytes(pdf.output())
