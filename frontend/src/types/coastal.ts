export interface CoastalConditionsResponse {
  location: {
    latitude: number
    longitude: number
    label: string
  }
  fetched_at: string
  marine: {
    time_utc: string | null
    wave_height_m: number | null
    wave_direction_deg: number | null
    wave_period_s: number | null
    swell_height_m: number | null
    swell_direction_deg: number | null
    swell_period_s: number | null
    wind_wave_height_m: number | null
    sea_surface_temp_c: number | null
  }
  weather: {
    wind_speed_kmh: number | null | undefined
    wind_direction_deg: number | null | undefined
    weather_code: number | null | undefined
    is_day: number | null | undefined
  }
  partial: boolean
  warnings: string[]
  attribution: string
}
