/**
 * Runtime API base URL — detects staging hostnames and routes to the
 * staging backend automatically.  All other hostnames use the
 * VITE_API_URL env var (set at build time) or the production fallback.
 */
const getApiUrl = () => {
  const hostname = window.location.hostname;
  if (hostname.includes("staging")) {
    return "https://parity-poc-api-staging.onrender.com";
  }
  return import.meta.env.VITE_API_URL || "https://parity-poc-api.onrender.com";
};

export const API_BASE = getApiUrl();
