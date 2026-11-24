"""Step 1 of the pipeline: is this upload a file we accept?

We check the file's *bytes*, not its name or the browser's Content-Type header,
because both of those are chosen by the client and can be wrong or faked.
"""

import hashlib
import io
import zipfile
from typing import Literal

from app.core.config import settings
from app.core.errors import AppError

FileKind = Literal["pdf", "docx"]

MIME_TYPES: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def detect_file_kind(data: bytes) -> FileKind:
    if data.startswith(b"%PDF-"):
        return "pdf"
    # A .docx is a zip archive that contains word/document.xml.
    if data.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if "word/document.xml" in archive.namelist():
                    return "docx"
        except zipfile.BadZipFile:
            pass
    raise AppError("unsupported_type", "Upload a PDF or DOCX file (old .doc files are not supported).", 415)


def validate_upload(data: bytes) -> FileKind:
    if not data:
        raise AppError("empty_file", "The uploaded file is empty.", 400)
    if len(data) > settings.RESUME_MAX_BYTES:
        raise AppError("file_too_large", f"Max file size is {settings.RESUME_MAX_BYTES // (1024 * 1024)} MB.", 413)
    return detect_file_kind(data)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
