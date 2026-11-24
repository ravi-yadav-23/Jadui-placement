from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Supabase ---
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    # Only needed if your Supabase project still signs JWTs with the legacy shared secret (HS256).
    # Projects using asymmetric signing keys are verified through the public JWKS endpoint instead.
    SUPABASE_JWT_SECRET: str = ""

    # "memory" keeps everything in RAM: for local development and the E2E test run only.
    DATABASE_BACKEND: Literal["supabase", "memory"] = "supabase"

    # --- LLM (resume v2) ---
    # "fake" returns canned JSON; used by tests and the Playwright E2E run.
    LLM_PROVIDER: Literal["gemini", "fake"] = "gemini"
    # Model names change often: check https://ai.google.dev/gemini-api/docs/deprecations and set in .env.
    # (gemini-2.0-flash was shut down on 2026-06-01.)
    LLM_PRIMARY_MODEL: str = "gemini-3.8-flash"
    LLM_FALLBACK_MODEL: str = "openai/gpt-oss-120b"  # Groq, strict structured outputs
    LLM_TIMEOUT_SECONDS: float = 45.0

    # --- Resume v2 limits ---
    RESUME_MAX_BYTES: int = 5 * 1024 * 1024
    RESUME_MAX_PAGES: int = 3
    DAILY_UPLOAD_LIMIT: int = 10
    DAILY_ANALYSIS_LIMIT: int = 15
    RESUME_STORAGE_BUCKET: str = "resumes"

    # --- Legacy AI settings (old modules, removed at the switchover) ---
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OPENAI_API_KEY: str | None = None
    MENTOR_TEMPERATURE: float = 0.88
    MENTOR_MAX_OUTPUT_TOKENS: int = 2048

    # --- App ---
    PORT: int = 8000
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "https://jadui-placement.vercel.app"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
