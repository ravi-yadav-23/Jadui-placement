"""Backend application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.coach.api import router as coach_v2_router
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.dashboard.api import router as dashboard_v2_router
from app.interview.api import router as interview_v2_router
from app.planner.api import router as planner_v2_router
from app.resume.api import router as resume_v2_router

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
app.include_router(interview_v2_router, prefix="/api/v2")
app.include_router(planner_v2_router, prefix="/api/v2")
app.include_router(dashboard_v2_router, prefix="/api/v2")
app.include_router(coach_v2_router, prefix="/api/v2")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
