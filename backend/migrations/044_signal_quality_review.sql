-- 044_signal_quality_review.sql
-- Add quality_review_status to signal_issues for topic review gate.
-- Topics must be approved before appearing publicly.

ALTER TABLE signal_issues
  ADD COLUMN IF NOT EXISTS quality_review_status TEXT DEFAULT 'pending';

ALTER TABLE signal_issues
  ADD CONSTRAINT chk_quality_review_status CHECK (
    quality_review_status IS NULL OR quality_review_status IN (
      'pending', 'approved', 'rejected'
    )
  );

-- Mark breast cancer topic as approved (existing topic)
UPDATE signal_issues
  SET quality_review_status = 'approved'
  WHERE slug = 'breast-cancer-therapies';

-- Reload PostgREST schema cache
SELECT pg_notify('pgrst', 'reload schema');
