import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './styles/index.css'

// Suppress browser extension errors (MetaMask, etc)
window.addEventListener('error', (event) => {
  if (event.message && event.message.includes('chrome-extension://')) {
    event.preventDefault()
  }
}, true)

// Also suppress uncaught promise rejections from extensions
window.addEventListener('unhandledrejection', (event) => {
  if (event.reason?.message?.includes('extension') || event.reason?.message?.includes('MetaMask')) {
    event.preventDefault()
  }
}, true)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
