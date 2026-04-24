"""
Video Upload & Processing API
=============================
Handle video uploads and trigger AI processing
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
import shutil
from pathlib import Path
import uuid
import subprocess
import threading
import logging
import cv2
import json
from typing import Optional
from app.utils import results_storage
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video", tags=["video"])

# Create uploads directory
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Store active processing jobs
processing_jobs = {}

def _run_ai_preflight(python_cmd: str) -> dict:
    """
    Validate the AI Python environment before spawning the long-running pipeline.

    Why: avoids "started processing" but no frames due to missing deps (cv2/torch/ultralytics).
    Returns a JSON-serializable dict with import results.
    """
    probe_code = r"""
import json, sys, importlib, platform
mods = ["cv2", "torch", "ultralytics"]
out = {
  "executable": sys.executable,
  "version": sys.version,
  "platform": platform.platform(),
  "imports": {}
}
for m in mods:
  try:
    mod = importlib.import_module(m)
    out["imports"][m] = {"ok": True, "version": getattr(mod, "__version__", None)}
  except Exception as e:
    out["imports"][m] = {"ok": False, "error": str(e)}
print(json.dumps(out))
"""
    completed = subprocess.run(
        [python_cmd, "-c", probe_code],
        capture_output=True,
        text=True,
        timeout=20,
    )
    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    try:
        data = json.loads(stdout) if stdout else {"error": "no_stdout", "stderr": stderr}
    except Exception:
        data = {"error": "invalid_json", "stdout": stdout[:500], "stderr": stderr[:500]}
    data["_returncode"] = completed.returncode
    if stderr:
        data["_stderr_preview"] = stderr[:500]
    return data


@router.get("/limits")
async def upload_limits():
    """Max video upload size (frontend should match for UX before upload)."""
    mb = max(1, settings.MAX_UPLOAD_VIDEO_BYTES // (1024 * 1024))
    return {
        "max_upload_bytes": settings.MAX_UPLOAD_VIDEO_BYTES,
        "max_upload_mb": mb,
    }


@router.get("/preflight")
async def ai_preflight():
    """Return AI environment health (imports + versions) for the configured AI python."""
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    ai_venv_python = project_root / "ai" / "venv" / "bin" / "python"
    python_cmd = str(ai_venv_python) if ai_venv_python.exists() else ("python3" if shutil.which("python3") else "python")
    return {"python_cmd": python_cmd, "preflight": _run_ai_preflight(python_cmd)}


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file for AI processing
    
    Returns:
        - video_id: Unique identifier for the uploaded video
        - video_path: Path where video is stored
    """
    try:
        # Generate unique video ID
        video_id = str(uuid.uuid4())

        max_bytes = settings.MAX_UPLOAD_VIDEO_BYTES
        cl = file.headers.get("content-length")
        if cl:
            try:
                if int(cl) > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail={
                            "error": "file_too_large",
                            "max_bytes": max_bytes,
                            "max_mb": max(1, max_bytes // (1024 * 1024)),
                        },
                    )
            except ValueError:
                pass

        # Create video directory structure (Task 1.2)
        video_dir = results_storage.create_video_directory(video_id)

        # Save video file in the video directory
        file_extension = Path(file.filename).suffix or ".mp4"
        video_filename = f"video{file_extension}"
        video_path = video_dir / video_filename

        chunk_size = 1024 * 1024
        written = 0
        with open(video_path, "wb") as buffer:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    try:
                        buffer.close()
                    except Exception:
                        pass
                    try:
                        video_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                    raise HTTPException(
                        status_code=413,
                        detail={
                            "error": "file_too_large",
                            "max_bytes": max_bytes,
                            "max_mb": max(1, max_bytes // (1024 * 1024)),
                        },
                    )
                buffer.write(chunk)
        
        # Extract video metadata
        width = height = 0
        fps = 0.0
        frame_count = 0
        duration = 0.0
        try:
            cap = cv2.VideoCapture(str(video_path))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            cap.release()
            
            # Save metadata (Task 1.2)
            results_storage.save_metadata(video_id, {
                "filename": file.filename,
                "width": width,
                "height": height,
                "fps": fps,
                "frame_count": frame_count,
                "duration_seconds": duration,
                "size_bytes": os.path.getsize(video_path)
            })
        except Exception as e:
            logger.warning(f"Failed to extract video metadata: {e}")
        
        logger.info(f"Video uploaded: {video_id} ({file.filename}) - {width}x{height}, {duration:.1f}s")
        
        return {
            "success": True,
            "video_id": video_id,
            "filename": file.filename,
            "video_path": str(video_path),
            "size": os.path.getsize(video_path),
            "dimensions": {"width": width, "height": height},
            "duration": duration
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading video: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/process/{video_id}")
async def process_video(video_id: str, camera_id: Optional[str] = None, show_window: bool = False):
    """
    Trigger AI processing on uploaded video
    
    This starts the AI pipeline in the background to process the video
    and send tracking data to the backend in real-time.
    """
    try:
        # Find video file in video directory (Task 1.2)
        video_dir = results_storage.get_video_dir(video_id)
        if not video_dir.exists():
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Look for video file
        video_files = list(video_dir.glob("video.*"))
        if not video_files:
            raise HTTPException(status_code=404, detail="Video file not found in directory")
        
        # Resolve to absolute path so AI subprocess (cwd=ai/) can find the file
        video_path = video_files[0].resolve()
        
        # Use provided camera_id or generate one
        if not camera_id:
            camera_id = f"upload_{video_id[:8]}"
        
        # Only block if this video has an *active* subprocess; allow re-runs after completion
        if video_id in processing_jobs:
            existing = processing_jobs[video_id].get("process")
            if existing is not None and existing.poll() is None:
                return {
                    "success": True,
                    "message": "Video is already being processed",
                    "video_id": video_id,
                    "camera_id": camera_id,
                    "status": "processing",
                }
            del processing_jobs[video_id]
        
        # Start AI pipeline in background
        # Get the project root (4 levels up from backend/app/routes/video.py)
        project_root = Path(__file__).parent.parent.parent.parent
        ai_script_path = project_root / "ai" / "main.py"
        
        if not ai_script_path.exists():
            raise HTTPException(
                status_code=500, 
                detail=f"AI pipeline script not found at {ai_script_path}"
            )
        
        # Set environment variables for AI pipeline
        env = os.environ.copy()
        # Ingest must hit THIS API instance (same port as uvicorn). Default localhost:8000 breaks when PORT≠8000
        # or when another service (e.g. Docker/nginx) occupies 8000.
        ingest_base = (env.get("BACKEND_URL") or "").strip() or (settings.BACKEND_URL or "").strip()
        if not ingest_base:
            ingest_base = f"http://127.0.0.1:{settings.PORT}"
        env["BACKEND_URL"] = ingest_base
        env["CAMERA_ID"] = camera_id
        env["VIDEO_ID"] = video_id  # So ingest stores under this video_id for playback
        env["SEND_TO_BACKEND"] = "true"
        # If enabled, the AI subprocess will open a local OpenCV window (cv2.imshow).
        # Note: this only appears on the machine running the backend/AI with a GUI session.
        env["SHOW_WINDOW"] = "true" if show_window else "false"
        
        # Use AI venv Python if it exists (has torch/ultralytics); else system python3
        ai_venv_python = project_root / "ai" / "venv" / "bin" / "python"
        if ai_venv_python.exists():
            python_cmd = str(ai_venv_python)
            logger.info(f"Using AI venv Python: {python_cmd}")
        else:
            python_cmd = "python3" if shutil.which("python3") else "python"
            logger.warning(
                "AI venv not found at ai/venv. Install AI deps: cd ai && python3 -m venv venv && pip install -r requirements.txt"
            )

        # Preflight AI environment so we fail fast with a helpful message.
        try:
            preflight = _run_ai_preflight(python_cmd)
            imports = preflight.get("imports") or {}
            missing = [m for m, v in imports.items() if isinstance(v, dict) and not v.get("ok")]
            if missing:
                logger.error("AI preflight failed. Missing/failed imports: %s. Details: %s", missing, preflight)
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "ai_preflight_failed",
                        "missing": missing,
                        "preflight": preflight,
                        "fix": f'Run: "{python_cmd}" -m pip install -r "{project_root / "ai" / "requirements.txt"}"',
                    },
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("AI preflight crashed: %s", e)
            raise HTTPException(status_code=500, detail={"error": "ai_preflight_crashed", "message": str(e)})
        
        # Start processing (non-blocking)
        # Change to ai directory so imports work correctly
        process = subprocess.Popen(
            [python_cmd, str(ai_script_path), str(video_path)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(project_root / "ai")  # Run from ai directory
        )

        def log_ai_stderr():
            """Read AI subprocess stderr and log so we see crashes/errors in backend terminal."""
            try:
                for line in iter(process.stderr.readline, b""):
                    if line:
                        logger.info("[AI] %s", line.decode("utf-8", errors="replace").rstrip())
            except Exception as e:
                logger.debug("AI stderr reader stopped: %s", e)

        t = threading.Thread(target=log_ai_stderr, daemon=True)
        t.start()

        processing_jobs[video_id] = {
            "process": process,
            "camera_id": camera_id,
            "video_path": str(video_path),
            "status": "processing"
        }
        
        logger.info(f"Started AI processing: {video_id} -> {camera_id}")
        
        return {
            "success": True,
            "message": "AI processing started",
            "video_id": video_id,
            "camera_id": camera_id,
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Error starting video processing: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/status/{video_id}")
async def get_processing_status(video_id: str):
    """Get processing status for a video"""
    if video_id not in processing_jobs:
        return {
            "video_id": video_id,
            "status": "not_found"
        }
    
    job = processing_jobs[video_id]
    process = job["process"]
    
    # Check if process is still running
    if process.poll() is None:
        return {
            "video_id": video_id,
            "status": "processing",
            "camera_id": job["camera_id"]
        }
    else:
        # Process finished
        return {
            "video_id": video_id,
            "status": "completed",
            "camera_id": job["camera_id"],
            "return_code": process.returncode
        }


@router.get("/{video_id}/metadata")
async def get_video_metadata(video_id: str):
    """
    Get video metadata (dimensions, duration, etc.)
    
    Returns metadata saved during upload, including:
    - filename: Original filename
    - width, height: Video dimensions
    - fps: Frames per second
    - duration_seconds: Total duration
    - frame_count: Total number of frames
    """
    try:
        metadata = results_storage.load_metadata(video_id)
        
        if metadata is None:
            raise HTTPException(status_code=404, detail="Video metadata not found")
        
        return {
            "success": True,
            "video_id": video_id,
            "metadata": metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load metadata: {str(e)}")


@router.get("/{video_id}/results")
async def get_video_results(
    video_id: str,
    from_ms: Optional[int] = None,
    to_ms: Optional[int] = None
):
    """
    Get processed FrameResults for a video (Task 1.3)
    
    This endpoint returns pre-computed AI results for playback without re-processing.
    
    Query Parameters:
        from_ms: Start timestamp in milliseconds (inclusive)
        to_ms: End timestamp in milliseconds (inclusive)
        
    Returns:
        - video_id: Video identifier
        - frame_count: Number of frames in response
        - results: Array of FrameResult objects
        
    Why lifeguards need this:
        - Instant replay of incidents without waiting for AI
        - Scrub through video and see matching detections
        - Review training scenarios
    """
    try:
        # Check if video has results
        if not results_storage.has_results(video_id):
            raise HTTPException(
                status_code=404, 
                detail="No results found for this video. Has it been processed?"
            )
        
        # Read results (with optional time range)
        if from_ms is not None or to_ms is not None:
            results = results_storage.read_results_range(video_id, from_ms, to_ms)
            logger.info(f"Returning {len(results)} results for range [{from_ms}, {to_ms}]")
        else:
            results = results_storage.read_all_results(video_id)
            logger.info(f"Returning all {len(results)} results")
        
        return {
            "success": True,
            "video_id": video_id,
            "frame_count": len(results),
            "from_ms": from_ms,
            "to_ms": to_ms,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load results: {str(e)}")


@router.get("/list")
async def list_uploaded_videos():
    """List all uploaded videos"""
    videos = []
    for video_file in UPLOAD_DIR.glob("*"):
        if video_file.is_file():
            videos.append({
                "filename": video_file.name,
                "size": os.path.getsize(video_file),
                "path": str(video_file)
            })
    return {"videos": videos}

