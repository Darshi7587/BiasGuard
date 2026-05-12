
import React, { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Sidebar, StatCard, Card, Button, LoadingSpinner, RiskIndicator, Badge } from '../components'
import { BiasChart, PerformanceChart, BiasDistributionChart, FeatureImportanceChart, BeforeAfterComparison } from '../components'
import { InsightsPanel } from '../components'
import { runAnalysis, evaluateMitigation } from '../utils/api'
import { Download, Gauge, Target, Shield, TrendingUp, Upload, Zap, AlertTriangle, CheckCircle } from 'lucide-react'

export default function DashboardPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const datasetId = location.state?.datasetId
  const targetColumn = location.state?.targetColumn
  const sensitiveAttrs = location.state?.sensitiveAttrs || []
  const modelType = location.state?.modelType

  const [results, setResults] = useState(null)
  const [mitigationResults, setMitigationResults] = useState(null)
  const [isAnalyzing, setIsAnalyzing] = useState(true)
  const [isMitigating, setIsMitigating] = useState(false)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    if (datasetId) {
      performAnalysis()
    } else {
      navigate('/upload')
    }
  }, [datasetId])

  useEffect(() => {
    if (results) {
      fetchMitigation()
    }
  }, [results])

  const fetchMitigation = async () => {
    if (!datasetId || !results) return

    const config = results.configuration || {}
    setIsMitigating(true)
    try {
      const response = await evaluateMitigation(
        datasetId,
        config.target_column,
        config.sensitive_attributes,
        config.model_types
      )
      setMitigationResults(response)
    } catch (err) {
      console.warn('Mitigation evaluation failed', err)
    } finally {
      setIsMitigating(false)
    }
  }

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
      console.log('API Response:', response)
      setResults(response)
    } catch (err) {
      console.log('Analysis error:', err)
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
        <Card className="bg-red-50 border border-red-200">
          <p className="text-red-700 mb-4">{error}</p>
          <Button onClick={() => navigate('/upload')}>Start Over</Button>
        </Card>
      </Sidebar>
    )
  }

  if (!results) {
    return <Sidebar><LoadingSpinner /></Sidebar>
  }

  // Safe data extraction with fallbacks
  const selectedModel = results?.selected_model || Object.keys(results?.model_performance || {})[0] || 'logistic_regression'
  const perf = results?.model_performance?.[selectedModel] || results?.metrics || {}
  const biasByFeature = results?.bias_by_feature || {}
  const biasChartData = Object.entries(biasByFeature).length > 0 
    ? Object.entries(biasByFeature).map(([name, metrics]) => ({
        name: String(name).substring(0, 20),
        value: Number(((metrics?.bias_score || 0) * 100).toFixed(1)),
      }))
    : []
  
  const firstAttribute = Object.keys(biasByFeature)[0]
  const biasDistributionData = firstAttribute
    ? Object.fromEntries(
        Object.entries(biasByFeature[firstAttribute]?.group_metrics || {}).map(([group, info]) => [
          String(group).substring(0, 15),
          Number(((info?.mean_prediction_rate || 0) * 100).toFixed(1))
        ])
      )
    : {}
  
  const insights = Array.isArray(results?.insights) ? results.insights : []
  const recommendations = Array.isArray(results?.mitigation_suggestions) ? results.mitigation_suggestions : []
  const config = results?.configuration || {}
  const decision = results?.decision || {}
  const bestMitigation = mitigationResults?.best_strategy || mitigationResults?.strategies?.[0] || null
  const mitigationLoading = isMitigating && !bestMitigation
  
  // Debug logging
  console.log('Dashboard Data:', { results, decision, perf, biasByFeature, biasChartData })

  return (
    <Sidebar>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Analysis Results</h1>
        <p className="text-gray-600">Dataset: {results.dataset_name || datasetId}</p>
      </motion.div>

      {/* Critical Warnings */}
      {perf.accuracy && perf.accuracy < 0.5 && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <Card className="bg-red-50 border-l-4 border-red-600">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-red-900">⚠️ Critical: Model Accuracy Too Low</h3>
                <p className="text-sm text-red-800 mt-1">
                  Accuracy is {(perf.accuracy * 100).toFixed(1)}%, which is below 50%. 
                  Fairness metrics are unreliable with such low model performance. 
                  Consider retraining with better features or more data.
                </p>
              </div>
            </div>
          </Card>
        </motion.div>
      )}

      {perf.accuracy && perf.accuracy < 0.65 && perf.accuracy >= 0.5 && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <Card className="bg-yellow-50 border-l-4 border-yellow-600">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-yellow-900">⚠️ Warning: Below-Average Model Performance</h3>
                <p className="text-sm text-yellow-800 mt-1">
                  Accuracy is {(perf.accuracy * 100).toFixed(1)}%. While the model has predictive power, 
                  fairness metrics should be interpreted cautiously. Focus on model improvement before fairness optimization.
                </p>
              </div>
            </div>
          </Card>
        </motion.div>
      )}

      <div className="grid md:grid-cols-5 gap-4 mb-8">
        <StatCard title="Accuracy" value={perf.accuracy != null ? `${(perf.accuracy * 100).toFixed(1)}%` : 'N/A'} icon={Target} color="blue" />
        <StatCard title="Precision" value={perf.precision != null ? `${(perf.precision * 100).toFixed(1)}%` : 'N/A'} icon={TrendingUp} color="purple" />
        <StatCard title="Recall" value={perf.recall != null ? `${(perf.recall * 100).toFixed(1)}%` : 'N/A'} icon={Shield} color="green" />
        <StatCard title="F1 Score" value={perf.f1 != null ? `${(perf.f1 * 100).toFixed(1)}%` : 'N/A'} icon={Gauge} color="purple" />
        <StatCard title="Bias Score" value={results.bias_score != null ? `${(results.bias_score * 100).toFixed(1)}%` : 'N/A'} icon={Zap} color="red" trend={results.bias_score > 0.2 ? 5 : -5} />
      </div>

      <div className="mb-8">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Risk Assessment</h3>
        <RiskIndicator level={results.risk_level || 'LOW'} />
      </div>

      {/* Intelligent Decision Panel */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <Card className={`${
          decision.model_reliability === 'Low' ? 'bg-red-50 border border-red-200' :
          decision.model_reliability === 'Medium' ? 'bg-yellow-50 border border-yellow-200' :
          'bg-green-50 border border-green-200'
        }`}>
          <div className="flex items-start gap-4 mb-4">
            {decision.model_reliability === 'Low' && <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0 mt-1" />}
            {decision.model_reliability === 'Medium' && <AlertTriangle className="w-6 h-6 text-yellow-600 flex-shrink-0 mt-1" />}
            {decision.model_reliability === 'High' && <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />}
            <div className="flex-grow">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Fairness Decision Intelligence</h3>
              <p className="text-sm text-gray-700 mb-4">{results.fairness_reasoning || 'Analyzing model fairness and reliability...'}</p>
              
              <div className="grid md:grid-cols-2 gap-4 mt-4">
                <div className="bg-white bg-opacity-60 p-3 rounded border border-gray-200">
                  <p className="text-xs font-semibold text-gray-600 mb-1">Bias Level</p>
                  <p className="text-lg font-bold text-gray-900">{decision.bias_level || 'Not Available'}</p>
                </div>
                <div className="bg-white bg-opacity-60 p-3 rounded border border-gray-200">
                  <p className="text-xs font-semibold text-gray-600 mb-1">Model Reliability</p>
                  <p className="text-lg font-bold text-gray-900">{decision.model_reliability || 'Not Available'}</p>
                </div>
                <div className="bg-white bg-opacity-60 p-3 rounded border border-gray-200">
                  <p className="text-xs font-semibold text-gray-600 mb-1">Mitigation Recommended</p>
                  <p className="text-lg font-bold text-gray-900">{decision.mitigation || 'Not Available'}</p>
                </div>
                <div className="bg-white bg-opacity-60 p-3 rounded border border-gray-200">
                  <p className="text-xs font-semibold text-gray-600 mb-1">Confidence Score</p>
                  <p className="text-lg font-bold text-gray-900">{decision.confidence || 'Not Available'}</p>
                </div>
              </div>

              {results.warning_flags && results.warning_flags.length > 0 && (
                <div className="mt-4 p-3 bg-white bg-opacity-60 rounded border-l-4 border-orange-500">
                  <p className="text-xs font-semibold text-gray-600 mb-2">⚠️ Warnings</p>
                  <ul className="space-y-1">
                    {results.warning_flags.map((warning, idx) => (
                      <li key={idx} className="text-sm text-gray-700">• {warning}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </Card>
      </motion.div>

      <div className="mb-8 flex gap-2 border-b border-gray-200">
        {['overview', 'metrics', 'charts'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-6 py-3 font-semibold transition ${
              activeTab === tab
                ? 'text-purple-600 border-b-2 border-purple-600'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            {tab === 'overview' ? '📋 Overview' : tab === 'metrics' ? '📊 Metrics' : '📈 Charts'}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8 mb-8">
          <Card className="bg-blue-50 border border-blue-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">📋 Column Selection Summary</h3>
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <span className="text-blue-600 font-bold">•</span>
                <div>
                  <p className="text-sm font-semibold text-gray-900">Target Column</p>
                  <p className="text-sm text-gray-700">{config.target_column || targetColumn || 'N/A'}</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-blue-600 font-bold">•</span>
                <div>
                  <p className="text-sm font-semibold text-gray-900">Sensitive Attributes</p>
                  <p className="text-sm text-gray-700">{(config.sensitive_attributes || sensitiveAttrs || []).join(', ') || 'N/A'}</p>
                </div>
              </div>
            </div>
          </Card>

          <div className="grid lg:grid-cols-2 gap-8">
            <Card>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Model Configuration</h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center pb-3 border-b">
                  <span className="text-gray-600">Selected Model</span>
                  <Badge color="purple">{selectedModel || 'Logistic Regression'}</Badge>
                </div>
                <div className="flex justify-between items-center pb-3 border-b">
                  <span className="text-gray-600">Train/Test Split</span>
                  <span className="text-gray-900 font-semibold">70/30</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Dataset Size</span>
                  <span className="text-gray-900 font-semibold">{results.dataset_info?.rows || 0} rows</span>
                </div>
              </div>
            </Card>

            <Card>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Sensitive Attributes</h3>
              <div className="space-y-3">
                {(config.sensitive_attributes || sensitiveAttrs || []).map((attr, idx) => (
                  <div key={idx} className="flex items-center gap-2 p-2 bg-purple-50 rounded">
                    <span className="text-purple-600 font-semibold">✓</span>
                    <span className="text-gray-700">{attr}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <InsightsPanel insights={insights} />

          {bestMitigation && (
            <Card className="bg-slate-900/90 border border-slate-700 text-white">
              <div className="mb-4">
                <h3 className="text-lg font-semibold text-white">Best Mitigation Strategy</h3>
                <p className="text-sm text-slate-300 mt-1">{bestMitigation.strategy.replace('_', ' ').toUpperCase()}</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg bg-slate-800 p-3 border border-slate-700">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Accuracy Change</p>
                  <p className="text-lg font-semibold text-white">
                    {bestMitigation.accuracy_after != null ? `${(bestMitigation.accuracy_after * 100).toFixed(1)}%` : 'N/A'}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-800 p-3 border border-slate-700">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Bias After</p>
                  <p className="text-lg font-semibold text-white">
                    {bestMitigation.bias_after != null ? `${(bestMitigation.bias_after * 100).toFixed(1)}%` : 'N/A'}
                  </p>
                </div>
              </div>
              <p className="mt-4 text-sm text-slate-300">{bestMitigation.recommendation}</p>
            </Card>
          )}

          <Card className="bg-green-50 border border-green-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🎯 Recommendations to Improve Fairness</h3>
            <div className="space-y-2">
              {recommendations.length > 0 ? (
                recommendations.map((rec, idx) => (
                  <div key={idx} className="flex items-start gap-3 p-2">
                    <span className="text-green-600 font-bold">→</span>
                    <p className="text-sm text-gray-700">{rec}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-600 italic">No specific recommendations available.</p>
              )}
            </div>
          </Card>
        </motion.div>
      )}

      {activeTab === 'metrics' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8 mb-8">
          <div className="grid lg:grid-cols-2 gap-8">
            {biasChartData.length > 0 ? (
              <BiasChart data={biasChartData} title="📊 Bias Score by Sensitive Attribute" />
            ) : (
              <Card className="h-96 flex items-center justify-center">
                <p className="text-gray-500">No bias data available for visualization</p>
              </Card>
            )}
            
            {Object.keys(biasDistributionData).length > 0 ? (
              <BiasDistributionChart groupData={biasDistributionData} />
            ) : (
              <Card className="h-96 flex items-center justify-center">
                <p className="text-gray-500">No group prediction data available</p>
              </Card>
            )}
          </div>

          <div className="grid lg:grid-cols-2 gap-8">
            <PerformanceChart data={Object.entries(results?.model_performance || {}).map(([name, metrics]) => ({
              name: String(name).substring(0, 15),
              accuracy: metrics?.accuracy || 0,
              precision: metrics?.precision || 0,
              recall: metrics?.recall || 0,
            }))} />
            
            <FeatureImportanceChart data={results?.feature_importance || results?.importances || {}} />
          </div>

          {bestMitigation ? (
            <BeforeAfterComparison before={{
              bias_score: bestMitigation.bias_before,
              accuracy: bestMitigation.accuracy_before,
            }} after={{
              bias_score: bestMitigation.bias_after,
              accuracy: bestMitigation.accuracy_after,
            }} />
          ) : mitigationLoading ? (
            <Card className="h-96 flex items-center justify-center">
              <div className="text-center">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="mb-4 inline-block"
                >
                  <Gauge className="w-8 h-8 text-gray-400" />
                </motion.div>
                <p className="text-gray-500">Evaluating mitigation strategies...</p>
              </div>
            </Card>
          ) : (
            <Card className="h-96 flex items-center justify-center bg-blue-50 border border-blue-200">
              <p className="text-gray-600">Mitigation comparison will appear after evaluation.</p>
            </Card>
          )}
        </motion.div>
      )}

      {activeTab === 'charts' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8 mb-8">
          <div className="grid lg:grid-cols-2 gap-8">
            {biasChartData.length > 0 && <BiasChart data={biasChartData} title="📊 Bias Score by Sensitive Attribute" />}
            {Object.keys(biasDistributionData).length > 0 && <BiasDistributionChart groupData={biasDistributionData} />}
          </div>

          <div className="grid lg:grid-cols-2 gap-8">
            <PerformanceChart data={Object.entries(results?.model_performance || {}).map(([name, metrics]) => ({
              name: String(name).substring(0, 15),
              accuracy: metrics?.accuracy || 0,
              precision: metrics?.precision || 0,
              recall: metrics?.recall || 0,
            }))} />
            <FeatureImportanceChart data={results?.feature_importance || results?.importances || {}} />
          </div>

          {bestMitigation && <BeforeAfterComparison before={{ bias_score: bestMitigation.bias_before, accuracy: bestMitigation.accuracy_before }} after={{ bias_score: bestMitigation.bias_after, accuracy: bestMitigation.accuracy_after }} />}
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
