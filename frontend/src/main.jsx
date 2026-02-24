import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import CivicScaleHomepage from './components/CivicScaleHomepage.jsx'
import TermsPage from './components/TermsPage.jsx'
import PrivacyPage from './components/PrivacyPage.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<CivicScaleHomepage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/parity-health/*" element={<App />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
