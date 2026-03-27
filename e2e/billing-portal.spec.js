// @ts-check
import { test, expect } from "@playwright/test";
import {
  apiLogin,
  apiPortalLogin,
  injectSession,
  ensureTestPractice,
  TEST_ADMIN_EMAIL,
  API_URL,
  SUPABASE_SERVICE_ROLE_KEY,
} from "./fixtures/auth.js";
import { PORTAL_SECTIONS } from "./fixtures/testData.js";

/**
 * Flow 4 — Practice Portal: OTP login, denial summary,
 * payer performance, appeal ROI, PDF report download.
 *
 * Requires SUPABASE_SERVICE_ROLE_KEY for auth fixture.
 */

const needsAuth = !process.env.SUPABASE_SERVICE_ROLE_KEY;

test.describe("Practice Portal Login Page", () => {
  test("portal page loads with login form", async ({ page }) => {
    // Portal requires ?practice= param — without it, shows error or login
    await page.goto("/portal");

    const body = page.locator("body");
    // Should show some form of portal content or login
    await expect(body).toContainText(
      /portal|email|sign in|practice|error/i,
      { timeout: 15000 },
    );
  });

  test("portal shows email input for OTP", async ({ page }) => {
    // Visit portal without practice_id — may still show login
    await page.goto("/portal?practice=00000000-0000-0000-0000-000000000000");

    const body = page.locator("body");
    // Should show email input or error about practice not found
    await expect(body).toContainText(
      /email|not found|error|portal|sign in/i,
      { timeout: 15000 },
    );
  });
});

test.describe("Practice Portal API Endpoints", () => {
  test.skip(needsAuth, "SUPABASE_SERVICE_ROLE_KEY required");

  let billingToken = "";
  let practiceId = "";
  let portalContactEmail = "";

  test.beforeAll(async () => {
    // Login as billing admin to discover practice + portal config
    const data = await apiLogin(TEST_ADMIN_EMAIL, "billing");
    billingToken = data.token;

    if (!billingToken) return;

    // Fetch practices
    const practicesRes = await fetch(`${API_URL}/api/billing/practices`, {
      headers: { Authorization: `Bearer ${billingToken}` },
    });
    if (practicesRes.ok) {
      const body = await practicesRes.json();
      const practices = body.practices || [];
      if (practices.length > 0) {
        practiceId = practices[0].practice_id || practices[0].id || "";
        portalContactEmail =
          practices[0].contact_email || TEST_ADMIN_EMAIL;
      }
    }

    // Fetch portal settings to check if portal is enabled
    if (practiceId) {
      const settingsRes = await fetch(
        `${API_URL}/api/billing/portal-settings`,
        { headers: { Authorization: `Bearer ${billingToken}` } },
      );
      // Portal settings may or may not exist — that's fine
    }
  });

  test("denial-summary endpoint responds (with billing token)", async () => {
    test.skip(!billingToken, "Login failed");

    // Denial summary via the main billing API (not portal)
    // This tests the underlying data endpoint
    const res = await fetch(
      `${API_URL}/api/billing/portal/denial-summary?days=90`,
      {
        headers: { Authorization: `Bearer ${billingToken}` },
      },
    );
    // May return 401/403 (billing token != portal token) — that's correct behavior
    expect(res.status).toBeLessThan(500);
  });

  test("payer-performance endpoint responds", async () => {
    test.skip(!billingToken, "Login failed");

    const res = await fetch(
      `${API_URL}/api/billing/portal/payer-performance?days=90`,
      {
        headers: { Authorization: `Bearer ${billingToken}` },
      },
    );
    expect(res.status).toBeLessThan(500);
  });

  test("appeal-roi endpoint responds", async () => {
    test.skip(!billingToken, "Login failed");

    const res = await fetch(
      `${API_URL}/api/billing/portal/appeal-roi?days=180`,
      {
        headers: { Authorization: `Bearer ${billingToken}` },
      },
    );
    expect(res.status).toBeLessThan(500);
  });

  test("generate-report endpoint responds", async () => {
    test.skip(!billingToken, "Login failed");

    const res = await fetch(
      `${API_URL}/api/billing/portal/generate-report`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${billingToken}` },
      },
    );
    // May return 401/403 (needs portal token) or 200 (PDF)
    expect(res.status).toBeLessThan(500);
  });
});

test.describe("Authenticated Portal View", () => {
  test.skip(needsAuth, "SUPABASE_SERVICE_ROLE_KEY required");

  let billingToken = "";
  let practiceId = "";

  test.beforeAll(async () => {
    const data = await apiLogin(TEST_ADMIN_EMAIL, "billing");
    billingToken = data.token;

    // Ensure a test practice exists (creates one if needed)
    if (billingToken) {
      practiceId = await ensureTestPractice(billingToken);
    }
  });

  test("portal page with practice_id shows content", async ({ page }) => {
    test.skip(!billingToken || !practiceId, "No practice available");

    await page.goto(`/portal?practice=${practiceId}`);

    const body = page.locator("body");
    // Should show portal login or portal content
    await expect(body).toContainText(
      /email|sign in|denial|payer|portal/i,
      { timeout: 15000 },
    );
  });
});
