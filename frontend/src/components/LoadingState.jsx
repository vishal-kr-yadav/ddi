const STEPS = [
  { key: 'fetching',  icon: '🌍', label: 'Searching 10+ global news sources…'      },
  { key: 'selecting', icon: '📊', label: 'Ranking articles by relevance…'           },
  { key: 'scraping',  icon: '📄', label: 'Scraping full article content…'           },
  { key: 'analyzing', icon: '🤖', label: 'AI engine cross-referencing all sources…'  },
  { key: 'building',  icon: '📋', label: 'Generating your fact-check report…'       },
]

const STEP_KEYS = STEPS.map((s) => s.key)

export default function LoadingState({ claim, currentStep }) {
  // currentStep = { step: 'fetching', message: 'Searching 10+ ...' }
  const currentIdx = STEP_KEYS.indexOf(currentStep?.step ?? '')

  return (
    <div className="flex flex-col items-center justify-center min-h-[65vh] gap-10 px-4">

      {/* Spinner + heading */}
      <div className="text-center">
        <div className="w-14 h-14 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-6" />
        <h2 className="text-2xl font-bold text-white mb-2">Searching the globe…</h2>
        <p className="text-gray-400 text-sm max-w-md leading-relaxed italic">
          "{claim}"
        </p>
      </div>

      {/* Real-time steps driven by server SSE events */}
      <div className="w-full max-w-md space-y-2">
        {STEPS.map((s, i) => {
          const isDone    = i < currentIdx
          const isCurrent = i === currentIdx
          return (
            <div
              key={s.key}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-500 ${
                isDone      ? 'bg-green-950/40 text-green-400'
                : isCurrent ? 'bg-blue-950/40 text-blue-300'
                : 'text-gray-700'
              }`}
            >
              <span className="text-base w-6 text-center flex-shrink-0">{s.icon}</span>
              <span className="text-sm flex-1">
                {isCurrent && currentStep?.message ? currentStep.message : s.label}
              </span>
              {isDone    && <span className="text-green-500 text-xs flex-shrink-0">✓</span>}
              {isCurrent && (
                <span className="w-3.5 h-3.5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
              )}
            </div>
          )
        })}
      </div>

      <p className="text-gray-600 text-xs">Typically 20–40 seconds</p>
    </div>
  )
}
