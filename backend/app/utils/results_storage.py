"""
Results Storage Utility
=======================
Manages storage and retrieval of processed video results.

Why this exists:
- Store per-frame FrameResults for later playback
- Lifeguards can replay incidents without re-processing
- Training and review without waiting for AI
"""

import json
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ResultsStorage:
    """
    Manages FrameResult storage in JSONL format.
    
    Directory structure:
    backend/uploads/{video_id}/
        video.mp4           (original video)
        results.jsonl       (frame-by-frame results, one JSON per line)
        metadata.json       (video metadata)
    """
    
    def __init__(self, base_dir: str = "uploads"):
        """
        Initialize results storage.
        
        Args:
            base_dir: Base directory for video uploads (default: "uploads")
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def get_video_dir(self, video_id: str) -> Path:
        """Get directory for a specific video"""
        return self.base_dir / video_id
    
    def get_results_file(self, video_id: str) -> Path:
        """Get path to results.jsonl file"""
        return self.get_video_dir(video_id) / "results.jsonl"
    
    def get_metadata_file(self, video_id: str) -> Path:
        """Get path to metadata.json file"""
        return self.get_video_dir(video_id) / "metadata.json"
    
    def create_video_directory(self, video_id: str) -> Path:
        """
        Create directory for video and its results.
        
        Args:
            video_id: Unique video identifier
            
        Returns:
            Path to created directory
        """
        video_dir = self.get_video_dir(video_id)
        video_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created video directory: {video_dir}")
        return video_dir
    
    def write_frame_result(self, video_id: str, frame_result: dict):
        """
        Append a FrameResult to the results file.
        
        Args:
            video_id: Video identifier
            frame_result: FrameResult as dictionary (from frame_result.to_websocket_message())
        """
        results_file = self.get_results_file(video_id)
        
        # Ensure directory exists
        results_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Append as single line JSON
        with open(results_file, 'a') as f:
            json.dump(frame_result, f)
            f.write('\n')
    
    def read_all_results(self, video_id: str) -> List[dict]:
        """
        Read all FrameResults for a video.
        
        Args:
            video_id: Video identifier
            
        Returns:
            List of FrameResult dictionaries
        """
        results_file = self.get_results_file(video_id)
        
        if not results_file.exists():
            logger.warning(f"Results file not found: {results_file}")
            return []
        
        results = []
        with open(results_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    result = json.loads(line)
                    results.append(result)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse line {line_num}: {e}")
        
        logger.info(f"Read {len(results)} frame results from {results_file}")
        return results
    
    def read_results_range(
        self, 
        video_id: str, 
        from_ms: Optional[int] = None, 
        to_ms: Optional[int] = None
    ) -> List[dict]:
        """
        Read FrameResults within a time range.
        
        Args:
            video_id: Video identifier
            from_ms: Start timestamp (milliseconds), inclusive
            to_ms: End timestamp (milliseconds), inclusive
            
        Returns:
            List of FrameResult dictionaries in the specified range
        """
        all_results = self.read_all_results(video_id)
        
        if from_ms is None and to_ms is None:
            return all_results
        
        filtered = []
        for result in all_results:
            timestamp = result.get('timestamp_ms', 0)
            
            if from_ms is not None and timestamp < from_ms:
                continue
            if to_ms is not None and timestamp > to_ms:
                continue
            
            filtered.append(result)
        
        logger.info(
            f"Filtered {len(filtered)}/{len(all_results)} results "
            f"for range [{from_ms}, {to_ms}]"
        )
        return filtered
    
    def get_result_count(self, video_id: str) -> int:
        """
        Get number of stored results for a video.
        
        Args:
            video_id: Video identifier
            
        Returns:
            Number of frame results stored
        """
        results_file = self.get_results_file(video_id)
        
        if not results_file.exists():
            return 0
        
        count = 0
        with open(results_file, 'r') as f:
            for line in f:
                if line.strip():
                    count += 1
        
        return count
    
    def save_metadata(self, video_id: str, metadata: dict):
        """
        Save video metadata.
        
        Args:
            video_id: Video identifier
            metadata: Metadata dictionary (e.g., filename, duration, dimensions)
        """
        metadata_file = self.get_metadata_file(video_id)
        
        # Add timestamps
        metadata['created_at'] = datetime.utcnow().isoformat()
        metadata['video_id'] = video_id
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved metadata for video {video_id}")
    
    def load_metadata(self, video_id: str) -> Optional[dict]:
        """
        Load video metadata.
        
        Args:
            video_id: Video identifier
            
        Returns:
            Metadata dictionary or None if not found
        """
        metadata_file = self.get_metadata_file(video_id)
        
        if not metadata_file.exists():
            logger.warning(f"Metadata file not found: {metadata_file}")
            return None
        
        with open(metadata_file, 'r') as f:
            return json.load(f)
    
    def has_results(self, video_id: str) -> bool:
        """
        Check if video has processed results.
        
        Args:
            video_id: Video identifier
            
        Returns:
            True if results file exists and is not empty
        """
        results_file = self.get_results_file(video_id)
        return results_file.exists() and results_file.stat().st_size > 0
    
    def delete_results(self, video_id: str):
        """
        Delete results for a video (keep video file).
        
        Args:
            video_id: Video identifier
        """
        results_file = self.get_results_file(video_id)
        if results_file.exists():
            results_file.unlink()
            logger.info(f"Deleted results for video {video_id}")
    
    def delete_video_directory(self, video_id: str):
        """
        Delete entire video directory (video + results + metadata).
        
        Args:
            video_id: Video identifier
        """
        import shutil
        video_dir = self.get_video_dir(video_id)
        if video_dir.exists():
            shutil.rmtree(video_dir)
            logger.info(f"Deleted video directory: {video_dir}")


# Global instance
results_storage = ResultsStorage()
