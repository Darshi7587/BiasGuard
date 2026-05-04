import React from 'react'
import { FileUpload } from '../components'

export default function UploadPage() {
  return (
    <div className="min-h-screen p-8">
      <h2 className="text-2xl text-white mb-4">Upload Dataset</h2>
      <FileUpload />
    </div>
  )
}
