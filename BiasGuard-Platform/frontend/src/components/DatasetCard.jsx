import React from 'react'
import { motion } from 'framer-motion'
import { Database, Table2, Target, ArrowRight, Play, BarChart3, CheckCircle2, Clock, AlertTriangle } from 'lucide-react'
import { Badge, Button, Card } from './UI.jsx'

function formatCount(value) {
  if (value === null || value === undefined || value === '') return 'N/A'
  return Number.isFinite(Number(value)) ? Number(value).toLocaleString() : String(value)
}

function getStatusMeta(status) {
  const normalized = String(status || 'Ready').toLowerCase()
  if (normalized === 'error') {
    return { label: 'Error', color: 'red', icon: AlertTriangle, textColor: 'text-red-300' }
  }
  if (normalized === 'processing' || normalized === 'running' || normalized === 'training') {
    return { label: 'Processing', color: 'yellow', icon: Clock, textColor: 'text-amber-300' }
  }
  return { label: 'Ready', color: 'green', icon: CheckCircle2, textColor: 'text-emerald-300' }
}

function getRandomAccentColor() {
  const colors = [
    { bg: 'from-indigo-500/15 to-purple-500/15', border: 'border-indigo-400/20', icon: 'text-indigo-300' },
    { bg: 'from-blue-500/15 to-cyan-500/15', border: 'border-blue-400/20', icon: 'text-blue-300' },
    { bg: 'from-purple-500/15 to-pink-500/15', border: 'border-purple-400/20', icon: 'text-purple-300' },
    { bg: 'from-emerald-500/15 to-teal-500/15', border: 'border-emerald-400/20', icon: 'text-emerald-300' },
    { bg: 'from-orange-500/15 to-red-500/15', border: 'border-orange-400/20', icon: 'text-orange-300' },
    { bg: 'from-pink-500/15 to-rose-500/15', border: 'border-pink-400/20', icon: 'text-pink-300' },
  ]
  return colors[Math.floor(Math.random() * colors.length)]
}

export default function DatasetCard({
  name,
  rows,
  columns,
  target,
  status = 'Ready',
  description,
  source,
  onAnalyze,
  onViewDetails,
}) {
  const statusMeta = getStatusMeta(status)
  const accentColor = getRandomAccentColor()
  const StatusIcon = statusMeta.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -6, scale: 1.02 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="h-full"
    >
      <Card className={`group relative h-full overflow-hidden rounded-3xl border ${accentColor.border} bg-gradient-to-br from-slate-900/95 to-slate-800/95 p-7 shadow-2xl backdrop-blur-sm transition-all duration-300 hover:border-indigo-400/40 hover:shadow-[0_32px_80px_rgba(99,102,241,0.15)]`}>
        {/* Background gradient overlay */}
        <div className={`absolute inset-0 bg-gradient-to-br ${accentColor.bg} opacity-0 transition-opacity duration-300 group-hover:opacity-100`} />

        {/* Animated border glow */}
        <div className="absolute inset-0 rounded-3xl ring-1 ring-white/5 transition-all duration-300 group-hover:ring-indigo-400/20" />

        <div className="relative">
          {/* Header */}
          <div className="flex items-start justify-between gap-4 mb-6">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-4">
                <div className={`flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-r ${accentColor.bg} ring-2 ${accentColor.border} shadow-lg transition-all duration-300 group-hover:scale-110`}>
                  <Database className={`h-7 w-7 ${accentColor.icon}`} />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="truncate text-xl font-bold text-white group-hover:text-indigo-100 transition-colors">{name}</h3>
                  {source && (
                    <p className="text-sm text-slate-400 mt-1">from {source}</p>
                  )}
                </div>
              </div>
            </div>

            <Badge color={statusMeta.color} className="shrink-0 shadow-lg">
              <span className="inline-flex items-center gap-2 font-semibold">
                <StatusIcon className="h-3.5 w-3.5" />
                {statusMeta.label}
              </span>
            </Badge>
          </div>

          {/* Stats Grid */}
          <div className="mb-6 grid gap-4 rounded-2xl bg-gradient-to-r from-slate-950/60 to-slate-900/60 p-5 ring-1 ring-white/5 backdrop-blur-sm">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-3 text-sm">
              <span className={`inline-flex items-center gap-2 font-semibold ${statusMeta.textColor}`}>
                <StatusIcon className="h-4 w-4" />
                Status: {statusMeta.label}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800/80 ring-1 ring-slate-700/50">
                  <Table2 className="h-4 w-4 text-indigo-300" />
                </div>
                <div>
                  <p className="text-xs font-medium uppercase tracking-wider text-slate-400">Rows</p>
                  <p className="text-lg font-bold text-white">{formatCount(rows)}</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800/80 ring-1 ring-slate-700/50">
                  <BarChart3 className="h-4 w-4 text-purple-300" />
                </div>
                <div>
                  <p className="text-xs font-medium uppercase tracking-wider text-slate-400">Columns</p>
                  <p className="text-lg font-bold text-white">{formatCount(columns)}</p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3 pt-2 border-t border-slate-700/50">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800/80 ring-1 ring-slate-700/50">
                <Target className="h-4 w-4 text-emerald-300" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium uppercase tracking-wider text-slate-400">Target</p>
                <p className="truncate text-base font-semibold text-white">{target || 'Not configured'}</p>
              </div>
            </div>
          </div>

          {/* Description */}
          {description && (
            <div className="mb-6">
              <p className="line-clamp-2 text-sm leading-6 text-slate-400 group-hover:text-slate-300 transition-colors">{description}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col gap-3">
            <Button
              onClick={onAnalyze}
              className="w-full inline-flex items-center justify-center gap-3 rounded-2xl bg-gradient-to-r from-indigo-500 to-purple-600 px-5 py-3.5 text-sm font-bold text-white shadow-xl shadow-indigo-500/25 transition-all hover:from-indigo-400 hover:to-purple-500 hover:shadow-2xl hover:shadow-indigo-400/30 hover:scale-[1.02]"
            >
              <Play className="h-4 w-4" />
              Analyze Dataset
            </Button>
            <Button
              variant="secondary"
              onClick={onViewDetails}
              className="w-full inline-flex items-center justify-center gap-3 rounded-2xl border border-slate-600/50 bg-slate-800/80 px-5 py-3.5 text-sm font-semibold text-slate-100 shadow-lg backdrop-blur-sm transition-all hover:bg-slate-700/90 hover:shadow-xl hover:border-slate-500/50 hover:scale-[1.02]"
            >
              View Details
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </Card>
    </motion.div>
  )
}
