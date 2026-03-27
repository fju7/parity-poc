import { StrictMode, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
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
// AuditAccount removed — /audit/account now redirects to /provider/account
import ProviderSignupPage from './components/ProviderSignupPage.jsx'
import ProviderLoginPage from './components/ProviderLoginPage.jsx'
import ProviderAccountPage from './components/ProviderAccountPage.jsx'
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
import HealthLoginPage from './components/HealthLoginPage.jsx'
import HealthSignupPage from './components/HealthSignupPage.jsx'
import BrokerLandingPage from './components/BrokerLandingPage.jsx'
import BrokerLoginPage from './components/BrokerLoginPage.jsx'
import BrokerSignupPage from './components/BrokerSignupPage.jsx'
import BrokerDashboard from './components/BrokerDashboard.jsx'
import BrokerAccountPage from './components/BrokerAccountPage.jsx'
import CAABrokerGuide from './components/CAABrokerGuide.jsx'
import RenewalPrepReport from './components/RenewalPrepReport.jsx'
import BrokerDemoPage from './components/BrokerDemoPage.jsx'
import EmployerSharedReport from './components/EmployerSharedReport.jsx'
import BillingApp from './BillingApp.jsx'
import BillingDemoPage from './components/BillingDemoPage.jsx'
import PracticePortal from './PracticePortal.jsx'

// Build version — injected by Vite at build time
window.__PARITY_VERSION__ = {
  commit: typeof __GIT_COMMIT__ !== 'undefined' ? __GIT_COMMIT__ : 'dev',
  built: typeof __BUILD_TIME__ !== 'undefined' ? __BUILD_TIME__ : 'dev',
};
// Inject meta tag for easy inspection (view-source or document.querySelector)
(() => {
  const meta = document.createElement('meta');
  meta.name = 'parity-version';
  meta.content = `${window.__PARITY_VERSION__.commit} (${window.__PARITY_VERSION__.built})`;
  document.head.appendChild(meta);
})();

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return null
}

const hostname = window.location.hostname
const isHealthSubdomain = hostname === 'health.civicscale.ai' || hostname === 'staging-health.civicscale.ai'
const isProviderSubdomain = hostname === 'provider.civicscale.ai' || hostname === 'staging-provider.civicscale.ai'
const isBrokerSubdomain = hostname === 'broker.civicscale.ai' || hostname === 'staging-broker.civicscale.ai'
const isEmployerSubdomain = hostname === 'employer.civicscale.ai' || hostname === 'staging-employer.civicscale.ai'
const isSignalSubdomain = hostname === 'signal.civicscale.ai' || hostname === 'staging-signal.civicscale.ai'
const isBillingSubdomain = hostname === 'billing.civicscale.ai' || hostname === 'staging-billing.civicscale.ai'

