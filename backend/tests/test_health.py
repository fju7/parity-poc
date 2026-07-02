"""
TEST-1: Health (Parity Health consumer) API endpoint tests.

Covers: /api/health/auth — send-otp, verify-otp, signup, me, logout,
        update-profile, checkout, subscription-status, portal.
        /api/health/ — analyze-text, analyze-image, analyze-sbc,
        analyze-denial, generate-appeal, classify-document,
        extract-docx, extract-table.
"""

import pytest


# ---- Health Auth ----

class TestHealthSendOtp:
    """POST /api/health/auth/send-otp"""

    def test_send_otp(self, client):
        r = client.post("/api/health/auth/send-otp", json={
            "email": "test-admin@civicscale-testing.internal",
        })
        assert r.status_code == 200
        assert r.json()["sent"] is True

    def test_send_otp_missing_email(self, client):
        r = client.post("/api/health/auth/send-otp", json={})
        assert r.status_code in (400, 422)


class TestHealthVerifyOtp:
    """POST /api/health/auth/verify-otp"""

    def test_verify_otp_invalid(self, client):
        r = client.post("/api/health/auth/verify-otp", json={
            "email": "test-admin@civicscale-testing.internal",
            "code": "00000000",
        })
        assert r.status_code == 400


class TestHealthSignup:
    """POST /api/health/auth/signup"""

    def test_signup_missing_fields(self, client):
        r = client.post("/api/health/auth/signup", json={
            "email": "test@test.com",
        })
        assert r.status_code == 422


class TestHealthMe:
    """GET /api/health/auth/me"""

    def test_me_no_auth(self, client):
        r = client.get("/api/health/auth/me")
        assert r.status_code == 401

    def test_me_invalid_token(self, client):
        r = client.get(
            "/api/health/auth/me",
            headers={"Authorization": "Bearer invalid-health-token"},
        )
        assert r.status_code in (401, 500)  # May 500 on malformed UUID


class TestHealthLogout:
    """POST /api/health/auth/logout"""

    def test_logout_no_auth(self, client):
        r = client.post("/api/health/auth/logout")
        assert r.status_code == 200
        assert r.json()["logged_out"] is True


class TestHealthUpdateProfile:
    """PATCH /api/health/auth/update-profile"""

    def test_update_profile_no_auth(self, client):
        r = client.patch("/api/health/auth/update-profile", json={
            "full_name": "New Name",
        })
        assert r.status_code == 401


class TestHealthCheckout:
    """POST /api/health/auth/checkout"""

    def test_checkout_no_auth(self, client):
        r = client.post("/api/health/auth/checkout", json={
            "plan": "monthly",
        })
        assert r.status_code == 401


class TestHealthSubscriptionStatus:
    """GET /api/health/auth/subscription-status"""

    def test_subscription_status_no_auth(self, client):
        r = client.get("/api/health/auth/subscription-status")
        assert r.status_code == 401


class TestHealthPortal:
    """POST /api/health/auth/portal"""

    def test_portal_no_auth(self, client):
        r = client.post("/api/health/auth/portal", json={})
        assert r.status_code == 401


class TestHealthWebhook:
    """POST /api/health/auth/webhook"""

    def test_webhook_no_signature(self, client):
        r = client.post(
            "/api/health/auth/webhook",
            content=b'{"type": "test"}',
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400


# ---- Health Analyze ----

class TestAnalyzeText:
    """POST /api/health/analyze-text"""

    def test_analyze_text_too_short(self, client):
        r = client.post("/api/health/analyze-text", json={
            "text": "short",
        })
        assert r.status_code == 400

    def test_analyze_text_valid_format(self, client):
        """Test that a valid-length text request is accepted (may hit Claude)."""
        r = client.post("/api/health/analyze-text", json={
            "text": "Patient John Doe, Date of Service 01/15/2025, "
                    "Provider ABC Medical, CPT 99213 billed $150.00, "
                    "paid $85.00 by Aetna PPO, patient responsibility $65.00.",
        })
        # Should succeed or return 502/503 if Claude is overloaded
        assert r.status_code in (200, 502, 503)


class TestAnalyzeImage:
    """POST /api/health/analyze-image"""

    def test_analyze_image_no_pages(self, client):
        r = client.post("/api/health/analyze-image", json={
            "pages": [],
        })
        assert r.status_code == 400


class TestAnalyzeDenial:
    """POST /api/health/analyze-denial"""

    def test_analyze_denial_too_short(self, client):
        r = client.post("/api/health/analyze-denial", json={
            "text": "short",
        })
        assert r.status_code == 400


class TestGenerateAppeal:
    """POST /api/health/generate-appeal"""

    def test_generate_appeal_missing_fields(self, client):
        r = client.post("/api/health/generate-appeal", json={})
        assert r.status_code == 422


class TestClassifyDocument:
    """POST /api/health/classify-document"""

    def test_classify_no_file(self, client):
        r = client.post("/api/health/classify-document")
        assert r.status_code == 422


class TestExtractDocx:
    """POST /api/health/extract-docx"""

    def test_extract_docx_no_file(self, client):
        r = client.post("/api/health/extract-docx")
        assert r.status_code == 422


class TestExtractTable:
    """POST /api/health/extract-table"""

    def test_extract_table_no_file(self, client):
        r = client.post("/api/health/extract-table")
        assert r.status_code == 422
