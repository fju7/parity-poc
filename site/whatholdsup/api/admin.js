// The publication board, behind a password.
//
// WHY THE BOARD IS EMBEDDED IN THE FUNCTION
// -----------------------------------------
// A static file under site/ is served at its own URL whether or not anything
// links to it, so putting the board there and guarding a different route would
// guard nothing. Files under api/ are functions, not static assets. Generating
// this file with the board inlined means there is exactly one path to the
// content and it runs through the check below.
//
// Regenerate with:  python scripts/whatholdsup/publish.py dashboard --web
// It is a snapshot at generation time, which is honest: the board reads gate
// reports and a publication record that live in the repo, and a serverless
// function cannot see those.
//
// WHY BASIC AUTH AND NOT A LOGIN PAGE
// -----------------------------------
// One operator, one secret, no session to store and nothing to get wrong.
// Comparison is constant-time. If ADMIN_PASSWORD is unset the route serves
// nothing at all rather than defaulting open — the failure mode of a guard
// that quietly stops guarding is worse than one that is plainly broken.

const crypto = require("crypto");

const BOARD = "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n<title>What Holds Up &mdash; publication board</title>\n<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">\n<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>\n<link rel=\"stylesheet\" href=\"https://fonts.googleapis.com/css2?family=Bitter:wght@400;600&family=Karla:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap\">\n<style>\n:root{--paper:#F1F2F0;--card:#FBFBFA;--card-2:#E7E9E6;--ink:#15181A;--ink-2:#4C545A;\n--ink-3:#7C858B;--rule:#CFD3CE;--rule-soft:#E0E3DF;--accent:#2C4A63;--accent-bg:#E3E9EE;\n--holds:#2E6E52;--partly:#9A6C1C;--nope:#9B3B32;}\n@media (prefers-color-scheme:dark){:root:not([data-theme=\"light\"]){\n--paper:#14171A;--card:#1B1F23;--card-2:#23282D;--ink:#E9ECEA;--ink-2:#AFB8BD;\n--ink-3:#7B858C;--rule:#333A40;--rule-soft:#262C31;--accent:#8FB4D0;--accent-bg:#1C2A36;\n--holds:#6CB795;--partly:#D2A15A;--nope:#D9827A;}}\n*{box-sizing:border-box}\nbody{background:var(--paper);color:var(--ink);margin:0;padding:0 1.25rem 4rem;\nfont:400 16px/1.6 Karla,system-ui,-apple-system,sans-serif}\n.wrap{max-width:50rem;margin:0 auto}\nheader.top{padding:3rem 0 1.5rem;border-bottom:1px solid var(--rule)}\nh1{font:600 2rem/1.15 Bitter,Georgia,serif;margin:0 0 .5rem;letter-spacing:-.015em}\n.mono{font:400 .82rem/1.5 \"IBM Plex Mono\",ui-monospace,monospace;color:var(--ink-3)}\n.eyebrow{font:500 .7rem/1 \"IBM Plex Mono\",ui-monospace,monospace;letter-spacing:.12em;\ntext-transform:uppercase;color:var(--ink-3)}\n.issue{margin-top:2.75rem}\n.issue>header{display:flex;justify-content:space-between;align-items:flex-end;gap:1rem;\nborder-bottom:1px solid var(--rule);padding-bottom:.6rem}\n.issue h2{font:600 1.3rem/1.2 Bitter,Georgia,serif;margin:.3rem 0 0}\n.count{font:500 .85rem/1 \"IBM Plex Mono\",ui-monospace,monospace;color:var(--ink-3);\nfont-variant-numeric:tabular-nums;white-space:nowrap}\n.nextup{background:var(--accent-bg);border:1px solid var(--rule-soft);border-radius:3px;\npadding:1rem 1.2rem;margin:1.1rem 0 .8rem}\n.nextup .kicker{font:500 .68rem/1 \"IBM Plex Mono\",ui-monospace,monospace;letter-spacing:.14em;\ntext-transform:uppercase;color:var(--accent);display:block;margin-bottom:.5rem}\n.nextup p{margin:0 0 .7rem;font-weight:500}\n.nextup p:last-child{margin-bottom:0}\ncode{display:block;font:400 .8rem/1.55 \"IBM Plex Mono\",ui-monospace,monospace;\nbackground:var(--card-2);color:var(--ink-2);padding:.5rem .7rem;border-radius:2px;\nmargin-top:.5rem;overflow-x:auto;white-space:pre}\n.livestate{font:400 .85rem/1.5 \"IBM Plex Mono\",ui-monospace,monospace;margin:0 0 1.2rem}\n.livestate.done{color:var(--holds)}.livestate.warn{color:var(--partly)}\n.livestate.blocked{color:var(--nope)}\nol.steps{list-style:none;margin:0;padding:0;display:grid;gap:.35rem}\nli.step{display:grid;grid-template-columns:auto 1fr;gap:.85rem;align-items:start;\npadding:.7rem .9rem;background:var(--card);border:1px solid var(--rule-soft);border-radius:3px}\nli.step .dot{width:.7rem;height:.7rem;border-radius:50%;margin-top:.42rem;\nbackground:var(--card-2);border:1.5px solid var(--ink-3)}\nli.step.done .dot{background:var(--holds);border-color:var(--holds)}\nli.step.blocked .dot{background:var(--nope);border-color:var(--nope)}\nli.step.warn .dot{background:var(--partly);border-color:var(--partly)}\nli.step.done{background:transparent;border-color:transparent}\nli.step.done b{color:var(--ink-3)}\nli.step b{display:block;font-weight:600}\n.detail{display:block;font:400 .87rem/1.5 \"IBM Plex Mono\",ui-monospace,monospace;\ncolor:var(--ink-2);margin-top:.15rem}\n.why{display:block;font-size:.87rem;color:var(--ink-3);margin-top:.2rem}\nfooter{margin-top:3rem;padding-top:1.2rem;border-top:1px solid var(--rule);\nfont-size:.87rem;color:var(--ink-3)}\n</style></head><body><div class=\"wrap\">\n<header class=\"top\">\n<span class=\"eyebrow\">What Holds Up &middot; internal</span>\n<h1>Publication board</h1>\n<p class=\"mono\">Generated 2026-08-28 14:02 from live state &mdash; gate reports, the publication\nrecord, the review archive, and the site itself. Not deployed.</p>\n</header>\n<section class=\"issue\"><header><div><span class=\"eyebrow\">melanoma &middot; 1</span><h2>The Melanoma Result</h2></div><span class=\"count\">1 / 7</span></header><div class=\"nextup\"><span class=\"kicker\">Next</span><p>gate the assessment \u2014 melanoma.html.gate.json records passed=False</p><code>python scripts/signal/factcheck_draft.py ../site/whatholdsup/melanoma.html --since ../site/whatholdsup/melanoma.html.gate.json --report ../site/whatholdsup/melanoma.html.gate.json</code></div><p class=\"livestate blocked\">live is behind the repo</p><ol class=\"steps\"><li class=\"step done\"><div class=\"dot\"></div><div><b>Draft</b><span class=\"detail\">assessment and email present</span><span class=\"why\">The assessment and the email exist.</span></div></li><li class=\"step blocked\"><div class=\"dot\"></div><div><b>Gate the assessment</b><span class=\"detail\">melanoma.html.gate.json records passed=False</span><span class=\"why\">Five adversarial roles. Blocks on fact, contradiction and unevidenced claims about third parties; records phrasing.</span><code>python scripts/signal/factcheck_draft.py ../site/whatholdsup/melanoma.html --since ../site/whatholdsup/melanoma.html.gate.json --report ../site/whatholdsup/melanoma.html.gate.json</code></div></li><li class=\"step blocked\"><div class=\"dot\"></div><div><b>Gate the email</b><span class=\"detail\">issue1-melanoma.html.gate.json records passed=False</span><span class=\"why\">The same, on the summary that reaches inboxes. It cannot be recalled once sent.</span><code>python scripts/signal/factcheck_draft.py ../site/whatholdsup/email/issue1-melanoma.html --since ../site/whatholdsup/email/issue1-melanoma.html.gate.json --report ../site/whatholdsup/email/issue1-melanoma.html.gate.json</code></div></li><li class=\"step blocked\"><div class=\"dot\"></div><div><b>Outside review</b><span class=\"detail\">no outside review has ever been recorded</span><span class=\"why\">An independent reader, given the assessment and the standards, and neither our findings nor our adjudication.</span><code>python scripts/whatholdsup/publish.py send-for-review melanoma</code></div></li><li class=\"step pending\"><div class=\"dot\"></div><div><b>Adjudicate</b><span class=\"detail\">2026-08-28-adjudication.md on file</span><span class=\"why\">We read the review together and decide. Every rejection goes on the record with a reason.</span><code>python scripts/whatholdsup/publish.py review melanoma --reviewer NAME --findings N --accepted M</code></div></li><li class=\"step pending\"><div class=\"dot\"></div><div><b>Publish the site</b><span class=\"detail\">not published</span><span class=\"why\">Commits, pushes, and waits for the deploy to actually serve it before recording anything.</span><code>python scripts/whatholdsup/publish.py publish melanoma --yes</code></div></li><li class=\"step pending\"><div class=\"dot\"></div><div><b>Announce</b><span class=\"detail\">not sent</span><span class=\"why\">The broadcast. Refuses if the site is behind the repo, so nobody follows a link to something older than their email.</span><code>python scripts/whatholdsup/publish.py announce melanoma --yes</code></div></li></ol></section>\n<section class=\"issue\"><header><div><span class=\"eyebrow\">not yet built</span>\n<h2>Subscriptions</h2></div></header>\n<p class=\"why\" style=\"margin-top:1rem\">Counts, growth, unsubscribes and the changelog's\nlast run belong here. Deliberately absent until the changelog delivers something:\na number on a board is not a working product, and a board full of numbers about a\nthing that has never run would be worse than an empty section.</p></section>\n<footer>Regenerate with <code style=\"display:inline;padding:.15rem .35rem\">python\nscripts/whatholdsup/publish.py dashboard</code>. It reads state, never changes it.</footer>\n</div></body></html>";

function ok(header, expected) {
  if (!header || !header.startsWith("Basic ")) return false;
  let decoded = "";
  try {
    decoded = Buffer.from(header.slice(6), "base64").toString("utf8");
  } catch { return false; }
  const given = decoded.slice(decoded.indexOf(":") + 1);
  const a = Buffer.from(given);
  const b = Buffer.from(expected);
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

module.exports = function handler(req, res) {
  const expected = process.env.ADMIN_PASSWORD;
  if (!expected) {
    console.error("ADMIN_PASSWORD is not set; refusing to serve the board.");
    res.status(500).send("Not configured.");
    return;
  }
  if (!ok(req.headers.authorization, expected)) {
    res.setHeader("WWW-Authenticate", 'Basic realm="What Holds Up", charset="UTF-8"');
    res.status(401).send("Authentication required.");
    return;
  }
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  // Never cached anywhere but the reader's own tab: this is operational state,
  // and a CDN copy of it would outlive the password check.
  res.setHeader("Cache-Control", "no-store, private");
  res.setHeader("X-Robots-Tag", "noindex, nofollow");
  res.status(200).send(BOARD);
};
