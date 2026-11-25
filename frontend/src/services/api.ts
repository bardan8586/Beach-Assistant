/**
 * API Service
 * ===========
 * HTTP client for backend communication
 */

import axios from 'axios'
import { API_BASE_URL, API_PREFIX } from '../utils/constants'
import type { Swimmer } from '../types/swimmer'
import type { Alert } from '../types/alert'
import type { Camera } from '../types/camera'
import type { CoastalConditionsResponse } from '../types/coastal'

export interface VideoUploadLimitsResponse {
  max_upload_bytes: number
  max_upload_mb: number
}

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: `${API_BASE_URL}${API_PREFIX}`,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

/**
 * API Service Class
 */
class ApiService {
  /**
   * Get active swimmers for a camera
   * Backend returns { success, data: Swimmer[], count }
   */
  async getSwimmers(cameraId?: string): Promise<Swimmer[]> {
    const params = cameraId ? { camera_id: cameraId } : {}
    const response = await apiClient.get<{ success: boolean; data: Swimmer[]; count?: number }>('/swimmers', { params })
    const body = response.data
    return Array.isArray(body) ? body : (body?.data ?? [])
  }

  /**
   * Get alerts (with optional filters)
   */
  async getAlerts(params?: {
    camera_id?: string
    status?: string
    severity?: string
    limit?: number
  }): Promise<Alert[]> {
    const response = await apiClient.get<Alert[]>('/alerts', { params })
    return response.data
  }

  /**
   * Get cameras
   */
  async getCameras(): Promise<Camera[]> {
    const response = await apiClient.get<Camera[]>('/cameras')
    return response.data
  }

  /**
   * Acknowledge an alert
   */
  async acknowledgeAlert(alertId: string): Promise<void> {
    await apiClient.patch(`/alerts/${alertId}`, {
      status: 'acknowledged',
      acknowledged_at: new Date().toISOString(),
    })
  }

  /**
   * Live coastal / marine conditions (Open-Meteo via backend proxy)
   */
  async getCoastalConditions(params?: {
    latitude?: number
    longitude?: number
  }): Promise<CoastalConditionsResponse> {
    const response = await apiClient.get<CoastalConditionsResponse>('/coastal/conditions', {
      timeout: 20000,
      params: params?.latitude != null && params?.longitude != null
        ? { latitude: params.latitude, longitude: params.longitude }
        : undefined,
    })
    return response.data
  }

  /** Server-enforced max video upload size (bytes + MB) for UI hints */
  async getVideoUploadLimits(): Promise<VideoUploadLimitsResponse> {
    const response = await apiClient.get<VideoUploadLimitsResponse>('/video/limits')
    return response.data
  }

  /**
   * Health check. A missing response or a gateway error means the free host
   * is probably still waking, not that the product is broken.
   */
  async probeApi(): Promise<'online' | 'waking'> {
    try {
      await axios.get(`${API_BASE_URL}/health`, { timeout: 8000 })
      return 'online'
    } catch (error) {
      if (axios.isAxiosError(error) && error.response && error.response.status < 500 && error.response.status !== 408) {
        return 'online'
      }
      return 'waking'
    }
  }

  async healthCheck(): Promise<boolean> {
    return (await this.probeApi()) === 'online'
  }
}

export const apiService = new ApiService()
export default apiService


