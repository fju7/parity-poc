"""
Bootstrap helpers for creating test data via the live API.

These are NOT pytest tests — they are utility functions called by test modules
that need authenticated sessions or pre-existing data.

All mutations are idempotent: calling them twice produces the same state.
"""

import httpx
from conftest import BASE_URL, REQUEST_TIMEOUT, TEST_ADMIN_EMAIL, TEST_ANALYST_EMAIL


def get_or_create_session(
    email: str,
    product: str,
    *,
    company_name: str | None = None,
    company_type: str | None = None,
    full_name: str = "Test User",
) -> dict:
    """
    Request OTP, read it from Supabase, verify it, and return the session dict.

    Because we cannot read OTP codes without the service-role key hitting
    the otp_codes table directly, and the test emails are fake addresses
    that never receive mail, this function relies on the Supabase service
    role to peek at the OTP.

    Returns dict with keys: token, email, product, user, company (or subset).
    Returns empty dict if the flow cannot complete (e.g. missing env vars).
    """
    from conftest import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

    if not SUPABASE_SERVICE_ROLE_KEY:
        return {}

    client = httpx.Client(base_url=BASE_URL, timeout=REQUEST_TIMEOUT)
    sb = httpx.Client(
        base_url=f"{SUPABASE_URL}/rest/v1/",
        headers={
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
        timeout=REQUEST_TIMEOUT,
    )

    # Step 1: Send OTP
    send_resp = client.post(
        "/api/auth/send-otp",
        json={"email": email, "product": product},
    )
    if send_resp.status_code != 200:
        return {}

    # Step 2: Read OTP from Supabase
    otp_resp = sb.get(
        "otp_codes",
        params={
            "select": "code",
            "email": f"eq.{email}",
            "product": f"eq.{product}",
            "order": "created_at.desc",
            "limit": "1",
        },
    )
    if otp_resp.status_code != 200 or not otp_resp.json():
        return {}

    code = otp_resp.json()[0]["code"]

    # Step 3: Verify OTP
    verify_resp = client.post(
        "/api/auth/verify-otp",
        json={"email": email, "code": code, "product": product},
    )
    if verify_resp.status_code != 200:
        return {}

    data = verify_resp.json()

    # Step 4: If needs_company and we have company info, create it
    if data.get("needs_company") and company_name and company_type:
        create_resp = client.post(
            "/api/auth/company",
            json={
                "email": email,
                "full_name": full_name,
                "company_name": company_name,
                "company_type": company_type,
            },
        )
        if create_resp.status_code == 200:
            data = create_resp.json()

    client.close()
    sb.close()
    return data
