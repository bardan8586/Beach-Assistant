/**
 * Application Store
 * =================
 * Zustand state management for global app state
 */

import { create } from 'zustand'
import type { Swimmer } from '../types/swimmer'
import type { Alert } from '../types/alert'
import type { Camera } from '../types/camera'

interface AppState {
  // Camera
  selectedCamera: string
  cameras: Camera[]
  setSelectedCamera: (cameraId: string) => void
  setCameras: (cameras: Camera[]) => void

  // Swimmers
  swimmers: Swimmer[]
  setSwimmers: (swimmers: Swimmer[]) => void
  updateSwimmers: (swimmers: Swimmer[]) => void

  // Alerts
  alerts: Alert[]
  setAlerts: (alerts: Alert[]) => void
  addAlert: (alert: Alert) => void
  acknowledgeAlert: (alertId: string) => void

  // UI State
  showBoundingBoxes: boolean
  showHeatmap: boolean
  toggleBoundingBoxes: () => void
  toggleHeatmap: () => void

  // Connection Status
  isConnected: boolean
  setIsConnected: (connected: boolean) => void
}

export const useAppStore = create<AppState>((set) => ({
  // Initial state
  selectedCamera: 'cam_001',
  cameras: [],
  swimmers: [],
  alerts: [],
  showBoundingBoxes: true,
  showHeatmap: false,
  isConnected: false,

  // Camera actions
  setSelectedCamera: (cameraId) => set({ selectedCamera: cameraId }),
  setCameras: (cameras) => set({ cameras }),

  // Swimmer actions
  setSwimmers: (swimmers) => set({ swimmers }),
  updateSwimmers: (newSwimmers) =>
    set((state) => ({
      swimmers: mergeSwimmers(state.swimmers, newSwimmers),
    })),

  // Alert actions
  setAlerts: (alerts) => set({ alerts }),
  addAlert: (alert) =>
    set((state) => ({
      alerts: [alert, ...state.alerts],
    })),
  acknowledgeAlert: (alertId) =>
    set((state) => ({
      alerts: state.alerts.map((a) =>
        a.alert_id === alertId
          ? { ...a, status: 'acknowledged' as const, acknowledged_at: new Date().toISOString() }
          : a
      ),
    })),

  // UI actions
  toggleBoundingBoxes: () =>
    set((state) => ({ showBoundingBoxes: !state.showBoundingBoxes })),
  toggleHeatmap: () =>
    set((state) => ({ showHeatmap: !state.showHeatmap })),

  // Connection actions
  setIsConnected: (isConnected) => set({ isConnected }),
}))

/**
 * Merge swimmers by track_id, keeping most recent data
 */
function mergeSwimmers(existing: Swimmer[], incoming: Swimmer[]): Swimmer[] {
  const merged = new Map<number, Swimmer>()

  // Add existing swimmers
  existing.forEach((s) => merged.set(s.track_id, s))

  // Update with incoming swimmers (overwrite)
  incoming.forEach((s) => merged.set(s.track_id, s))

  return Array.from(merged.values())
}


