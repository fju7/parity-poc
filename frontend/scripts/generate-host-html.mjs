/**
 * Post-build: write one HTML entry point per hostname, with correct <head> tags.
 *
 * WHY
 * ---
 * We ship a single Vite bundle served from one Vercel project across seven
 * hostnames. index.html therefore carried one hardcoded title and description,
 * and main.jsx patched them per-host after hydration. Crawlers and link-preview
 * bots don't run JavaScript, so every product's shared links previewed with
 * whatever index.html happened to say — which was Parity Health's bill-analysis
 * copy, even on Parity Signal.
 *
 * This script reads the built dist/index.html once and writes a copy per
 * hostname with the head rewritten. vercel.json then points each host at its own
 * file. Same bundle, same asset hashes, no runtime cost, correct previews.
 *
 * It also emits a robots.txt per hostname so staging hosts stay out of the index.
 *
 * Per-ROUTE metadata — a distinct title for each Signal topic — is a different
 * problem that needs prerendering. It cannot be solved from the hostname alone.
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { SITE_META, HOST_MAP, DEFAULT_KEY } from "../src/lib/siteMeta.js";

const here = dirname(fileURLToPath(import.meta.url));
const dist = join(here, "..", "dist");
const indexPath = join(dist, "index.html");

if (!existsSync(indexPath)) {
  console.error("[host-html] dist/index.html not found — run vite build first.");
  process.exit(1);
}

const template = readFileSync(indexPath, "utf8");

/** Escape a value for use inside a double-quoted HTML attribute. */
function attr(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function headFor({ title, description, url, index }) {
  return [
    `<title>${attr(title)}</title>`,
    `<meta name="description" content="${attr(description)}" />`,
    `<link rel="canonical" href="${attr(url)}" />`,
    `<meta name="robots" content="${index ? "index, follow" : "noindex, nofollow"}" />`,
    `<meta property="og:type" content="website" />`,
    `<meta property="og:site_name" content="CivicScale" />`,
    `<meta property="og:title" content="${attr(title)}" />`,
    `<meta property="og:description" content="${attr(description)}" />`,
    `<meta property="og:url" content="${attr(url)}" />`,
    `<meta name="twitter:card" content="summary_large_image" />`,
    `<meta name="twitter:title" content="${attr(title)}" />`,
    `<meta name="twitter:description" content="${attr(description)}" />`,
  ]
    .map((tag) => `    ${tag}`)
    .join("\n");
}

/** Tags in the template that this script owns and replaces wholesale. */
const STRIP = [
  /^[ \t]*<title>[\s\S]*?<\/title>[ \t]*\n/gm,
  /^[ \t]*<meta\s+name="description"[^>]*>[ \t]*\n/gm,
  /^[ \t]*<meta\s+property="og:[^"]*"[^>]*>[ \t]*\n/gm,
  /^[ \t]*<meta\s+name="twitter:[^"]*"[^>]*>[ \t]*\n/gm,
  /^[ \t]*<link\s+rel="canonical"[^>]*>[ \t]*\n/gm,
  /^[ \t]*<meta\s+name="robots"[^>]*>[ \t]*\n/gm,
];

function render(meta) {
  let html = template;
  for (const re of STRIP) html = html.replace(re, "");
  html = html.replace(/\n{3,}/g, "\n\n");
  // Swallow the whitespace before </head> so the injected block controls its
  // own indentation rather than inheriting whatever the strip left behind.
  return html.replace(/[ \t]*\n?[ \t]*<\/head>/, `\n${headFor(meta)}\n  </head>`);
}

const outDir = join(dist, "_hosts");
mkdirSync(outDir, { recursive: true });

const written = [];
for (const [hostname, { key, index }] of Object.entries(HOST_MAP)) {
  const meta = SITE_META[key] || SITE_META[DEFAULT_KEY];
  const slug = hostname.replace(/\./g, "_");

  writeFileSync(join(outDir, `${slug}.html`), render({ ...meta, index }));
  writeFileSync(
    join(outDir, `robots-${slug}.txt`),
    index ? "User-agent: *\nAllow: /\n" : "User-agent: *\nDisallow: /\n"
  );

  written.push(hostname);
}

// The catch-all rewrite still serves dist/index.html. Give it the main-site
// metadata rather than leaving whatever the source template happened to carry.
writeFileSync(indexPath, render({ ...SITE_META[DEFAULT_KEY], index: true }));

console.log(
  `[host-html] wrote ${written.length} host entry points + robots to dist/_hosts\n` +
    written.map((h) => `           ${h}`).join("\n")
);

// ---------------------------------------------------------------------------
// Invariant check: vercel.json and this script must agree.
//
// The rewrites are configuration. Nothing type-checks them, and the failure is
// silent and total — a rewrite pointing at a file that was never generated
// makes that entire product return 404, with no error anywhere in the build
// log. Host-based routing is also the one thing a Vercel preview deployment
// cannot exercise, because a preview URL matches none of the host rules.
//
// So the check runs here, at build time, in both directions. A mismatch fails
// the build, Vercel keeps the previous deployment live, and the mistake never
// reaches a hostname.
// ---------------------------------------------------------------------------

const vercelPath = join(here, "..", "vercel.json");
const { rewrites = [] } = JSON.parse(readFileSync(vercelPath, "utf8"));

const errors = [];

// 1. Every /_hosts/* destination a rewrite points at must exist on disk.
const referenced = new Set();
for (const { source, has, destination } of rewrites) {
  if (!destination.startsWith("/_hosts/")) continue;
  referenced.add(destination);
  if (!existsSync(join(dist, destination.replace(/^\//, "")))) {
    const host = has?.[0]?.value ?? "(no host condition)";
    errors.push(`rewrite ${host} ${source} -> ${destination} — file was not generated`);
  }
}

// 2. Every host in HOST_MAP must have both rewrites, or it silently falls
//    through to the catch-all and serves the wrong product's metadata.
for (const hostname of Object.keys(HOST_MAP)) {
  const slug = hostname.replace(/\./g, "_");
  for (const dest of [`/_hosts/${slug}.html`, `/_hosts/robots-${slug}.txt`]) {
    if (!referenced.has(dest)) {
      errors.push(`host ${hostname} has no vercel.json rewrite to ${dest}`);
    }
  }
}

// 3. Host-conditional rewrites must precede the unconditional catch-alls.
const firstCatchAll = rewrites.findIndex((r) => !r.has);
const lastConditional = rewrites.map((r) => Boolean(r.has)).lastIndexOf(true);
if (firstCatchAll !== -1 && lastConditional > firstCatchAll) {
  errors.push(
    `a catch-all rewrite at index ${firstCatchAll} shadows host rules that follow it`
  );
}

if (errors.length) {
  console.error(
    `\n[host-html] FAILED — vercel.json and siteMeta.js disagree:\n` +
      errors.map((e) => `  · ${e}`).join("\n") +
      `\n\nFix vercel.json or src/lib/siteMeta.js so they match. ` +
      `Refusing to produce a build that would 404 a live hostname.\n`
  );
  process.exit(1);
}

console.log(`[host-html] verified ${referenced.size} rewrite destinations against dist/`);
