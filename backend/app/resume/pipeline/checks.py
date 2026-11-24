"""Parse-health checks: "can a parser (and a skimming recruiter) read this file correctly?"

This is NOT a fake "ATS score". Each check is a concrete, explainable rule with a fix.
Every check is a small pure function taking the same CheckContext and returning a Check.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

from app.resume.pipeline.contacts import visible_in_text
from app.resume.pipeline.document import ExtractedDoc
from app.resume.pipeline.sections import SectionMap
from app.resume.schemas import Check, Contacts

MIN_TEXT_CHARS = 200
MIN_ALNUM_RATIO = 0.45          # same threshold as the CV Optimizer build check
MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
DATE = re.compile(rf"\b{MONTH}\s*'?\d{{2,4}}\b|\b\d{{1,2}}/\d{{4}}\b|\b(?:19|20)\d{{2}}\s*[-–—]", re.IGNORECASE)


@dataclass
class CheckContext:
    doc: ExtractedDoc
    contacts: Contacts
    sections: SectionMap
    filename: str


def _pass(check_id: str, message: str) -> Check:
    return Check(id=check_id, status="pass", message=message)


def text_extractable(ctx: CheckContext) -> Check:
    if len(ctx.doc.text.strip()) < MIN_TEXT_CHARS:
        return Check(id="text_extractable", status="fail",
                     message="Almost no text could be extracted. This looks like a scanned or image-only file.",
                     fix="Export the resume from Word, Google Docs or LaTeX as a PDF instead of scanning it.")
    return _pass("text_extractable", "Text extracts cleanly.")


def garbled(ctx: CheckContext) -> Check:
    chars = [c for c in ctx.doc.text if not c.isspace()]
    ratio = sum(c.isalnum() for c in chars) / len(chars) if chars else 1.0
    cid_tokens = ctx.doc.text.count("(cid:") + ctx.doc.text.count("�")
    if ratio < MIN_ALNUM_RATIO or cid_tokens > 5:
        return Check(id="garbled", status="fail",
                     message="Parts of the text come out as junk characters (font encoding problem).",
                     fix="Re-export using standard fonts, or 'Save as PDF' instead of 'Print to PDF'.")
    return _pass("garbled", "No garbled characters.")


def icon_glyphs(ctx: CheckContext) -> Check:
    # Icon fonts (e.g. FontAwesome) use the Unicode "private use area": parsers see junk.
    icons = sum(1 for c in ctx.doc.text if 0xE000 <= ord(c) <= 0xF8FF or ord(c) >= 0xF0000)
    if icons:
        return Check(id="icon_glyphs", status="warn", message=f"{icons} icon character(s) won't be readable.",
                     fix="Replace icons with plain labels like 'Email:' or 'GitHub:'.")
    return _pass("icon_glyphs", "No icon-font characters.")


def columns(ctx: CheckContext) -> Check:
    if ctx.doc.columns > 1:
        return Check(id="columns", status="warn",
                     message="Multi-column layout detected. Some parsers mix up the reading order.",
                     fix="A single-column layout is safest. Check the extracted text below reads in order.")
    return _pass("columns", "Single-column layout.")


def contact_email(ctx: CheckContext) -> Check:
    if not ctx.contacts.email:
        return Check(id="contact_email", status="fail", message="No email address found.",
                     fix="Add your email as plain text near the top.")
    return _pass("contact_email", f"Email found: {ctx.contacts.email}")


def contact_phone(ctx: CheckContext) -> Check:
    if not ctx.contacts.phone:
        return Check(id="contact_phone", status="warn", message="No phone number found.",
                     fix="Add a phone number with country code, e.g. +91 98765 43210.")
    return _pass("contact_phone", "Phone number found.")


def profile_links(ctx: CheckContext) -> Check:
    missing = [name for name, value in (("LinkedIn", ctx.contacts.linkedin), ("GitHub", ctx.contacts.github))
               if not value]
    if missing:
        return Check(id="profile_links", status="warn", message=f"Missing profile link(s): {', '.join(missing)}.",
                     fix="Tech recruiters expect LinkedIn and GitHub links in the header.")
    return _pass("profile_links", "LinkedIn and GitHub links found.")


def hyperlink_only(ctx: CheckContext) -> Check:
    hidden = [url for url in ctx.doc.links
              if url.startswith("http") and not visible_in_text(url, ctx.doc.text)]
    if hidden:
        return Check(id="hyperlink_only", status="info",
                     message=f"{len(hidden)} link(s) exist only as clickable text (e.g. 'GitHub'), not visible URLs.",
                     fix="Plain-text parsers and printouts lose these. Show key URLs as text, e.g. github.com/you.")
    return _pass("hyperlink_only", "All links are visible as text.")


def headings(ctx: CheckContext) -> Check:
    found = ctx.sections.found
    missing = [name for name in ("education", "skills") if name not in found]
    if "experience" not in found and "projects" not in found:
        missing.append("experience or projects")
    if missing:
        return Check(id="headings", status="warn",
                     message=f"No standard heading found for: {', '.join(missing)}.",
                     fix="Use standard headings such as EDUCATION, EXPERIENCE, PROJECTS, SKILLS.")
    return _pass("headings", "Standard section headings found.")


def nonstandard_headings(ctx: CheckContext) -> Check:
    if ctx.sections.nonstandard:
        names = ", ".join(ctx.sections.nonstandard[:4])
        return Check(id="nonstandard_headings", status="info", message=f"Unrecognised heading(s): {names}.",
                     fix="Creative headings may not be mapped to the right section by a parser.")
    return _pass("nonstandard_headings", "No unusual headings.")


def dates(ctx: CheckContext) -> Check:
    has_dated_sections = any(s in ctx.sections.found for s in ("experience", "education"))
    if has_dated_sections and not DATE.search(ctx.doc.text):
        return Check(id="dates", status="warn", message="No recognisable dates found.",
                     fix="Use a consistent format like 'Jun 2025 – Aug 2025'.")
    return _pass("dates", "Dates are in a recognisable format.")


def length(ctx: CheckContext) -> Check:
    pages = ctx.doc.page_count
    if pages > 2:
        return Check(id="length", status="warn", message=f"{pages} pages is long for most tech roles.",
                     fix="Aim for 1 page as a student/fresher, 2 pages at most with several years of experience.")
    if pages == 2:
        return Check(id="length", status="info", message="2 pages. Students and freshers are expected to fit 1.",
                     fix="Cut older or less relevant bullets rather than shrinking the font.")
    return _pass("length", "Length is fine.")


def word_count(ctx: CheckContext) -> Check:
    words = len(ctx.doc.text.split())
    if words < 250:
        return Check(id="word_count", status="warn", message=f"Only {words} words: the resume looks thin.",
                     fix="Add 2-3 specific bullets per role/project describing what you built and the result.")
    if words > 1000:
        return Check(id="word_count", status="warn", message=f"{words} words: likely too dense to skim.",
                     fix="Recruiters skim in seconds. Keep the strongest, most relevant bullets.")
    return _pass("word_count", f"{words} words: good density.")


def images_and_tables(ctx: CheckContext) -> Check:
    if ctx.doc.image_count:
        return Check(id="images_tables", status="warn",
                     message=f"{ctx.doc.image_count} image(s) found. Any text inside images is invisible to parsers.",
                     fix="Remove photos/graphics and keep all information as real text.")
    if ctx.doc.table_count:
        return Check(id="images_tables", status="info", message="Tables found. Most parsers cope, some scramble them.",
                     fix="Simple lines of text are the safest format for skills and dates.")
    return _pass("images_tables", "No images or tables.")


def header_footer_contact(ctx: CheckContext) -> Check:
    hidden = " ".join(ctx.doc.header_footer_text)
    if ctx.contacts.email and ctx.contacts.email in hidden:
        return Check(id="header_footer_contact", status="warn",
                     message="Your contact details are inside the Word header/footer.",
                     fix="Some parsers skip header/footer sections. Move contact details into the main body.")
    return _pass("header_footer_contact", "Contact details are in the main body.")


def filename(ctx: CheckContext) -> Check:
    name = ctx.filename.lower()
    if re.search(r"final|v\d|copy|\(\d\)|untitled|document|^resume\.", name):
        return Check(id="filename", status="info", message=f"File name '{ctx.filename}' looks generic.",
                     fix="Name it like Firstname_Lastname_Resume.pdf.")
    return _pass("filename", "File name looks professional.")


CHECKS: list[Callable[[CheckContext], Check]] = [
    text_extractable, garbled, icon_glyphs, columns, contact_email, contact_phone, profile_links,
    hyperlink_only, headings, nonstandard_headings, dates, length, word_count, images_and_tables,
    header_footer_contact, filename,
]


def run_checks(ctx: CheckContext) -> list[Check]:
    # A file with no text makes every other check meaningless, so stop early.
    first = text_extractable(ctx)
    if first.status == "fail":
        return [first]
    return [check(ctx) for check in CHECKS]
