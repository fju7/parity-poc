import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import CivicScaleHomepage from './components/CivicScaleHomepage.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<CivicScaleHomepage />} />
        <Route path="/parity-health/*" element={<App />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
