/**
 * Camera Types
 * =============
 * TypeScript interfaces for camera configuration
 */

export type CameraStatus = 'active' | 'inactive' | 'maintenance';

export interface CameraLocation {
  beach: string;
  lat?: number;
  lng?: number;
  description?: string;
}

export interface Camera {
  camera_id: string;
  name: string;
  location: CameraLocation;
  status: CameraStatus;
  created_at: string;
  last_seen?: string;
}


