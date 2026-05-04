
import axios from 'axios'

const api = axios.create({ baseURL: '/api', headers: { 'Content-Type': 'application/json' } })

export const uploadDataset = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  const resp = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return resp.data
}

export const getDatasetInfo = async (datasetId) => {
  const resp = await api.get(`/datasets/${datasetId}`)
  return resp.data
}

export const configureAnalysis = async (datasetId, targetColumn, sensitiveAttributes, modelTypes = ['logistic_regression', 'decision_tree']) => {
  const resp = await api.post('/configure', {
    dataset_id: datasetId,
    target_column: targetColumn,
    sensitive_attributes: sensitiveAttributes,
    model_types: modelTypes,
  })
  return resp.data
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
  const resp = await api.post('/analyze', body)
  return resp.data
}

export const getResults = async (datasetId) => {
  const resp = await api.get(`/results/${datasetId}`)
  return resp.data
}

export default {
  uploadDataset,
  getDatasetInfo,
  configureAnalysis,
  listDatasets,
  runAnalysis,
  getResults,
}
