import React from 'react'
import { motion } from 'framer-motion'
import { AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react'

export function Card({ children, className = '' }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`card-glass p-6 rounded-xl text-slate-100 ${className}`}
    >
      {children}
    </motion.div>
  )
}

export function StatCard({ title, value, icon: Icon, color = 'blue', trend = null }) {
  const colors = {
    blue: 'from-blue-500 to-blue-600',
    purple: 'from-purple-500 to-purple-600',
    green: 'from-green-500 to-green-600',
    red: 'from-red-500 to-red-600',
  }

  return (
    <Card className="overflow-hidden bg-slate-900/85 border border-white/10 shadow-2xl">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-slate-300 font-medium text-sm">{title}</h3>
        <div className={`bg-gradient-to-br ${colors[color]} p-3 rounded-lg`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
      </div>
      <div className="flex items-end justify-between">
        <div>
          <p className="text-3xl font-bold text-white">{value}</p>
          {trend && (
            <p className={`text-xs mt-1 ${trend > 0 ? 'text-red-300' : 'text-emerald-300'}`}>
              {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}%
            </p>
          )}
        </div>
      </div>
    </Card>
  )
}

export function RiskIndicator({ level = 'LOW' }) {
  const config = {
    LOW: {
      color: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/50',
      icon: CheckCircle,
      label: 'Low Risk',
    },
    MEDIUM: {
      color: 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/50',
      icon: AlertTriangle,
      label: 'Medium Risk',
    },
    HIGH: {
      color: 'bg-red-500/20 text-red-300 border border-red-500/50',
      icon: AlertCircle,
      label: 'High Risk',
    },
  }

  const normalizedLevel = (level || 'LOW').toUpperCase()
  const cfg = config[normalizedLevel] || config.LOW
  const Icon = cfg.icon

  return (
    <motion.div
      initial={{ scale: 0.9 }}
      animate={{ scale: 1 }}
      className={`${cfg.color} px-6 py-4 rounded-lg flex items-center gap-3 font-semibold shadow-lg`}
    >
      <Icon className="w-5 h-5" />
      {cfg.label}
    </motion.div>
  )
}

export function Button({ children, variant = 'primary', isLoading = false, ...props }) {
  const variants = {
    primary: 'btn-primary bg-slate-100 text-slate-950 hover:bg-slate-200',
    secondary: 'btn-secondary bg-slate-800 text-white border border-slate-600 hover:bg-slate-700',
  }

  return (
    <button
      disabled={isLoading}
      className={`${variants[variant]} disabled:opacity-90 disabled:cursor-not-allowed flex items-center gap-2 px-4 py-3 rounded-xl font-semibold transition-all duration-150 ${props.className || ''}`}
      {...props}
    >
      {isLoading && (
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity }}
          className="w-4 h-4 border-2 border-transparent border-t-slate-950 rounded-full"
        />
      )}
      {children}
    </button>
  )
}

export function Badge({ children, color = 'blue', className = '' }) {
  const colors = {
    green: 'badge-success',
    yellow: 'badge-warning',
    red: 'badge-error',
    blue: 'bg-blue-100 text-blue-800',
  }
  return <span className={`${colors[color]} px-3 py-1 rounded-full text-sm ${className}`}>{children}</span>
}

export function LoadingSpinner() {
  return (
    <motion.div className="flex items-center justify-center p-8 text-white">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        className="w-12 h-12 border-4 border-white/20 border-t-cyan-400 rounded-full"
      />
    </motion.div>
  )
}

export function Sidebar({ children }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-slate-100">
      <div className="max-w-7xl mx-auto px-4 py-8">{children}</div>
    </div>
  )
}
