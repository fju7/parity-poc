import { API_BASE } from "./apiBase";
/**
 * Parity Signal — lightweight privacy-first event capture.
 *
 * Uses a per-session random UUID (not linked to user account).
 * navigator.sendBeacon for reliability. Never blocks the UI.
 */

const ENDPOINT = `${API_BASE}/api/signal/events`;

/** Per-session random ID — regenerated every page load. */
let _sessionId = null;
function getSessionId() {
  if (!_sessionId) {
    _sessionId = crypto.randomUUID();
  }
  return _sessionId;
}

/** Track max layer depth reached in this session. */
let _maxDepth = 0;
export function recordDepth(layer) {
  if (layer > _maxDepth) _maxDepth = layer;
}
export function getMaxDepth() {
  return _maxDepth;
}

/**
 * Track a Signal analytics event. Fire and forget — never blocks UI.
 *
 * @param {string} eventType
 * @param {Object} [eventData={}]
 * @param {string} [topicSlug=""]
 * @param {string} [elementId=""]
 */
export function trackEvent(eventType, eventData = {}, topicSlug = "", elementId = "") {
  const payload = JSON.stringify({
    event_type: eventType,
    session_id: getSessionId(),
    topic_slug: topicSlug,
    element_id: elementId,
    event_data: eventData,
  });

  if (navigator.sendBeacon) {
    const blob = new Blob([payload], { type: "text/plain" });
    const sent = navigator.sendBeacon(ENDPOINT, blob);
    if (sent) return;
  }

  fetch(ENDPOINT, {
    method: "POST",
    body: payload,
    headers: { "Content-Type": "text/plain" },
    keepalive: true,
  }).catch(() => {});
}
