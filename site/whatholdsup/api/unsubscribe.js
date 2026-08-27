// One-click unsubscribe, RFC 8058.
//
// WHY POST AND NOT GET
// --------------------
// RFC 8058 exists because List-Unsubscribe alone was unsafe to automate: mail
// scanners, link checkers and preview generators fetch every URL in a message,
// so a GET that unsubscribes will unsubscribe people who never clicked
// anything. One-click therefore requires a POST carrying the body
// `List-Unsubscribe=One-Click`, and the header pair:
//
//   List-Unsubscribe: <https://whatholdsup.org/api/unsubscribe?e=..&t=..>,
//                     <mailto:unsubscribe@whatholdsup.org?subject=Unsubscribe>
//   List-Unsubscribe-Post: List-Unsubscribe=One-Click
//
// This function NEVER unsubscribes on GET. A GET renders a page with a form
// whose submit posts here. That is the human path; the POST is the mail
// client's path. Both end in the same place.
//
// WHY A SIGNED TOKEN
// ------------------
// The endpoint is public and takes an address. Without a signature anyone could
// unsubscribe anyone, and a bored person with a wordlist could empty the list.
// The token is an HMAC of the address under a secret only the sender knows, so
// a valid request can only have come from an email we sent. No database lookup
// is needed to validate it, which matters because this has to answer fast.
//
// Comparison is constant-time. A timing oracle on an HMAC is a real forgery
// path, not a theoretical one.

// CommonJS deliberately. ESM `import` in a bare .js file on Vercel's Node
// runtime requires a package.json declaring "type": "module" in the project
// root directory, and this one has none. Adding a package.json here would also
// change Vercel's framework detection for a site that has no build step.
// require() works under either setting, so the deployment cannot fail on it.
const crypto = require("crypto");

const RESEND_API = "https://api.resend.com";

function b64urlDecode(s) {
  return Buffer.from(s.replace(/-/g, "+").replace(/_/g, "/"), "base64").toString("utf8");
}

function sign(email, secret) {
  return crypto.createHmac("sha256", secret).update(email.toLowerCase().trim())
    .digest("base64url");
}

function verify(email, token, secret) {
  const expected = sign(email, secret);
  const a = Buffer.from(expected);
  const b = Buffer.from(String(token || ""));
  // timingSafeEqual throws on length mismatch, which is itself a length oracle;
  // check length first and return the same failure either way.
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

function page(title, body) {
  return `<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title} — What Holds Up</title>
<style>
  :root { color-scheme: light dark; }
  body { font: 16px/1.6 Georgia, "Times New Roman", serif; max-width: 34rem;
         margin: 4rem auto; padding: 0 1.5rem; }
  h1 { font-size: 1.4rem; margin: 0 0 1rem; }
  button { font: inherit; padding: .6rem 1.2rem; cursor: pointer; }
  .muted { opacity: .7; font-size: .92rem; }
</style>
<h1>${title}</h1>
${body}`;
}

module.exports = async function handler(req, res) {
  const secret = process.env.UNSUBSCRIBE_SECRET;
  if (!secret) {
    // Fail closed and loudly. An unsubscribe endpoint that silently accepts
    // everything while doing nothing is worse than one that is plainly broken:
    // the sender believes the obligation is met.
    console.error("UNSUBSCRIBE_SECRET is not set; refusing to pretend this worked.");
    res.status(500).send(page("Something is wrong at our end",
      "<p>We could not process this request. Please email " +
      "<a href='mailto:unsubscribe@whatholdsup.org'>unsubscribe@whatholdsup.org</a> " +
      "and we will remove you by hand.</p>"));
    return;
  }

  const url = new URL(req.url, "https://whatholdsup.org");
  const e = url.searchParams.get("e") || "";
  const t = url.searchParams.get("t") || "";

  let email = "";
  try {
    email = b64urlDecode(e);
  } catch {
    email = "";
  }

  const ok = email && verify(email, t, secret);

  if (req.method === "GET") {
    if (!ok) {
      res.status(400).send(page("That link is not valid",
        "<p>The unsubscribe link may have been truncated by your mail client. " +
        "Email <a href='mailto:unsubscribe@whatholdsup.org'>unsubscribe@whatholdsup.org</a> " +
        "and we will remove you by hand.</p>"));
      return;
    }
    // A GET must not change anything: scanners fetch it.
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.status(200).send(page("Unsubscribe",
      `<p>This removes <strong>${email.replace(/[<>&]/g, "")}</strong> from What Holds Up.</p>
       <form method="POST">
         <input type="hidden" name="List-Unsubscribe" value="One-Click">
         <button type="submit">Unsubscribe</button>
       </form>
       <p class="muted">You will stop receiving issues immediately. Nothing else happens.</p>`));
    return;
  }

  if (req.method !== "POST") {
    res.setHeader("Allow", "GET, POST");
    res.status(405).send("Method not allowed");
    return;
  }

  if (!ok) {
    res.status(400).send("Invalid unsubscribe token");
    return;
  }

  // Resend is the send path, so Resend's flag is what actually stops mail.
  const key = process.env.RESEND_WHATHOLDSUP_KEY;
  let resendOk = false;
  if (key) {
    try {
      const r = await fetch(`${RESEND_API}/contacts/${encodeURIComponent(email)}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
        body: JSON.stringify({ unsubscribed: true }),
      });
      resendOk = r.ok;
      if (!r.ok) console.error("resend PATCH failed", r.status, await r.text());
    } catch (err) {
      console.error("resend PATCH threw", err);
    }
  } else {
    console.error("RESEND_WHATHOLDSUP_KEY is not set; unsubscribe not propagated.");
  }

  // Our own durable record, independent of Resend. If the API call above failed
  // this row is what a human uses to honour the request by hand, and it is the
  // evidence that the request was made and when.
  const sb = process.env.SUPABASE_URL;
  const sbKey = process.env.SUPABASE_SERVICE_KEY;
  if (sb && sbKey) {
    try {
      await fetch(`${sb}/rest/v1/whatholdsup_unsubscribes`, {
        method: "POST",
        headers: {
          apikey: sbKey,
          Authorization: `Bearer ${sbKey}`,
          "Content-Type": "application/json",
          Prefer: "resolution=merge-duplicates",
        },
        body: JSON.stringify({
          email: email.toLowerCase().trim(),
          propagated_to_resend: resendOk,
          source: req.headers["user-agent"] ? "one-click" : "unknown",
        }),
      });
    } catch (err) {
      console.error("supabase insert threw", err);
    }
  }

  // RFC 8058: answer 200 and do not redirect. The mail client is not a browser
  // and will not follow one. Returning an error here makes some clients retry
  // and some show the user a failure for a request we did in fact honour.
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.status(200).send(page("Unsubscribed",
    "<p>You will not receive further issues of What Holds Up.</p>" +
    "<p class='muted'>If this was a mistake, reply to any earlier issue and " +
    "we will put you back.</p>"));
};
