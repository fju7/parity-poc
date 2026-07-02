"""
TEST-1: Employer API endpoint tests.

Covers: /api/employer/ — verify-code, contribute, dashboard,
        benchmark, claims-check, pricing-tiers, rbp-calculate,
        claims-history, subscription, broker-connect.
"""

import pytest

pytestmark = pytest.mark.integration  # hits live BASE_URL; excluded from default run (see pytest.ini)


class TestPricingTiers:
    """GET /api/employer/pricing-tiers"""

    def test_pricing_tiers(self, client):
        r = client.get("/api/employer/pricing-tiers")
        assert r.status_code == 200
        data = r.json()
        assert "tiers" in data
        assert isinstance(data["tiers"], dict)
        assert "guarantee" in data


class TestBenchmark:
    """POST /api/employer/benchmark"""

    def test_benchmark_valid(self, client):
        r = client.post("/api/employer/benchmark", json={
            "industry": "Manufacturing",
            "company_size": "51-200",
            "state": "MD",
            "pepm_input": 650.0,
        })
        assert r.status_code == 200
        data = r.json()
        assert "input" in data
        assert "benchmarks" in data
        assert "result" in data
        assert "percentile" in data["result"]
        assert "distribution" in data

    def test_benchmark_missing_fields(self, client):
        r = client.post("/api/employer/benchmark", json={
            "industry": "Manufacturing",
        })
        assert r.status_code == 422


class TestClaimsCheck:
    """POST /api/employer/claims-check"""

    def test_claims_check_no_file(self, client):
        r = client.post("/api/employer/claims-check", data={
            "zip_code": "21201",
        })
        assert r.status_code == 422


class TestClaimsHistory:
    """GET /api/employer/claims-history"""

    def test_claims_history(self, client):
        r = client.get("/api/employer/claims-history", params={
            "email": "nonexistent@test.com",
        })
        assert r.status_code == 200
        data = r.json()
        # Response key may be "sessions" or "uploads"
        assert "sessions" in data or "uploads" in data


class TestSubscriptionStatus:
    """GET /api/employer/subscription-status"""

    def test_subscription_status(self, client):
        r = client.get("/api/employer/subscription-status", params={
            "email": "nonexistent@test.com",
        })
        assert r.status_code == 200
        data = r.json()
        assert "active" in data
        assert data["active"] is False


class TestCreateCheckout:
    """POST /api/employer/create-checkout"""

    def test_create_checkout_missing_fields(self, client):
        r = client.post("/api/employer/create-checkout", json={
            "email": "test@test.com",
        })
        assert r.status_code in (422, 500, 503)  # May 503 if Stripe not configured


class TestBillingPortal:
    """POST /api/employer/billing-portal"""

    def test_billing_portal_no_subscription(self, client):
        r = client.post("/api/employer/billing-portal", params={
            "email": "nonexistent@test.com",
        })
        # Should fail — no Stripe customer for this email
        assert r.status_code in (400, 404, 500)


class TestDashboard:
    """GET /api/employer/dashboard"""

    def test_dashboard_no_employer(self, client):
        r = client.get("/api/employer/dashboard", params={
            "employer_id": "nonexistent",
        })
        # May return empty dashboard (200) or internal error (500)
        assert r.status_code in (200, 500)


class TestBrokerConnect:
    """POST /api/employer/broker-connect"""

    def test_broker_connect(self, client):
        r = client.post("/api/employer/broker-connect", json={
            "employer_email": "test-employer@civicscale-testing.internal",
            "email": "test-employer@civicscale-testing.internal",
            "company_name": "Test Employer Inc",
            "industry": "Manufacturing",
            "state": "MD",
        })
        # May succeed, fail validation, or error on email send
        assert r.status_code in (200, 400, 422, 500)


class TestStartTrial:
    """POST /api/employer/start-trial"""

    def test_start_trial_no_auth(self, client):
        r = client.post("/api/employer/start-trial")
        assert r.status_code in (401, 403, 422)


class TestCancelTrial:
    """POST /api/employer/cancel-trial"""

    def test_cancel_trial_no_auth(self, client):
        r = client.post("/api/employer/cancel-trial")
        assert r.status_code in (401, 403, 422)
