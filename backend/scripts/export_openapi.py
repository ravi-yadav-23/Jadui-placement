"""Write the v2 API's OpenAPI schema to frontend/openapi.json.

The frontend turns it into TypeScript types (`npm run gen:api`), so if a backend response
shape changes, the frontend type check fails instead of the UI silently breaking.

    python scripts/export_openapi.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI  # noqa: E402

from app.resume.api import router  # noqa: E402

app = FastAPI(title="Jadui Placement API v2")
app.include_router(router, prefix="/api/v2")

target = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"
target.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
print(f"wrote {target}")