// ── SEO: per-subdomain meta tags ──
const SEO_META = {
  health:   { title: "Parity Health — Understand Your Medical Bill", description: "Upload your medical bill, EOB, or denial letter. See what you should actually owe — powered by CMS benchmark data.", url: "https://health.civicscale.ai" },
  employer: { title: "Parity Employer — Independent Claims Analytics", description: "Benchmark your health plan against CMS data. Identify overpayments before renewal. No TPA required.", url: "https://employer.civicscale.ai" },
  broker:   { title: "Parity Broker — Independent Benchmarking for Benefits Brokers", description: "Give every client independent benchmark data. Generate CAA-compliant data request letters. Free for up to 10 clients.", url: "https://broker.civicscale.ai" },
  provider: { title: "Parity Provider — Contract Integrity and Denial Intelligence", description: "Audit your remittance files against contracted rates. Identify underpayments and denial patterns automatically.", url: "https://provider.civicscale.ai" },
  billing:  { title: "Parity Billing — RCM Analytics Across Your Practice Portfolio", description: "Batch 835 ingestion, payer benchmarking, and cross-practice escalation tracking for billing companies.", url: "https://billing.civicscale.ai" },
  signal:   { title: "Parity Signal — Evidence Scoring for Complex Topics", description: "AI-powered evidence scoring across health, policy, and science. Know what the evidence actually says.", url: "https://signal.civicscale.ai" },
};
const seoKey = isHealthSubdomain ? 'health' : isEmployerSubdomain ? 'employer' : isBrokerSubdomain ? 'broker' : isProviderSubdomain ? 'provider' : isBillingSubdomain ? 'billing' : isSignalSubdomain ? 'signal' : null;
if (seoKey && SEO_META[seoKey]) {
  const m = SEO_META[seoKey];
  document.title = m.title;
  const setMeta = (attr, key, val) => {
    let el = document.querySelector(`meta[${attr}="${key}"]`);
    if (!el) { el = document.createElement('meta'); el.setAttribute(attr, key); document.head.appendChild(el); }
    el.setAttribute('content', val);
  };
  setMeta('name', 'description', m.description);
  setMeta('property', 'og:title', m.title);
  setMeta('property', 'og:description', m.description);
  setMeta('property', 'og:url', m.url);
  setMeta('property', 'og:type', 'website');
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
    <BrowserRouter>
      <ScrollToTop />
      <Routes>
        {isHealthSubdomain ? (
          <>
            <Route path="/" element={<ParityHealthLandingPage />} />
            <Route path="/health/login" element={<HealthLoginPage />} />
            <Route path="/health/signup" element={<HealthSignupPage />} />
            <Route path="/*" element={<App />} />
          </>
        ) : isBrokerSubdomain ? (
          <>
            <Route path="/" element={<BrokerLandingPage />} />
            <Route path="/login" element={<BrokerLoginPage />} />
            <Route path="/signup" element={<BrokerSignupPage />} />
            <Route path="/demo" element={<BrokerDemoPage />} />
            <Route path="/dashboard" element={<BrokerDashboard />} />
            <Route path="/account" element={<BrokerAccountPage />} />
            <Route path="/caa-guide" element={<CAABrokerGuide />} />
            <Route path="/renewal-prep/:companySlug" element={<RenewalPrepReport />} />
            {/* Also support old /broker/* paths for backward compat */}
            <Route path="/broker/login" element={<Navigate to="/login" replace />} />
            <Route path="/broker/signup" element={<Navigate to="/signup" replace />} />
            <Route path="/broker/dashboard" element={<Navigate to="/dashboard" replace />} />
            <Route path="/broker/account" element={<Navigate to="/account" replace />} />
            <Route path="/broker/caa-guide" element={<Navigate to="/caa-guide" replace />} />
            <Route path="/broker/renewal-prep/:companySlug" element={<RenewalPrepReport />} />
            <Route path="/employer/shared-report/:shareToken" element={<EmployerSharedReport />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
          </>
        ) : isEmployerSubdomain ? (
          <>
            <Route path="/" element={<EmployerProductPage />} />
            <Route path="/login" element={<EmployerLoginPage />} />
            <Route path="/signup" element={<EmployerSignupPage />} />
            <Route path="/dashboard" element={<EmployerDashboard />} />
            <Route path="/account" element={<EmployerAccountPage />} />
            <Route path="/benchmark" element={<EmployerBenchmark />} />
            <Route path="/claims-check" element={<EmployerClaimsCheck />} />
            <Route path="/scorecard" element={<EmployerScorecard />} />
            <Route path="/subscribe" element={<EmployerSubscribe />} />
            <Route path="/contract-parse" element={<EmployerContractParser />} />
            <Route path="/rbp-calculator" element={<EmployerRBPCalculator />} />
            <Route path="/pharmacy" element={<EmployerPharmacy />} />
            <Route path="/demo" element={<EmployerDemoPage />} />
            <Route path="/accept-invite" element={<AcceptInvitePage />} />
            {/* Also support old /billing/employer/* paths for backward compat */}
            <Route path="/billing/employer" element={<Navigate to="/" replace />} />
            <Route path="/billing/employer/signup" element={<Navigate to="/signup" replace />} />
            <Route path="/billing/employer/login" element={<Navigate to="/login" replace />} />
            <Route path="/billing/employer/dashboard" element={<Navigate to="/dashboard" replace />} />
            <Route path="/billing/employer/account" element={<Navigate to="/account" replace />} />
            <Route path="/billing/employer/benchmark" element={<Navigate to="/benchmark" replace />} />
            <Route path="/billing/employer/claims-check" element={<Navigate to="/claims-check" replace />} />
            <Route path="/billing/employer/scorecard" element={<Navigate to="/scorecard" replace />} />
            <Route path="/billing/employer/subscribe" element={<Navigate to="/subscribe" replace />} />
            <Route path="/billing/employer/contract-parse" element={<Navigate to="/contract-parse" replace />} />
            <Route path="/billing/employer/rbp-calculator" element={<Navigate to="/rbp-calculator" replace />} />
            <Route path="/billing/employer/pharmacy" element={<Navigate to="/pharmacy" replace />} />
            <Route path="/billing/employer/demo" element={<Navigate to="/demo" replace />} />
            <Route path="/employer/login" element={<Navigate to="/login" replace />} />
            <Route path="/employer/shared-report/:shareToken" element={<EmployerSharedReport />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
          </>
        ) : isSignalSubdomain ? (
          <>
            <Route path="/*" element={<SignalApp />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
            {/* Also support old /signal/* paths for backward compat */}
            <Route path="/signal/*" element={<Navigate to="/" replace />} />
          </>
        ) : isBillingSubdomain ? (
          <>
            <Route path="/" element={<BillingApp />} />
            <Route path="/login" element={<BillingApp />} />
            <Route path="/dashboard" element={<BillingApp />} />
            <Route path="/portal" element={<PracticePortal />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
          </>
        ) : isProviderSubdomain ? (
          <>
            <Route path="/" element={<ProviderProductPage />} />
            <Route path="/login" element={<ProviderLoginPage />} />
            <Route path="/signup" element={<ProviderSignupPage />} />
            <Route path="/account" element={<ProviderAccountPage />} />
            <Route path="/dashboard" element={<ProviderApp />} />
            <Route path="/audit" element={<AuditStandalone />} />
            <Route path="/demo" element={<ProviderDemoPage />} />
            <Route path="/report/:token" element={<PublicAuditReport />} />
            <Route path="/accept-invite" element={<AcceptInvitePage />} />
            {/* Backward compat: /provider/* → clean paths */}
            <Route path="/provider/login" element={<Navigate to="/login" replace />} />
            <Route path="/provider/signup" element={<Navigate to="/signup" replace />} />
            <Route path="/provider/account" element={<Navigate to="/account" replace />} />
            <Route path="/provider/dashboard" element={<Navigate to="/dashboard" replace />} />
            <Route path="/provider/demo" element={<Navigate to="/demo" replace />} />
            <Route path="/audit/account" element={<Navigate to="/account" replace />} />
            <Route path="/billing/provider" element={<Navigate to="/" replace />} />
            <Route path="/billing/provider/demo" element={<Navigate to="/demo" replace />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
          </>
        ) : (
          <>
        <Route path="/" element={<CivicScaleHomepage />} />
        {/* Provider demo must be public — listed before /provider/* catch-all */}
        <Route path="/provider/demo" element={<ProviderDemoPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/investors" element={<InvestorsPage />} />
        <Route path="/audit/account" element={<Navigate to="/provider/account" replace />} />
        <Route path="/provider" element={<ProviderProductPage />} />
        <Route path="/provider/signup" element={<ProviderSignupPage />} />
        <Route path="/provider/login" element={<ProviderLoginPage />} />
        <Route path="/provider/account" element={<ProviderAccountPage />} />
        <Route path="/audit" element={<AuditStandalone />} />
        <Route path="/billing" element={<BillingLanding />} />
        <Route path="/billing/demo" element={<BillingDemoPage />} />
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
        <Route path="/parity-health/login" element={<HealthLoginPage />} />
        <Route path="/parity-health/signup" element={<HealthSignupPage />} />
        <Route path="/parity-health/*" element={<App />} />
          </>
        )}
      </Routes>
    </BrowserRouter>
    </AuthProvider>
  </StrictMode>,
)
