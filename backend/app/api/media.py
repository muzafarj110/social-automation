"""Media upload — accepts image/video files, stores on server, returns a URL."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User

router = APIRouter(prefix="/media", tags=["media"])

UPLOAD_DIR = Path("/app/uploads")
MAX_BYTES = 50 * 1024 * 1024  # 50 MB

ALLOWED = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "video/mp4", "video/quicktime", "video/webm",
}


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    current: User = Depends(get_current_user),
) -> dict:
    if file.content_type not in ALLOWED:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            f"Unsupported file type: {file.content_type}")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large (max 50 MB)")
    ext = Path(file.filename or "upload").suffix.lower() or ".bin"
    filename = f"{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / filename).write_bytes(content)
    base = (settings.app_base_url or "").rstrip("/")
    return {"ok": True, "url": f"{base}/uploads/{filename}"}
