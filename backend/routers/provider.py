"""
Provider dashboard endpoints — thin router that includes all sub-routers.

All endpoint implementations are in:
  - provider_audit.py        — audit CRUD, analysis, report generation, admin management
  - provider_appeals.py      — appeal letter generation, listing, status tracking
  - provider_subscription.py — subscription management, Stripe checkout/webhook, monitoring
  - provider_trends.py       — trend computation engine (no endpoints, helper functions only)
  - provider_shared.py       — shared helpers, constants, Pydantic models

No PHI is stored. Contract rates and analysis results are tied to user_id.
"""

from fastapi import APIRouter

from routers.provider_audit import router as audit_router
from routers.provider_appeals import router as appeals_router
from routers.provider_subscription import router as subscription_router

router = APIRouter(prefix="/api/provider", tags=["provider"])

# Include all sub-routers — they have no prefix, so all endpoints
# retain their original URLs under /api/provider/...
router.include_router(audit_router)
router.include_router(appeals_router)
router.include_router(subscription_router)
