/**
 * Audio Alert Service
 * ===================
 * Handles audio notifications for lifeguards
 * 
 * Features:
 * - Text-to-speech alerts
 * - Alert sound effects (beeps, alarms)
 * - Volume control
 * - Enable/disable toggle
 * - Browser notification integration
 */

class AudioAlertService {
  private audioContext: AudioContext | null = null
  private enabled: boolean = true
  private volume: number = 0.7
  private spokenAlertIds: Set<string> = new Set()
  
  constructor() {
    // Initialize on first user interaction (browser requirement)
    document.addEventListener('click', () => this.initialize(), { once: true })
  }
  
  private initialize() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
    }
  }
  
  public setEnabled(enabled: boolean) {
    this.enabled = enabled
  }
  
  public setVolume(volume: number) {
    this.volume = Math.max(0, Math.min(1, volume))
  }
  
  /**
   * Play alert sound based on severity
   */
  public playAlertSound(level: 'watch' | 'alert' | 'emergency') {
    if (!this.enabled || !this.audioContext) return

    if (level === 'emergency') {
      // Triple urgent beep
      this.playBeep(880, 0.3, 0)
      this.playBeep(880, 0.3, 0.4)
      this.playBeep(1100, 0.4, 0.8)
    } else if (level === 'alert') {
      // Double beep
      this.playBeep(660, 0.3, 0)
      this.playBeep(660, 0.3, 0.35)
    } else {
      // Single soft beep
      this.playBeep(440, 0.2, 0)
    }
  }
  
  private playBeep(frequency: number, duration: number, delay: number) {
    if (!this.audioContext) return
    
    const ctx = this.audioContext
    const oscillator = ctx.createOscillator()
    const gainNode = ctx.createGain()
    
    oscillator.connect(gainNode)
    gainNode.connect(ctx.destination)
    
    oscillator.frequency.value = frequency
    oscillator.type = 'sine'
    
    const startTime = ctx.currentTime + delay
    gainNode.gain.setValueAtTime(this.volume * 0.3, startTime)
    gainNode.gain.exponentialRampToValueAtTime(0.01, startTime + duration)
    
    oscillator.start(startTime)
    oscillator.stop(startTime + duration)
  }
  
  /**
   * Speak alert using text-to-speech
   */
  public speakAlert(
    swimmerId: number,
    level: 'watch' | 'alert' | 'emergency',
    zone: string,
    action: string,
    alertId: string
  ) {
    if (!this.enabled || !('speechSynthesis' in window)) return
    
    // Don't repeat same alert
    if (this.spokenAlertIds.has(alertId)) return
    this.spokenAlertIds.add(alertId)
    
    // Play sound first
    this.playAlertSound(level)
    
    // Then speak (slight delay for sound to finish)
    setTimeout(() => {
      const utterance = new SpeechSynthesisUtterance()
      
      if (level === 'emergency') {
        utterance.text = `Emergency! Swimmer ${swimmerId}. ${zone} zone. ${action}`
        utterance.rate = 1.1
        utterance.pitch = 1.2
        utterance.volume = this.volume
      } else if (level === 'alert') {
        utterance.text = `Alert: Swimmer ${swimmerId}. ${zone} zone. ${action}`
        utterance.rate = 1.0
        utterance.pitch = 1.0
        utterance.volume = this.volume * 0.9
      } else {
        utterance.text = `Watch: Swimmer ${swimmerId}. Monitor closely.`
        utterance.rate = 0.9
        utterance.pitch = 0.9
        utterance.volume = this.volume * 0.7
      }
      
      window.speechSynthesis.speak(utterance)
    }, 600)
  }
  
  /**
   * Request browser notification permission and show notification
   */
  public async showBrowserNotification(
    title: string,
    body: string,
    level: 'watch' | 'alert' | 'emergency'
  ) {
    if (!this.enabled || !('Notification' in window)) return
    
    // Request permission if needed
    if (Notification.permission === 'default') {
      await Notification.requestPermission()
    }
    
    if (Notification.permission === 'granted') {
      const icon = level === 'emergency' ? '🚨' : level === 'alert' ? '⚠️' : '👁️'
      
      new Notification(title, {
        body,
        icon: `/favicon.ico`,
        badge: icon,
        tag: `beach-alert-${level}`,
        requireInteraction: level === 'emergency',
      })
    }
  }
  
  /**
   * Clear spoken alert history (for testing)
   */
  public clearSpokenHistory() {
    this.spokenAlertIds.clear()
  }
}

// Singleton instance
export const audioAlertService = new AudioAlertService()
