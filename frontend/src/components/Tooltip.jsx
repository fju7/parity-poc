/**
 * HelpTip — contextual help "?" icon with hover/focus tooltip.
 *
 * Usage:  <HelpTip text="Explanation shown on hover or tap." />
 *
 * - Dark theme (navy bg, white text)
 * - Accessible: keyboard-focusable via tabIndex
 * - Mobile: tap to show (via :focus-within), tap elsewhere to dismiss
 * - No external dependencies
 */

export default function HelpTip({ text }) {
  return (
    <span
      style={{
        position: "relative",
        display: "inline-flex",
        alignItems: "center",
        marginLeft: 6,
        verticalAlign: "middle",
      }}
    >
      <span
        tabIndex={0}
        role="button"
        aria-label="Help"
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: 16,
          height: 16,
          borderRadius: "50%",
          border: "1px solid rgba(13,148,136,0.4)",
          color: "#94a3b8",
          fontSize: 10,
          fontWeight: 700,
          cursor: "help",
          lineHeight: 1,
          flexShrink: 0,
          outline: "none",
        }}
        className="helptip-trigger"
      >
        ?
      </span>
      <span
        role="tooltip"
        className="helptip-popup"
        style={{
          position: "absolute",
          bottom: "calc(100% + 8px)",
          left: "50%",
          transform: "translateX(-50%)",
          background: "#0f1f35",
          color: "#e2e8f0",
          fontSize: 12,
          lineHeight: 1.5,
          fontWeight: 400,
          padding: "8px 12px",
          borderRadius: 8,
          border: "1px solid rgba(255,255,255,0.1)",
          width: "max-content",
          maxWidth: 260,
          pointerEvents: "none",
          opacity: 0,
          transition: "opacity 0.15s",
          zIndex: 100,
          boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
          whiteSpace: "normal",
          textAlign: "left",
        }}
      >
        {text}
      </span>
      <style>{`
        .helptip-trigger:hover + .helptip-popup,
        .helptip-trigger:focus + .helptip-popup {
          opacity: 1 !important;
        }
      `}</style>
    </span>
  );
}
