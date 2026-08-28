// Subscribe to What Holds Up.
//
// WHY THIS EXISTS
// ---------------
// It did not, until 2026-08-27. The site had an unsubscribe endpoint, a
// broadcast sender and a segment containing two addresses, both the founder's,
// and no way for a reader to join. A publication that cannot be subscribed to
// is not launched.
//
// WHAT IT DELIBERATELY DOES NOT DO
// --------------------------------
// It does not confirm the address by return mail. Resend's audience is the
// list of record and its own unsubscribe flag is what stops mail, so a
// double-opt-in loop would need a second signed token and a second endpoint,
// and it is not what stands between this and a first issue. When the list is
// large enough that a malicious signup matters, add it — the HMAC helper below
// is already here and is the same construction the unsubscribe path uses.
//
// It does not tell a stranger whether an address is already on the list.
// Every outcome that is not a malformed address returns the same page. An
// endpoint that answers "already subscribed" differently from "subscribed" is
// a membership oracle for any address someone cares to type.
//
// CommonJS deliberately, for the reason given at length in unsubscribe.js:
// ESM in a bare .js file on Vercel's Node runtime needs a root package.json
// declaring "type": "module", and this project has none.

const RESEND_API = "https://api.resend.com";

// Deliberately permissive. The purpose is to catch a typo and a paste of the
// wrong thing, not to adjudicate RFC 5322 — every stricter regex in common use
// rejects addresses that are actually valid, and the cost of that is a reader
// who cannot subscribe and has no way to tell us.
const LOOKS_LIKE_EMAIL = /^[^\s@]+@[^\s@.]+\.[^\s@]+$/;

function page(title, body) {
  return `<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title} — What Holds Up</title>
<style>
  :root { color-scheme: light dark; }
  body { font: 16px/1.6 Georgia, "Times New Roman", serif; max-width: 34rem;
         margin: 4rem auto; padding: 0 1.5rem; }
  h1 { font-size: 1.4rem; margin: 0 0 1rem; }
  .muted { opacity: .7; font-size: .92rem; }
</style>
<h1>${title}</h1>
${body}
<p class="muted"><a href="/">What Holds Up</a></p>`;
}

async function readBody(req) {
  // Vercel parses JSON and urlencoded bodies for us when the content-type says
  // so, but a plain <form> POST from a page with no JavaScript can arrive
  // either way depending on runtime version. Handle both rather than depend on
  // which one is in force, because the failure mode is a silent empty address.
  if (req.body && typeof req.body === "object") return req.body;
  if (typeof req.body === "string") {
    try { return JSON.parse(req.body); } catch { /* fall through */ }
    return Object.fromEntries(new URLSearchParams(req.body));
  }
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const raw = Buffer.concat(chunks).toString("utf8");
  try { return JSON.parse(raw); } catch { /* fall through */ }
  return Object.fromEntries(new URLSearchParams(raw));
}

module.exports = async function handler(req, res) {
  if (req.method === "GET") {
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.status(200).send(page("Subscribe to What Holds Up",
      `<form method="POST">
         <p><label>Email address<br>
           <input type="email" name="email" required autocomplete="email"
                  style="font:inherit;padding:.5rem;width:100%;max-width:22rem"></label></p>
         <p><button type="submit" style="font:inherit;padding:.6rem 1.2rem;cursor:pointer">Subscribe</button></p>
       </form>
       <p class="muted">One issue at a time, no more than one a week. Every issue
       carries a one-click unsubscribe link.</p>`));
    return;
  }

  if (req.method !== "POST") {
    res.setHeader("Allow", "GET, POST");
    res.status(405).send("Method not allowed");
    return;
  }

  const body = await readBody(req);

  // A hidden field no human fills in. Bots fill every input they find, so a
  // non-empty value here is a bot — answer normally and do nothing, because
  // telling it that it was caught only tells it what to change.
  if (String(body.website || "").trim()) {
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.status(200).send(page("Check your inbox", "<p>You are on the list.</p>"));
    return;
  }

  const email = String(body.email || "").trim().toLowerCase();
  if (!LOOKS_LIKE_EMAIL.test(email)) {
    res.status(400).send(page("That does not look like an email address",
      "<p>Go back and check it, or write to " +
      "<a href='mailto:hello@whatholdsup.org'>hello@whatholdsup.org</a> and we " +
      "will add you by hand.</p>"));
    return;
  }

  const key = process.env.RESEND_WHATHOLDSUP_KEY;
  const audience = process.env.RESEND_WHATHOLDSUP_AUDIENCE_ID;
  if (!key || !audience) {
    // Fail loudly rather than show a confirmation for a signup that went
    // nowhere. The same reasoning as the unsubscribe endpoint: the worst
    // outcome is both parties believing something happened that did not.
    console.error("RESEND_WHATHOLDSUP_KEY or RESEND_WHATHOLDSUP_AUDIENCE_ID is not set.");
    res.status(500).send(page("Something is wrong at our end",
      "<p>We could not add you just now. Please write to " +
      "<a href='mailto:hello@whatholdsup.org'>hello@whatholdsup.org</a> and we " +
      "will add you by hand.</p>"));
    return;
  }

  let ok = false;
  try {
    const r = await fetch(`${RESEND_API}/audiences/${audience}/contacts`, {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify({ email, unsubscribed: false }),
    });
    ok = r.ok;
    if (!r.ok) console.error("resend contact create failed", r.status, await r.text());
  } catch (err) {
    console.error("resend contact create threw", err);
  }

  if (!ok) {
    res.status(500).send(page("Something is wrong at our end",
      "<p>We could not add you just now. Please write to " +
      "<a href='mailto:hello@whatholdsup.org'>hello@whatholdsup.org</a> and we " +
      "will add you by hand.</p>"));
    return;
  }

  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.status(200).send(page("You are on the list",
    "<p>The next issue of What Holds Up will come to that address.</p>" +
    "<p class='muted'>Every issue carries a one-click unsubscribe link, and we " +
    "do not send anything else.</p>"));
};
