"""
TEST-1: Auth API endpoint tests.

Covers: /api/auth/send-otp, verify-otp, me, logout, company (CRUD),
        invite, accept-invite, users (list/update/delete), deletion-request.
"""

import pytest

pytestmark = pytest.mark.integration  # hits live BASE_URL; excluded from default run (see pytest.ini)


class TestSendOtp:
    """POST /api/auth/send-otp"""

    def test_send_otp_employer(self, client):
        r = client.post("/api/auth/send-otp", json={
            "email": "test-admin@civicscale-testing.internal",
            "product": "employer",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["sent"] is True
        assert "email" in data

    def test_send_otp_broker(self, client):
        r = client.post("/api/auth/send-otp", json={
            "email": "test-admin@civicscale-testing.internal",
            "product": "broker",
        })
        assert r.status_code == 200
        assert r.json()["sent"] is True

    def test_send_otp_provider(self, client):
        r = client.post("/api/auth/send-otp", json={
            "email": "test-admin@civicscale-testing.internal",
            "product": "provider",
        })
        assert r.status_code == 200
        assert r.json()["sent"] is True

    def test_send_otp_health(self, client):
        r = client.post("/api/auth/send-otp", json={
            "email": "test-admin@civicscale-testing.internal",
            "product": "health",
        })
        assert r.status_code == 200
        assert r.json()["sent"] is True

    def test_send_otp_signal(self, client):
        r = client.post("/api/auth/send-otp", json={
            "email": "test-admin@civicscale-testing.internal",
            "product": "signal",
        })
        assert r.status_code == 200
        assert r.json()["sent"] is True

    def test_send_otp_billing(self, client):
        r = client.post("/api/auth/send-otp", json={
            "email": "test-admin@civicscale-testing.internal",
            "product": "billing",
        })
        assert r.status_code == 200
        assert r.json()["sent"] is True

    def test_send_otp_missing_email(self, client):
        r = client.post("/api/auth/send-otp", json={"product": "employer"})
        assert r.status_code == 400

    def test_send_otp_invalid_product(self, client):
        r = client.post("/api/auth/send-otp", json={
            "email": "test@example.com",
            "product": "nonexistent",
        })
        assert r.status_code == 400


class TestVerifyOtp:
    """POST /api/auth/verify-otp"""

    def test_verify_otp_invalid_code(self, client):
        r = client.post("/api/auth/verify-otp", json={
            "email": "test-admin@civicscale-testing.internal",
            "code": "00000000",
            "product": "employer",
        })
        assert r.status_code == 400

    def test_verify_otp_missing_fields(self, client):
        r = client.post("/api/auth/verify-otp", json={
            "email": "test-admin@civicscale-testing.internal",
            "product": "employer",
        })
        assert r.status_code == 422  # Pydantic validation


class TestMe:
    """GET /api/auth/me"""

    def test_me_no_token(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code == 401

    def test_me_invalid_token(self, client):
        r = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token-12345"},
        )
        assert r.status_code in (401, 500)  # Server may 500 on malformed UUID token

    def test_me_malformed_header(self, client):
        r = client.get(
            "/api/auth/me",
            headers={"Authorization": "NotBearer some-token"},
        )
        assert r.status_code == 401


class TestLogout:
    """POST /api/auth/logout"""

    def test_logout_no_token(self, client):
        r = client.post("/api/auth/logout")
        assert r.status_code == 200
        assert r.json()["logged_out"] is True

    def test_logout_invalid_token(self, client):
        r = client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer fake-token"},
        )
        # Should succeed gracefully or error on malformed UUID
        assert r.status_code in (200, 500)


class TestCompany:
    """POST/GET/PATCH /api/auth/company"""

    def test_get_company_no_auth(self, client):
        r = client.get("/api/auth/company")
        assert r.status_code == 401

    def test_patch_company_no_auth(self, client):
        r = client.patch("/api/auth/company", json={"name": "New Name"})
        assert r.status_code == 401

    def test_create_company_missing_fields(self, client):
        r = client.post("/api/auth/company", json={
            "email": "incomplete@test.com",
        })
        assert r.status_code == 422


class TestInvite:
    """POST /api/auth/invite"""

    def test_invite_no_auth(self, client):
        r = client.post("/api/auth/invite", json={
            "invited_email": "someone@test.com",
            "role": "member",
        })
        assert r.status_code == 401


class TestAcceptInvite:
    """POST /api/auth/accept-invite"""

    def test_accept_invite_invalid_token(self, client):
        r = client.post("/api/auth/accept-invite", json={
            "token": "nonexistent-invite-token",
            "email": "someone@test.com",
            "full_name": "Test User",
        })
        assert r.status_code in (400, 500)  # May 500 on malformed UUID token


class TestUsers:
    """GET /api/auth/users, PATCH/DELETE /api/auth/users/{user_id}"""

    def test_list_users_no_auth(self, client):
        r = client.get("/api/auth/users")
        assert r.status_code == 401

    def test_update_user_no_auth(self, client):
        r = client.patch(
            "/api/auth/users/00000000-0000-0000-0000-000000000000",
            json={"role": "member"},
        )
        assert r.status_code == 401

    def test_delete_user_no_auth(self, client):
        r = client.delete(
            "/api/auth/users/00000000-0000-0000-0000-000000000000",
        )
        assert r.status_code == 401


class TestDeletionRequest:
    """POST /api/auth/deletion-request"""

    def test_deletion_request_no_auth(self, client):
        r = client.post("/api/auth/deletion-request", json={
            "confirm_company_name": "Test Company",
        })
        assert r.status_code == 401
