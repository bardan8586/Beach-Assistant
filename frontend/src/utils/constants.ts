/**
 * Application Constants
 * ======================
 * Configuration and constant values
 */

// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const API_PREFIX = '/api';
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

// Colors for bounding boxes (rotating colors for different track IDs)
export const TRACK_COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // yellow
  '#ef4444', // red
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#14b8a6', // teal
  '#f97316', // orange
];

// Alert severity colors
export const SEVERITY_COLORS = {
  low: '#10b981',      // green
  medium: '#f59e0b',   // yellow
  high: '#f97316',     // orange
  critical: '#ef4444',  // red
};

// Refresh intervals (ms)
export const REFRESH_INTERVAL = 5000;  // 5 seconds
export const WS_RECONNECT_INTERVAL = 3000;  // 3 seconds

