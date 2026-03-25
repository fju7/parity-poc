"""Parity Billing endpoints — multi-practice billing company management."""

from __future__ import annotations

from fastapi import APIRouter, Request

from routers.auth import get_current_user

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("/health")
async def billing_health(request: Request):
    """Health check endpoint — confirms router is wired and auth works."""
    auth_header = request.headers.get("authorization", "")
    get_current_user(auth_header)

    return {"status": "ok", "product": "parity-billing"}
