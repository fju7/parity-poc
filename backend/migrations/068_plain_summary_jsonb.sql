-- Migration 068: Convert plain_summary from TEXT to JSONB
-- Existing text values are wrapped in {"text": "..."} for backward compatibility.
-- Frontend checks for .mechanism (new structured format) vs .text (old format).

ALTER TABLE signal_issues ALTER COLUMN plain_summary TYPE JSONB USING
  CASE
    WHEN plain_summary IS NOT NULL THEN jsonb_build_object('text', plain_summary)
    ELSE NULL
  END;
