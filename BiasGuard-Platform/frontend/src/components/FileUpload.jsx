import React, { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Upload, File, CheckCircle } from 'lucide-react'
import { Card, Button, LoadingSpinner } from './UI'
import { uploadDataset } from '../utils/api'

const MAX_FILE_SIZE = 50 * 1024 * 1024

export default function FileUpload({ onSuccess }) {
  const [isDragging, setIsDragging] = useState(false)
  const [file, setFile] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    const droppedFile = e.dataTransfer.files[0]
    if (!droppedFile) {
      return
    }

    if (droppedFile.size > MAX_FILE_SIZE) {
      setError('File must be 50 MB or smaller')
      setFile(null)
      return
    }

    if (droppedFile.name.endsWith('.csv') || droppedFile.name.endsWith('.xlsx') || droppedFile.name.endsWith('.xls')) {
      setFile(droppedFile)
      setError(null)
    } else {
      setError('Only CSV and Excel files are supported')
      setFile(null)
    }
  }

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files?.[0]
    if (!selectedFile) {
      return
    }

    if (selectedFile.size > MAX_FILE_SIZE) {
      setError('File must be 50 MB or smaller')
      setFile(null)
      return
    }

    if (selectedFile.name.endsWith('.csv') || selectedFile.name.endsWith('.xlsx') || selectedFile.name.endsWith('.xls')) {
      setFile(selectedFile)
      setError(null)
    } else {
      setError('Only CSV and Excel files are supported')
      setFile(null)
    }
  }

  const handleUpload = async () => {
    if (!file) return

    if (file.size > MAX_FILE_SIZE) {
      setError('File must be 50 MB or smaller')
      return
    }

    setIsLoading(true)
    try {
      const response = await uploadDataset(file)
      onSuccess(response)
      setFile(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="max-w-2xl mx-auto"
    >
      <Card>
        <motion.div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          animate={isDragging ? { scale: 1.02 } : { scale: 1 }}
          className={`border-2 border-dashed rounded-lg p-12 text-center transition ${
            isDragging ? 'border-purple-500 bg-purple-500/20' : 'border-slate-600'
          }`}
        >
          {file ? (
            <div className="flex flex-col items-center">
              <CheckCircle className="w-12 h-12 text-emerald-400 mb-4" />
              <p className="font-semibold text-white">{file.name}</p>
              <p className="text-sm text-slate-400 mt-1">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
          ) : (
            <div>
              <Upload className="w-12 h-12 text-purple-400 mx-auto mb-4" />
              <p className="text-lg font-semibold text-white mb-2">
                Drag and drop your dataset here
              </p>
              <p className="text-slate-400 mb-4">or</p>
              <label>
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <span className="btn-secondary cursor-pointer">Browse Files</span>
              </label>
              <p className="text-xs text-slate-500 mt-4">Supported formats: CSV, Excel</p>
            </div>
          )}
        </motion.div>

        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-4 p-3 bg-red-500/20 text-red-300 rounded-lg text-sm border border-red-500/30"
          >
            {error}
          </motion.div>
        )}

        {file && (
          <motion.div className="mt-6 flex gap-3">
            <Button
              onClick={handleUpload}
              isLoading={isLoading}
              className="flex-1"
            >
              {isLoading ? 'Uploading...' : 'Upload Dataset'}
            </Button>
            <Button
              variant="secondary"
              onClick={() => setFile(null)}
              disabled={isLoading}
              className="flex-1"
            >
              Cancel
            </Button>
          </motion.div>
        )}
      </Card>
    </motion.div>
  )
}
