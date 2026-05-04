
import React, { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Card, Button, Badge } from '../components'
import { configureAnalysis, getDatasetInfo } from '../utils/api'
import { CheckCircle2, AlertCircle } from 'lucide-react'

export default function ConfigurationPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const dataset = location.state?.dataset

  const [datasetInfo, setDatasetInfo] = useState(null)
  const [targetColumn, setTargetColumn] = useState(dataset?.suggested_target || '')
  const [sensitiveAttrs, setSensitiveAttrs] = useState(dataset?.suggested_sensitive_attrs || [])
  const [modelType, setModelType] = useState('logistic_regression')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const availableColumns = datasetInfo?.column_names?.length
    ? datasetInfo.column_names
    : (dataset?.column_names || [])

  useEffect(() => {
    let mounted = true

    const loadDatasetInfo = async () => {
      if (!dataset?.dataset_id) return

      try {
        const info = await getDatasetInfo(dataset.dataset_id)
        if (!mounted) return
        setDatasetInfo(info)
        if (info.target) setTargetColumn(info.target)
        if (info.sensitive_attributes?.length) setSensitiveAttrs(info.sensitive_attributes)
      } catch (err) {
        if (mounted) setError('Failed to load dataset information')
      }
    }

    loadDatasetInfo()
    return () => {
      mounted = false
    }
  }, [dataset])

  const handleToggleSensitiveAttr = (attr) => {
    setSensitiveAttrs((prev) =>
      prev.includes(attr) ? prev.filter((a) => a !== attr) : [...prev, attr]
    )
  }

  const handleConfigure = async () => {
    if (!targetColumn || sensitiveAttrs.length === 0) {
      setError('Please select a target column and at least one sensitive attribute')
      return
    }

    if (!availableColumns.includes(targetColumn)) {
      setError('Selected target column is not available in the dataset')
      return
    }

    setIsLoading(true)
    setError(null)
    try {
      await configureAnalysis(dataset.dataset_id, targetColumn, sensitiveAttrs, [modelType])
      navigate('/dashboard', { state: { datasetId: dataset.dataset_id, targetColumn, sensitiveAttrs, modelType } })
    } catch (err) {
      setError(err.response?.data?.detail || 'Configuration failed')
    } finally {
      setIsLoading(false)
    }
  }

  if (!dataset) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-slate-100">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="text-center py-16">
            <p className="text-slate-300 mb-4">No dataset uploaded. Please upload a dataset first.</p>
            <Button onClick={() => navigate('/upload')} className="bg-emerald-600 hover:bg-emerald-700">
              Go to Upload
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-slate-100">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Configure Analysis</h1>
          <p className="text-slate-300">Select the prediction target and sensitive attributes for fairness analysis.</p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-4 mb-8">
          <Card className="bg-slate-900/90 border border-slate-700">
            <div className="text-center">
              <p className="text-slate-400 text-sm font-medium">Dataset</p>
              <p className="text-2xl font-bold text-white mt-1">{dataset.filename}</p>
            </div>
          </Card>
          <Card className="bg-slate-900/90 border border-slate-700">
            <div className="text-center">
              <p className="text-slate-400 text-sm font-medium">Rows</p>
              <p className="text-2xl font-bold text-white mt-1">{dataset.rows || '?'}</p>
            </div>
          </Card>
          <Card className="bg-slate-900/90 border border-slate-700">
            <div className="text-center">
              <p className="text-slate-400 text-sm font-medium">Columns</p>
              <p className="text-2xl font-bold text-white mt-1">{dataset.columns || '?'}</p>
            </div>
          </Card>
        </div>

        <div className="grid md:grid-cols-2 gap-6 mb-8">
          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
            <Card className="bg-slate-900/90 border border-slate-700">
              <h3 className="text-lg font-semibold text-white mb-4">Target Column</h3>
              <select
                value={targetColumn}
                onChange={(e) => setTargetColumn(e.target.value)}
                className="w-full p-3 bg-slate-800 border border-slate-700 rounded-lg text-white"
              >
                <option value="">Select target...</option>
                {availableColumns.map((col) => (
                  <option key={col} value={col}>{col}</option>
                ))}
              </select>
              {targetColumn && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-3 p-3 bg-emerald-500/20 rounded-lg flex items-center gap-2 text-emerald-300 text-sm border border-emerald-500/50">
                  <CheckCircle2 className="w-4 h-4" />
                  Selected: {targetColumn}
                </motion.div>
              )}
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}>
            <Card className="bg-slate-900/90 border border-slate-700">
              <h3 className="text-lg font-semibold text-white mb-4">Sensitive Attributes</h3>
              <div className="space-y-2 max-h-56 overflow-y-auto">
                {availableColumns
                  .filter((col) => col !== targetColumn)
                  .map((col) => (
                    <label key={col} className="flex items-center p-2 rounded cursor-pointer hover:bg-slate-800/50 transition">
                      <input
                        type="checkbox"
                        checked={sensitiveAttrs.includes(col)}
                        onChange={() => handleToggleSensitiveAttr(col)}
                        className="w-4 h-4 accent-emerald-500"
                      />
                      <span className="ml-3 text-slate-200 text-sm">{col}</span>
                    </label>
                  ))}
              </div>

              <div className="mt-4 space-y-2">
                {['logistic_regression', 'decision_tree'].map((type) => (
                  <label key={type} className="flex items-center p-2 rounded cursor-pointer hover:bg-slate-800/50 transition">
                    <input
                      type="radio"
                      value={type}
                      checked={modelType === type}
                      onChange={(e) => setModelType(e.target.value)}
                      className="w-4 h-4 accent-emerald-500"
                    />
                    <span className="ml-3 text-slate-200 text-sm">{type === 'logistic_regression' ? 'Logistic Regression' : 'Decision Tree'}</span>
                  </label>
                ))}
              </div>

              {sensitiveAttrs.length > 0 && (
                <div className="mt-4 p-3 bg-blue-500/20 rounded-lg border border-blue-500/50 text-blue-200 text-sm">
                  <p className="font-semibold mb-2">Selected ({sensitiveAttrs.length}):</p>
                  <div className="flex flex-wrap gap-1">
                    {sensitiveAttrs.map((attr) => (
                      <Badge key={attr} color="blue" className="text-xs">{attr}</Badge>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          </motion.div>
        </div>

        {error && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-6 p-4 bg-red-500/20 border border-red-500/50 text-red-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
            <p>{error}</p>
          </motion.div>
        )}

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }} className="flex gap-4">
          <Button onClick={handleConfigure} isLoading={isLoading} className="flex-1 bg-emerald-600 hover:bg-emerald-700">
            {isLoading ? 'Configuring...' : 'Configure & Analyze'}
          </Button>
          <Button variant="secondary" onClick={() => navigate('/upload')} disabled={isLoading} className="flex-1 bg-slate-700 hover:bg-slate-600">
            Back
          </Button>
        </motion.div>
      </div>
    </div>
  )
}
