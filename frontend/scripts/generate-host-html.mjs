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
