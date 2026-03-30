export default function UsageBadge({ checksRemaining, checksUsed }) {
  const total = checksRemaining + checksUsed
  const isLow = checksRemaining <= 1

  return (
    <div
      className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border ${
        isLow
          ? 'bg-red-950/50 border-red-800/50 text-red-400'
          : 'bg-gray-900 border-gray-700 text-gray-400'
      }`}
    >
      <span className="font-medium">{checksRemaining}/{total}</span>
      <span className="hidden sm:inline">checks today</span>
    </div>
  )
}
