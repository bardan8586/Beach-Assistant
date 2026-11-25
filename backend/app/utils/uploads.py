"""Video upload checks shared by the API and tests."""

from __future__ import annotations

from pathlib import Path

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}

_GENERIC_CONTENT_TYPES = {
    "",
    "application/octet-stream",
    "binary/octet-stream",
    "application/binary",
}


def video_upload_error(filename: str | None, content_type: str | None = None) -> str | None:
    """Return a user-facing error, or None when the upload looks like a video.

    Browsers sometimes send ``application/octet-stream`` for valid clips, so
    extension is the required check and content type only rejects obvious
    non-video types such as ``text/plain``.
    """
    if filename is None or not str(filename).strip():
        return "A video filename is required."
    safe_name = Path(str(filename)).name
    if safe_name in {"", ".", ".."}:
        return "A video filename is required."
    extension = Path(safe_name).suffix.lower()
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        shown = extension or "unknown"
        return (
            f"Unsupported video type '{shown}'. "
            "Use MP4, MOV, AVI, MKV, WebM, or M4V."
        )
    if content_type:
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type not in _GENERIC_CONTENT_TYPES and not media_type.startswith("video/"):
            return f"Unsupported content type '{media_type}'."
    return None


def safe_video_suffix(filename: str) -> str:
    """Suffix to store on disk. Caller must have validated the name."""
    return Path(filename).suffix.lower() or ".mp4"
