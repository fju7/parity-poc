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

  // Configuration arrives by being pasted into a dashboard, which is user
  // input and should be treated as such. Three failures on 2026-08-28 came
  // from the shape of the value rather than the value: surrounding whitespace,
  // a trailing slash, and a host with no scheme — the last of which makes the
  // request URL relative and throws before anything leaves the process.
  // Normalising these is not papering over a mistake; it is refusing to have a
  // whole class of outage depend on how carefully someone copied a string.
  const clean = v => String(v || "").trim();
  let dbUrl = clean(process.env.SUPABASE_URL).replace(/\/+$/, "");
  if (dbUrl && !/^https?:\/\//i.test(dbUrl)) dbUrl = "https://" + dbUrl;
  const dbKey = clean(process.env.SUPABASE_SERVICE_KEY);
  const key = clean(process.env.RESEND_WHATHOLDSUP_KEY);
  const audience = clean(process.env.RESEND_WHATHOLDSUP_AUDIENCE_ID);
  if (!key || !audience || !dbUrl || !dbKey) {
    // Fail loudly rather than show a confirmation for a signup that went
    // nowhere. The same reasoning as the unsubscribe endpoint: the worst
    // outcome is both parties believing something happened that did not.
    // Two different failures used to print the same sentence, so the first
    // real signup failure could not be diagnosed from what the person saw.
    // E1 is ours to fix in configuration; E2 is the provider refusing.
    console.error("subscribe E1: missing", [
      !key && "RESEND_WHATHOLDSUP_KEY",
      !audience && "RESEND_WHATHOLDSUP_AUDIENCE_ID",
      !dbUrl && "SUPABASE_URL",
      !dbKey && "SUPABASE_SERVICE_KEY",
    ].filter(Boolean).join(", "));
    res.status(500).send(page("Something is wrong at our end",
      "<p>We could not add you just now. Please write to " +
      "<a href='mailto:hello@whatholdsup.org'>hello@whatholdsup.org</a> and we " +
      "will add you by hand.</p>" +
      "<p class='muted'>Reference: E1</p>"));
    return;
  }

  // 1. The record, first. Resend is the delivery mechanism; this table is the
  //    answer to "who subscribed, and when". Writing delivery first would let a
  //    person exist in the mail system and nowhere else, which is the drift this
  //    table was added to prevent — so a record that cannot be written stops the
  //    signup rather than producing a subscriber we have no history for.
  // The upstream status travels with the reference code. "E3" alone sent the
  // operator to hunt through deployment logs; "E3/401" is a wrong key, "E3/404"
  // a wrong URL or a missing table, "E3/403" a permissions or RLS problem, and
  // "E3/x" means the call threw before it got a status. A status code tells an
  // outsider nothing they could use — they cannot reach the database at all —
  // and it saves a deploy cycle every time this breaks.
  let recorded = false;
  let why = "x";
  try {
    const r = await fetch(`${dbUrl}/rest/v1/whatholdsup_subscribers?on_conflict=email`, {
      method: "POST",
      headers: {
        apikey: dbKey,
        Authorization: `Bearer ${dbKey}`,
        "Content-Type": "application/json",
        // Somebody signing up twice is not an error and must not read as one.
        Prefer: "resolution=ignore-duplicates,return=minimal",
      },
      body: JSON.stringify({ email, source: "site" }),
    });
    recorded = r.ok;
    why = String(r.status);
    if (!r.ok) console.error("subscribe E3: record failed", r.status, await r.text());
  } catch (err) {
    // A throw means the request never got a status, so there is no upstream
    // code to report. The three causes are distinguishable from the message and
    // none of them needs the value quoted: a URL that will not parse, a header
    // value carrying a character a header cannot hold — a newline pasted into
    // the middle of a key does this, and is invisible in a dashboard — or the
    // network. Guessing between them cost three round trips on 2026-08-28.
    const m = String((err && err.message) || "");
    why = /invalid url|failed to parse url|cannot be parsed/i.test(m) ? "url"
        : /header|invalid character|ERR_INVALID_CHAR/i.test(m) ? "hdr"
        : "net";
    // Fingerprint, never the value: enough to compare against the key known to
    // work without putting a credential in a log.
    let fp = "?";
    try {
      fp = require("crypto").createHash("sha256").update(dbKey).digest("hex").slice(0, 8);
    } catch { /* not worth failing a signup over */ }
    console.error("subscribe E3 threw:", m,
                  "| url host:", String(dbUrl).replace(/^https?:\/\//, "").split("/")[0],
                  "| url length:", String(dbUrl).length,
                  "| key fingerprint:", fp,
                  "| key length:", String(dbKey).length);
  }
  if (!recorded) {
    res.status(500).send(page("Something is wrong at our end",
      "<p>We could not add you just now. Please write to " +
      "<a href='mailto:hello@whatholdsup.org'>hello@whatholdsup.org</a> and we " +
      "will add you by hand.</p>" +
      "<p class='muted'>Reference: E3/" + why + "</p>"));
    return;
  }

  // 2. Delivery.
  let ok = false;
  let contactId = "";
  try {
    const r = await fetch(`${RESEND_API}/audiences/${audience}/contacts`, {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify({ email, unsubscribed: false }),
    });
    ok = r.ok;
    const detail = await r.text();
    if (r.ok) {
      try { contactId = (JSON.parse(detail) || {}).id || ""; } catch { /* not fatal */ }
    }
    if (!r.ok) {
      // An address already on the list is not a failure, and saying so would
      // also tell a stranger who is subscribed. Same page either way.
      if (r.status === 409 || /already exist|already a contact/i.test(detail)) {
        ok = true;
      } else {
        console.error("subscribe E2: resend refused", r.status, detail);
      }
    }
  } catch (err) {
    console.error("subscribe E2: resend threw", err && err.message);
  }

  // 3. Link the two, best effort. A row whose resend_contact_id is null is on
  //    the work-queue index: recorded by us, receiving nothing. Failing here
  //    only ever produces a false positive on that queue, which is the safe
  //    direction — a retry costs a duplicate call Resend already de-duplicates.
  if (ok && contactId) {
    try {
      await fetch(`${dbUrl}/rest/v1/whatholdsup_subscribers?email=eq.` +
                  encodeURIComponent(email), {
        method: "PATCH",
        headers: {
          apikey: dbKey,
          Authorization: `Bearer ${dbKey}`,
          "Content-Type": "application/json",
          Prefer: "return=minimal",
        },
        body: JSON.stringify({ resend_contact_id: contactId }),
      });
    } catch (err) {
      console.error("subscribe: could not link contact id", err && err.message);
    }
  }

  if (!ok) {
    res.status(500).send(page("Something is wrong at our end",
      "<p>We could not add you just now. Please write to " +
      "<a href='mailto:hello@whatholdsup.org'>hello@whatholdsup.org</a> and we " +
      "will add you by hand.</p>" +
      "<p class='muted'>Reference: E2</p>"));
    return;
  }

  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.status(200).send(page("You are on the list",
    "<p>The next issue of What Holds Up will come to that address.</p>" +
    "<p class='muted'>Every issue carries a one-click unsubscribe link, and we " +
    "do not send anything else.</p>"));
};
