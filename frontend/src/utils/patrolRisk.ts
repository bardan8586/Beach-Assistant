/**
 * Patrol-wide risk state derived from live alerts and tracks.
 * The banner uses this so the operator sees one state, not a pile of badges.
 */

export type PatrolState = 'idle' | 'clear' | 'watch' | 'alert' | 'emergency' | 'offline' | 'analyzing' | 'waking'

export interface PatrolAlert {
  level: string
  acknowledged?: boolean
}

export interface PatrolSwimmer {
  risk_level?: string
  risk_score?: number
}

export function derivePatrolState(input: {
  apiOnline: boolean | null
  apiPhase?: 'checking' | 'online' | 'waking' | 'offline'
  wsConnected: boolean
  analyzing: boolean
  hasClip: boolean
  alerts: PatrolAlert[]
  swimmers: PatrolSwimmer[]
}): PatrolState {
  if (input.apiPhase === 'waking') return 'waking'
  if (input.apiPhase === 'offline' && !input.wsConnected) return 'offline'
  if (input.apiOnline === false && !input.wsConnected) return 'offline'
  const open = input.alerts.filter((alert) => !alert.acknowledged)
  if (open.some((alert) => alert.level === 'emergency')) return 'emergency'
  if (open.some((alert) => alert.level === 'alert')) return 'alert'
  const watchFromAlert = open.some((alert) => alert.level === 'watch')
  const watchFromTrack = input.swimmers.some((swimmer) => {
    const level = (swimmer.risk_level || '').toLowerCase()
    return level === 'high' || level === 'medium' || level === 'critical' || (swimmer.risk_score ?? 0) >= 50
  })
  if (watchFromAlert || watchFromTrack) return 'watch'
  if (input.analyzing && input.swimmers.length === 0 && open.length === 0) return 'analyzing'
  if (input.hasClip || input.swimmers.length > 0 || input.wsConnected) return 'clear'
  return 'idle'
}
