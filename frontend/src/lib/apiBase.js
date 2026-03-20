/**
 * Runtime API base URL — purely hostname-based, no build-time env vars.
 *
 * Routing rules:
 *   localhost            → http://localhost:8000  (local dev)
 *   staging-*.civicscale → staging backend
 *   Vercel preview URLs  → staging backend (for pre-production testing)
 *   everything else      → production backend
 */
const getApiUrl = () => {
  const hostname = window.location.hostname;
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "http://localhost:8000";
  }
  if (hostname.startsWith("staging-") || hostname === "staging.civicscale.ai") {
    return "https://parity-poc-api-staging.onrender.com";
  }
  // Vercel preview deployments (e.g. parity-poc-xxxx.vercel.app) should
  // hit the staging backend so new features can be tested before promotion.
  if (hostname.endsWith(".vercel.app")) {
    return "https://parity-poc-api-staging.onrender.com";
  }
  return "https://parity-poc-api.onrender.com";
};

export const API_BASE = getApiUrl();
