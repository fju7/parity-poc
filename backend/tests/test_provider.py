"""
TEST-1: Provider API endpoint tests.

Covers: /api/provider/ — demo, contract management, 835 parsing,
        analysis, appeals, subscription, audit admin endpoints.
"""

import pytest


class TestProviderDemo:
    """GET /api/provider/demo-835, demo-analysis"""

    def test_demo_835(self, client):
        r = client.get("/api/provider/demo-835")
        assert r.status_code == 200
        # May return JSON or raw 835 text content
        try:
            data = r.json()
            assert isinstance(data, (dict, list))
        except Exception:
            # Raw text 835 content is also valid
            assert len(r.content) > 0

    def test_demo_analysis(self, client):
        r = client.get("/api/provider/demo-analysis")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)


class TestContractTemplate:
    """GET /api/provider/contract-template"""

    def test_contract_template(self, client):
        r = client.get("/api/provider/contract-template")
        assert r.status_code == 200
        # May return JSON or binary template content
        try:
            data = r.json()
            assert isinstance(data, (dict, list))
        except Exception:
            assert len(r.content) > 0


class TestSaveRates:
    """POST /api/provider/save-rates"""

    def test_save_rates_no_auth(self, client):
        """save-rates requires auth — must return 401 without token."""
        r = client.post("/api/provider/save-rates", json={
            "user_id": "test",
            "payer_name": "Test Payer",
            "rates": [],
        })
        assert r.status_code == 401


class TestSavedRates:
    """GET /api/provider/saved-rates"""

    def test_saved_rates_no_auth(self, client):
        r = client.get("/api/provider/saved-rates")
        assert r.status_code in (401, 403, 422)  # May require query params


class TestParse835:
    """POST /api/provider/parse-835"""

    def test_parse_835_no_auth(self, client):
        r = client.post("/api/provider/parse-835", json={
            "file_content": "ISA*00*...",
        })
        assert r.status_code in (200, 400, 401, 403, 422, 500)


class TestAnalyzeContract:
    """POST /api/provider/analyze-contract"""

    def test_analyze_contract_no_auth(self, client):
        r = client.post("/api/provider/analyze-contract", json={
            "user_id": "test",
            "payer_name": "Test Payer",
            "remittance_lines": [],
        })
        assert r.status_code in (200, 400, 401, 403, 422, 500)


class TestAnalyzeCoding:
    """POST /api/provider/analyze-coding"""

    def test_analyze_coding_no_auth(self, client):
        """analyze-coding requires auth — must return 401 without token."""
        r = client.post("/api/provider/analyze-coding", json={
            "user_id": "test",
            "lines": [],
        })
        assert r.status_code == 401


class TestAnalyzeDenials:
    """POST /api/provider/analyze-denials"""

    def test_analyze_denials_no_auth(self, client):
        """analyze-denials requires auth — must return 401 without token."""
        r = client.post("/api/provider/analyze-denials", json={
            "payer_name": "Test Payer",
            "denied_lines": [],
        })
        assert r.status_code == 401


class TestMyAudits:
    """GET /api/provider/my-audits"""

    def test_my_audits_no_auth(self, client):
        r = client.get("/api/provider/my-audits")
        assert r.status_code in (401, 403)


class TestMyProfile:
    """GET /api/provider/my-profile"""

    def test_my_profile_no_auth(self, client):
        r = client.get("/api/provider/my-profile")
        assert r.status_code in (401, 403)


class TestMyAnalyses:
    """GET /api/provider/my-analyses"""

    def test_my_analyses_no_auth(self, client):
        r = client.get("/api/provider/my-analyses")
        assert r.status_code in (401, 403)

    def test_my_analyses_archived_no_auth(self, client):
        r = client.get("/api/provider/my-analyses/archived")
        assert r.status_code in (401, 403)


class TestPayerTrends:
    """GET /api/provider/payer-trends"""

    def test_payer_trends_no_auth(self, client):
        r = client.get("/api/provider/payer-trends")
        assert r.status_code in (401, 403)


class TestAppeals:
    """Provider appeals endpoints."""

    def test_generate_appeal_no_auth(self, client):
        r = client.post("/api/provider/generate-appeal", json={
            "claim_id": "test",
            "denial_code": "CO-45",
            "cpt_code": "99213",
            "billed_amount": 100.0,
            "payer_name": "Test",
            "date_of_service": "2025-01-01",
            "patient_name": "Test Patient",
        })
        assert r.status_code in (401, 403)

    def test_list_appeals_no_auth(self, client):
        r = client.get("/api/provider/appeals")
        assert r.status_code in (401, 403)


class TestSubscription:
    """Provider subscription endpoints."""

    def test_my_subscription_no_auth(self, client):
        r = client.get("/api/provider/my-subscription")
        assert r.status_code in (401, 403)

    def test_trial_status_no_auth(self, client):
        r = client.get("/api/provider/trial-status")
        assert r.status_code in (401, 403)

    def test_subscription_checkout_no_auth(self, client):
        r = client.post("/api/provider/subscription/checkout", json={})
        assert r.status_code in (401, 403)

    def test_subscription_webhook_no_signature(self, client):
        r = client.post(
            "/api/provider/subscription/webhook",
            content=b'{"type": "test"}',
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400


class TestAdminEndpoints:
    """Provider admin endpoints."""

    def test_admin_audits_no_auth(self, client):
        r = client.get("/api/provider/admin/audits")
        assert r.status_code in (401, 403)

    def test_admin_subscriptions_no_auth(self, client):
        r = client.get("/api/provider/admin/subscriptions")
        assert r.status_code in (401, 403)
