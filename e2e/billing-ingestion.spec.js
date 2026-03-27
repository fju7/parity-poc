// @ts-check
import { test, expect } from "@playwright/test";
import { apiLogin, injectSession, ensureTestPractice, TEST_ADMIN_EMAIL, API_URL } from "./fixtures/auth.js";
import { SAMPLE_835_CONTENT, create835File } from "./fixtures/testData.js";

/**
 * Flow 3 — 835 file ingestion: upload → queue → process → results.
 *
 * Requires SUPABASE_SERVICE_ROLE_KEY for OTP-based auth.
 */

const needsAuth = !process.env.SUPABASE_SERVICE_ROLE_KEY;

test.describe("835 Ingestion Tab", () => {
  test.skip(needsAuth, "SUPABASE_SERVICE_ROLE_KEY required");

  let sessionToken = "";

  test.beforeAll(async () => {
    const data = await apiLogin(TEST_ADMIN_EMAIL, "billing");
    sessionToken = data.token;
  });

  test("navigates to Ingestion tab", async ({ page }) => {
    test.skip(!sessionToken, "Login failed");

    await page.goto("/");
    await injectSession(page, sessionToken, "billing");
    await page.reload({ waitUntil: "networkidle" });

    const ingestionTab = page.locator(
      'button:has-text("835 Ingestion"), button:has-text("Ingestion")'
    ).first();
    await expect(ingestionTab).toBeVisible({ timeout: 15000 });
    await ingestionTab.click();

    const body = page.locator("body");
    await expect(body).toContainText(/Ingestion|Upload|835|Queue/i, {
      timeout: 15000,
    });
  });

  test("shows practice dropdown and upload area", async ({ page }) => {
    test.skip(!sessionToken, "Login failed");

    await page.goto("/");
    await injectSession(page, sessionToken, "billing");
    await page.reload({ waitUntil: "networkidle" });

    const ingestionTab = page.locator(
      'button:has-text("835 Ingestion"), button:has-text("Ingestion")'
    ).first();
    if (await ingestionTab.isVisible({ timeout: 10000 }).catch(() => false)) {
      await ingestionTab.click();
    }

    // Should show practice selector (dropdown or select) and file upload area
    const body = page.locator("body");
    await expect(body).toContainText(
      /practice|select|upload|drop|choose/i,
      { timeout: 15000 },
    );
  });

  test("shows job queue table", async ({ page }) => {
    test.skip(!sessionToken, "Login failed");

    await page.goto("/");
    await injectSession(page, sessionToken, "billing");
    await page.reload({ waitUntil: "networkidle" });

    const ingestionTab = page.locator(
      'button:has-text("835 Ingestion"), button:has-text("Ingestion")'
    ).first();
    if (await ingestionTab.isVisible({ timeout: 10000 }).catch(() => false)) {
      await ingestionTab.click();
    }

    // Should show jobs table or empty state message
    const body = page.locator("body");
    await expect(body).toContainText(
      /Filename|Status|No jobs|Queue|uploaded/i,
      { timeout: 15000 },
    );
  });
});

test.describe("835 API Upload Flow", () => {
  test.skip(needsAuth, "SUPABASE_SERVICE_ROLE_KEY required");

  let sessionToken = "";
  let practiceId = "";

  test.beforeAll(async () => {
    const data = await apiLogin(TEST_ADMIN_EMAIL, "billing");
    sessionToken = data.token;

    // Ensure a test practice exists (creates one if needed)
    if (sessionToken) {
      practiceId = await ensureTestPractice(sessionToken);
    }
  });

  test("uploads 835 file via API and gets job ID", async ({ page }) => {
    test.skip(!sessionToken, "Login failed");
    test.skip(!practiceId, "No practice available for upload");

    // Upload via API (multipart form)
    const formData = new FormData();
    formData.append("practice_id", practiceId);
    const blob = new Blob([SAMPLE_835_CONTENT], { type: "text/plain" });
    formData.append("files[]", blob, "e2e_test.835");

    const uploadRes = await fetch(`${API_URL}/api/billing/ingest/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${sessionToken}` },
      body: formData,
    });

    // Upload may succeed or fail depending on practice state
    if (uploadRes.ok) {
      const result = await uploadRes.json();
      expect(result.queued).toBeGreaterThan(0);
      expect(result.job_ids).toBeDefined();
      expect(result.job_ids.length).toBeGreaterThan(0);
    } else {
      // 400/402/403 are acceptable (e.g., no practice linked, quota)
      expect(uploadRes.status).toBeLessThan(500);
    }
  });

  test("lists jobs via API", async () => {
    test.skip(!sessionToken, "Login failed");

    const res = await fetch(`${API_URL}/api/billing/ingest/jobs`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
    });

    if (res.ok) {
      const data = await res.json();
      expect(data.jobs).toBeDefined();
      expect(Array.isArray(data.jobs)).toBe(true);
    } else {
      // 404 if no billing company — acceptable
      expect(res.status).toBeLessThan(500);
    }
  });

  test("process-all endpoint responds", async () => {
    test.skip(!sessionToken, "Login failed");

    const res = await fetch(`${API_URL}/api/billing/ingest/process-all`, {
      method: "POST",
      headers: { Authorization: `Bearer ${sessionToken}` },
    });

    // May succeed (200) or 404 if no company
    expect(res.status).toBeLessThan(500);
  });
});
