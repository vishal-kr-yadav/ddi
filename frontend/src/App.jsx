import { useState, useEffect } from 'react'
import SearchBox from './components/SearchBox'
import FactCheckResult from './components/FactCheckResult'
import LoadingState from './components/LoadingState'
import TrendingSection from './components/TrendingSection'
import UsageBadge from './components/UsageBadge'
import StatsSection from './components/StatsSection'
import HowItWorks from './components/HowItWorks'
import WhyDifferent from './components/WhyDifferent'
import { checkFactStream, getFactCheckById, getDeviceId, getDeviceUsage } from './services/api'

export default function App() {
  const [result,      setResult]      = useState(null)
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState(null)
  const [activeClaim, setClaim]       = useState('')
  const [streamStep,  setStreamStep]  = useState(null)
  const [usage,       setUsage]       = useState(null)

  const deviceId = getDeviceId()

  // ── On mount: load usage + check shared link ───────────────────────
  useEffect(() => {
    getDeviceUsage(deviceId).then(setUsage)

    const path = window.location.pathname
    if (path.startsWith('/check/')) {
      const id = path.replace('/check/', '').trim()
      if (id) loadById(id)
    }
  }, [])

  // ── Load a stored result by ID (shareable URL) ─────────────────────
  const loadById = async (id) => {
    setLoading(true)
    setError(null)
    setResult(null)
    setStreamStep({ step: 'fetching', message: 'Loading saved result...' })
    try {
      const data = await getFactCheckById(id)
      setResult(data)
      setClaim(data.claim)
      window.history.replaceState(null, '', `/check/${id}`)
    } catch {
      setError('Fact-check not found. It may have expired.')
      window.history.replaceState(null, '', '/')
    } finally {
      setLoading(false)
      setStreamStep(null)
    }
  }

  // ── Run a new fact-check via SSE stream ────────────────────────────
  const handleFactCheck = async (claim) => {
    // Check local usage before making request
    if (usage && usage.checks_remaining <= 0) {
      setError(`Daily limit reached (${usage.limit} checks). Come back in a few hours.`)
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)
    setClaim(claim)
    setStreamStep({ step: 'fetching', message: 'Starting...' })

    await checkFactStream(claim, deviceId, {
      onProgress: (msg) => setStreamStep(msg),
      onResult: (data) => {
        setResult(data)
        setLoading(false)
        setStreamStep(null)
        if (data.id) {
          window.history.pushState(null, '', `/check/${data.id}`)
        }
        // Refresh usage counter
        getDeviceUsage(deviceId).then(setUsage)
      },
      onError: (err) => {
        const msg = err.message || 'Something went wrong. Please try again.'
        if (msg.includes('Daily limit') || msg.includes('429')) {
          setError('You\'ve used all your fact-checks for today. Come back in a few hours!')
          getDeviceUsage(deviceId).then(setUsage)
        } else {
          setError(msg)
        }
        setLoading(false)
        setStreamStep(null)
      },
    })
  }

  const handleReset = () => {
    setResult(null)
    setError(null)
    setClaim('')
    setStreamStep(null)
    window.history.pushState(null, '', '/')
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">

      {/* ── Header ───────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-gray-800/60 bg-gray-950/80 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-4 py-3.5 flex items-center justify-between">
          <button onClick={handleReset} className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500
              flex items-center justify-center text-white font-extrabold text-xs">
              DDI
            </div>
            <div className="leading-none">
              <span className="font-bold text-white group-hover:text-blue-300 transition-colors">
                Data Driven
              </span>
              <span className="font-bold text-blue-400 group-hover:text-blue-300 transition-colors">
                {' '}Intelligence
              </span>
            </div>
          </button>

          <div className="flex items-center gap-3">
            {usage && (
              <UsageBadge
                checksRemaining={usage.checks_remaining}
                checksUsed={usage.checks_used}
              />
            )}
            {(result || error) && !loading && (
              <button
                onClick={handleReset}
                className="text-sm text-gray-400 hover:text-white transition-colors ml-2"
              >
                &larr; New
              </button>
            )}
          </div>
        </div>
      </header>

      {/* ── Main ─────────────────────────────────────────────────── */}
      <main className="max-w-6xl mx-auto px-4 py-10">

        {/* Landing */}
        {!result && !loading && (
          <>
            {/* Section A: Hero + Search */}
            <div className="flex flex-col items-center pt-8 pb-12 gap-8">
              <div className="text-center max-w-2xl">
                <div className="inline-flex items-center gap-2 bg-blue-950/50 border border-blue-800/50
                  text-blue-400 text-xs px-3 py-1 rounded-full mb-6">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                  Searches 10+ global sources &middot; AI-powered analysis
                </div>
                <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight mb-4 leading-tight">
                  Don't just believe.
                  <br />
                  <span className="bg-gradient-to-r from-blue-400 to-cyan-400
                    bg-clip-text text-transparent">
                    Verify.
                  </span>
                </h1>
                <p className="text-gray-400 text-lg leading-relaxed">
                  Paste any news claim &mdash; we search USA, Europe and Asia,
                  scrape full articles, and fact-check with AI.
                </p>
              </div>

              <SearchBox onSubmit={handleFactCheck} />

              {error && (
                <div className="bg-red-950/50 border border-red-800 rounded-lg px-5 py-3.5
                  text-red-300 text-sm max-w-xl w-full text-center">
                  {error}
                </div>
              )}
            </div>

            {/* Section B: Why This Matters */}
            <StatsSection />

            {/* Section C: How DDI Works */}
            <HowItWorks />

            {/* Section D: What Makes DDI Different */}
            <WhyDifferent />

            {/* Section E: Trending + Recent */}
            <div className="flex flex-col items-center py-12 gap-10 border-t border-gray-900">
              <TrendingSection onLoadResult={loadById} />
            </div>

            {/* Section F: Source Pills */}
            <div className="text-center pb-16 border-t border-gray-900 pt-12">
              <p className="text-gray-700 text-xs mb-3 uppercase tracking-widest">Sources searched</p>
              <div className="flex flex-wrap gap-2 justify-center max-w-2xl mx-auto">
                {[
                  'GDELT', 'Google News (USA)', 'Google News (EU)', 'Google News (Asia)',
                  'NewsAPI', 'The Guardian', 'New York Times', 'GNews', 'Currents API', 'Bing News',
                ].map((s) => (
                  <span key={s}
                    className="bg-gray-900 border border-gray-800 text-gray-600
                      px-2.5 py-1 rounded-full text-xs">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Loading — real-time server progress */}
        {loading && <LoadingState claim={activeClaim} currentStep={streamStep} />}

        {/* Results */}
        {result && !loading && (
          <>
            <div className="flex justify-center mb-8">
              <SearchBox onSubmit={handleFactCheck} isCompact />
            </div>
            {error && (
              <div className="bg-red-950/50 border border-red-800 rounded-lg px-5 py-3.5
                text-red-300 text-sm mb-6 text-center">
                {error}
              </div>
            )}
            <FactCheckResult result={result} />
          </>
        )}
      </main>

      {/* ── Footer ───────────────────────────────────────────────── */}
      <footer className="border-t border-gray-900 mt-16 py-8 text-center text-gray-700 text-xs">
        DDI &mdash; Data Driven Intelligence &nbsp;&middot;&nbsp; Powered by AI + Global News Sources
      </footer>
    </div>
  )
}
