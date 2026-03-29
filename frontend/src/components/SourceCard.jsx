const STANCE = {
  SUPPORTS:    { bar: 'border-l-green-500',  badge: 'bg-green-900/40 text-green-400',  label: 'Supports'    },
  CONTRADICTS: { bar: 'border-l-red-500',    badge: 'bg-red-900/40 text-red-400',      label: 'Contradicts' },
  NEUTRAL:     { bar: 'border-l-blue-500',   badge: 'bg-blue-900/30 text-blue-400',    label: 'Related'     },
  UNRELATED:   { bar: 'border-l-gray-600',   badge: 'bg-gray-800 text-gray-500',       label: 'Unrelated'   },
}

const CREDIBILITY_STYLE = {
  green:  { dot: 'bg-green-400',  text: 'text-green-400'  },
  blue:   { dot: 'bg-blue-400',   text: 'text-blue-400'   },
  yellow: { dot: 'bg-yellow-400', text: 'text-yellow-400' },
  red:    { dot: 'bg-red-400',    text: 'text-red-400'    },
  gray:   { dot: 'bg-gray-500',   text: 'text-gray-500'   },
}

function fmt(dateStr) {
  if (!dateStr) return ''
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
    })
  } catch {
    return String(dateStr).slice(0, 10)
  }
}

export default function SourceCard({ article }) {
  const stance = STANCE[article.stance] || STANCE.NEUTRAL
  const credColor = article.credibility_color || 'gray'
  const credStyle = CREDIBILITY_STYLE[credColor] || CREDIBILITY_STYLE.gray

  return (
    <div
      className={`bg-gray-900 border border-gray-800 border-l-4 ${stance.bar}
        rounded-lg p-4 hover:bg-gray-800/60 transition-colors`}
    >
      {/* Top row: source name + stance badge */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-gray-500 text-xs font-medium truncate">{article.source}</span>
        <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${stance.badge}`}>
          {stance.label}
        </span>
      </div>

      {/* Title */}
      <a
        href={article.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-white text-sm font-semibold hover:text-blue-400 transition-colors
          line-clamp-2 block mb-2 leading-snug"
      >
        {article.title || 'Untitled article'}
      </a>

      {/* Key point (Claude's insight) or fallback description */}
      {article.key_point ? (
        <p className="text-gray-400 text-xs line-clamp-3 mb-3 italic leading-relaxed">
          {article.key_point}
        </p>
      ) : article.description ? (
        <p className="text-gray-500 text-xs line-clamp-2 mb-3">{article.description}</p>
      ) : null}

      {/* Footer: credibility + date + link */}
      <div className="flex items-center justify-between gap-2 pt-2 border-t border-gray-800/60">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${credStyle.dot}`} />
          <span className={`text-xs truncate ${credStyle.text}`}>
            {article.credibility_tier || 'Unrated'}
            {article.credibility_score != null && (
              <span className="opacity-60"> · {article.credibility_score}</span>
            )}
          </span>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <span className="text-gray-700 text-xs">{fmt(article.published_at)}</span>
          {article.url && (
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-500 hover:text-blue-400 text-xs transition-colors"
            >
              Read →
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
