-- 049_platform_cases.sql
-- Unified case tracking for Provider appeals and Health disputes.

CREATE TABLE IF NOT EXISTS platform_cases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product TEXT NOT NULL,
  user_id UUID,
  case_type TEXT,
  cpt_code TEXT,
  denial_code TEXT,
  payer TEXT,
  signal_topic_slug TEXT,
  signal_score FLOAT,
  description TEXT,
  status TEXT DEFAULT 'open' CHECK (status IN ('open','won','lost','partial','withdrawn')),
  opened_at TIMESTAMPTZ DEFAULT now(),
  resolved_at TIMESTAMPTZ,
  reminder_sent_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_platform_cases_product ON platform_cases(product);
CREATE INDEX IF NOT EXISTS idx_platform_cases_user ON platform_cases(user_id);
CREATE INDEX IF NOT EXISTS idx_platform_cases_status ON platform_cases(status);
CREATE INDEX IF NOT EXISTS idx_platform_cases_opened ON platform_cases(opened_at);
