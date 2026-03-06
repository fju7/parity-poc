const SITE_URL = import.meta.env.VITE_SITE_URL || "https://civicscale.ai";

export function getRedirectOrigin() {
  if (typeof window !== "undefined" && window.location.hostname === "localhost") {
    return window.location.origin;
  }
  return SITE_URL;
}
