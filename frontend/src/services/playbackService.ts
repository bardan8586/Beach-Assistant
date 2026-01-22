/**
 * Playback Service
 * ================
 * Loads pre-processed FrameResult data for instant replay
 */

import type { FrameResult } from '../types/frameResult'

const API_BASE = 'http://localhost:8000'

export const playbackService = {
  /**
   * Load all processed frame results for a video
   */
  async loadFrameResults(videoId: string, fromMs?: number, toMs?: number): Promise<FrameResult[]> {
    const params = new URLSearchParams()
    if (fromMs !== undefined) params.append('from_ms', fromMs.toString())
    if (toMs !== undefined) params.append('to_ms', toMs.toString())
    
    const url = `${API_BASE}/api/video/${videoId}/results${params.toString() ? '?' + params.toString() : ''}`
    
    console.log(`📥 Loading frame results from: ${url}`)
    const response = await fetch(url)
    
    if (!response.ok) {
      throw new Error(`Failed to load frame results: ${response.statusText}`)
    }
    
    const data = await response.json()
    console.log(`✅ Loaded ${data.length} frame results for video ${videoId}`)
    return data
  },

  /**
   * Load video metadata (dimensions, FPS, duration)
   */
  async loadMetadata(videoId: string): Promise<any> {
    const url = `${API_BASE}/api/video/${videoId}/metadata`
    
    console.log(`📥 Loading metadata from: ${url}`)
    const response = await fetch(url)
    
    if (!response.ok) {
      throw new Error(`Failed to load metadata: ${response.statusText}`)
    }
    
    const data = await response.json()
    console.log(`✅ Loaded metadata for video ${videoId}:`, data)
    return data
  },

  /**
   * Get the video file URL
   */
  getVideoUrl(videoId: string, filename: string): string {
    return `${API_BASE}/uploads/${videoId}/${filename}`
  }
}
