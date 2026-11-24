"""DOCX -> text, keeping paragraphs and tables in the order they appear in the document.

python-docx exposes `doc.paragraphs` and `doc.tables` as two separate lists, which loses
their relative order (a skills table in the middle would end up at the bottom).
So we walk the document body's XML children in order instead.
"""

import io

import docx
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.resume.pipeline.document import ExtractedDoc


def _table_lines(table: Table) -> list[str]:
    lines = []
    for row in table.rows:
        cells: list[str] = []
        for cell in row.cells:
            text = cell.text.strip()
            if text and text not in cells:  # merged cells repeat their text
                cells.append(text)
        if cells:
            lines.append(" | ".join(cells))
    return lines


def extract_docx(data: bytes) -> ExtractedDoc:
    document = docx.Document(io.BytesIO(data))
    lines: list[str] = []
    tables = 0
    for child in document.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]  # strip the XML namespace
        if tag == "p":
            text = Paragraph(child, document).text.strip()
            if text:
                lines.append(text)
        elif tag == "tbl":
            tables += 1
            lines += _table_lines(Table(child, document))

    header_footer = []
    for section in document.sections:
        for part in (section.header, section.footer):
            header_footer += [p.text.strip() for p in part.paragraphs if p.text.strip()]

    return ExtractedDoc(
        text="\n".join(lines),
        page_count=0,  # Word decides pagination at render time; the .docx itself doesn't know
        table_count=tables,
        image_count=len(document.inline_shapes),
        header_footer_text=header_footer,
    )
