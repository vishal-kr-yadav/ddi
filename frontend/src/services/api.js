const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:8000')

// ---------------------------------------------------------------------------
// Device ID — persisted in localStorage
// ---------------------------------------------------------------------------
export function getDeviceId() {
  let id = localStorage.getItem('ddi_device_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('ddi_device_id', id)
  }
  return id
}

// ---------------------------------------------------------------------------
// Streaming fact-check  (primary — uses SSE over fetch)
// ---------------------------------------------------------------------------
export async function checkFactStream(claim, deviceId, { onProgress, onResult, onError }) {
  try {
    const response = await fetch(`${API_BASE}/api/v1/fact-check/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Device-ID': deviceId,
      },
      body: JSON.stringify({ claim }),
    })

    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || `Server error (${response.status})`)
    }

    const reader  = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer    = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // SSE messages are delimited by double newlines
      const parts = buffer.split('\n\n')
      buffer = parts.pop()  // keep incomplete trailing chunk

      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data: ')) continue
        try {
          const msg = JSON.parse(line.slice(6))
          if      (msg.event === 'progress') onProgress?.(msg)
          else if (msg.event === 'result')   onResult?.(msg.data)
          else if (msg.event === 'error')    onError?.(new Error(msg.message))
        } catch {
          // malformed chunk — ignore
        }
      }
    }
  } catch (err) {
    onError?.(err)
  }
}

// ---------------------------------------------------------------------------
// Load a stored result by share ID
// ---------------------------------------------------------------------------
export async function getFactCheckById(id) {
  const res = await fetch(`${API_BASE}/api/v1/result/${id}`)
  if (!res.ok) throw new Error('Fact-check not found.')
  return res.json()
}

// ---------------------------------------------------------------------------
// Trending + recent
// ---------------------------------------------------------------------------
export async function getTrending() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/trending`)
    return res.ok ? res.json() : { trending: [] }
  } catch { return { trending: [] } }
}

export async function getRecent() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/recent`)
    return res.ok ? res.json() : { recent: [] }
  } catch { return { recent: [] } }
}

// ---------------------------------------------------------------------------
// Device usage
// ---------------------------------------------------------------------------
export async function getDeviceUsage(deviceId) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/device-usage?device_id=${encodeURIComponent(deviceId)}`)
    return res.ok ? res.json() : { checks_used: 0, checks_remaining: 5, limit: 5 }
  } catch { return { checks_used: 0, checks_remaining: 5, limit: 5 } }
}
