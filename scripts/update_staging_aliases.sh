#!/bin/bash
# Update all staging subdomain aliases for a new Vercel deployment.
#
# Usage:
#   ./scripts/update_staging_aliases.sh parity-poc-repo-XXXXX-fju7s-projects.vercel.app
#
# This assigns all 6 staging subdomains to the given deployment URL.
# Requires: npm i -g vercel (and `vercel login` completed)

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <vercel-deployment-url>"
  echo "Example: $0 parity-poc-repo-abc123-fju7s-projects.vercel.app"
  exit 1
fi

DEPLOYMENT_URL="$1"

ALIASES=(
  "staging.civicscale.ai"
  "staging-signal.civicscale.ai"
  "staging-health.civicscale.ai"
  "staging-employer.civicscale.ai"
  "staging-broker.civicscale.ai"
  "staging-provider.civicscale.ai"
)

echo "Aliasing deployment: $DEPLOYMENT_URL"
echo ""

FAILED=0
for ALIAS in "${ALIASES[@]}"; do
  echo -n "  $ALIAS ... "
  if npx vercel alias "$DEPLOYMENT_URL" "$ALIAS" 2>/dev/null; then
    echo "OK"
  else
    echo "FAILED"
    FAILED=$((FAILED + 1))
  fi
done

echo ""
if [ $FAILED -eq 0 ]; then
  echo "All 6 aliases updated successfully."
else
  echo "$FAILED alias(es) failed. Check Vercel project settings and domain configuration."
  exit 1
fi
