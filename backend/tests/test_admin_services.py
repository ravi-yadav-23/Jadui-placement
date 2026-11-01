import pytest
from modules.admin_ai.services import admin_service

def test_rank_students_query_matching(monkeypatch):
    mock_students = [
        {
            "user_id": "std-1",
            "name": "Frontend Dev",
            "target_role": "Frontend Engineer",
            "skills": ["React", "JavaScript", "Tailwind"],
            "avgScore": 85,
        },
        {
            "user_id": "std-2",
            "name": "Backend Dev",
            "target_role": "Backend Engineer",
            "skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
            "avgScore": 80,
        },
    ]
    
    monkeypatch.setattr(admin_service, "get_all_students", lambda: mock_students)
    
    # Query for backend skills
    backend_results = admin_service.rank_students_for_job("python, fastapi")
    assert len(backend_results) == 2
    assert backend_results[0]["user_id"] == "std-2", "Backend candidate should rank first for Python query"
    assert "python" in backend_results[0]["matched_terms"]
    assert "fastapi" in backend_results[0]["matched_terms"]
    
    # Query for frontend skills
    frontend_results = admin_service.rank_students_for_job("react")
    assert frontend_results[0]["user_id"] == "std-1", "Frontend candidate should rank first for React query"
    assert "react" in frontend_results[0]["matched_terms"]

