import { StrictMode, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import { AuthProvider } from './context/AuthContext'
import CivicScaleHomepage from './components/CivicScaleHomepage.jsx'
import TermsPage from './components/TermsPage.jsx'
import PrivacyPage from './components/PrivacyPage.jsx'
import InvestorsPage from './components/InvestorsPage.jsx'
import EmployerLandingPage from './components/EmployerLandingPage.jsx'
import EmployerLoginPage from './components/EmployerLoginPage.jsx'
import EmployerDashboard from './components/EmployerDashboard.jsx'
import EmployerAuthCallback from './components/EmployerAuthCallback.jsx'
import EmployerSignupPage from './components/EmployerSignupPage.jsx'
import EmployerAccountPage from './components/EmployerAccountPage.jsx'
import AcceptInvitePage from './components/AcceptInvitePage.jsx'
import BillingLanding from './components/BillingLanding.jsx'
import EmployerProductPage from './components/EmployerProductPage.jsx'
import ProviderProductPage from './components/ProviderProductPage.jsx'
import EmployerDemoPage from './components/EmployerDemoPage.jsx'
import ProviderDemoPage from './components/ProviderDemoPage.jsx'
import ProviderApp from './ProviderApp.jsx'
import SignalApp from './SignalApp.jsx'
import AuditAccount from './components/AuditAccount.jsx'
import ProviderSignupPage from './components/ProviderSignupPage.jsx'
import ProviderLoginPage from './components/ProviderLoginPage.jsx'
import AuditStandalone from './components/AuditStandalone.jsx'
import PublicAuditReport from './components/PublicAuditReport.jsx'
import EmployerBenchmark from './components/EmployerBenchmark.jsx'
import EmployerClaimsCheck from './components/EmployerClaimsCheck.jsx'
import EmployerScorecard from './components/EmployerScorecard.jsx'
import EmployerSubscribe from './components/EmployerSubscribe.jsx'
import EmployerContractParser from './components/EmployerContractParser.jsx'
import EmployerRBPCalculator from './components/EmployerRBPCalculator.jsx'
import EmployerPharmacy from './components/EmployerPharmacy.jsx'
import ParityHealthLandingPage from './components/ParityHealthLandingPage.jsx'
import BrokerLandingPage from './components/BrokerLandingPage.jsx'
import BrokerLoginPage from './components/BrokerLoginPage.jsx'
import BrokerSignupPage from './components/BrokerSignupPage.jsx'
import BrokerDashboard from './components/BrokerDashboard.jsx'
import BrokerAccountPage from './components/BrokerAccountPage.jsx'
import CAABrokerGuide from './components/CAABrokerGuide.jsx'
import RenewalPrepReport from './components/RenewalPrepReport.jsx'
import EmployerSharedReport from './components/EmployerSharedReport.jsx'

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return null
}

const hostname = window.location.hostname
const isHealthSubdomain = hostname === 'health.civicscale.ai'
const isProviderSubdomain = hostname === 'provider.civicscale.ai'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
    <BrowserRouter>
      <ScrollToTop />
      <Routes>
        {isHealthSubdomain ? (
          <>
            <Route path="/" element={<ParityHealthLandingPage />} />
            <Route path="/*" element={<App />} />
          </>
        ) : (
          <>
        <Route path="/" element={isProviderSubdomain ? <ProviderProductPage /> : <CivicScaleHomepage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/investors" element={<InvestorsPage />} />
        <Route path="/audit/account" element={<AuditAccount />} />
        <Route path="/provider/signup" element={<ProviderSignupPage />} />
        <Route path="/provider/login" element={<ProviderLoginPage />} />
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
        <Route path="/billing/employer/pharmacy" element={<EmployerPharmacy />} />
        <Route path="/billing/employer/demo" element={<EmployerDemoPage />} />
        <Route path="/billing/provider/demo" element={<ProviderDemoPage />} />
        <Route path="/billing/employer/signup" element={<EmployerSignupPage />} />
        <Route path="/billing/employer/dashboard" element={<EmployerDashboard />} />
        <Route path="/billing/employer/account" element={<EmployerAccountPage />} />
        <Route path="/accept-invite" element={<AcceptInvitePage />} />
        <Route path="/employer" element={<EmployerLandingPage />} />
        <Route path="/employer/login" element={<EmployerLoginPage />} />
        <Route path="/employer/auth/callback" element={<EmployerAuthCallback />} />
        <Route path="/employer/dashboard" element={<EmployerDashboard />} />
        <Route path="/broker" element={<BrokerLandingPage />} />
        <Route path="/broker/login" element={<BrokerLoginPage />} />
        <Route path="/broker/signup" element={<BrokerSignupPage />} />
        <Route path="/broker/dashboard" element={<BrokerDashboard />} />
        <Route path="/broker/account" element={<BrokerAccountPage />} />
        <Route path="/broker/caa-guide" element={<CAABrokerGuide />} />
        <Route path="/broker/renewal-prep/:companySlug" element={<RenewalPrepReport />} />
        <Route path="/employer/shared-report/:shareToken" element={<EmployerSharedReport />} />
        <Route path="/report/:token" element={<PublicAuditReport />} />
        <Route path="/provider/*" element={<ProviderApp />} />
        <Route path="/signal/*" element={<SignalApp />} />
        <Route path="/parity-health" element={<ParityHealthLandingPage />} />
        <Route path="/parity-health/*" element={<App />} />
          </>
        )}
      </Routes>
    </BrowserRouter>
    </AuthProvider>
  </StrictMode>,
)
