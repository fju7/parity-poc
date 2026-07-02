"""
TEST-1: Billing escalations endpoint tests.

Covers: /api/billing/escalations — detect-patterns, create, list,
        detail, update-status, export.
"""

import pytest


class TestDetectPatterns:
    """GET /api/billing/escalations/detect-patterns"""

    def test_detect_patterns_no_auth(self, client):
        r = client.get("/api/billing/escalations/detect-patterns")
        assert r.status_code in (401, 403)


class TestCreateEscalation:
    """POST /api/billing/escalations"""

    def test_create_no_auth(self, client):
        r = client.post("/api/billing/escalations", json={
            "payer_name": "Aetna",
            "denial_code": "CO-16",
        })
        assert r.status_code in (401, 403, 307)  # May redirect to trailing slash


class TestListEscalations:
    """GET /api/billing/escalations"""

    def test_list_no_auth(self, client):
        r = client.get("/api/billing/escalations")
        assert r.status_code in (401, 403, 307)  # May redirect to trailing slash


class TestEscalationDetail:
    """GET /api/billing/escalations/{escalation_id}"""

    def test_detail_no_auth(self, client):
        r = client.get(
            "/api/billing/escalations/00000000-0000-0000-0000-000000000000"
        )
        assert r.status_code in (401, 403, 404)


class TestUpdateStatus:
    """PATCH /api/billing/escalations/{escalation_id}/status"""

    def test_update_status_no_auth(self, client):
        r = client.patch(
            "/api/billing/escalations/00000000-0000-0000-0000-000000000000/status",
            json={"status": "in_progress"},
        )
        assert r.status_code in (401, 403, 404)


class TestExportEscalation:
    """GET /api/billing/escalations/{escalation_id}/export"""

    def test_export_no_auth(self, client):
        r = client.get(
            "/api/billing/escalations/00000000-0000-0000-0000-000000000000/export"
        )
        assert r.status_code in (401, 403, 404)
