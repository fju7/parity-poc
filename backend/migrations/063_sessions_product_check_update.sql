-- Migration 063: Update sessions.product CHECK constraint to include all products
-- Session BL-9 bugfix
-- The original constraint from migration 001 only allowed employer/broker/provider/health.
-- Signal, billing, and billing_portal were added later but the constraint was never updated.

ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_product_check;
ALTER TABLE sessions ADD CONSTRAINT sessions_product_check
    CHECK (product IN ('employer', 'broker', 'provider', 'health', 'signal', 'billing', 'billing_portal'));
