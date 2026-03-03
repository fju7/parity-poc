import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { createPortal } from "react-dom";

/**
 * Tooltip that positions itself above a target element using a portal.
 * Shows on hover (desktop) or tap (mobile). Tap elsewhere to dismiss.
 */
function Tooltip({ text, anchorRef, onClose }) {
  const tipRef = useRef(null);
  const [pos, setPos] = useState(null);

  useEffect(() => {
    const anchor = anchorRef.current;
    const tip = tipRef.current;
    if (!anchor || !tip) return;

    const anchorRect = anchor.getBoundingClientRect();
    const tipRect = tip.getBoundingClientRect();

    let top = anchorRect.top - tipRect.height - 6;
    let left = anchorRect.left + anchorRect.width / 2 - tipRect.width / 2;

    // Flip below if no room above
    if (top < 4) {
      top = anchorRect.bottom + 6;
    }
    // Clamp horizontally
    left = Math.max(8, Math.min(left, window.innerWidth - tipRect.width - 8));

    setPos({ top: top + window.scrollY, left: left + window.scrollX });
  }, [anchorRef]);

  // Close on tap/click outside
  useEffect(() => {
    function handleDown(e) {
      if (
        tipRef.current && !tipRef.current.contains(e.target) &&
        anchorRef.current && !anchorRef.current.contains(e.target)
      ) {
        onClose();
      }
    }
    document.addEventListener("pointerdown", handleDown);
    return () => document.removeEventListener("pointerdown", handleDown);
  }, [onClose, anchorRef]);

  return createPortal(
    <div
      ref={tipRef}
      role="tooltip"
      style={{
        position: "absolute",
        top: pos ? pos.top : -9999,
        left: pos ? pos.left : -9999,
        visibility: pos ? "visible" : "hidden",
      }}
      className="z-50 max-w-xs px-3 py-2 text-xs leading-relaxed text-white bg-[#1B3A5C] rounded-lg shadow-lg pointer-events-auto"
    >
      {text}
    </div>,
    document.body
  );
}

/**
 * A single glossary term span with hover/tap tooltip.
 */
function GlossaryTerm({ children, definition, activeId, onActivate, id }) {
  const spanRef = useRef(null);
  const isOpen = activeId === id;

  const handleClick = useCallback(
    (e) => {
      e.stopPropagation();
      onActivate(isOpen ? null : id);
    },
    [isOpen, id, onActivate]
  );

  return (
    <>
      <span
        ref={spanRef}
        onClick={handleClick}
        onMouseEnter={() => onActivate(id)}
        onMouseLeave={() => {
          // Only auto-close on mouseleave if it was hover-triggered (desktop)
          // On touch devices the pointerdown handler handles closing
          if (isOpen) onActivate(null);
        }}
        className="underline decoration-dotted decoration-current/40 underline-offset-2 text-inherit cursor-help"
      >
        {children}
      </span>
      {isOpen && (
        <Tooltip
          text={definition}
          anchorRef={spanRef}
          onClose={() => onActivate(null)}
        />
      )}
    </>
  );
}

/**
 * Renders text with glossary terms highlighted and tooltipped.
 *
 * Props:
 *   text      — the plain string to render
 *   glossary  — { term: definition } object from summary_json.glossary
 *   className — optional className for the wrapper span
 */
export default function GlossaryText({ text, glossary, className }) {
  const [activeId, setActiveId] = useState(null);

  // Build a regex from glossary terms, longest first for greedy matching
  const { regex, termMap } = useMemo(() => {
    if (!glossary || !text) return { regex: null, termMap: {} };

    const entries = Object.entries(glossary);
    if (entries.length === 0) return { regex: null, termMap: {} };

    // Sort longest first so "heart failure with preserved ejection fraction"
    // matches before "heart failure"
    entries.sort((a, b) => b[0].length - a[0].length);

    const map = {};
    const patterns = [];
    for (const [term, def] of entries) {
      const key = term.toLowerCase();
      map[key] = def;
      // Escape regex special chars, match case-insensitive at word boundaries
      const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      patterns.push(escaped);
    }

    const combined = new RegExp(`\\b(${patterns.join("|")})\\b`, "gi");
    return { regex: combined, termMap: map };
  }, [glossary, text]);

  // Split text into segments: plain strings and glossary matches
  const segments = useMemo(() => {
    if (!regex || !text) return [text];

    const result = [];
    let lastIndex = 0;
    let match;
    // Reset lastIndex in case regex was reused
    regex.lastIndex = 0;
    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        result.push({ type: "text", value: text.slice(lastIndex, match.index) });
      }
      result.push({
        type: "term",
        value: match[0],
        key: match[0].toLowerCase(),
        index: match.index,
      });
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < text.length) {
      result.push({ type: "text", value: text.slice(lastIndex) });
    }
    return result;
  }, [regex, text]);

  if (!glossary || !text || !regex) {
    return <span className={className}>{text}</span>;
  }

  return (
    <span className={className}>
      {segments.map((seg, i) =>
        seg.type === "term" ? (
          <GlossaryTerm
            key={`${seg.index}-${i}`}
            id={`${seg.index}-${i}`}
            definition={termMap[seg.key]}
            activeId={activeId}
            onActivate={setActiveId}
          >
            {seg.value}
          </GlossaryTerm>
        ) : (
          <span key={i}>{seg.value}</span>
        )
      )}
    </span>
  );
}
