// Turns raw XHR upload-progress ticks into a human "4.2 MB/s · 12s left"
// label. Speed is smoothed (exponential moving average) since two progress
// events close together can otherwise make the instantaneous rate jump
// around wildly and the label unreadable.
export function createSpeedTracker() {
  let lastTime = performance.now()
  let lastLoaded = 0
  let smoothedBps = 0

  return function onProgress(loaded: number, total: number): string {
    const now = performance.now()
    const dt = (now - lastTime) / 1000
    if (dt > 0.05) {
      const instantBps = (loaded - lastLoaded) / dt
      smoothedBps = smoothedBps === 0 ? instantBps : smoothedBps * 0.7 + instantBps * 0.3
      lastTime = now
      lastLoaded = loaded
    }
    if (smoothedBps <= 0) return ''
    const remaining = total - loaded
    const etaSeconds = remaining / smoothedBps
    const speedText = formatRate(smoothedBps)
    const etaText = etaSeconds > 0.5 ? `${formatDuration(etaSeconds)} left` : ''
    return [speedText, etaText].filter(Boolean).join(' · ')
  }
}

function formatRate(bytesPerSec: number): string {
  if (bytesPerSec >= 1024 * 1024) return `${(bytesPerSec / (1024 * 1024)).toFixed(1)} MB/s`
  if (bytesPerSec >= 1024) return `${(bytesPerSec / 1024).toFixed(0)} KB/s`
  return `${Math.round(bytesPerSec)} B/s`
}

function formatDuration(seconds: number): string {
  if (seconds >= 60) return `${Math.ceil(seconds / 60)}m`
  return `${Math.ceil(seconds)}s`
}
