#!/bin/bash
# CivicScale Staging Environment Setup
# These steps must be completed manually in browser-based dashboards
# Run after Session M3 Claude Code work is complete

# STEP 1 — SUPABASE (https://supabase.com)
# Create new project: name=parity-poc-staging, region=East US
# Save the project URL and service_role_key
# Run all migrations: paste contents of each backend/migrations/*.sql file in order
# Update backend/.env.staging with the real URL and key

# STEP 2 — RENDER (https://dashboard.render.com)
# Create new Web Service
# Connect to GitHub repo: fju7/parity-poc
# Branch: staging
# Root directory: backend
# Build command: pip install -r requirements.txt
# Start command: uvicorn main:app --host 0.0.0.0 --port $PORT
# Instance type: Free
# Add all environment variables from backend/.env.staging (with real Supabase values)
# Note the assigned URL: parity-poc-api-staging.onrender.com (or similar)

# STEP 3 — VERCEL (https://vercel.com)
# For each of the 5 product projects:
#   Go to project Settings → Git
#   Add branch deployment: staging branch → staging subdomain
#   Health: staging-health.civicscale.ai
#   Employer: staging-employer.civicscale.ai
#   Broker: staging-broker.civicscale.ai
#   Provider: staging-provider.civicscale.ai
#   Signal: staging-signal.civicscale.ai
#   Add environment variable for staging: VITE_API_URL=https://[staging-render-url]

# STEP 4 — VERIFY SEPARATION
# Make a small test change on staging branch
# Push to staging
# Confirm change appears on staging URLs but NOT on production URLs
# Revert test change

echo "Staging setup checklist — complete each step above before running Session N"
