"""The output of text extraction, shared by the PDF and DOCX extractors."""

from dataclasses import dataclass, field


@dataclass
class ExtractedDoc:
    text: str                      # whole document in reading order, one line per "\n"
    page_count: int
    columns: int = 1               # max text columns detected on any page
    image_count: int = 0
    table_count: int = 0           # DOCX only
    header_footer_text: list[str] = field(default_factory=list)  # text in Word header/footer sections
    links: list[str] = field(default_factory=list)   # hyperlink targets (may not be visible as text)

    @property
    def lines(self) -> list[str]:
        return [line for line in self.text.split("\n") if line.strip()]

    def meta(self) -> dict:
        """What we store in resumes.extract_meta."""
        return {
            "page_count": self.page_count,
            "columns": self.columns,
            "image_count": self.image_count,
            "table_count": self.table_count,
            "header_footer_text": self.header_footer_text,
            "links": self.links,
        }
