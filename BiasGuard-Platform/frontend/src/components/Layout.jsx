import React from 'react'
import { Sidebar } from './UI.jsx'

export default function Layout({ children }) {
  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <Sidebar>
        <div className="min-h-screen bg-slate-900 px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </div>
      </Sidebar>
    </div>
  )
}
