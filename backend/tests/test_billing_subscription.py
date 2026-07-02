"""
TEST-1: Billing subscription endpoint tests.

Covers: /api/billing/subscription — checkout, portal, status, webhook.
Also covers /api/billing/team — analysts, assignments.
"""

import pytest


class TestSubscriptionCheckout:
    """POST /api/billing/subscription/checkout"""

    def test_checkout_no_auth(self, client):
        r = client.post("/api/billing/subscription/checkout", json={
            "tier": "starter",
        })
        assert r.status_code in (401, 403)

    def test_checkout_invalid_tier(self, client):
        r = client.post("/api/billing/subscription/checkout", json={
            "tier": "nonexistent",
        })
        assert r.status_code in (400, 401, 403)


class TestSubscriptionPortal:
    """POST /api/billing/subscription/portal"""

    def test_portal_no_auth(self, client):
        r = client.post("/api/billing/subscription/portal")
        assert r.status_code in (401, 403)


class TestSubscriptionStatus:
    """GET /api/billing/subscription/status"""

    def test_status_no_auth(self, client):
        r = client.get("/api/billing/subscription/status")
        assert r.status_code in (401, 403)


class TestSubscriptionWebhook:
    """POST /api/billing/subscription/webhook"""

    def test_webhook_no_signature(self, client):
        r = client.post(
            "/api/billing/subscription/webhook",
            content=b'{"type": "test"}',
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400


class TestTeamAnalysts:
    """GET /api/billing/team/analysts"""

    def test_analysts_no_auth(self, client):
        r = client.get("/api/billing/team/analysts")
        assert r.status_code in (401, 403)


class TestTeamAssignments:
    """POST /api/billing/team/assignments"""

    def test_assignments_no_auth(self, client):
        r = client.post("/api/billing/team/assignments", json={
            "analyst_user_id": "00000000-0000-0000-0000-000000000000",
            "practice_ids": [],
        })
        assert r.status_code in (401, 403)
