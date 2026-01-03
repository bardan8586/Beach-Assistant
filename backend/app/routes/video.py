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
import logging
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video", tags=["video"])

# Create uploads directory
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Store active processing jobs
processing_jobs = {}


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
        file_extension = Path(file.filename).suffix or ".mp4"
        video_filename = f"{video_id}{file_extension}"
        video_path = UPLOAD_DIR / video_filename
        
        # Save uploaded file
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Video uploaded: {video_id} ({file.filename})")
        
        return {
            "success": True,
            "video_id": video_id,
            "filename": file.filename,
            "video_path": str(video_path),
            "size": os.path.getsize(video_path)
        }
        
    except Exception as e:
        logger.error(f"Error uploading video: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/process/{video_id}")
async def process_video(video_id: str, camera_id: Optional[str] = None):
    """
    Trigger AI processing on uploaded video
    
    This starts the AI pipeline in the background to process the video
    and send tracking data to the backend in real-time.
    """
    try:
        # Find video file
        video_files = list(UPLOAD_DIR.glob(f"{video_id}.*"))
        if not video_files:
            raise HTTPException(status_code=404, detail="Video not found")
        
        video_path = video_files[0]
        
        # Use provided camera_id or generate one
        if not camera_id:
            camera_id = f"upload_{video_id[:8]}"
        
        # Check if already processing
        if video_id in processing_jobs:
            return {
                "success": True,
                "message": "Video is already being processed",
                "video_id": video_id,
                "camera_id": camera_id,
                "status": "processing"
            }
        
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
        env["BACKEND_URL"] = os.getenv("BACKEND_URL", "http://localhost:8000")
        env["CAMERA_ID"] = camera_id
        env["SEND_TO_BACKEND"] = "true"
        env["SHOW_WINDOW"] = "false"  # Disable OpenCV window for web mode
        
        # Use python3 or python (try python3 first)
        python_cmd = "python3" if shutil.which("python3") else "python"
        
        # Start processing (non-blocking)
        # Change to ai directory so imports work correctly
        process = subprocess.Popen(
            [python_cmd, str(ai_script_path), str(video_path)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(project_root / "ai")  # Run from ai directory
        )
        
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

