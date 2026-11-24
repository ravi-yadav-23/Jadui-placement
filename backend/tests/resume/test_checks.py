import pytest

from app.resume.pipeline import checks as c
from app.resume.pipeline.contacts import extract_contacts
from app.resume.pipeline.document import ExtractedDoc
from app.resume.pipeline.sections import find_sections
from app.resume.schemas import Contacts
from tests.resume.builders import SAMPLE_RESUME


def ctx_for(text: str = SAMPLE_RESUME, filename: str = "Asha_Verma_Resume.pdf", **doc_fields) -> c.CheckContext:
    doc = ExtractedDoc(text=text, page_count=doc_fields.pop("page_count", 1), **doc_fields)
    return c.CheckContext(doc, extract_contacts(text, doc.links), find_sections(doc.lines), filename)


# ---------- contacts ----------

def test_contacts_from_sample_resume():
    contacts = extract_contacts(SAMPLE_RESUME, [])
    assert contacts == Contacts(email="asha.verma@example.com", phone="+91 98765 43210",
                                linkedin="linkedin.com/in/ashaverma", github="github.com/ashaverma")


def test_email_domain_is_not_mistaken_for_a_portfolio():
    assert extract_contacts("me@asha.dev", []).portfolio is None
    assert extract_contacts("Portfolio: asha.vercel.app", []).portfolio == "asha.vercel.app"


def test_links_are_a_fallback_source():
    contacts = extract_contacts("Asha Verma | GitHub", ["https://github.com/ashaverma"])
    assert contacts.github == "https://github.com/ashaverma"


@pytest.mark.parametrize("text", ["Roll no 12345678", "2022 - 2026", "CGPA 8.4/10"])
def test_numbers_that_are_not_phones(text):
    assert extract_contacts(text, []).phone is None


# ---------- sections ----------

def test_finds_standard_sections_and_flags_creative_ones():
    sections = find_sections(["Asha", "Work Experience:", "x", "MY JOURNEY", "Technical Skills", "AWS"])
    assert sections.found == {"experience": 1, "skills": 4}
    assert sections.nonstandard == ["MY JOURNEY"]  # "AWS" is too short to be a heading


# ---------- checks ----------

def statuses(ctx) -> dict[str, str]:
    return {check.id: check.status for check in c.run_checks(ctx)}


def test_sample_resume_passes_the_important_checks():
    result = statuses(ctx_for())
    for check_id in ("garbled", "contact_email", "contact_phone", "profile_links", "headings", "dates", "columns"):
        assert result[check_id] == "pass", check_id
    assert result["word_count"] == "warn"  # the sample is deliberately short


def test_scanned_file_stops_after_first_check():
    result = c.run_checks(ctx_for(text="   "))
    assert [(r.id, r.status) for r in result] == [("text_extractable", "fail")]


@pytest.mark.parametrize(("check", "ctx", "expected"), [
    (c.garbled, ctx_for(text=SAMPLE_RESUME + " (cid:12)" * 8), "fail"),
    (c.icon_glyphs, ctx_for(text=SAMPLE_RESUME + " "), "warn"),
    (c.columns, ctx_for(columns=2), "warn"),
    (c.contact_email, ctx_for(text=SAMPLE_RESUME.replace("asha.verma@example.com", "")), "fail"),
    (c.headings, ctx_for(text=SAMPLE_RESUME.replace("SKILLS", "Stuff I know")), "warn"),
    (c.length, ctx_for(page_count=3), "warn"),
    (c.length, ctx_for(page_count=2), "info"),
    (c.images_and_tables, ctx_for(image_count=1), "warn"),
    (c.images_and_tables, ctx_for(table_count=1), "info"),
    (c.filename, ctx_for(filename="resume_final_v3.pdf"), "info"),
    (c.hyperlink_only, ctx_for(links=["https://github.com/ashaverma/placement-tracker"]), "info"),
    (c.hyperlink_only, ctx_for(links=["https://github.com/ashaverma"]), "pass"),  # visible in text
    (c.header_footer_contact, ctx_for(header_footer_text=["asha.verma@example.com"]), "warn"),
])
def test_individual_checks(check, ctx, expected):
    assert check(ctx).status == expected


def test_every_non_pass_check_explains_the_fix():
    ctx = ctx_for(columns=2, page_count=3, image_count=2, filename="final.pdf")
    for check in c.run_checks(ctx):
        if check.status in ("warn", "fail"):
            assert check.fix, check.id
