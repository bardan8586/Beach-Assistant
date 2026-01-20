/**
 * FrameResult - Unified Schema for AI → Backend → Frontend
 * 
 * This is the SINGLE SOURCE OF TRUTH for all frame processing data.
 * Must match backend/app/models/frame_result.py exactly.
 * 
 * Why this exists:
 * - Frontend needs video dimensions to correctly scale bounding boxes
 * - Frontend needs timestamps to sync with video playback
 * - Frontend needs consistent data structure for rendering
 */

/**
 * Bounding box in absolute video pixel coordinates (x, y, w, h)
 */
export interface BoundingBox {
  /** Left edge X coordinate (pixels) */
  x: number;
  /** Top edge Y coordinate (pixels) */
  y: number;
  /** Width (pixels) */
  w: number;
  /** Height (pixels) */
  h: number;
}

/**
 * Data for a single tracked swimmer
 */
export interface SwimmerData {
  /** Unique tracking ID */
  track_id: number;
  /** Bounding box in video coordinates */
  bbox: BoundingBox;
  /** Detection confidence (0-1) */
  confidence: number;
  /** Risk score (0-100) */
  risk_score: number;
  /** Risk level: LOW, MEDIUM, HIGH, CRITICAL */
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  /** Behavior pattern: NORMAL, STATIONARY, ERRATIC, RAPID */
  behavior: 'NORMAL' | 'STATIONARY' | 'ERRATIC' | 'RAPID';
  /** Water zone: SAFE, CAUTION, DANGER */
  zone: 'SAFE' | 'CAUTION' | 'DANGER';
  /** Time in water (seconds) */
  time_in_water?: number;
  /** Estimated distance from shore (meters) */
  distance_from_shore?: number | null;
  /** Current velocity (pixels/second) */
  velocity?: number;
}

/**
 * Scene analysis data (shore, horizon, water conditions)
 */
export interface SceneData {
  /** Shore line Y coordinate (pixels) */
  shore_line_y: number | null;
  /** Horizon Y coordinate (pixels) */
  horizon_y: number | null;
  /** Percentage of frame that is water (0-100) */
  water_percentage?: number;
  /** Water visibility score (0-1) */
  visibility?: number;
  /** Wave activity score (0-1) */
  wave_activity?: number;
  /** Water calm score (0-1) */
  calm_score?: number;
}

/**
 * Processing performance metrics for system health monitoring
 */
export interface ProcessingMetrics {
  /** Current processing FPS */
  fps?: number;
  /** Processing latency (milliseconds) */
  latency_ms?: number;
  /** Raw detections before filtering */
  detections_raw?: number;
  /** Detections after filtering */
  detections_filtered?: number;
  /** Currently active tracks */
  active_tracks?: number;
}

/**
 * Complete result for a single processed video frame.
 * 
 * This is the MASTER SCHEMA used everywhere:
 * - AI pipeline sends this via POST to backend
 * - Backend stores this for playback
 * - Backend broadcasts this via WebSocket
 * - Frontend renders using this exact structure
 * 
 * CRITICAL FIELDS for rendering:
 * - video_width, video_height: Frontend MUST have these to scale boxes correctly
 * - frame_index: For seeking/syncing
 * - timestamp_ms: For precise video sync
 * - swimmers[].bbox: In absolute video pixel coordinates
 */
export interface FrameResult {
  // Video identification
  /** Unique video/upload ID */
  video_id: string;
  /** Camera ID (e.g., 'cam_001') */
  camera_id: string;
  
  // Frame identification & timing
  /** Frame number (0-based) */
  frame_index: number;
  /** Video timestamp in milliseconds */
  timestamp_ms: number;
  
  // Video dimensions (CRITICAL for coordinate scaling)
  /** Video frame width (pixels) */
  video_width: number;
  /** Video frame height (pixels) */
  video_height: number;
  
  // Data
  /** Detected swimmers */
  swimmers: SwimmerData[];
  /** Scene analysis data */
  scene?: SceneData;
  /** Processing metrics */
  metrics?: ProcessingMetrics;
  
  // Metadata
  /** When this frame was processed (ISO 8601) */
  processed_at?: string;
  /** System mode: playback or live */
  system_mode?: 'playback' | 'live';
}

/**
 * Helper function to convert legacy swimmer data to FrameResult format
 * For backward compatibility during migration
 */
export function legacyToFrameResult(legacyData: any): FrameResult {
  const videoWidth = legacyData.video_width || 1280;
  const videoHeight = legacyData.video_height || 720;
  
  const swimmers: SwimmerData[] = (legacyData.swimmers || []).map((s: any) => ({
    track_id: s.id || 0,
    bbox: {
      x: s.bbox?.x || 0,
      y: s.bbox?.y || 0,
      w: s.bbox?.w || 0,
      h: s.bbox?.h || 0,
    },
    confidence: s.confidence || 0.0,
    risk_score: s.risk_score || 0,
    risk_level: s.risk_level || 'LOW',
    behavior: s.behavior || 'NORMAL',
    zone: s.zone || 'SAFE',
    time_in_water: s.time_in_water || 0.0,
    distance_from_shore: s.distance_from_shore,
    velocity: s.velocity || 0.0,
  }));
  
  return {
    video_id: legacyData.video_id || 'unknown',
    camera_id: legacyData.camera_id || 'cam_001',
    frame_index: legacyData.frame_index || 0,
    timestamp_ms: legacyData.timestamp_ms || 0,
    video_width: videoWidth,
    video_height: videoHeight,
    swimmers,
    scene: legacyData.scene,
    metrics: legacyData.metrics,
    system_mode: legacyData.system_mode || 'playback',
  };
}

/**
 * Convert FrameResult to legacy Swimmer format for backward compatibility
 */
export function frameResultToLegacySwimmers(frameResult: FrameResult) {
  return frameResult.swimmers.map(s => ({
    id: s.track_id.toString(),
    camera_id: frameResult.camera_id,
    position: {
      x: s.bbox.x + s.bbox.w / 2, // Center X
      y: s.bbox.y + s.bbox.h / 2, // Center Y
    },
    bbox: s.bbox,
    risk_level: s.risk_level,
    status: 'active',
    last_seen: frameResult.processed_at || new Date().toISOString(),
    confidence: s.confidence,
  }));
}
