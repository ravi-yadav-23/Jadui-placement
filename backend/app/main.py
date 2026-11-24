"""Backend application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import register_error_handlers
from app.resume.api import router as resume_v2_router
from modules.admin_ai.routes import router as admin_router
from modules.github_profile.routes import router as github_profile_router
from modules.github_review.routes import router as github_review_router
from modules.interview_ai.routes import router as interview_router
from modules.mentor_ai.routes import router as mentor_router
from modules.resume_ai.routes import router as resume_router
from modules.system_ai.routes import router as system_router

app = FastAPI(title="Jadui Placement API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
register_error_handlers(app)

# v2 (rebuilt) features
app.include_router(resume_v2_router, prefix="/api/v2")

# Legacy modules: removed as each pillar is rebuilt.
app.include_router(admin_router, prefix="/api")
app.include_router(github_profile_router, prefix="/api")
app.include_router(github_review_router, prefix="/api")
app.include_router(interview_router, prefix="/api")
app.include_router(mentor_router, prefix="/api")
app.include_router(resume_router, prefix="/api")
app.include_router(system_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
