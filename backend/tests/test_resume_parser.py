import io
import pytest
from modules.resume_ai.parser import parser

def test_parse_docx_with_paragraphs():
    import docx
    doc = docx.Document()
    doc.add_paragraph("Jane Doe")
    doc.add_paragraph("Professional Summary: Experienced backend developer.")
    
    buf = io.BytesIO()
    doc.save(buf)
    
    text = parser._parse_docx(buf.getvalue())
    assert "Jane Doe" in text
    assert "Experienced backend developer" in text

def test_parse_docx_with_tables():
    import docx
    doc = docx.Document()
    doc.add_paragraph("Alex Smith")
    
    # Add a table with skills and coursework
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Category"
    table.cell(0, 1).text = "Skills"
    table.cell(1, 0).text = "Backend"
    table.cell(1, 1).text = "FastAPI, Python, Redis, Docker"
    
    buf = io.BytesIO()
    doc.save(buf)
    
    text = parser._parse_docx(buf.getvalue())
    assert "Alex Smith" in text
    assert "FastAPI" in text
    assert "Python" in text
    assert "Docker" in text

