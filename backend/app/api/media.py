"""Media upload — accepts image/video files, stores on server, returns a URL."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User

router = APIRouter(prefix="/media", tags=["media"])

# Shared with app/main.py, which mounts this same directory as /uploads.
UPLOAD_DIR = Path(settings.upload_dir)
MAX_BYTES = 50 * 1024 * 1024  # 50 MB
CHUNK_SIZE = 1_000_000  # 1 MB

# Extension is derived ONLY from this validated content-type map — never from
# the client-supplied filename. Otherwise an attacker can send
# Content-Type: image/png with filename "x.svg": it passes this allow-list,
# gets saved as "<uuid>.svg", and since /uploads is served via StaticFiles on
# the SPA's own origin, Starlette serves it as image/svg+xml — browsers
# execute any embedded <script>, which is a stored-XSS / JWT-theft path.
ALLOWED = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    current: User = Depends(get_current_user),
) -> dict:
    ext = ALLOWED.get(file.content_type or "")
    if ext is None:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            f"Unsupported file type: {file.content_type}")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / filename

    # Stream to disk in fixed-size chunks so a huge/slow upload never gets
    # fully buffered in memory before the size check runs.
    total = 0
    too_large = False
    try:
        with dest.open("wb") as out:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_BYTES:
                    too_large = True
                    break
                out.write(chunk)
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    if too_large:
        dest.unlink(missing_ok=True)
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large (max 50 MB)")

    base = (settings.app_base_url or "").rstrip("/")
    return {"ok": True, "url": f"{base}/uploads/{filename}"}
