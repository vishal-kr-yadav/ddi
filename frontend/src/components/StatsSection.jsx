import { useState, useEffect, useRef } from 'react'

const STATS = [
  { value: 86,  suffix: '%', label: 'of internet users exposed to fake news',            source: 'Statista' },
  { value: 78,  prefix: '$', suffix: 'B', label: 'annual global cost of misinformation', source: 'Economic Impact Report' },
  { value: 6,   suffix: 'x', label: 'faster — false news spreads vs truth',              source: 'MIT Research' },
  { value: 67,  suffix: '%', label: 'of people struggle to spot misinformation',          source: 'Digital Literacy Study' },
]

function AnimatedCounter({ target, prefix = '', suffix = '' }) {
  const [count, setCount] = useState(0)
  const [started, setStarted] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setStarted(true) },
      { threshold: 0.3 }
    )
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!started) return
    const duration = 2000
    const step = target / (duration / 16)
    let current = 0
    const timer = setInterval(() => {
      current += step
      if (current >= target) {
        setCount(target)
        clearInterval(timer)
      } else {
        setCount(Math.floor(current))
      }
    }, 16)
    return () => clearInterval(timer)
  }, [started, target])

  return (
    <span
      ref={ref}
      className="text-4xl md:text-5xl font-extrabold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent"
    >
      {prefix}{count}{suffix}
    </span>
  )
}

export default function StatsSection() {
  return (
    <section className="py-16 border-t border-gray-900">
      <p className="text-gray-600 text-xs uppercase tracking-widest text-center mb-10">
        Why this matters
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto">
        {STATS.map((s, i) => (
          <div key={i} className="bg-gray-900/50 border border-gray-800 rounded-xl p-5 text-center">
            <AnimatedCounter target={s.value} prefix={s.prefix || ''} suffix={s.suffix} />
            <p className="text-gray-400 text-sm mt-2 leading-snug">{s.label}</p>
            <p className="text-gray-700 text-xs mt-1">{s.source}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
