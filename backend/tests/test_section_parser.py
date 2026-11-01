import pytest
from modules.resume_ai.section_parser import section_parser

def test_extract_skills_no_false_positives():
    text = "Engineered digital signal algorithms and advanced machine learning models."
    skills = section_parser.extract_skills(text)
    # Ensure substring collisions are prevented
    assert "git" not in skills, "Should not match 'git' inside 'digital'"
    assert "machine learning" in skills, "Should match 'machine learning'"

def test_extract_skills_valid_matches():
    text = "Full stack engineer with Python, React, Next.js, Docker, and PostgreSQL experience."
    skills = section_parser.extract_skills(text)
    assert "python" in skills
    assert "react" in skills
    assert "next.js" in skills
    assert "docker" in skills
    assert "postgresql" in skills

def test_extract_sections_basic():
    resume_text = """
    John Doe
    Summary:
    Experienced software engineer with 5 years of background.
    
    Technical Skills:
    Python, FastAPI, React, Docker
    
    Experience:
    Built distributed microservices.
    """
    sections = section_parser.extract_all_sections(resume_text)
    assert "technical_skills" in sections
    assert "FastAPI" in sections["technical_skills"] or "Python" in sections["technical_skills"]

