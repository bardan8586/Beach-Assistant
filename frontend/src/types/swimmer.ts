/**
 * Swimmer Tracking Types
 * =======================
 * TypeScript interfaces for swimmer data from backend / WebSocket
 */

export interface BoundingBox {
  x1?: number;
  y1?: number;
  x2?: number;
  y2?: number;
  x?: number;
  y?: number;
  w?: number;
  h?: number;
}

export interface Swimmer {
  track_id: number;
  camera_id: string;
  bbox: BoundingBox;
  confidence: number;
  first_seen: string;
  last_seen: string;
  status: 'active' | 'inactive' | 'alerted';
  /** Risk score 0–100 from AI */
  risk_score?: number;
  risk_level?: string;
  behavior?: string;
  zone?: string;
  time_in_water?: number;
  velocity?: number;
}


