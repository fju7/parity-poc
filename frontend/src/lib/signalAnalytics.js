import { API_BASE } from "./apiBase";
/**
 * Parity Signal — lightweight event capture.
 *
 * Uses navigator.sendBeacon for mobile reliability (survives tab
 * switches and background transitions). Falls back to fetch.
 *
 * No PII — uses an anonymous UUID stored in localStorage.
 */

const ENDPOINT = `${API_BASE}/api/signal/events`;
const STORAGE_KEY = "_parity_signal_uid";

/** Get or create a persistent anonymous user ID. */
function getAnonymousId() {
  try {
    let id = localStorage.getItem(STORAGE_KEY);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(STORAGE_KEY, id);
    }
    return id;
  } catch {
    // Private browsing or storage unavailable — use a session-only ID
    return crypto.randomUUID();
  }
}

/** Detect device type from viewport width. */
function getDeviceType() {
  const w = window.innerWidth;
  if (w < 768) return "mobile";
  if (w < 1024) return "tablet";
  return "desktop";
}

/**
 * Track a Signal analytics event.
 *
 * @param {string} eventType - One of: issue_viewed, category_selected,
 *   claim_expanded, score_rationale_viewed, source_clicked, summary_scroll_depth
 * @param {Object} [eventData={}] - Event-specific data (no PII)
 */
export function trackEvent(eventType, eventData = {}) {
  const payload = JSON.stringify({
    event_type: eventType,
    anonymous_id: getAnonymousId(),
    device_type: getDeviceType(),
    event_data: eventData,
  });

  // Prefer sendBeacon — reliable on mobile (survives page hide)
  if (navigator.sendBeacon) {
    const blob = new Blob([payload], { type: "text/plain" });
    const sent = navigator.sendBeacon(ENDPOINT, blob);
    if (sent) return;
  }

  // Fallback: fetch with keepalive
  fetch(ENDPOINT, {
    method: "POST",
    body: payload,
    headers: { "Content-Type": "text/plain" },
    keepalive: true,
  }).catch(() => {
    // Silently discard — analytics should never break the UI
  });
}
