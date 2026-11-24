"""Build synthetic resume files in code (no binary fixtures in the repo, no real personal data)."""

import io

import docx
import pymupdf

SAMPLE_RESUME = """Asha Verma
asha.verma@example.com | +91 98765 43210 | linkedin.com/in/ashaverma | github.com/ashaverma
EDUCATION
B.Tech Computer Science, Example Institute of Technology, 2022 - 2026, CGPA 8.4/10
EXPERIENCE
Backend Intern, Acme Payments, Jun 2025 - Aug 2025
Built a FastAPI service for invoice reconciliation handling 20k requests per day
Responsible for writing unit tests with pytest
PROJECTS
Campus Placement Tracker
Developed a Next.js dashboard backed by PostgreSQL for 300 students
Implemented Redis caching that cut page load time by 40%
SKILLS
Python, FastAPI, PostgreSQL, Redis, Docker, React, Kubernetes"""


def single_column_pdf(text: str = SAMPLE_RESUME) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    y = 70
    for line in text.split("\n"):
        page.insert_text((50, y), line, fontsize=10)
        y += 16
    return doc.tobytes()


def two_column_pdf() -> bytes:
    """Full-width header, then a narrow left column (skills) and a wide right column (experience)."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 60), "Asha Verma - Backend Engineer - asha.verma@example.com - github.com/ashaverma",
                     fontsize=10)
    left = ["SKILLS", "Python", "FastAPI", "PostgreSQL", "Redis", "Docker"]
    right = ["EXPERIENCE", "Backend Intern, Acme Payments", "Built a FastAPI service for invoices",
             "Wrote pytest suites for the billing API", "Added Redis caching to hot endpoints", "PROJECTS"]
    for i, (lt, rt) in enumerate(zip(left, right, strict=True)):
        y = 100 + i * 16
        page.insert_text((50, y), lt, fontsize=10)    # left column: x 50..~150
        page.insert_text((230, y), rt, fontsize=10)   # right column starts at x 230
    return doc.tobytes()


def scanned_pdf() -> bytes:
    """A page that is only an image (what a phone scan looks like to a parser)."""
    doc = pymupdf.open()
    page = doc.new_page()
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 200, 260), False)
    pix.clear_with(230)
    page.insert_image(pymupdf.Rect(40, 40, 555, 800), pixmap=pix)
    return doc.tobytes()


def resume_docx(with_table: bool = True, header_text: str | None = None) -> bytes:
    document = docx.Document()
    if header_text:  # Word header section (some parsers skip it)
        document.sections[0].header.paragraphs[0].text = header_text
    lines = SAMPLE_RESUME.split("\n")
    skills_at = lines.index("SKILLS")
    for line in lines[:skills_at]:
        document.add_paragraph(line)
    document.add_paragraph("SKILLS")
    if with_table:
        table = document.add_table(rows=2, cols=2)
        table.cell(0, 0).text, table.cell(0, 1).text = "Backend", "Python, FastAPI, PostgreSQL"
        table.cell(1, 0).text, table.cell(1, 1).text = "Tools", "Redis, Docker"
    document.add_paragraph("References available on request")
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()
