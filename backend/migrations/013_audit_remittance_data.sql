-- Migration 013: Add remittance_data column to provider_audits
-- Stores parsed 835 line items so admin can run analysis without re-uploading
-- Run in Supabase SQL Editor

ALTER TABLE provider_audits
    ADD COLUMN IF NOT EXISTS remittance_data JSONB DEFAULT '[]'::jsonb;
-- Array of {filename, payer_name, claims: [{cpt_code, billed_amount, paid_amount, units, adjustments, claim_id}]}

COMMENT ON COLUMN provider_audits.remittance_data IS 'Parsed 835 line items grouped by file, stored at submission for admin analysis';

-- Also update payer_list comment to reflect that fee_schedule_data is now included
COMMENT ON COLUMN provider_audits.payer_list IS 'Array of {payer_name, fee_schedule_method, fee_schedule_data: {cpt: rate}, code_count}';
