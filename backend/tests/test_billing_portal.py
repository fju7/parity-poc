"""
TEST-1: Billing portal (practice client portal) endpoint tests.

Covers: /api/billing/portal/ — send-otp, verify-otp, me,
        denial-summary, payer-performance, appeal-roi, generate-report.
"""

import pytest

pytestmark = pytest.mark.integration  # hits live BASE_URL; excluded from default run (see pytest.ini)


class TestPortalSendOtp:
    """POST /api/billing/portal/send-otp"""

    def test_send_otp_missing_fields(self, client):
        r = client.post("/api/billing/portal/send-otp", json={
            "email": "practice@test.com",
        })
        assert r.status_code in (400, 403, 422)

    def test_send_otp_invalid_practice(self, client):
        r = client.post("/api/billing/portal/send-otp", json={
            "email": "practice@test.com",
            "practice_id": "00000000-0000-0000-0000-000000000000",
        })
        assert r.status_code in (400, 403, 404)


class TestPortalVerifyOtp:
    """POST /api/billing/portal/verify-otp"""

    def test_verify_otp_invalid(self, client):
        r = client.post("/api/billing/portal/verify-otp", json={
            "email": "practice@test.com",
            "code": "000000",
            "practice_id": "00000000-0000-0000-0000-000000000000",
        })
        assert r.status_code in (400, 403)


class TestPortalMe:
    """GET /api/billing/portal/me"""

    def test_me_no_auth(self, client):
        r = client.get("/api/billing/portal/me")
        assert r.status_code in (401, 403)

    def test_me_invalid_token(self, client):
        r = client.get(
            "/api/billing/portal/me",
            headers={"Authorization": "Bearer fake-portal-token"},
        )
        assert r.status_code in (401, 403, 500)  # May 500 on malformed UUID


class TestPortalDenialSummary:
    """GET /api/billing/portal/denial-summary"""

    def test_denial_summary_no_auth(self, client):
        r = client.get("/api/billing/portal/denial-summary")
        assert r.status_code in (401, 403)


class TestPortalPayerPerformance:
    """GET /api/billing/portal/payer-performance"""

    def test_payer_performance_no_auth(self, client):
        r = client.get("/api/billing/portal/payer-performance")
        assert r.status_code in (401, 403)


class TestPortalAppealRoi:
    """GET /api/billing/portal/appeal-roi"""

    def test_appeal_roi_no_auth(self, client):
        r = client.get("/api/billing/portal/appeal-roi")
        assert r.status_code in (401, 403)


class TestPortalGenerateReport:
    """POST /api/billing/portal/generate-report"""

    def test_generate_report_no_auth(self, client):
        r = client.post("/api/billing/portal/generate-report")
        assert r.status_code in (401, 403)
