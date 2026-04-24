/**
 * Video Service
 * ============
 * Handle video upload and processing
 */

import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface VideoUploadResponse {
  success: boolean
  video_id: string
  filename: string
  video_path: string
  size: number
}

export interface VideoProcessResponse {
  success: boolean
  message: string
  video_id: string
  camera_id: string
  status: string
}

export interface VideoProcessParams {
  camera_id?: string
  show_window?: boolean
}

export interface ProcessingStatus {
  video_id: string
  status: 'not_found' | 'processing' | 'completed'
  camera_id?: string
  return_code?: number
}

const UPLOAD_TIMEOUT_MS = 6 * 60 * 1000 // large clips on slow uplinks

export const videoService = {
  /**
   * Upload video file to backend
   * @param file Video file to upload
   * @param onProgress Optional callback for upload progress (0-100)
   */
  async uploadVideo(
    file: File,
    onProgress?: (percent: number) => void,
  ): Promise<VideoUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await axios.post<VideoUploadResponse>(
      `${API_URL}/api/video/upload`,
      formData,
      {
        timeout: UPLOAD_TIMEOUT_MS,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (evt) => {
          if (!onProgress || !evt.total) return
          const pct = Math.round((evt.loaded / evt.total) * 100)
          onProgress(pct)
        },
      }
    )

    return response.data
  },

  /**
   * Start AI processing on uploaded video
   */
  async processVideo(videoId: string, params?: VideoProcessParams): Promise<VideoProcessResponse> {
    const response = await axios.post<VideoProcessResponse>(
      `${API_URL}/api/video/process/${videoId}`,
      null,
      {
        params: params ?? {},
      }
    )

    return response.data
  },

  /**
   * Get processing status
   */
  async getStatus(videoId: string): Promise<ProcessingStatus> {
    const response = await axios.get<ProcessingStatus>(
      `${API_URL}/api/video/status/${videoId}`
    )

    return response.data
  },
}


