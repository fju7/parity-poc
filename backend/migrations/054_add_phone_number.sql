-- Migration 054: Add phone_number to company_users and otp_codes for SMS OTP auth
ALTER TABLE company_users ADD COLUMN IF NOT EXISTS phone_number TEXT;
ALTER TABLE otp_codes ADD COLUMN IF NOT EXISTS phone_number TEXT;
