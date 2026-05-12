
import axios from 'axios'

const api = axios.create({ baseURL: '/api', headers: { 'Content-Type': 'application/json' } })

const encodeDatasetId = (datasetId) => encodeURIComponent(datasetId)

const isNotFoundError = (error) => error?.response?.status === 404

export const uploadDataset = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  const resp = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return resp.data
}

export const getDatasetInfo = async (datasetId) => {
  const encodedDatasetId = encodeDatasetId(datasetId)

  try {
    const resp = await api.get(`/datasets/${encodedDatasetId}`)
    return resp.data
  } catch (error) {
    if (!isNotFoundError(error)) {
      throw error
    }
  }

  try {
    const resp = await api.get(`/dataset-info/${encodedDatasetId}`)
    return resp.data
  } catch (error) {
    if (!isNotFoundError(error)) {
      throw error
    }
  }

  const resp = await api.get(`/dataset/${encodedDatasetId}`)
  return resp.data
}

export const configureAnalysis = async (datasetId, targetColumn, sensitiveAttributes, modelTypes = ['logistic_regression', 'decision_tree']) => {
  const payload = {
    dataset_id: datasetId,
    target_column: targetColumn,
    sensitive_attributes: sensitiveAttributes,
    model_types: modelTypes,
  }

  try {
    const resp = await api.post('/configure', payload)
    return resp.data
  } catch (error) {
    if (!isNotFoundError(error)) {
      throw error
    }
  }

  const legacyResp = await api.post('/configure-uploaded', {
    dataset_id: datasetId,
    target_column: targetColumn,
    sensitive_attributes: sensitiveAttributes,
    model_type: modelTypes?.[0] || 'logistic_regression',
  })
  return legacyResp.data
}

export const listDatasets = async () => {
  const resp = await api.get('/datasets')
  return resp.data
}

export const runAnalysis = async (datasetId, targetColumn = null, sensitiveAttributes = [], modelTypes = ['logistic_regression', 'decision_tree']) => {
  const body = {
    dataset_id: datasetId,
    target_column: targetColumn,
    sensitive_attributes: sensitiveAttributes,
    model_types: modelTypes,
  }

  try {
    const resp = await api.post('/analyze', body)
    return resp.data
  } catch (error) {
    if (!isNotFoundError(error)) {
      throw error
    }
  }

  const params = new URLSearchParams()
  params.set('dataset_id', datasetId)
  if (targetColumn) {
    params.set('target_column', targetColumn)
  }
  if (sensitiveAttributes?.length) {
    params.set('sensitive_attributes', sensitiveAttributes.join(','))
  }

  const legacyResp = await api.post(`/analyze?${params.toString()}`)
  return legacyResp.data
}

export const evaluateMitigation = async (datasetId, targetColumn = null, sensitiveAttributes = [], modelTypes = ['logistic_regression', 'decision_tree']) => {
  const body = {
    dataset_id: datasetId,
    target_column: targetColumn,
    sensitive_attributes: sensitiveAttributes,
    model_types: modelTypes,
  }

  try {
    const resp = await api.post('/mitigation', body)
    return resp.data
  } catch (error) {
    throw error
  }
}

export const getResults = async (datasetId) => {
  const encodedDatasetId = encodeDatasetId(datasetId)
  const resp = await api.get(`/results/${encodedDatasetId}`)
  return resp.data
}

export default {
  uploadDataset,
  getDatasetInfo,
  configureAnalysis,
  listDatasets,
  runAnalysis,
  evaluateMitigation,
  getResults,
}
