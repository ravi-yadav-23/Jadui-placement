"""PDF -> text in human reading order.

Why this is needed: a PDF stores text in whatever order the tool that made it chose.
For a two-column resume, a naive extractor often interleaves the columns line by line
("Python   Software Intern at X ..."), which wrecks everything downstream.

How we fix it, per page:
  1. Get every text line with its bounding box (x0, y0, x1, y1) from PyMuPDF.
  2. Look for a vertical "gutter": an x-position in the middle of the page that almost
     no line crosses, with plenty of lines on both sides. That means two columns.
  3. Lines that cross the gutter (e.g. the name/contact header) are full-width "separators".
     Between two separators we read the whole left column top-to-bottom, then the right column.
"""

from dataclasses import dataclass

import pymupdf

from app.resume.pipeline.document import ExtractedDoc

MIN_LINES_PER_COLUMN = 4
MAX_GUTTER_CROSSINGS = 0.15  # at most 15% of lines may cross the gutter (full-width lines)


@dataclass
class Line:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float


def page_lines(page: pymupdf.Page) -> list[Line]:
    lines: list[Line] = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line["spans"]).strip()
            if text:
                lines.append(Line(text, *line["bbox"]))
    return lines


def find_gutter(lines: list[Line], page_width: float) -> float | None:
    """Return the x-coordinate of a column gutter, or None for a single-column page."""
    if len(lines) < 2 * MIN_LINES_PER_COLUMN:
        return None
    best_x, best_crossings = None, len(lines) + 1
    # Only consider the middle of the page; margins are not gutters.
    for step in range(25, 76):
        x = page_width * step / 100
        crossings = sum(1 for ln in lines if ln.x0 < x < ln.x1)
        left = sum(1 for ln in lines if ln.x1 <= x)
        right = sum(1 for ln in lines if ln.x0 >= x)
        if left >= MIN_LINES_PER_COLUMN and right >= MIN_LINES_PER_COLUMN and crossings < best_crossings:
            best_x, best_crossings = x, crossings
    if best_x is None or best_crossings > MAX_GUTTER_CROSSINGS * len(lines):
        return None
    return best_x


def order_lines(lines: list[Line], gutter: float | None) -> list[Line]:
    by_position = sorted(lines, key=lambda ln: (round(ln.y0), ln.x0))
    if gutter is None:
        return by_position

    ordered: list[Line] = []
    left: list[Line] = []
    right: list[Line] = []

    def flush() -> None:
        ordered.extend(left)
        ordered.extend(right)
        left.clear()
        right.clear()

    for ln in by_position:
        if ln.x0 < gutter < ln.x1:   # full-width line: ends the current two-column section
            flush()
            ordered.append(ln)
        elif ln.x1 <= gutter:
            left.append(ln)
        else:
            right.append(ln)
    flush()
    return ordered


def extract_pdf(data: bytes) -> ExtractedDoc:
    out_lines: list[str] = []
    links: list[str] = []
    max_columns, images = 1, 0

    with pymupdf.open(stream=data, filetype="pdf") as doc:
        page_count = doc.page_count
        for page in doc:
            lines = page_lines(page)
            gutter = find_gutter(lines, page.rect.width)
            max_columns = max(max_columns, 2 if gutter else 1)
            images += len(page.get_images())
            links += [link["uri"] for link in page.get_links() if link.get("uri")]
            out_lines += [ln.text for ln in order_lines(lines, gutter)]

    return ExtractedDoc(
        text="\n".join(out_lines),
        page_count=page_count,
        columns=max_columns,
        image_count=images,
        links=links,
        # PDFs have no real header/footer sections (unlike Word), so nothing to report here.
    )


def count_pdf_pages(data: bytes) -> int:
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        return doc.page_count
