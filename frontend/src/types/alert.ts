/**
 * Alert Types
 * ============
 * TypeScript interfaces for safety alerts
 */

export type AlertType = 'stationary' | 'erratic' | 'zone_violation' | 'drowning';
export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';
export type AlertStatus = 'active' | 'acknowledged' | 'resolved' | 'false_positive';

export interface Alert {
  alert_id: string;
  camera_id: string;
  track_id: number;
  alert_type: AlertType;
  severity: AlertSeverity;
  risk_score: number;
  timestamp: string;
  status: AlertStatus;
  snapshot_url?: string;
  acknowledged_by?: string;
  acknowledged_at?: string;
  resolved_at?: string;
  notes?: string;
}

