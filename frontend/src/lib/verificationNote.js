// The consumer for a verify.policy verdict on the page (shared assertion
// policy, amendment 3: "UNCHECKED must have a consumer"). A verdict the API
// returns but nothing renders is a verdict silently equivalent to ok.
//
// verification = { ok, verified, refused: [...], unchecked: [...], flags: [...], checked }
export function verificationSummary(verification) {
  if (!verification) return null;
  const refused = verification.refused?.length || 0;
  const unchecked = verification.unchecked?.length || 0;
  const checked = verification.checked || 0;
  if (verification.verified) {
    return { tone: "ok", text: `${checked} value${checked === 1 ? "" : "s"} verified against the source.` };
  }
  const parts = [];
  if (refused) parts.push(`${refused} value${refused === 1 ? "" : "s"} not found in the source and removed`);
  if (unchecked) {
    const why = verification.unchecked[0]?.reason || "";
    parts.push(`${unchecked} value${unchecked === 1 ? "" : "s"} could not be verified${/no text layer/i.test(why) ? " (read from an image or a PDF with no text layer)" : ""}`);
  }
  return { tone: unchecked && !refused ? "unchecked" : "refused", text: parts.join("; ") + ". Check these against the original before relying on them." };
}

export const VERIFICATION_STYLES = {
  ok:        { background: "rgba(13,148,136,0.10)", border: "1px solid rgba(94,234,212,0.35)", color: "#5eead4" },
  unchecked: { background: "rgba(245,158,11,0.10)", border: "1px solid rgba(245,158,11,0.45)", color: "#fbbf24" },
  refused:   { background: "rgba(239,68,68,0.10)",  border: "1px solid rgba(239,68,68,0.45)",  color: "#fca5a5" },
};
