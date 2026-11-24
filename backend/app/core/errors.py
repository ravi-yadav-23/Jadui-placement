"""One error shape for the whole v2 API: {"error": {"code": ..., "message": ...}}.

Raise `AppError("not_found", "Resume not found", 404)` anywhere; the handler below turns it
into a JSON response. The frontend only ever has to read `error.code` and `error.message`.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
