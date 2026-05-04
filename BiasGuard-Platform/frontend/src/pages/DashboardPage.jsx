
import React, { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Sidebar, StatCard, Card, Button, LoadingSpinner, RiskIndicator, Badge } from '../components'
import { BiasChart, PerformanceChart, BiasDistributionChart, FeatureImportanceChart } from '../components'
import { InsightsPanel } from '../components'
import { runAnalysis } from '../utils/api'
import { Download, Gauge, Target, Shield, TrendingUp, Upload, Zap } from 'lucide-react'

export default function DashboardPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const datasetId = location.state?.datasetId
  const targetColumn = location.state?.targetColumn
  const sensitiveAttrs = location.state?.sensitiveAttrs || []
  const modelType = location.state?.modelType

  const [results, setResults] = useState(null)
  const [isAnalyzing, setIsAnalyzing] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    if (datasetId) {
      performAnalysis()
    } else {
      navigate('/upload')
    }
  }, [datasetId])

  const performAnalysis = async () => {
    setIsAnalyzing(true)
    setError(null)
    try {
      const response = await runAnalysis(
        datasetId,
        targetColumn,
        sensitiveAttrs,
        modelType ? [modelType] : ['logistic_regression', 'decision_tree']
      )
      setResults(response)
    } catch (err) {
      setError(err.response?.data?.detail || 'Analysis failed')
    } finally {
      setIsAnalyzing(false)
    }
  }

  if (isAnalyzing) {
    return (
      <Sidebar>
        <div className="flex flex-col items-center justify-center py-20">
          <motion.div
            animate={{ scale: [1, 1.1, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="mb-6"
          >
            <Gauge className="w-16 h-16 text-purple-400" />
          </motion.div>
          <h2 className="text-2xl font-bold text-white mb-2">Analyzing Your Dataset</h2>
          <p className="text-slate-300 mt-2 mb-4">Running model training and fairness evaluation.</p>
          <div className="w-64 bg-slate-700 rounded-full h-3 mb-4">
            <motion.div
              className="bg-gradient-to-r from-purple-500 to-blue-500 h-3 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: '70%' }}
              transition={{ duration: 1.2, repeat: Infinity, repeatType: 'reverse' }}
            />
          </div>
          <LoadingSpinner />
        </div>
      </Sidebar>
    )
  }

  if (error) {
    return (
      <Sidebar>
        <Card className="bg-red-500/20 border border-red-500/50">
          <p className="text-red-300 mb-4">{error}</p>
          <Button onClick={() => navigate('/upload')}>Start Over</Button>
        </Card>
      </Sidebar>
    )
  }

  if (!results) {
    return <Sidebar><LoadingSpinner /></Sidebar>
  }

  const selectedModel = results.selected_model || Object.keys(results.model_performance || {})[0]
  const perf = results.model_performance?.[selectedModel] || {}
  const biasByFeature = results.bias_by_feature || {}
  const biasChartData = Object.entries(biasByFeature).map(([name, metrics]) => ({
    name,
    value: Number(((metrics?.bias_score || 0) * 100).toFixed(1)),
  }))
  const firstAttribute = Object.keys(biasByFeature)[0]
  const biasDistributionData = firstAttribute
    ? Object.fromEntries(
        Object.entries(biasByFeature[firstAttribute]?.group_metrics || {}).map(([group, info]) => [group, Number(((info?.mean_prediction_rate || 0) * 100).toFixed(1))])
      )
    : {}
  const insights = results.insights || []
  const recommendations = results.mitigation_suggestions || []
  const config = results.configuration || {}

  return (
    <Sidebar>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-2">Analysis Results</h1>
        <p className="text-slate-300">Dataset: {results.dataset_name || datasetId}</p>
      </motion.div>

      <div className="grid md:grid-cols-5 gap-4 mb-8">
        <StatCard title="Accuracy" value={perf.accuracy != null ? `${(perf.accuracy * 100).toFixed(1)}%` : 'N/A'} icon={Target} color="blue" />
        <StatCard title="Precision" value={perf.precision != null ? `${(perf.precision * 100).toFixed(1)}%` : 'N/A'} icon={TrendingUp} color="purple" />
        <StatCard title="Recall" value={perf.recall != null ? `${(perf.recall * 100).toFixed(1)}%` : 'N/A'} icon={Shield} color="green" />
        <StatCard title="F1 Score" value={perf.f1 != null ? `${(perf.f1 * 100).toFixed(1)}%` : 'N/A'} icon={Gauge} color="purple" />
        <StatCard title="Bias Score" value={results.bias_score != null ? `${(results.bias_score * 100).toFixed(1)}%` : 'N/A'} icon={Zap} color="red" trend={results.bias_score > 0.2 ? 5 : -5} />
      </div>

      <div className="mb-8">
        <h3 className="text-lg font-semibold text-white mb-4">Risk Assessment</h3>
        <RiskIndicator level={results.risk_level || 'LOW'} />
      </div>

      <div className="mb-8 flex gap-2 border-b border-slate-600">
        {['overview', 'metrics'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-6 py-3 font-semibold transition ${
              activeTab === tab
                ? 'text-cyan-400 border-b-2 border-cyan-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8 mb-8">
          <Card className="bg-slate-800 border border-blue-500/30">
            <h3 className="text-lg font-semibold text-white mb-4">📋 Column Selection Summary</h3>
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <span className="text-blue-400 font-bold">•</span>
                <div>
                  <p className="text-sm font-semibold text-white">Target Column</p>
                  <p className="text-sm text-slate-300">{config.target_column || targetColumn || 'N/A'}</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-blue-400 font-bold">•</span>
                <div>
                  <p className="text-sm font-semibold text-white">Sensitive Attributes</p>
                  <p className="text-sm text-slate-300">{(config.sensitive_attributes || sensitiveAttrs || []).join(', ') || 'N/A'}</p>
                </div>
              </div>
            </div>
          </Card>

          <div className="grid lg:grid-cols-2 gap-8">
            <Card>
              <h3 className="text-lg font-semibold text-white mb-4">Model Configuration</h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center pb-3 border-b border-slate-600">
                  <span className="text-slate-400">Selected Model</span>
                  <Badge color="purple">{selectedModel || 'Logistic Regression'}</Badge>
                </div>
                <div className="flex justify-between items-center pb-3 border-b border-slate-600">
                  <span className="text-slate-400">Train/Test Split</span>
                  <span className="text-white font-semibold">70/30</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Dataset Size</span>
                  <span className="text-white font-semibold">{results.dataset_info?.rows || 0} rows</span>
                </div>
              </div>
            </Card>

            <Card>
              <h3 className="text-lg font-semibold text-white mb-4">Sensitive Attributes</h3>
              <div className="space-y-3">
                {(config.sensitive_attributes || sensitiveAttrs || []).map((attr, idx) => (
                  <div key={idx} className="flex items-center gap-2 p-2 bg-purple-500/20 rounded">
                    <span className="text-purple-400 font-semibold">✓</span>
                    <span className="text-slate-200">{attr}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <InsightsPanel insights={insights} />

          <Card className="bg-slate-800 border border-green-500/30">
            <h3 className="text-lg font-semibold text-white mb-4">🎯 Recommendations to Improve Fairness</h3>
            <div className="space-y-2">
              {recommendations.length > 0 ? (
                recommendations.map((rec, idx) => (
                  <div key={idx} className="flex items-start gap-3 p-2">
                    <span className="text-green-400 font-bold">→</span>
                    <p className="text-sm text-slate-300">{rec}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-400 italic">No specific recommendations available.</p>
              )}
            </div>
          </Card>
        </motion.div>
      )}

      {activeTab === 'metrics' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid lg:grid-cols-2 gap-8 mb-8">
          <BiasChart data={biasChartData} title="Bias Score by Sensitive Attribute" />
          <BiasDistributionChart groupData={biasDistributionData} />
          <PerformanceChart data={Object.entries(results.model_performance || {}).map(([name, metrics]) => ({
            name,
            accuracy: metrics.accuracy || 0,
            precision: metrics.precision || 0,
            recall: metrics.recall || 0,
          }))} />
          <FeatureImportanceChart data={results.feature_importance || {}} />
        </motion.div>
      )}

      <div className="mt-12 flex gap-4 flex-wrap">
        <Button onClick={() => navigate('/upload')} className="flex items-center gap-2">
          <Upload className="w-4 h-4" /> Upload New Dataset
        </Button>
        <Button variant="secondary" className="flex items-center gap-2">
          <Download className="w-4 h-4" /> Download Report
        </Button>
      </div>
    </Sidebar>
  )
}
