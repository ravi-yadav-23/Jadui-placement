import pytest

from app.core.errors import AppError
from app.resume.pipeline.extract_docx import extract_docx
from app.resume.pipeline.extract_pdf import extract_pdf
from app.resume.pipeline.ingest import detect_file_kind, validate_upload
from tests.resume import builders


def test_detects_pdf_and_docx_by_bytes():
    assert detect_file_kind(builders.single_column_pdf()) == "pdf"
    assert detect_file_kind(builders.resume_docx()) == "docx"


@pytest.mark.parametrize("data", [b"hello", b"PK\x03\x04not-a-zip", b"\xd0\xcf\x11\xe0 old .doc"])
def test_rejects_other_files(data):
    with pytest.raises(AppError) as err:
        detect_file_kind(data)
    assert err.value.status == 415


def test_rejects_empty_and_oversized(monkeypatch):
    from app.core.config import settings

    with pytest.raises(AppError):
        validate_upload(b"")
    monkeypatch.setattr(settings, "RESUME_MAX_BYTES", 10)
    with pytest.raises(AppError) as err:
        validate_upload(b"%PDF-" + b"x" * 20)
    assert err.value.code == "file_too_large"


def test_single_column_keeps_one_line_per_line():
    doc = extract_pdf(builders.single_column_pdf())
    assert doc.columns == 1
    assert doc.page_count == 1
    assert doc.lines == builders.SAMPLE_RESUME.split("\n")  # newlines preserved, order intact


def test_two_column_reads_left_column_then_right_column():
    doc = extract_pdf(builders.two_column_pdf())
    assert doc.columns == 2
    lines = doc.lines
    assert lines[0].startswith("Asha Verma")                     # full-width header first
    assert lines[1:7] == ["SKILLS", "Python", "FastAPI", "PostgreSQL", "Redis", "Docker"]
    assert lines[7] == "EXPERIENCE"                               # then the right column, intact
    assert "Built a FastAPI service for invoices" in lines


def test_scanned_pdf_has_no_text_but_an_image():
    doc = extract_pdf(builders.scanned_pdf())
    assert doc.text == ""
    assert doc.image_count == 1


def test_docx_header_section_text_is_reported():
    doc = extract_docx(builders.resume_docx(header_text="asha.verma@example.com"))
    assert doc.header_footer_text == ["asha.verma@example.com"]


def test_docx_keeps_table_in_document_order():
    doc = extract_docx(builders.resume_docx())
    lines = doc.lines
    skills = lines.index("SKILLS")
    assert lines[skills + 1] == "Backend | Python, FastAPI, PostgreSQL"   # table right after its heading
    assert lines[-1] == "References available on request"                # paragraph after the table
    assert doc.table_count == 1
