import { StrictMode, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import CivicScaleHomepage from './components/CivicScaleHomepage.jsx'
import TermsPage from './components/TermsPage.jsx'
import PrivacyPage from './components/PrivacyPage.jsx'
import InvestorsPage from './components/InvestorsPage.jsx'
import EmployerLandingPage from './components/EmployerLandingPage.jsx'
import EmployerLoginPage from './components/EmployerLoginPage.jsx'
import EmployerDashboard from './components/EmployerDashboard.jsx'
import EmployerAuthCallback from './components/EmployerAuthCallback.jsx'
import BillingLanding from './components/BillingLanding.jsx'
import EmployerProductPage from './components/EmployerProductPage.jsx'
import ProviderProductPage from './components/ProviderProductPage.jsx'
import EmployerDemoPage from './components/EmployerDemoPage.jsx'
import ProviderDemoPage from './components/ProviderDemoPage.jsx'
import ProviderApp from './ProviderApp.jsx'
import SignalApp from './SignalApp.jsx'
import AuditAccount from './components/AuditAccount.jsx'
import AuditStandalone from './components/AuditStandalone.jsx'
import PublicAuditReport from './components/PublicAuditReport.jsx'
import EmployerBenchmark from './components/EmployerBenchmark.jsx'
import EmployerClaimsCheck from './components/EmployerClaimsCheck.jsx'
import EmployerScorecard from './components/EmployerScorecard.jsx'
import EmployerSubscribe from './components/EmployerSubscribe.jsx'
import EmployerContractParser from './components/EmployerContractParser.jsx'
import EmployerRBPCalculator from './components/EmployerRBPCalculator.jsx'

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return null
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<CivicScaleHomepage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/investors" element={<InvestorsPage />} />
        <Route path="/audit/account" element={<AuditAccount />} />
        <Route path="/audit" element={<AuditStandalone />} />
        <Route path="/billing" element={<BillingLanding />} />
        <Route path="/billing/employer" element={<EmployerProductPage />} />
        <Route path="/billing/provider" element={<ProviderProductPage />} />
        <Route path="/billing/employer/benchmark" element={<EmployerBenchmark />} />
        <Route path="/billing/employer/claims-check" element={<EmployerClaimsCheck />} />
        <Route path="/billing/employer/scorecard" element={<EmployerScorecard />} />
        <Route path="/billing/employer/subscribe" element={<EmployerSubscribe />} />
        <Route path="/billing/employer/contract-parse" element={<EmployerContractParser />} />
        <Route path="/billing/employer/rbp-calculator" element={<EmployerRBPCalculator />} />
        <Route path="/billing/employer/demo" element={<EmployerDemoPage />} />
        <Route path="/billing/provider/demo" element={<ProviderDemoPage />} />
        <Route path="/employer" element={<EmployerLandingPage />} />
        <Route path="/employer/login" element={<EmployerLoginPage />} />
        <Route path="/employer/auth/callback" element={<EmployerAuthCallback />} />
        <Route path="/employer/dashboard" element={<EmployerDashboard />} />
        <Route path="/report/:token" element={<PublicAuditReport />} />
        <Route path="/provider/*" element={<ProviderApp />} />
        <Route path="/signal/*" element={<SignalApp />} />
        <Route path="/parity-health/*" element={<App />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
