import { useState, useEffect } from 'react'
import { registerUser, loginUser, verifyRegister, verifyLogin } from '../services/api'

export default function AuthScreen({ onAuthenticated, inline = false }) {
  const [email, setEmail]         = useState('')
  const [otp, setOtp]             = useState('')
  const [error, setError]         = useState('')
  const [loading, setLoading]     = useState(false)
  const [isRegister, setIsRegister] = useState(false)
  const [step, setStep]           = useState('email')   // 'email' | 'otp'
  const [cooldown, setCooldown]   = useState(0)

  // Resend cooldown timer
  useEffect(() => {
    if (cooldown <= 0) return
    const t = setTimeout(() => setCooldown(cooldown - 1), 1000)
    return () => clearTimeout(t)
  }, [cooldown])

  const handleSendOtp = async (e) => {
    e.preventDefault()
    const cleaned = email.trim().toLowerCase()
    if (!cleaned) {
      setError('Please enter your email address.')
      return
    }
    if (!/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(cleaned)) {
      setError('Please enter a valid email address.')
      return
    }

    setError('')
    setLoading(true)

    try {
      if (isRegister) {
        await registerUser(cleaned)
      } else {
        await loginUser(cleaned)
      }
      setStep('otp')
      setCooldown(30)
    } catch (err) {
      setError(err.message || 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyOtp = async (e) => {
    e.preventDefault()
    const trimmedOtp = otp.trim()
    if (!trimmedOtp || trimmedOtp.length !== 6) {
      setError('Please enter the 6-digit code.')
      return
    }

    setError('')
    setLoading(true)

    try {
      const cleaned = email.trim().toLowerCase()
      if (isRegister) {
        const res = await verifyRegister(cleaned, trimmedOtp)
        onAuthenticated(cleaned, {
          checks_used: 0,
          checks_remaining: res.checks_remaining,
          resets_at: null,
        })
      } else {
        const res = await verifyLogin(cleaned, trimmedOtp)
        onAuthenticated(cleaned, {
          checks_used: res.checks_used,
          checks_remaining: res.checks_remaining,
          resets_at: res.resets_at,
        })
      }
    } catch (err) {
      setError(err.message || 'Verification failed.')
    } finally {
      setLoading(false)
    }
  }

  const handleResend = async () => {
    if (cooldown > 0) return
    setError('')
    setLoading(true)
    try {
      const cleaned = email.trim().toLowerCase()
      if (isRegister) {
        await registerUser(cleaned)
      } else {
        await loginUser(cleaned)
      }
      setCooldown(30)
    } catch (err) {
      setError(err.message || 'Failed to resend.')
    } finally {
      setLoading(false)
    }
  }

  const handleBack = () => {
    setStep('email')
    setOtp('')
    setError('')
  }

  const card = (
    <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-2xl p-8">

      {/* ── Step 1: Email ───────────────────────────────────── */}
      {step === 'email' && (
        <>
          <h2 className="text-2xl font-bold text-center mb-2">
            {isRegister ? 'Create your account' : 'Welcome back'}
          </h2>
          <p className="text-gray-400 text-center text-sm mb-6">
            {isRegister
              ? 'Register with your email to start fact-checking'
              : 'Enter your email to continue fact-checking'}
          </p>

          <form onSubmit={handleSendOtp} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Email address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
                disabled={loading}
                autoFocus
              />
            </div>

            {error && (
              <div className="text-red-400 text-sm bg-red-950/30 border border-red-900/50 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed rounded-xl font-medium transition"
            >
              {loading ? 'Sending code...' : isRegister ? 'Register' : 'Sign In'}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-gray-500">
            {isRegister ? (
              <>
                Already registered?{' '}
                <button
                  onClick={() => { setIsRegister(false); setError('') }}
                  className="text-blue-400 hover:text-blue-300 transition"
                >
                  Sign in
                </button>
              </>
            ) : (
              <>
                New here?{' '}
                <button
                  onClick={() => { setIsRegister(true); setError('') }}
                  className="text-blue-400 hover:text-blue-300 transition"
                >
                  Register
                </button>
              </>
            )}
          </div>
        </>
      )}

      {/* ── Step 2: OTP ─────────────────────────────────────── */}
      {step === 'otp' && (
        <>
          <h2 className="text-2xl font-bold text-center mb-2">
            Check your email
          </h2>
          <p className="text-gray-400 text-center text-sm mb-1">
            We sent a 6-digit code to
          </p>
          <p className="text-blue-400 text-center text-sm font-medium mb-6">
            {email}
          </p>

          <form onSubmit={handleVerifyOtp} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Verification code</label>
              <input
                type="text"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
                maxLength={6}
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white text-center text-2xl tracking-[0.5em] placeholder-gray-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition font-mono"
                disabled={loading}
                autoFocus
              />
            </div>

            {error && (
              <div className="text-red-400 text-sm bg-red-950/30 border border-red-900/50 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || otp.length !== 6}
              className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed rounded-xl font-medium transition"
            >
              {loading ? 'Verifying...' : 'Verify'}
            </button>
          </form>

          <div className="mt-5 flex items-center justify-between text-sm">
            <button
              onClick={handleBack}
              className="text-gray-500 hover:text-gray-300 transition"
            >
              Change email
            </button>
            <button
              onClick={handleResend}
              disabled={cooldown > 0 || loading}
              className="text-blue-400 hover:text-blue-300 disabled:text-gray-600 disabled:cursor-not-allowed transition"
            >
              {cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend code'}
            </button>
          </div>
        </>
      )}

      <div className="mt-6 pt-4 border-t border-gray-800 text-center text-xs text-gray-600">
        10 free fact-checks per week per account
      </div>
    </div>
  )

  if (inline) return card

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center px-4">
      {/* Logo */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-sm font-bold tracking-wide">
          DDI
        </div>
        <h1 className="text-xl font-semibold">
          Data Driven <span className="text-blue-500">Intelligence</span>
        </h1>
      </div>
      {card}
    </div>
  )
}
