import React from 'react'
import { motion } from 'framer-motion'
import { CheckCircle, AlertTriangle, AlertCircle } from 'lucide-react'
import { Card } from './UI'

export function InsightsPanel({ insights }) {
  const getBackgroundColor = (insight) => {
    const severity = typeof insight === 'string' ? 'info' : insight.severity || 'info'
    if (severity === 'critical') return 'bg-red-500/10 border-red-400/30 hover:border-red-300'
    if (severity === 'warning') return 'bg-amber-500/10 border-amber-400/30 hover:border-amber-300'
    return 'bg-emerald-500/10 border-emerald-400/30 hover:border-emerald-300'
  }

  return (
    <Card className="bg-slate-900/85 border border-white/10 text-white shadow-2xl">
      <h3 className="text-lg font-semibold text-white mb-6">📊 Bias Analysis Insights</h3>
      <div className="space-y-3">
        {insights?.map((insight, idx) => {
          const title = typeof insight === 'string' ? insight : insight.title || 'Insight'
          const description = typeof insight === 'string' ? null : insight.description || null
          return (
            <motion.div
              key={idx}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1 }}
              className={`flex flex-col gap-3 p-4 rounded-lg border transition ${getBackgroundColor(insight)}`}
            >
              <div className="flex items-center gap-3">
                <span className="font-semibold flex-shrink-0 text-lg">•</span>
                <p className="text-sm text-slate-100 font-semibold">{title}</p>
              </div>
              {description && <p className="text-sm text-slate-200 leading-relaxed">{description}</p>}
            </motion.div>
          )
        })}
        {(!insights || insights.length === 0) && (
          <p className="text-slate-300 text-center py-8">No insights available yet</p>
        )}
      </div>
    </Card>
  )
}

export function RecommendationsPanel({ recommendations }) {
  return (
    <Card className="bg-slate-900/85 border border-white/10 text-white shadow-2xl">
      <h3 className="text-lg font-semibold text-white mb-6">Recommendations</h3>
      <div className="space-y-3">
        {recommendations?.map((rec, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="flex gap-3 p-3 bg-cyan-500/10 rounded-lg border border-cyan-400/20 hover:border-cyan-300/40 transition"
          >
            <span className="text-cyan-300 font-bold flex-shrink-0">{idx + 1}.</span>
            <p className="text-slate-100 text-sm">{rec}</p>
          </motion.div>
        ))}
        {(!recommendations || recommendations.length === 0) && (
          <p className="text-slate-300 text-center py-8">No recommendations available</p>
        )}
      </div>
    </Card>
  )
}
