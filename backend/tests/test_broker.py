"""
TEST-1: Broker API endpoint tests.

Covers: /api/broker/ — plan, subscribe, cancel, portal, account,
        clients (CRUD, onboard, bulk, share, notify, activity),
        portfolio, renewal pipeline, referral system, prospects.
"""

import pytest


class TestBrokerPlan:
    """GET /api/broker/plan"""

    def test_plan_no_auth(self, client):
        r = client.get("/api/broker/plan")
        assert r.status_code in (401, 403)


class TestBrokerSubscribe:
    """POST /api/broker/subscribe"""

    def test_subscribe_no_auth(self, client):
        r = client.post("/api/broker/subscribe")
        assert r.status_code in (401, 403)


class TestBrokerCancelSubscription:
    """POST /api/broker/cancel-subscription"""

    def test_cancel_no_auth(self, client):
        r = client.post("/api/broker/cancel-subscription")
        assert r.status_code in (401, 403)


class TestBrokerReactivate:
    """POST /api/broker/reactivate-subscription"""

    def test_reactivate_no_auth(self, client):
        r = client.post("/api/broker/reactivate-subscription")
        assert r.status_code in (401, 403)


class TestBrokerPortal:
    """POST /api/broker/portal"""

    def test_portal_no_auth(self, client):
        r = client.post("/api/broker/portal")
        assert r.status_code in (401, 403)


class TestBrokerAccount:
    """GET/PATCH /api/broker/account"""

    def test_get_account_no_auth(self, client):
        r = client.get("/api/broker/account")
        assert r.status_code in (401, 403)

    def test_patch_account_no_auth(self, client):
        r = client.patch("/api/broker/account", json={
            "contact_name": "Test Broker",
        })
        assert r.status_code in (401, 403)


class TestBrokerClients:
    """GET /api/broker/clients, POST /api/broker/clients/add"""

    def test_list_clients_no_auth(self, client):
        r = client.get("/api/broker/clients")
        assert r.status_code in (401, 403)

    def test_add_client_no_auth(self, client):
        r = client.post("/api/broker/clients/add", json={
            "employer_email": "test@test.com",
        })
        assert r.status_code in (401, 403)

    def test_delete_client_no_auth(self, client):
        r = client.delete("/api/broker/clients/test@test.com")
        assert r.status_code in (401, 403)


class TestBrokerClientSummary:
    """GET /api/broker/clients/{email}/summary"""

    def test_client_summary_no_auth(self, client):
        r = client.get("/api/broker/clients/test@test.com/summary")
        assert r.status_code in (401, 403)


class TestBrokerOnboard:
    """POST /api/broker/clients/onboard"""

    def test_onboard_no_auth(self, client):
        r = client.post("/api/broker/clients/onboard", json={
            "company_name": "Test Corp",
            "industry": "Manufacturing",
            "state": "MD",
        })
        assert r.status_code in (401, 403)


class TestBrokerBulkOnboard:
    """POST /api/broker/clients/bulk-onboard"""

    def test_bulk_onboard_no_auth(self, client):
        r = client.post("/api/broker/clients/bulk-onboard", json={
            "clients": [{
                "company_name": "Test1",
                "employee_count_range": "51-200",
                "industry": "Manufacturing",
                "state": "MD",
            }],
        })
        assert r.status_code in (401, 403)


class TestBrokerShareLink:
    """GET /api/broker/clients/{email}/share-link"""

    def test_share_link_no_auth(self, client):
        r = client.get("/api/broker/clients/test@test.com/share-link")
        assert r.status_code in (401, 403)


class TestBrokerNotify:
    """POST /api/broker/clients/{email}/notify"""

    def test_notify_no_auth(self, client):
        r = client.post("/api/broker/clients/test@test.com/notify", json={})
        assert r.status_code in (401, 403)


class TestBrokerActivity:
    """GET /api/broker/clients/{email}/activity"""

    def test_activity_no_auth(self, client):
        r = client.get("/api/broker/clients/test@test.com/activity")
        assert r.status_code in (401, 403)


class TestBrokerPortfolio:
    """GET /api/broker/portfolio"""

    def test_portfolio_no_auth(self, client):
        r = client.get("/api/broker/portfolio")
        assert r.status_code in (401, 403)


class TestBrokerRenewalPipeline:
    """GET /api/broker/renewal-pipeline"""

    def test_renewal_pipeline_no_auth(self, client):
        r = client.get("/api/broker/renewal-pipeline")
        assert r.status_code in (401, 403)


class TestBrokerRenewalPrep:
    """GET /api/broker/renewal-prep/{company_name}"""

    def test_renewal_prep_no_auth(self, client):
        r = client.get("/api/broker/renewal-prep/Test%20Corp")
        assert r.status_code in (401, 403)


class TestBrokerSendRenewalReminders:
    """POST /api/broker/send-renewal-reminders"""

    def test_renewal_reminders_no_cron_secret(self, client):
        r = client.post("/api/broker/send-renewal-reminders")
        assert r.status_code in (401, 403)


class TestBrokerProspects:
    """POST /api/broker/prospect-benchmark, GET /api/broker/prospects"""

    def test_prospect_benchmark_no_auth(self, client):
        r = client.post("/api/broker/prospect-benchmark", json={
            "company_name": "Prospect Inc",
            "employee_count_range": "51-200",
            "industry": "Manufacturing",
            "state": "MD",
        })
        assert r.status_code in (401, 403)

    def test_list_prospects_no_auth(self, client):
        r = client.get("/api/broker/prospects")
        assert r.status_code in (401, 403)


class TestBrokerReferral:
    """GET /api/broker/referral, POST /api/broker/referral/send"""

    def test_get_referral_no_auth(self, client):
        r = client.get("/api/broker/referral")
        assert r.status_code in (401, 403)

    def test_send_referral_no_auth(self, client):
        r = client.post("/api/broker/referral/send", json={
            "recipient_email": "colleague@test.com",
        })
        assert r.status_code in (401, 403, 422, 500)

    def test_referral_stats_no_auth(self, client):
        r = client.get("/api/broker/referral/stats")
        assert r.status_code in (401, 403)


class TestBrokerCaaLetter:
    """POST /api/broker/clients/{email}/caa-letter"""

    def test_caa_letter_no_auth(self, client):
        r = client.post("/api/broker/clients/test@test.com/caa-letter")
        assert r.status_code in (401, 403)


class TestBrokerInviteEmployer:
    """POST /api/broker/invite-employer"""

    def test_invite_employer_no_auth(self, client):
        r = client.post("/api/broker/invite-employer", json={
            "email": "employer@test.com",
        })
        assert r.status_code in (401, 403)
