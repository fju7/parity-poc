"""
TEST-5: Stripe webhook simulation tests.

Covers the 5 core Stripe webhook event types across all 4 product webhook
endpoints (billing, employer, provider, health):

  1. checkout.session.completed
  2. customer.subscription.updated
  3. customer.subscription.deleted
  4. invoice.payment_failed
  5. invoice.payment_succeeded

Each event is tested for:
  - Correct HTTP response (200 or 400 for bad signature)
  - Signature validation (rejects missing/invalid signatures)
  - Idempotency (replaying the same event twice produces the same result)

These tests hit the LIVE production API. They do NOT bypass Stripe signature
verification — instead, they verify that missing/bad signatures are rejected
with 400. Testing actual DB mutations would require a valid Stripe webhook
secret, which we test structurally here.
"""

import json
import time
import pytest
import httpx

BASE_URL = "https://parity-poc-api.onrender.com"
TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Stripe event payload builders
# ---------------------------------------------------------------------------

def _stripe_event(event_type: str, data_object: dict, event_id: str = None) -> dict:
    """Build a minimal Stripe event payload."""
    return {
        "id": event_id or f"evt_test_{event_type.replace('.', '_')}_{int(time.time())}",
        "object": "event",
        "type": event_type,
        "api_version": "2023-10-16",
        "created": int(time.time()),
        "data": {
            "object": data_object,
        },
        "livemode": False,
        "pending_webhooks": 1,
        "request": {"id": "req_test", "idempotency_key": None},
    }


def checkout_completed_event(metadata: dict = None) -> dict:
    return _stripe_event("checkout.session.completed", {
        "id": "cs_test_checkout_001",
        "object": "checkout.session",
        "mode": "subscription",
        "customer": "cus_test_e2e_001",
        "subscription": "sub_test_e2e_001",
        "metadata": metadata or {
            "type": "employer_subscription",
            "email": "test-webhook@civicscale-testing.internal",
            "tier": "starter",
            "company_name": "Webhook Test Corp",
        },
        "customer_email": "test-webhook@civicscale-testing.internal",
    })


def subscription_updated_event() -> dict:
    return _stripe_event("customer.subscription.updated", {
        "id": "sub_test_e2e_001",
        "object": "subscription",
        "customer": "cus_test_e2e_001",
        "status": "active",
        "items": {
            "data": [{
                "price": {"id": "price_test_starter"},
                "quantity": 1,
            }],
        },
        "current_period_end": int(time.time()) + 30 * 86400,
        "cancel_at_period_end": False,
    })


def subscription_deleted_event() -> dict:
    return _stripe_event("customer.subscription.deleted", {
        "id": "sub_test_e2e_001",
        "object": "subscription",
        "customer": "cus_test_e2e_001",
        "status": "canceled",
    })


def payment_failed_event() -> dict:
    return _stripe_event("invoice.payment_failed", {
        "id": "in_test_failed_001",
        "object": "invoice",
        "customer": "cus_test_e2e_001",
        "subscription": "sub_test_e2e_001",
        "status": "open",
        "amount_due": 29900,
        "currency": "usd",
    })


def payment_succeeded_event() -> dict:
    return _stripe_event("invoice.payment_succeeded", {
        "id": "in_test_success_001",
        "object": "invoice",
        "customer": "cus_test_e2e_001",
        "subscription": "sub_test_e2e_001",
        "status": "paid",
        "amount_paid": 29900,
        "currency": "usd",
    })


# ---------------------------------------------------------------------------
# Webhook endpoints
# ---------------------------------------------------------------------------

WEBHOOK_ENDPOINTS = [
    ("/api/billing/subscription/webhook", "billing"),
    ("/api/employer/webhook", "employer"),
    ("/api/provider/subscription/webhook", "provider"),
    ("/api/health/auth/webhook", "health"),
]


# ---------------------------------------------------------------------------
# Tests: Signature validation (all endpoints reject bad signatures)
# ---------------------------------------------------------------------------

