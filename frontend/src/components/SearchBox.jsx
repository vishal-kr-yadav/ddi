import { useState } from 'react'

export default function SearchBox({ onSubmit, isCompact = false }) {
  const [claim, setClaim] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    const trimmed = claim.trim()
    if (!trimmed) {
      setError('Please enter a news claim to fact-check.')
      return
    }
    if (trimmed.split(/\s+/).length < 3) {
      setError('Please use at least 3 words for a better search.')
      return
    }
    setError('')
    onSubmit(trimmed)
  }

  return (
    <form onSubmit={handleSubmit} className={`w-full ${isCompact ? 'max-w-3xl' : 'max-w-2xl'}`}>
      <div className="relative">
        <textarea
          value={claim}
          onChange={(e) => {
            setClaim(e.target.value)
            if (error) setError('')
          }}
          placeholder={
            isCompact
              ? 'Enter another claim to fact-check...'
              : 'e.g. "Is Donald Trump getting the Nobel Prize?" or "Did India land on Mars?"'
          }
          className="w-full bg-gray-900 border border-gray-700 rounded-xl px-5 py-4 text-white
            placeholder-gray-600 resize-none focus:outline-none focus:border-blue-500
            focus:ring-1 focus:ring-blue-500/30 transition-all text-base leading-relaxed"
          rows={isCompact ? 2 : 3}
          maxLength={500}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSubmit(e)
            }
          }}
        />
        <div className="flex items-center justify-between mt-3">
          <div>
            {error && <p className="text-red-400 text-sm">{error}</p>}
            {!error && (
              <p className="text-gray-600 text-xs">
                {claim.length}/500 &nbsp;·&nbsp; Press Enter or click Fact Check
              </p>
            )}
          </div>
          <button
            type="submit"
            disabled={!claim.trim()}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-600
              text-white px-6 py-2.5 rounded-lg font-semibold transition-all text-sm"
          >
            Fact Check →
          </button>
        </div>
      </div>
    </form>
  )
}
