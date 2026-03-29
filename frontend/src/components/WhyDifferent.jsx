const FEATURES = [
  {
    icon: '\u{1F30D}',
    title: '10+ Global Sources',
    desc: 'GDELT, Guardian, NYT, GNews, Bing, and regional feeds across USA, Europe, and Asia.',
  },
  {
    icon: '\u{1F4C4}',
    title: 'Deep Article Scraping',
    desc: 'We read full article content, not just headlines \u2014 for real context.',
  },
  {
    icon: '\u{1F916}',
    title: 'Smart Cross-Reference',
    desc: 'Our proprietary engine compares all sources to find consensus and contradictions.',
  },
  {
    icon: '\u{1F6E1}\uFE0F',
    title: 'Source Credibility Scoring',
    desc: 'Every source gets a trust rating so you know what to weight.',
  },
]

export default function WhyDifferent() {
  return (
    <section className="py-16 border-t border-gray-900">
      <p className="text-gray-600 text-xs uppercase tracking-widest text-center mb-10">
        What makes DDI different
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-3xl mx-auto">
        {FEATURES.map((f, i) => (
          <div
            key={i}
            className="bg-gray-900/60 border border-gray-800 rounded-xl p-5
              hover:border-gray-700 transition-colors"
          >
            <div className="text-2xl mb-3">{f.icon}</div>
            <h3 className="text-white font-bold text-sm mb-1">{f.title}</h3>
            <p className="text-gray-500 text-sm leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
