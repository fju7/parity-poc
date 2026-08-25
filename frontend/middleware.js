/**
 * Edge Middleware — per-host metadata for the ROOT path only.
 *
 * WHY THIS EXISTS
 * ---------------
 * Vercel evaluates rewrites AFTER the filesystem check. `/` matches
 * dist/index.html on disk, so the host-conditional rewrites in vercel.json
 * never fire for the homepage — every subdomain's root served index.html's
 * metadata regardless of host. Deeper paths (/glp1-drugs, /pricing) have no
 * matching file, so their rewrites fire correctly and always did.
 *
 * Middleware runs BEFORE the filesystem check, which makes it the only place
 * the homepage can be routed by host. Everything else keeps working through
 * vercel.json — hence `matcher: "/"`. The blast radius is one path.
 *
 * FAILURE MODE
 * ------------
 * Any unknown host, or any error at all, returns undefined and the request
 * continues down normal routing to index.html. That is exactly the behaviour
 * we have today: a homepage with the wrong <title>. This middleware must never
 * be the reason a homepage 500s — wrong metadata is a cosmetic problem, a dead
 * homepage is not.
 */

import { rewrite } from "@vercel/edge";

import { HOST_MAP } from "./src/lib/siteMeta.js";

export const config = {
  // Only the root path. Every other path is already handled by vercel.json's
  // rewrites, which fire correctly because no static file shadows them.
  matcher: "/",
};

export default function middleware(request) {
  try {
    const host = (request.headers.get("host") || "")
      .toLowerCase()
      .split(":")[0];

    if (!Object.prototype.hasOwnProperty.call(HOST_MAP, host)) {
      // Preview URLs (*.vercel.app) and anything unrecognised fall through to
      // index.html, which carries the main-site metadata.
      return;
    }

    const slug = host.replace(/\./g, "_");
    return rewrite(new URL(`/_hosts/${slug}.html`, request.url));
  } catch {
    // Never break the homepage over a <title>.
    return;
  }
}
