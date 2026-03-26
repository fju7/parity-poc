-- Migration 061: Add branding columns to billing_companies
-- Session BL-8
-- logo_url already exists from 055 but report_header_text and report_footer_text are new

ALTER TABLE billing_companies
    ADD COLUMN IF NOT EXISTS report_header_text text,
    ADD COLUMN IF NOT EXISTS report_footer_text text;
