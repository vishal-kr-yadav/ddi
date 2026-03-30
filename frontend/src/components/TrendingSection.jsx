import { useState, useEffect } from 'react'
import { getTrending, getRecent } from '../services/api'

const VERDICT_STYLE = {
  VERIFIED:   { badge: 'bg-green-900/50 text-green-400',  dot: '🟢' },
  FALSE:      { badge: 'bg-red-900/50 text-red-400',      dot: '🔴' },
  MISLEADING: { badge: 'bg-orange-900/50 text-orange-400',dot: '🟡' },
  UNVERIFIED: { badge: 'bg-gray-800 text-gray-400',       dot: '⚫' },
}

function ClaimRow({ item, onClick }) {
  const style = VERDICT_STYLE[item.verdict] || VERDICT_STYLE.UNVERIFIED
  return (
    <button
      onClick={() => onClick(item.id)}
      className="w-full text-left flex items-center gap-3 px-4 py-3 rounded-lg
        bg-gray-900 hover:bg-gray-800 border border-gray-800 hover:border-gray-700
        transition-all group"
    >
      <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${style.badge}`}>
        {item.verdict}
      </span>
      <span className="text-gray-300 text-sm group-hover:text-white transition-colors truncate flex-1">
        {item.claim}
      </span>
      {item.check_count > 1 && (
        <span className="text-gray-600 text-xs flex-shrink-0">
          ×{item.check_count}
        </span>
      )}
      <span className="text-gray-600 group-hover:text-gray-400 text-xs flex-shrink-0">→</span>
    </button>
  )
}

export default function TrendingSection({ onLoadResult }) {
  const [trending, setTrending] = useState([])
  const [recent,   setRecent]   = useState([])

  useEffect(() => {
    getTrending().then((d) => setTrending(d.trending || []))
    getRecent().then((d)   => setRecent(d.recent   || []))
  }, [])

  if (!trending.length && !recent.length) return null

  return (
    <div className="w-full max-w-2xl space-y-6">
      {trending.length > 0 && (
        <div>
          <p className="text-gray-600 text-xs uppercase tracking-widest mb-3">
            🔥 Trending today
          </p>
          <div className="space-y-2">
            {trending.map((item) => (
              <ClaimRow key={item.id} item={item} onClick={onLoadResult} />
            ))}
          </div>
        </div>
      )}

      {recent.length > 0 && (
        <div>
          <p className="text-gray-600 text-xs uppercase tracking-widest mb-3">
            🕐 Recently checked
          </p>
          <div className="space-y-2">
            {recent.map((item) => (
              <ClaimRow key={item.id} item={item} onClick={onLoadResult} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
