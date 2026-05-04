import React from 'react'
import { Link } from 'react-router-dom'

export default function HomePage() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="max-w-3xl p-10">
        <h1 className="text-4xl font-bold text-white mb-4">BiasGuard</h1>
        <p className="text-slate-300 mb-6">Explore datasets and inspect fairness metrics.</p>
        <div className="flex gap-3">
          <Link to="/datasets" className="px-4 py-2 bg-emerald-600 rounded-lg text-white">Go to Dashboard</Link>
          <Link to="/upload" className="px-4 py-2 bg-slate-700 rounded-lg text-white">Upload</Link>
        </div>
      </div>
    </div>
  )
}
