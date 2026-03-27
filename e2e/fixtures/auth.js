/**
 * Auth fixture — OTP-based login helpers for Playwright E2E tests.
 *
 * Strategy:
 *   1. POST /api/billing/send-otp  (or /api/auth/send-otp)
 *   2. Peek the OTP code from Supabase otp_codes table via service-role key
 *   3. POST /api/billing/verify-otp → session token
 *   4. Inject token into localStorage so the SPA picks it up on reload
 *
 * Requires env vars:
 *   SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
 */

const API_URL =
  process.env.API_URL || "https://parity-poc-api.onrender.com";
const SUPABASE_URL =
  process.env.SUPABASE_URL || "https://kfxxpscdwoemtzylhhhb.supabase.co";
const SUPABASE_SERVICE_ROLE_KEY =
  process.env.SUPABASE_SERVICE_ROLE_KEY || "";

const TEST_ADMIN_EMAIL = "test-admin@civicscale-testing.internal";

/**
 * Read the most-recent OTP code for an email + product from Supabase.
 */
async function peekOtp(email, product = "billing") {
  if (!SUPABASE_SERVICE_ROLE_KEY) {
    throw new Error("SUPABASE_SERVICE_ROLE_KEY is required for OTP peek");
  }
  const url = new URL(`${SUPABASE_URL}/rest/v1/otp_codes`);
  url.searchParams.set("select", "code");
  url.searchParams.set("email", `eq.${email}`);
  url.searchParams.set("product", `eq.${product}`);
  url.searchParams.set("order", "created_at.desc");
  url.searchParams.set("limit", "1");

  const res = await fetch(url.toString(), {
    headers: {
      apikey: SUPABASE_SERVICE_ROLE_KEY,
      Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
    },
  });
  if (!res.ok) throw new Error(`OTP peek failed: ${res.status}`);
  const rows = await res.json();
  if (!rows.length) throw new Error(`No OTP found for ${email}/${product}`);
  return rows[0].code;
}

/**
 * Full API-level login: send OTP → peek → verify → return session data.
 * Does NOT touch the browser — use injectSession() after this.
 */
async function apiLogin(email = TEST_ADMIN_EMAIL, product = "billing", _retryCount = 0) {
  // 1. Request OTP
  const sendEndpoint =
    product === "billing"
      ? `${API_URL}/api/billing/send-otp`
      : `${API_URL}/api/auth/send-otp`;

  const sendBody =
    product === "billing"
      ? { email }
      : { email, product };

  const sendRes = await fetch(sendEndpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(sendBody),
  });
  if (!sendRes.ok) {
    throw new Error(`send-otp failed: ${sendRes.status} ${await sendRes.text()}`);
  }

  // 2. Peek OTP from Supabase
  const code = await peekOtp(email, product);

  // 3. Verify OTP
  const verifyEndpoint =
    product === "billing"
      ? `${API_URL}/api/billing/verify-otp`
      : `${API_URL}/api/auth/verify-otp`;

  const verifyBody =
    product === "billing"
      ? { email, code }
      : { email, code, product };

  const verifyRes = await fetch(verifyEndpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(verifyBody),
  });
  if (!verifyRes.ok) {
    throw new Error(`verify-otp failed: ${verifyRes.status} ${await verifyRes.text()}`);
  }

  const data = await verifyRes.json();

  // 4. If the user has no billing company yet, register one automatically
  if (data.needs_company && product === "billing" && !data.token) {
    const regRes = await fetch(`${API_URL}/api/billing/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        full_name: "E2E Test Admin",
        company_name: "CivicScale E2E Testing",
      }),
    });
    if (regRes.ok) {
      return regRes.json();
    }
    // 409 = already exists — try logging in again
    if (regRes.status === 409) {
      if (_retryCount > 0) throw new Error("Registration loop detected");
      return apiLogin(email, product, _retryCount + 1);
    }
    throw new Error(`register failed: ${regRes.status} ${await regRes.text()}`);
  }

  // For non-billing products: if needs_company, create via /api/auth/company
  if (data.needs_company && product !== "billing" && !data.token) {
    const createRes = await fetch(`${API_URL}/api/auth/company`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        full_name: "E2E Test Admin",
        company_name: "CivicScale E2E Testing",
        company_type: product,
      }),
    });
    if (createRes.ok) {
      return createRes.json();
    }
    if (createRes.status === 409) {
      if (_retryCount > 0) throw new Error("Registration loop detected");
      return apiLogin(email, product, _retryCount + 1);
    }
    throw new Error(`company create failed: ${createRes.status}`);
  }

  return data;
}

/**
 * Portal-specific login for practice portal tests.
 */
async function apiPortalLogin(email, practiceId) {
  // 1. Send portal OTP
  const sendRes = await fetch(`${API_URL}/api/billing/portal/send-otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, practice_id: practiceId }),
  });
  if (!sendRes.ok) {
    throw new Error(`portal send-otp failed: ${sendRes.status}`);
  }

  // 2. Peek OTP (portal OTPs use product "billing" in otp_codes)
  const code = await peekOtp(email, "billing");

  // 3. Verify
  const verifyRes = await fetch(`${API_URL}/api/billing/portal/verify-otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code, practice_id: practiceId }),
  });
  if (!verifyRes.ok) {
    throw new Error(`portal verify-otp failed: ${verifyRes.status}`);
  }
  return verifyRes.json();
}

/**
 * Inject a session token into the browser's localStorage so the SPA
 * recognises the user as logged in on next navigation.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} token - session UUID
 * @param {"billing"|"portal"} type
 */
async function injectSession(page, token, type = "billing") {
  const key = type === "portal" ? "portal_token" : "cs_session_token";
  await page.evaluate(
    ([k, v]) => localStorage.setItem(k, v),
    [key, token],
  );
}

/**
 * Combined helper: API login + inject into page + reload.
 */
async function loginAndInject(page, email = TEST_ADMIN_EMAIL) {
  const data = await apiLogin(email, "billing");
  const token = data.token;
  if (!token) throw new Error("No token returned from login");
  await injectSession(page, token, "billing");
  await page.reload({ waitUntil: "networkidle" });
  return data;
}

/**
 * Ensure the test billing company has at least one practice linked.
 * Creates "E2E Test Practice" via the billing API if none exists.
 * Returns the practice_id (UUID) or empty string on failure.
 */
async function ensureTestPractice(sessionToken) {
  // 1. Check if practice already exists
  const listRes = await fetch(`${API_URL}/api/billing/practices`, {
    headers: { Authorization: `Bearer ${sessionToken}` },
  });
  if (listRes.ok) {
    const body = await listRes.json();
    if (body.practices?.length > 0) {
      return body.practices[0].practice_id;
    }
  }

  // 2. Create test practice via the same API the UI uses
  const addRes = await fetch(`${API_URL}/api/billing/practices`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${sessionToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      practice_name: "E2E Test Practice",
      contact_email: "e2e-practice@civicscale-testing.internal",
    }),
  });
  if (addRes.ok) {
    const data = await addRes.json();
    return data.practice_id;
  }
  if (addRes.status === 409) {
    // Already linked — re-fetch to get the ID
    const retry = await fetch(`${API_URL}/api/billing/practices`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
    });
    if (retry.ok) {
      const body = await retry.json();
      return body.practices?.[0]?.practice_id || "";
    }
  }
  return "";
}

export {
  peekOtp,
  apiLogin,
  apiPortalLogin,
  injectSession,
  loginAndInject,
  ensureTestPractice,
  API_URL,
  SUPABASE_URL,
  SUPABASE_SERVICE_ROLE_KEY,
  TEST_ADMIN_EMAIL,
};
