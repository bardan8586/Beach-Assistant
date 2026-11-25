"""Non-blocking ingest and upload validation."""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai"))
sys.path.insert(0, str(ROOT / "backend"))

from ingest_client import AsyncIngestClient  # noqa: E402
from app.utils.uploads import video_upload_error  # noqa: E402
from app.config import parse_allowed_origins  # noqa: E402


class _SlowSession:
    def post(self, *_args, **_kwargs):
        time.sleep(0.3)

        class _Response:
            status_code = 200

        return _Response()


def test_ingest_submit_does_not_wait_for_http():
    client = AsyncIngestClient(
        "http://127.0.0.1:9/api/data/ingest",
        timeout=2.0,
        max_queue=2,
        session_factory=_SlowSession,
    )
    try:
        started = time.perf_counter()
        for index in range(6):
            client.submit({"frame_index": index})
        elapsed = time.perf_counter() - started
    finally:
        client.close()
    assert elapsed < 0.2
    assert client.dropped >= 1


def test_video_upload_rejects_non_video():
    assert video_upload_error(None) is not None
    assert video_upload_error("notes.txt") is not None
    assert video_upload_error("clip.mp4", "text/plain") is not None
    assert video_upload_error("clip.mp4", "video/mp4") is None
    assert video_upload_error("clip.MOV", "application/octet-stream") is None
    assert ".." not in (video_upload_error("../secret.mp4") or "")


def test_origins_accept_comma_separated_env():
    parsed = parse_allowed_origins(
        "https://beach-assistant-preview.vercel.app, http://localhost:5173"
    )
    assert parsed == [
        "https://beach-assistant-preview.vercel.app",
        "http://localhost:5173",
    ]
    assert parse_allowed_origins(["http://localhost:5173"]) == ["http://localhost:5173"]


def test_settings_accept_plain_comma_and_json_origins(monkeypatch):
    """Render crashed when ALLOWED_ORIGINS was a plain URL. All three forms must boot."""
    from app.config import Settings

    monkeypatch.setenv("ALLOWED_ORIGINS", "https://beach-assistant-preview.vercel.app")
    single = Settings(_env_file=None)
    assert single.ALLOWED_ORIGINS == ["https://beach-assistant-preview.vercel.app"]

    monkeypatch.setenv(
        "ALLOWED_ORIGINS",
        "https://beach-assistant-preview.vercel.app, http://localhost:5173",
    )
    comma = Settings(_env_file=None)
    assert comma.ALLOWED_ORIGINS == [
        "https://beach-assistant-preview.vercel.app",
        "http://localhost:5173",
    ]

    monkeypatch.setenv(
        "ALLOWED_ORIGINS",
        '["https://beach-assistant-preview.vercel.app"]',
    )
    as_json = Settings(_env_file=None)
    assert as_json.ALLOWED_ORIGINS == ["https://beach-assistant-preview.vercel.app"]
