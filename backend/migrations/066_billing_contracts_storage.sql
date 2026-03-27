-- Migration 066: Move contract PDFs from file_content column to Supabase Storage
-- Session: Architecture fix — binary files belong in Storage, not table columns

-- Add storage_path column to reference files in the billing-contracts bucket
ALTER TABLE billing_contracts ADD COLUMN IF NOT EXISTS storage_path text;

-- Create the Storage bucket (private, service_role access only)
INSERT INTO storage.buckets (id, name, public)
VALUES ('billing-contracts', 'billing-contracts', false)
ON CONFLICT (id) DO NOTHING;

-- RLS policy: only service_role can read/write contract files
CREATE POLICY "billing_contracts_storage_service_role"
  ON storage.objects FOR ALL
  USING (bucket_id = 'billing-contracts' AND auth.role() = 'service_role')
  WITH CHECK (bucket_id = 'billing-contracts' AND auth.role() = 'service_role');
