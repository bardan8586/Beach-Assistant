/**
 * Swimmer Tracking Types
 * =======================
 * TypeScript interfaces for swimmer data from backend
 */

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface Swimmer {
  track_id: number;
  camera_id: string;
  bbox: BoundingBox;
  confidence: number;
  first_seen: string;  // ISO timestamp
  last_seen: string;
  status: 'active' | 'inactive' | 'alerted';
}


