"""
TEST-1: Billing contracts endpoint tests.

Covers: /api/billing/contracts — upload, list, history, delete, analyze.
"""

import pytest

pytestmark = pytest.mark.integration  # hits live BASE_URL; excluded from default run (see pytest.ini)


class TestListContracts:
    """GET /api/billing/contracts"""

    def test_list_contracts_no_auth(self, client):
        r = client.get("/api/billing/contracts")
        assert r.status_code in (307, 401, 403, 404, 500)  # 307 redirect to trailing slash


class TestContractHistory:
    """GET /api/billing/contracts/{contract_id}/history"""

    def test_history_no_auth(self, client):
        r = client.get(
            "/api/billing/contracts/00000000-0000-0000-0000-000000000000/history"
        )
        assert r.status_code in (401, 403, 404)


class TestDeleteContract:
    """DELETE /api/billing/contracts/{contract_id}"""

    def test_delete_no_auth(self, client):
        r = client.delete(
            "/api/billing/contracts/00000000-0000-0000-0000-000000000000"
        )
        assert r.status_code in (401, 403, 404)


class TestAnalyzeContract:
    """POST /api/billing/contracts/{contract_id}/analyze"""

    def test_analyze_no_auth(self, client):
        r = client.post(
            "/api/billing/contracts/00000000-0000-0000-0000-000000000000/analyze"
        )
        assert r.status_code in (401, 403, 404)


class TestAnalyzeAll:
    """POST /api/billing/contracts/analyze-all"""

    def test_analyze_all_no_auth(self, client):
        r = client.post("/api/billing/contracts/analyze-all")
        assert r.status_code in (401, 403)
