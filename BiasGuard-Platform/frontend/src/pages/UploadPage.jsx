import React from 'react'
import { useNavigate } from 'react-router-dom'
import { FileUpload } from '../components'

export default function UploadPage() {
  const navigate = useNavigate()

  const handleUploadSuccess = (response) => {
    navigate('/configure', {
      state: {
        dataset: {
          dataset_id: response.dataset_id,
          filename: response.filename,
          rows: response.rows,
          columns: response.columns,
          column_names: response.column_names,
          suggested_target: response.suggested_target,
          suggested_sensitive_attrs: response.suggested_sensitive_attrs,
        },
      },
    })
  }

  return (
    <div className="min-h-screen p-8">
      <h2 className="text-2xl text-white mb-4">Upload Dataset</h2>
      <FileUpload onSuccess={handleUploadSuccess} />
    </div>
  )
}
