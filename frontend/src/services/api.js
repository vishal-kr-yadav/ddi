const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:8000')

// ---------------------------------------------------------------------------
// Streaming fact-check  (primary — uses SSE over fetch)
// ---------------------------------------------------------------------------
export async function checkFactStream(claim, email, { onProgress, onResult, onError }) {
  try {
    const response = await fetch(`${API_BASE}/api/v1/fact-check/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Email': email,
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

export async function getMyHistory(email) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/my-history?email=${encodeURIComponent(email)}`)
    return res.ok ? res.json() : { history: [] }
  } catch { return { history: [] } }
}

// ---------------------------------------------------------------------------
// User registration, login, usage
// ---------------------------------------------------------------------------
export async function registerUser(email) {
  const res = await fetch(`${API_BASE}/api/v1/users/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Registration failed (${res.status})`)
  }
  return res.json()
}

export async function loginUser(email) {
  const res = await fetch(`${API_BASE}/api/v1/users/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Email not found (${res.status})`)
  }
  return res.json()
}

export async function getUserUsage(email) {
  const res = await fetch(`${API_BASE}/api/v1/users/usage?email=${encodeURIComponent(email)}`)
  if (!res.ok) throw new Error('Failed to fetch usage')
  return res.json()
}

export async function verifyRegister(email, otp) {
  const res = await fetch(`${API_BASE}/api/v1/users/verify-register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, otp }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Verification failed (${res.status})`)
  }
  return res.json()
}

export async function verifyLogin(email, otp) {
  const res = await fetch(`${API_BASE}/api/v1/users/verify-login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, otp }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Verification failed (${res.status})`)
  }
  return res.json()
}
