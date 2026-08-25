/**
 * Post-deploy smoke check for host-based routing.
 *
 * Run this immediately after any deploy that touches vercel.json, siteMeta.js,
 * or generate-host-html.mjs:
 *
 *     npm run smoke              # production hosts
 *     npm run smoke -- --staging # staging hosts too
 *
 * WHY THIS AND NOT A PREVIEW DEPLOY
 * ---------------------------------
 * Vercel preview URLs (parity-poc-git-*.vercel.app) match none of the host
 * conditions in vercel.json, so every preview falls through to the catch-all.
 * A preview therefore cannot tell you whether health.civicscale.ai routes
 * correctly — it is structurally blind to the exact failure this guards.
 * Production is the first place host routing is real, so the check has to run
 * against production, right after the deploy, while you are still watching.
 *
 * Exits non-zero on any failure so it can gate a deploy script or CI step.
 * On failure: roll back in the Vercel dashboard (Deployments -> the previous
 * production deployment -> Promote to Production), or `vercel rollback`.
 */

import { SITE_META, HOST_MAP } from "../src/lib/siteMeta.js";

const includeStaging = process.argv.includes("--staging");
const TIMEOUT_MS = 15000;

const hosts = Object.entries(HOST_MAP).filter(
  ([hostname]) => includeStaging || !hostname.startsWith("staging-")
);

/** Pull the <title> out of served HTML without parsing the whole document. */
function titleOf(html) {
  const m = html.match(/<title>([\s\S]*?)<\/title>/i);
  return m ? m[1].trim() : null;
}

function decode(s) {
  return s
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"');
}

async function get(url) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      signal: ctl.signal,
      redirect: "follow",
      headers: { "User-Agent": "parity-smoke-check" },
    });
    return { status: res.status, body: await res.text() };
  } finally {
    clearTimeout(timer);
  }
}

async function checkHost(hostname, { key, index }) {
  const expected = SITE_META[key];
  const failures = [];

  // 1. The document serves, and serves THIS product's title.
  try {
    const { status, body } = await get(`https://${hostname}/`);
    if (status !== 200) {
      failures.push(`GET / returned ${status}`);
    } else {
      const title = titleOf(body);
      if (!title) {
        failures.push("no <title> in the served HTML");
      } else if (decode(title) !== expected.title) {
        failures.push(
          `served the wrong product\n      expected: ${expected.title}\n      got:      ${decode(title)}`
        );
      }
      if (!body.includes(`<link rel="canonical" href="${expected.url}"`)) {
        failures.push(`canonical is not ${expected.url}`);
      }
      const wantRobots = index ? "index, follow" : "noindex, nofollow";
      if (!body.includes(`content="${wantRobots}"`)) {
        failures.push(`robots meta is not "${wantRobots}"`);
      }
    }
  } catch (err) {
    failures.push(`GET / failed: ${err.message}`);
  }

  // 2. robots.txt matches the host's indexing policy.
  try {
    const { status, body } = await get(`https://${hostname}/robots.txt`);
    if (status !== 200) {
      failures.push(`GET /robots.txt returned ${status}`);
    } else if (body.includes("<!doctype") || body.includes("<html")) {
      failures.push("robots.txt served HTML — the rewrite is missing");
    } else {
      const wants = index ? "Allow: /" : "Disallow: /";
      if (!body.includes(wants)) {
        failures.push(`robots.txt does not contain "${wants}"`);
      }
    }
  } catch (err) {
    failures.push(`GET /robots.txt failed: ${err.message}`);
  }

  return failures;
}

console.log(`Checking ${hosts.length} hosts...\n`);

const results = await Promise.all(
  hosts.map(async ([hostname, cfg]) => [hostname, await checkHost(hostname, cfg)])
);

let failed = 0;
for (const [hostname, failures] of results) {
  if (failures.length === 0) {
    console.log(`  PASS  ${hostname}`);
  } else {
    failed++;
    console.log(`  FAIL  ${hostname}`);
    for (const f of failures) console.log(`        ${f}`);
  }
}

if (failed > 0) {
  console.error(
    `\n${failed} of ${hosts.length} hosts failed.\n\n` +
      `Roll back now, then diagnose:\n` +
      `  vercel rollback\n` +
      `or in the dashboard: Deployments -> previous production deploy -> Promote to Production.\n`
  );
  process.exit(1);
}

console.log(`\nAll ${hosts.length} hosts serving correctly.`);
