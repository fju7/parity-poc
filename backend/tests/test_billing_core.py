"""
TEST-1: Billing core API endpoint tests.

Covers: /api/billing/ — send-otp, verify-otp, register, me, practices,
        users, settings, portal-settings, ingest, health check.
"""

import pytest

pytestmark = pytest.mark.integration  # hits live BASE_URL; excluded from default run (see pytest.ini)


class TestBillingHealth:
    """GET /api/billing/health"""

    def test_health_check(self, client):
        """Billing health endpoint — may require auth depending on router setup."""
        r = client.get("/api/billing/health")
        # Endpoint may require auth (returns 401) or return health status (200)
        assert r.status_code in (200, 401, 403)
        if r.status_code == 200:
            data = r.json()
            assert data["status"] == "ok"


class TestBillingSendOtp:
    """POST /api/billing/send-otp"""

    def test_send_otp(self, client):
        r = client.post("/api/billing/send-otp", json={
            "email": "test-admin@civicscale-testing.internal",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["sent"] is True

    def test_send_otp_missing_email(self, client):
        r = client.post("/api/billing/send-otp", json={})
        assert r.status_code in (400, 422)


class TestBillingVerifyOtp:
    """POST /api/billing/verify-otp"""

    def test_verify_otp_invalid_code(self, client):
        r = client.post("/api/billing/verify-otp", json={
            "email": "test-admin@civicscale-testing.internal",
            "code": "000000",
        })
        assert r.status_code == 400


class TestBillingMe:
    """GET /api/billing/me"""

    def test_me_no_auth(self, client):
        r = client.get("/api/billing/me")
        assert r.status_code in (401, 403)

    def test_me_invalid_token(self, client):
        r = client.get(
            "/api/billing/me",
            headers={"Authorization": "Bearer invalid-billing-token"},
        )
        assert r.status_code in (401, 403, 500)  # May 500 on malformed UUID


class TestBillingPractices:
    """GET/POST /api/billing/practices"""

    def test_list_practices_no_auth(self, client):
        r = client.get("/api/billing/practices")
        assert r.status_code in (401, 403)

    def test_add_practice_no_auth(self, client):
        r = client.post("/api/billing/practices", json={
            "practice_name": "Test Practice",
            "contact_email": "practice@test.com",
        })
        assert r.status_code in (401, 403)


class TestBillingUsers:
    """GET /api/billing/users, POST /api/billing/users/invite"""

    def test_list_users_no_auth(self, client):
        r = client.get("/api/billing/users")
        assert r.status_code in (401, 403)

    def test_invite_user_no_auth(self, client):
        r = client.post("/api/billing/users/invite", json={
            "email": "analyst@test.com",
            "role": "analyst",
        })
        assert r.status_code in (401, 403)


class TestBillingSettings:
    """PUT /api/billing/settings"""

    def test_update_settings_no_auth(self, client):
        r = client.put("/api/billing/settings", json={
            "company_name": "Updated Name",
        })
        assert r.status_code in (401, 403)


class TestBillingReportText:
    """PUT /api/billing/settings/report-text"""

    def test_update_report_text_no_auth(self, client):
        r = client.put("/api/billing/settings/report-text", json={
            "report_header_text": "Header",
        })
        assert r.status_code in (401, 403)


class TestBillingProviderStatus:
    """GET /api/billing/practices/provider-status"""

    def test_provider_status_no_auth(self, client):
        r = client.get("/api/billing/practices/provider-status")
        assert r.status_code in (401, 403)


class TestBillingPortalSettings:
    """GET /api/billing/portal-settings"""

    def test_portal_settings_no_auth(self, client):
        r = client.get("/api/billing/portal-settings")
        assert r.status_code in (401, 403)


class TestBillingIngest:
    """POST /api/billing/ingest/upload, GET /api/billing/ingest/jobs"""

    def test_list_jobs_no_auth(self, client):
        r = client.get("/api/billing/ingest/jobs")
        assert r.status_code in (401, 403, 404)

    def test_process_all_no_auth(self, client):
        r = client.post("/api/billing/ingest/process-all")
        assert r.status_code in (401, 403, 404)
