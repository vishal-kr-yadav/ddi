import { useState } from 'react'
import SourceCard from './SourceCard'

function ShareButton({ resultId }) {
  const [copied, setCopied] = useState(false)
  if (!resultId) return null

  const handleCopy = async () => {
    const url = `${window.location.origin}/check/${resultId}`
    try {
      await navigator.clipboard.writeText(url)
    } catch {
      // fallback for browsers without clipboard API
      const el = document.createElement('textarea')
      el.value = url
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 border border-gray-700
        text-gray-300 hover:text-white text-sm px-4 py-2 rounded-lg transition-all"
    >
      {copied ? '✓ Link copied!' : '🔗 Share result'}
    </button>
  )
}

const VERDICT = {
  VERIFIED: {
    bg: 'bg-green-950/50',
    border: 'border-green-700',
    text: 'text-green-400',
    badge: 'bg-green-600',
    bar: 'bg-green-500',
    icon: '✓',
    label: 'VERIFIED',
    subtitle: 'Confirmed by sources',
  },
  FALSE: {
    bg: 'bg-red-950/50',
    border: 'border-red-700',
    text: 'text-red-400',
    badge: 'bg-red-600',
    bar: 'bg-red-500',
    icon: '✗',
    label: 'FALSE',
    subtitle: 'Contradicted by sources',
  },
  MISLEADING: {
    bg: 'bg-orange-950/50',
    border: 'border-orange-700',
    text: 'text-orange-400',
    badge: 'bg-orange-500',
    bar: 'bg-orange-500',
    icon: '⚠',
    label: 'MISLEADING',
    subtitle: 'Partially true, lacks context',
  },
  UNVERIFIED: {
    bg: 'bg-gray-900/80',
    border: 'border-gray-700',
    text: 'text-gray-400',
    badge: 'bg-gray-600',
    bar: 'bg-gray-500',
    icon: '?',
    label: 'UNVERIFIED',
    subtitle: 'Insufficient evidence found',
  },
}

export default function FactCheckResult({ result }) {
  const cfg = VERDICT[result.verdict] || VERDICT.UNVERIFIED

  const supporting    = result.articles.filter((a) => a.stance === 'SUPPORTS')
  const contradicting = result.articles.filter((a) => a.stance === 'CONTRADICTS')
  const neutral       = result.articles.filter((a) => a.stance === 'NEUTRAL' || a.stance === 'UNRELATED')

  return (
    <div className="space-y-5 max-w-5xl mx-auto">

      {/* ── Claim Card ─────────────────────────────────────────── */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-gray-500 text-xs uppercase tracking-widest mb-1">Claim Analyzed</p>
            <p className="text-white text-lg font-medium leading-snug">"{result.claim}"</p>
            <p className="text-gray-600 text-xs mt-2">
              Searched&nbsp;<span className="text-gray-400 font-semibold">{result.sources_searched}</span>&nbsp;articles
              &nbsp;·&nbsp;
              Completed in&nbsp;<span className="text-gray-400 font-semibold">{result.processing_time}s</span>
            </p>
          </div>
          <div className="flex-shrink-0">
            <ShareButton resultId={result.id} />
          </div>
        </div>
      </div>

      {/* ── Verdict Banner ─────────────────────────────────────── */}
      <div className={`${cfg.bg} border ${cfg.border} rounded-xl p-6`}>
        <div className="flex items-start gap-4">
          <div className={`${cfg.badge} w-12 h-12 rounded-full flex items-center justify-center
            text-white text-xl font-bold flex-shrink-0`}>
            {cfg.icon}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-1.5 flex-wrap">
              <span className={`${cfg.badge} text-white text-xs font-bold px-3 py-1 rounded-full`}>
                {cfg.label}
              </span>
              <span className="text-gray-500 text-xs">{cfg.subtitle}</span>
              <span className={`${cfg.text} text-xs font-semibold ml-auto`}>
                {result.confidence}% confidence
              </span>
            </div>
            <p className={`${cfg.text} text-base font-medium leading-snug`}>
              {result.verdict_explanation}
            </p>
          </div>
        </div>

        {/* Confidence bar */}
        <div className="mt-4 bg-gray-800/70 rounded-full h-1.5 overflow-hidden">
          <div
            className={`${cfg.bar} h-1.5 rounded-full transition-all duration-700`}
            style={{ width: `${result.confidence}%` }}
          />
        </div>
      </div>

      {/* ── Key Findings ───────────────────────────────────────── */}
      {result.key_findings?.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-white font-bold mb-3">Key Findings</h2>
          <ul className="space-y-2">
            {result.key_findings.map((f, i) => (
              <li key={i} className="flex items-start gap-3 text-gray-300 text-sm leading-relaxed">
                <span className="text-blue-400 font-bold mt-0.5 flex-shrink-0">·</span>
                {f}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Summary ────────────────────────────────────────────── */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-white font-bold mb-3">What Sources Are Saying</h2>
        <div className="text-gray-300 text-sm leading-relaxed whitespace-pre-line">
          {result.summary}
        </div>
      </div>

      {/* ── Guidance ───────────────────────────────────────────── */}
      <div className="bg-blue-950/40 border border-blue-800/60 rounded-xl p-5">
        <h2 className="text-blue-300 font-bold mb-2">Our Guidance to You</h2>
        <p className="text-gray-300 text-sm leading-relaxed">{result.guidance}</p>
      </div>

      {/* ── Sources ────────────────────────────────────────────── */}
      <div>
        <h2 className="text-white font-bold mb-4">
          Sources Analyzed&nbsp;
          <span className="text-gray-500 font-normal text-sm">({result.articles.length})</span>
        </h2>

        {/* Grouped columns */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Supporting */}
          {supporting.length > 0 && (
            <div>
              <h3 className="text-green-400 text-xs font-bold uppercase tracking-widest mb-3">
                Supporting ({supporting.length})
              </h3>
              <div className="space-y-3">
                {supporting.map((a, i) => <SourceCard key={i} article={a} index={i} />)}
              </div>
            </div>
          )}

          {/* Contradicting */}
          {contradicting.length > 0 && (
            <div>
              <h3 className="text-red-400 text-xs font-bold uppercase tracking-widest mb-3">
                Contradicting ({contradicting.length})
              </h3>
              <div className="space-y-3">
                {contradicting.map((a, i) => <SourceCard key={i} article={a} index={i} />)}
              </div>
            </div>
          )}

          {/* Neutral / Related */}
          {neutral.length > 0 && (
            <div>
              <h3 className="text-blue-400 text-xs font-bold uppercase tracking-widest mb-3">
                Related Context ({neutral.length})
              </h3>
              <div className="space-y-3">
                {neutral.map((a, i) => <SourceCard key={i} article={a} index={i} />)}
              </div>
            </div>
          )}

          {/* Fallback: all articles in a grid if none are categorized */}
          {supporting.length === 0 && contradicting.length === 0 && neutral.length === 0 && (
            <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-2 gap-3">
              {result.articles.map((a, i) => <SourceCard key={i} article={a} index={i} />)}
            </div>
          )}
        </div>
      </div>

      {/* Disclaimer */}
      <p className="text-gray-700 text-xs text-center pb-4">
        DDI searches public news sources and uses AI to summarize findings.
        Always read original sources. AI can make mistakes.
      </p>
    </div>
  )
}
