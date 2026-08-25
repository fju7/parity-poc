/**
 * Runtime <head> management.
 *
 * The tags that matter for crawlers and link previews are baked into static
 * HTML at build time (scripts/generate-host-html.mjs) — nothing here reaches a
 * bot. These helpers keep the live DOM correct for client-side navigation:
 * the browser tab, the bookmark name, and the browser-history entry.
 */

import { metaForHost } from "./siteMeta";

function setTag(attr, key, value) {
  let el = document.querySelector(`meta[${attr}="${key}"]`);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, key);
    document.head.appendChild(el);
  }
  el.setAttribute("content", value);
}

function setCanonical(href) {
  let el = document.querySelector('link[rel="canonical"]');
  if (!el) {
    el = document.createElement("link");
    el.setAttribute("rel", "canonical");
    document.head.appendChild(el);
  }
  el.setAttribute("href", href);
}

/** Base title for the current host, used when a page clears its own title. */
let baseTitle = document.title;
let baseUrl = "";

/** Apply the product-level metadata for a hostname. Call once on boot. */
export function applyHostMeta(hostname) {
  const meta = metaForHost(hostname);

  baseTitle = meta.title;
  baseUrl = meta.url;

  document.title = meta.title;
  setTag("name", "description", meta.description);
  setTag("name", "robots", meta.index ? "index, follow" : "noindex, nofollow");
  setTag("property", "og:type", "website");
  setTag("property", "og:site_name", "CivicScale");
  setTag("property", "og:title", meta.title);
  setTag("property", "og:description", meta.description);
  setTag("property", "og:url", meta.url);
  setCanonical(meta.url);

  return meta;
}

/**
 * Set the title and description for one page within the current product.
 *
 * Pass null/undefined to restore the product default — which is what the
 * cleanup returned by usePageMeta does on unmount.
 */
export function setPageMeta({ title, description } = {}) {
  const fullTitle = title ? `${title} — ${baseTitle}` : baseTitle;
  document.title = fullTitle;
  setTag("property", "og:title", fullTitle);
  if (description) {
    setTag("name", "description", description);
    setTag("property", "og:description", description);
  }
  if (baseUrl) {
    const href = `${baseUrl}${window.location.pathname}`;
    setCanonical(href);
    setTag("property", "og:url", href);
  }
}

/** Restore the product-level title and canonical. */
export function resetPageMeta() {
  document.title = baseTitle;
  setTag("property", "og:title", baseTitle);
  if (baseUrl) {
    setCanonical(baseUrl);
    setTag("property", "og:url", baseUrl);
  }
}
