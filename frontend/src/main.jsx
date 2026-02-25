import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import CivicScaleHomepage from './components/CivicScaleHomepage.jsx'
import TermsPage from './components/TermsPage.jsx'
import PrivacyPage from './components/PrivacyPage.jsx'
import InvestorsPage from './components/InvestorsPage.jsx'
import EmployerLandingPage from './components/EmployerLandingPage.jsx'
import EmployerLoginPage from './components/EmployerLoginPage.jsx'
import EmployerDashboard from './components/EmployerDashboard.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<CivicScaleHomepage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/investors" element={<InvestorsPage />} />
        <Route path="/employer" element={<EmployerLandingPage />} />
        <Route path="/employer/login" element={<EmployerLoginPage />} />
        <Route path="/employer/dashboard" element={<EmployerDashboard />} />
        <Route path="/parity-health/*" element={<App />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
