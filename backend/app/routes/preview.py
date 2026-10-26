"""Local demo JPEG preview transport.

Single-process, in-memory only; no authentication, persistence, or multi-worker sync.
Do not expose this route publicly without access controls.
"""
import asyncio
import time
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/preview", tags=["preview"])
_frames: dict[str, tuple[bytes, float]] = {}
MAX_JPEG_BYTES = 400_000

@router.post("/{camera_id}")
async def publish_frame(camera_id: str, request: Request):
    if not camera_id.isascii() or not camera_id.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "Invalid camera ID")
    if request.headers.get("content-type", "").split(";")[0] != "image/jpeg":
        raise HTTPException(415, "Expected image/jpeg")
    body = await request.body()
    if not body or len(body) > MAX_JPEG_BYTES or not body.startswith(b"\xff\xd8") or not body.endswith(b"\xff\xd9"):
        raise HTTPException(413, "Invalid or oversized JPEG")
    _frames[camera_id] = (body, time.monotonic())
    return {"ok": True}

@router.get("/{camera_id}.mjpg")
async def stream_frames(camera_id: str):
    if not camera_id.isascii() or not camera_id.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "Invalid camera ID")

    async def stream():
        last_seen = -1.0
        while True:
            item = _frames.get(camera_id)
            if item and item[1] != last_seen and time.monotonic() - item[1] < 5:
                jpeg, last_seen = item
                yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " +
                       str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n")
            await asyncio.sleep(0.12)

    return StreamingResponse(stream(), media_type="multipart/x-mixed-replace; boundary=frame",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