class TestWebhookSignatureValidation:
    """All webhook endpoints must reject payloads without valid Stripe signature."""

    @pytest.mark.parametrize("endpoint,product", WEBHOOK_ENDPOINTS)
    def test_rejects_missing_signature(self, endpoint, product):
        """No stripe-signature header → 400."""
        event = checkout_completed_event()
        r = httpx.post(
            f"{BASE_URL}{endpoint}",
            content=json.dumps(event),
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 400, (
            f"{product} webhook accepted payload without signature: {r.status_code}"
        )

    @pytest.mark.parametrize("endpoint,product", WEBHOOK_ENDPOINTS)
    def test_rejects_invalid_signature(self, endpoint, product):
        """Invalid stripe-signature header → 400."""
        event = checkout_completed_event()
        r = httpx.post(
            f"{BASE_URL}{endpoint}",
            content=json.dumps(event),
            headers={
                "Content-Type": "application/json",
                "stripe-signature": "t=1234567890,v1=invalid_signature_value",
            },
            timeout=TIMEOUT,
        )
        assert r.status_code == 400, (
            f"{product} webhook accepted invalid signature: {r.status_code}"
        )


# ---------------------------------------------------------------------------
# Tests: Event type coverage (structural — verifies endpoint routing)
# ---------------------------------------------------------------------------

class TestCheckoutSessionCompleted:
    """checkout.session.completed event — the most critical webhook."""

    @pytest.mark.parametrize("endpoint,product", WEBHOOK_ENDPOINTS)
    def test_rejected_without_signature(self, endpoint, product):
        event = checkout_completed_event()
        r = httpx.post(
            f"{BASE_URL}{endpoint}",
            content=json.dumps(event),
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 400

    @pytest.mark.parametrize("endpoint,product", WEBHOOK_ENDPOINTS)
    def test_idempotent_replay(self, endpoint, product):
        """Same event sent twice produces same response (both 400 bad sig)."""
        event = checkout_completed_event()
        payload = json.dumps(event)
        headers = {"Content-Type": "application/json"}

        r1 = httpx.post(f"{BASE_URL}{endpoint}", content=payload,
                        headers=headers, timeout=TIMEOUT)
        r2 = httpx.post(f"{BASE_URL}{endpoint}", content=payload,
                        headers=headers, timeout=TIMEOUT)

        assert r1.status_code == r2.status_code, (
            f"{product}: replay gave different status {r1.status_code} vs {r2.status_code}"
        )


class TestSubscriptionUpdated:
    """customer.subscription.updated — syncs tier and status changes."""

    @pytest.mark.parametrize("endpoint,product", WEBHOOK_ENDPOINTS)
    def test_rejected_without_signature(self, endpoint, product):
        event = subscription_updated_event()
        r = httpx.post(
            f"{BASE_URL}{endpoint}",
            content=json.dumps(event),
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 400

    @pytest.mark.parametrize("endpoint,product", WEBHOOK_ENDPOINTS)
    def test_idempotent_replay(self, endpoint, product):
        event = subscription_updated_event()
        payload = json.dumps(event)
        headers = {"Content-Type": "application/json"}

        r1 = httpx.post(f"{BASE_URL}{endpoint}", content=payload,
                        headers=headers, timeout=TIMEOUT)
        r2 = httpx.post(f"{BASE_URL}{endpoint}", content=payload,
                        headers=headers, timeout=TIMEOUT)
        assert r1.status_code == r2.status_code


class TestSubscriptionDeleted:
    """customer.subscription.deleted — reverts to free/expired tier."""

    @pytest.mark.parametrize("endpoint,product", WEBHOOK_ENDPOINTS)
    def test_rejected_without_signature(self, endpoint, product):
        event = subscription_deleted_event()
        r = httpx.post(
            f"{BASE_URL}{endpoint}",
            content=json.dumps(event),
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 400

    @pytest.mark.parametrize("endpoint,product", WEBHOOK_ENDPOINTS)
    def test_idempotent_replay(self, endpoint, product):
        event = subscription_deleted_event()
        payload = json.dumps(event)
        headers = {"Content-Type": "application/json"}

        r1 = httpx.post(f"{BASE_URL}{endpoint}", content=payload,
                        headers=headers, timeout=TIMEOUT)
        r2 = httpx.post(f"{BASE_URL}{endpoint}", content=payload,
                        headers=headers, timeout=TIMEOUT)
        assert r1.status_code == r2.status_code


class TestPaymentFailed:
    """invoice.payment_failed — marks subscription as past_due."""

    @pytest.mark.parametrize("endpoint,product", WEBHOOK_ENDPOINTS)
    def test_rejected_without_signature(self, endpoint, product):
        event = payment_failed_event()
        r = httpx.post(
            f"{BASE_URL}{endpoint}",
            content=json.dumps(event),
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 400

    @pytest.mark.parametrize("endpoint,product", WEBHOOK_ENDPOINTS)
    def test_idempotent_replay(self, endpoint, product):
        event = payment_failed_event()
        payload = json.dumps(event)
        headers = {"Content-Type": "application/json"}

        r1 = httpx.post(f"{BASE_URL}{endpoint}", content=payload,
                        headers=headers, timeout=TIMEOUT)
        r2 = httpx.post(f"{BASE_URL}{endpoint}", content=payload,
                        headers=headers, timeout=TIMEOUT)
        assert r1.status_code == r2.status_code


class TestPaymentSucceeded:
    """invoice.payment_succeeded — logged, no DB mutation."""

    @pytest.mark.parametrize("endpoint,product", WEBHOOK_ENDPOINTS)
    def test_rejected_without_signature(self, endpoint, product):
        event = payment_succeeded_event()
        r = httpx.post(
            f"{BASE_URL}{endpoint}",
            content=json.dumps(event),
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 400

    @pytest.mark.parametrize("endpoint,product", WEBHOOK_ENDPOINTS)
    def test_idempotent_replay(self, endpoint, product):
        event = payment_succeeded_event()
        payload = json.dumps(event)
        headers = {"Content-Type": "application/json"}

        r1 = httpx.post(f"{BASE_URL}{endpoint}", content=payload,
                        headers=headers, timeout=TIMEOUT)
        r2 = httpx.post(f"{BASE_URL}{endpoint}", content=payload,
                        headers=headers, timeout=TIMEOUT)
        assert r1.status_code == r2.status_code


# ---------------------------------------------------------------------------
# Tests: Payload structure validation
# ---------------------------------------------------------------------------

class TestPayloadStructure:
    """Verify webhook endpoints handle malformed payloads gracefully."""

    @pytest.mark.parametrize("endpoint,product", WEBHOOK_ENDPOINTS)
    def test_empty_body(self, endpoint, product):
        """Empty body → 400 (not 500)."""
        r = httpx.post(
            f"{BASE_URL}{endpoint}",
            content=b"",
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT,
        )
        assert r.status_code in (400, 422), (
            f"{product} returned {r.status_code} for empty body (expected 400/422)"
        )

    @pytest.mark.parametrize("endpoint,product", WEBHOOK_ENDPOINTS)
    def test_invalid_json(self, endpoint, product):
        """Invalid JSON → 400 (not 500)."""
        r = httpx.post(
            f"{BASE_URL}{endpoint}",
            content=b"not json at all",
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT,
        )
        assert r.status_code in (400, 422), (
            f"{product} returned {r.status_code} for invalid JSON (expected 400/422)"
        )

    @pytest.mark.parametrize("endpoint,product", WEBHOOK_ENDPOINTS)
    def test_missing_type_field(self, endpoint, product):
        """JSON without 'type' field → 400."""
        r = httpx.post(
            f"{BASE_URL}{endpoint}",
            content=json.dumps({"data": {"object": {}}}),
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT,
        )
        assert r.status_code in (400, 422)
