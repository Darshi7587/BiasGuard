
import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Card, Button, LoadingSpinner, DatasetCard } from '../components'
import { listDatasets } from '../utils/api'
import { RefreshCw, Layers, BarChart3, Sparkles, Plus, TrendingUp, Activity, Database } from 'lucide-react'

export default function DatasetsDashboardPage() {
  const navigate = useNavigate()
  const [datasets, setDatasets] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadDatasets()
  }, [])

  const loadDatasets = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await listDatasets()
      const datasetList = response.datasets || []
      setDatasets(datasetList)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load datasets')
    } finally {
      setIsLoading(false)
    }
  }

  const handleRefresh = async () => {
    await loadDatasets()
  }

  const getDatasetStatus = (dataset) => {
    if (dataset?.error) return 'Error'
    if (dataset?.analyzed) return 'Ready'
    return 'Ready'
  }

  const openConfigure = (dataset) => {
    navigate('/configure', { state: { dataset } })
  }

  const openDetails = (dataset) => {
    navigate('/dashboard', { state: { datasetId: dataset.dataset_id } })
  }

  const readyCount = datasets.filter((dataset) => dataset.analyzed).length
  const pendingCount = datasets.filter((dataset) => !dataset.analyzed).length
  const processingCount = datasets.filter((dataset) => dataset.processing || dataset.training).length

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-12"
        >
          <div className="flex flex-col gap-8 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-4xl">
              <div className="mb-6 inline-flex items-center gap-3 rounded-full border border-indigo-400/30 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 px-4 py-2 text-sm font-medium text-indigo-200 shadow-lg shadow-indigo-500/10">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-gradient-to-r from-indigo-500 to-purple-500">
                  <Layers className="h-3.5 w-3.5 text-white" />
                </div>
                Multi-dataset BiasGuard dashboard
              </div>
              <h1 className="text-5xl font-bold tracking-tight text-white sm:text-6xl lg:text-7xl">
                <span className="bg-gradient-to-r from-white via-indigo-100 to-purple-200 bg-clip-text text-transparent">
                  BiasGuard
                </span>
                <br />
                <span className="text-3xl font-semibold text-slate-300 sm:text-4xl lg:text-5xl">
                  AI Fairness Platform
                </span>
              </h1>
              <p className="mt-6 max-w-3xl text-lg leading-8 text-slate-300 sm:text-xl">
                Explore datasets, review bias signals, and start analysis with a streamlined workflow.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-4 lg:justify-end">
              <Button
                onClick={handleRefresh}
                variant="secondary"
                className="inline-flex items-center gap-3 rounded-2xl border border-slate-600/50 bg-slate-800/80 px-6 py-4 text-base font-semibold text-slate-100 shadow-lg backdrop-blur-sm transition-all hover:bg-slate-700/90 hover:shadow-xl"
              >
                <RefreshCw className="h-5 w-5" />
                Refresh
              </Button>
              <Button
                onClick={() => navigate('/upload')}
                className="inline-flex items-center gap-3 rounded-2xl bg-gradient-to-r from-indigo-500 to-purple-600 px-6 py-4 text-base font-semibold text-white shadow-xl shadow-indigo-500/25 transition-all hover:from-indigo-400 hover:to-purple-500 hover:shadow-2xl hover:shadow-indigo-400/30"
              >
                <Plus className="h-5 w-5" />
                Upload Dataset
              </Button>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mb-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4"
        >
          <Card className="group relative overflow-hidden rounded-3xl border border-slate-700/50 bg-gradient-to-br from-slate-900/90 to-slate-800/90 p-6 shadow-2xl backdrop-blur-sm transition-all hover:shadow-indigo-500/10">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 opacity-0 transition-opacity group-hover:opacity-100" />
            <div className="relative">
              <div className="flex items-center justify-between">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-r from-indigo-500 to-purple-600 shadow-lg">
                  <Database className="h-6 w-6 text-white" />
                </div>
                <TrendingUp className="h-5 w-5 text-indigo-300" />
              </div>
              <p className="mt-4 text-sm font-medium uppercase tracking-wider text-slate-400">Total Datasets</p>
              <p className="mt-2 text-3xl font-bold text-white">{datasets.length}</p>
            </div>
          </Card>

          <Card className="group relative overflow-hidden rounded-3xl border border-slate-700/50 bg-gradient-to-br from-emerald-900/20 to-emerald-800/20 p-6 shadow-2xl backdrop-blur-sm transition-all hover:shadow-emerald-500/10">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-green-500/5 opacity-0 transition-opacity group-hover:opacity-100" />
            <div className="relative">
              <div className="flex items-center justify-between">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-r from-emerald-500 to-green-600 shadow-lg">
                  <Activity className="h-6 w-6 text-white" />
                </div>
                <TrendingUp className="h-5 w-5 text-emerald-300" />
              </div>
              <p className="mt-4 text-sm font-medium uppercase tracking-wider text-slate-400">Ready</p>
              <p className="mt-2 text-3xl font-bold text-emerald-300">{readyCount}</p>
            </div>
          </Card>

          <Card className="group relative overflow-hidden rounded-3xl border border-slate-700/50 bg-gradient-to-br from-amber-900/20 to-amber-800/20 p-6 shadow-2xl backdrop-blur-sm transition-all hover:shadow-amber-500/10">
            <div className="absolute inset-0 bg-gradient-to-br from-amber-500/5 to-orange-500/5 opacity-0 transition-opacity group-hover:opacity-100" />
            <div className="relative">
              <div className="flex items-center justify-between">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-r from-amber-500 to-orange-600 shadow-lg">
                  <BarChart3 className="h-6 w-6 text-white" />
                </div>
                <TrendingUp className="h-5 w-5 text-amber-300" />
              </div>
              <p className="mt-4 text-sm font-medium uppercase tracking-wider text-slate-400">Pending</p>
              <p className="mt-2 text-3xl font-bold text-amber-300">{pendingCount}</p>
            </div>
          </Card>

          <Card className="group relative overflow-hidden rounded-3xl border border-slate-700/50 bg-gradient-to-br from-slate-900/90 to-slate-800/90 p-6 shadow-2xl backdrop-blur-sm transition-all hover:shadow-slate-500/10">
            <div className="absolute inset-0 bg-gradient-to-br from-slate-500/5 to-gray-500/5 opacity-0 transition-opacity group-hover:opacity-100" />
            <div className="relative">
              <div className="flex items-center justify-between">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-r from-slate-500 to-gray-600 shadow-lg">
                  <Sparkles className="h-6 w-6 text-white" />
                </div>
                <TrendingUp className="h-5 w-5 text-slate-300" />
              </div>
              <p className="mt-4 text-sm font-medium uppercase tracking-wider text-slate-400">Processing</p>
              <p className="mt-2 text-3xl font-bold text-slate-300">{processingCount}</p>
            </div>
          </Card>
        </motion.div>

        {error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mb-8"
          >
            <Card className="rounded-3xl border border-red-500/30 bg-gradient-to-r from-red-500/10 to-red-600/10 p-6 text-red-200 shadow-xl backdrop-blur-sm">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-500/20">
                  <span className="text-lg">⚠️</span>
                </div>
                <p className="text-base font-medium">{error}</p>
              </div>
            </Card>
          </motion.div>
        )}

        {isLoading ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <Card className="rounded-3xl border border-slate-700/50 bg-gradient-to-br from-slate-900/90 to-slate-800/90 text-white shadow-2xl backdrop-blur-sm">
              <div className="flex flex-col items-center justify-center gap-6 p-16 text-center">
                <div className="relative">
                  <LoadingSpinner />
                  <div className="absolute inset-0 rounded-full bg-gradient-to-r from-indigo-500/20 to-purple-500/20 blur-xl" />
                </div>
                <div>
                  <p className="text-xl font-semibold text-white">Loading datasets...</p>
                  <p className="mt-2 text-slate-400">Discovering and analyzing your data</p>
                </div>
              </div>
            </Card>
          </motion.div>
        ) : datasets.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <Card className="rounded-3xl border border-slate-700/50 bg-gradient-to-br from-slate-900/90 to-slate-800/90 text-white shadow-2xl backdrop-blur-sm">
              <div className="p-16 text-center">
                <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-r from-indigo-500/10 to-purple-500/10 ring-2 ring-indigo-400/20">
                  <BarChart3 className="h-10 w-10 text-indigo-300" />
                </div>
                <h3 className="text-2xl font-bold text-white">No datasets found</h3>
                <p className="mt-3 text-lg text-slate-400">Upload a dataset from the Upload page to get started with bias analysis.</p>
                <Button
                  onClick={() => navigate('/upload')}
                  className="mt-8 inline-flex items-center gap-3 rounded-2xl bg-gradient-to-r from-indigo-500 to-purple-600 px-8 py-4 text-lg font-semibold text-white shadow-xl shadow-indigo-500/25 transition-all hover:from-indigo-400 hover:to-purple-500 hover:shadow-2xl hover:shadow-indigo-400/30"
                >
                  <Plus className="h-5 w-5" />
                  Upload Dataset
                </Button>
              </div>
            </Card>
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="grid gap-6 [grid-template-columns:repeat(auto-fit,minmax(380px,1fr))]"
          >
            {datasets.map((dataset, index) => (
              <motion.div
                key={dataset.dataset_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
              >
                <DatasetCard
                  name={dataset.filename || dataset.dataset_id || 'Dataset'}
                  rows={dataset.rows}
                  columns={dataset.columns}
                  target={dataset.target}
                  status={getDatasetStatus(dataset)}
                  description={dataset.description}
                  source={dataset.source}
                  onAnalyze={() => openConfigure(dataset)}
                  onViewDetails={() => openDetails(dataset)}
                />
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </div>
  )
}
