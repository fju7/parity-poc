// The signup endpoint, tested as a function.
//
// Run:  node backend/tests/whatholdsup/subscribe.test.js
//
// WHY THIS EXISTS
// The first person to use the form on the live site got "Something is wrong at
// our end." Two entirely different failures printed that same sentence, so the
// page could not say which had happened, and nothing had ever exercised either
// path. Now E1 (our configuration) and E2 (the provider) are distinguishable,
// and an address already on the list is a success rather than an error.
//
// No network: fetch is stubbed for every case.

const path = require("path");
const handler = require(path.join(__dirname, "..", "..", "..",
                                  "site", "whatholdsup", "api", "subscribe.js"));
let pass = 0, fail = 0;
const t = (n, ok) => { console.log((ok ? "  ok   " : "  FAIL ") + n); ok ? pass++ : fail++; };

function res() {
  const o = { code: 0, headers: {}, body: "" };
  return { o,
    setHeader: (k, v) => { o.headers[k.toLowerCase()] = v; },
    status: c => { o.code = c; return { send: b => { o.body = String(b || ""); } }; } };
}

async function call({ method = "POST", body = {}, env = {}, fetchImpl } = {}) {
  const saved = { ...process.env };
  delete process.env.RESEND_WHATHOLDSUP_KEY;
  delete process.env.RESEND_WHATHOLDSUP_AUDIENCE_ID;
  Object.assign(process.env, env);
  const realFetch = global.fetch;
  if (fetchImpl) global.fetch = fetchImpl;
  const r = res();
  try {
    await handler({ method, headers: { "content-type": "application/json" }, body }, r);
  } finally {
    global.fetch = realFetch;
    for (const k of Object.keys(process.env)) delete process.env[k];
    Object.assign(process.env, saved);
  }
  return r.o;
}

const CONFIGURED = {
  RESEND_WHATHOLDSUP_KEY: "re_test",
  RESEND_WHATHOLDSUP_AUDIENCE_ID: "aud_test",
  SUPABASE_URL: "https://db.example",
  SUPABASE_SERVICE_KEY: "svc_test",
};

// The handler now makes up to three calls in a fixed order: record, deliver,
// link. The stub routes by URL and logs every call, so the ORDER can be
// asserted — writing delivery before the record is the specific mistake this
// table was added to prevent.
function router({ record = { ok: true, status: 201, body: "" },
                  resend = { ok: true, status: 201, body: '{"id":"con_1"}' } } = {}) {
  const calls = [];
  const fn = async (url, opts) => {
    const u = String(url);
    calls.push({ url: u, method: (opts && opts.method) || "GET",
                 body: opts && opts.body, headers: (opts && opts.headers) || {} });
    const r = u.includes("whatholdsup_subscribers") && (opts || {}).method === "PATCH"
      ? { ok: true, status: 204, body: "" }
      : u.includes("whatholdsup_subscribers") ? record
      : resend;
    if (r.throws) throw new Error(r.throws);
    return { ok: r.ok, status: r.status, text: async () => r.body };
  };
  fn.calls = calls;
  return fn;
}
const okFetch = () => router();
const failFetch = (status, body) => router({ resend: { ok: false, status, body } });

(async () => {
  console.log();

  let o = await call({ body: { email: "a@b.com" } });
  t("unconfigured -> 500 and says E1", o.code === 500 && /Reference: E1/.test(o.body));

  o = await call({ env: { RESEND_WHATHOLDSUP_KEY: "re_test" }, body: { email: "a@b.com" } });
  t("half-configured is still E1", o.code === 500 && /Reference: E1/.test(o.body));

  o = await call({ env: CONFIGURED, body: { email: "not-an-email" } });
  t("a bad address -> 400, and never reaches the provider", o.code === 400);

  o = await call({ env: CONFIGURED, body: { email: "a@b.com", website: "spam" },
                   fetchImpl: okFetch() });
  t("the honeypot is not an error page", o.code === 200);

  o = await call({ env: CONFIGURED, body: { email: "a@b.com" }, fetchImpl: okFetch() });
  const good = o.body;
  t("a real signup -> 200 and confirms", o.code === 200 && /on the list/i.test(o.body));

  o = await call({ env: CONFIGURED, body: { email: "a@b.com" },
                   fetchImpl: failFetch(409, '{"message":"Contact already exists"}') });
  t("an address already on the list -> 200, not an error", o.code === 200);
  t("and the page is identical, so it leaks nothing", o.body === good);

  o = await call({ env: CONFIGURED, body: { email: "a@b.com" },
                   fetchImpl: failFetch(422, '{"message":"invalid audience"}') });
  t("a provider refusal -> 500 and says E2", o.code === 500 && /Reference: E2/.test(o.body));

  o = await call({ env: CONFIGURED, body: { email: "a@b.com" },
                   fetchImpl: router({ record: { throws: "db unreachable" } }) });
  o = await call({ env: CONFIGURED, body: { email: "a@b.com" },
                   fetchImpl: router({ record: { throws: "Failed to parse URL from x" } }) });
  t("a throw on a bad URL -> E3/url", o.code === 500 && /Reference: E3\/url/.test(o.body));

  o = await call({ env: CONFIGURED, body: { email: "a@b.com" },
                   fetchImpl: router({ record: { throws: "Invalid value for header Authorization" } }) });
  t("a throw on a bad header -> E3/hdr", o.code === 500 && /Reference: E3\/hdr/.test(o.body));

  o = await call({ env: CONFIGURED, body: { email: "a@b.com" },
                   fetchImpl: router({ record: { throws: "fetch failed" } }) });
  t("any other throw -> E3/net", o.code === 500 && /Reference: E3\/net/.test(o.body));

  o = await call({ env: CONFIGURED, body: { email: "a@b.com" },
                   fetchImpl: router({ resend: { throws: "network down" } }) });
  t("a throw on delivery -> E2", o.code === 500 && /Reference: E2/.test(o.body));

  o = await call({ method: "PUT", env: CONFIGURED, body: {} });
  t("PUT -> 405", o.code === 405);

  o = await call({ method: "GET", env: CONFIGURED });
  t("GET serves the form", o.code === 200 && /<form/i.test(o.body));

  // --- the record is the system of record, and goes first -------------------
  let f = router();
  o = await call({ env: CONFIGURED, body: { email: "a@b.com" }, fetchImpl: f });
  t("the record is written before delivery",
    f.calls.length >= 2
    && f.calls[0].url.includes("whatholdsup_subscribers")
    && f.calls[1].url.includes("audiences"));
  t("and it records where the signup came from",
    JSON.parse(f.calls[0].body || "{}").source === "site");
  t("the record tolerates a repeat signup rather than erroring",
    /resolution=ignore-duplicates/.test(String(f.calls[0].headers.Prefer || "")));
  t("the Resend contact id is written back",
    f.calls.length === 3 && f.calls[2].method === "PATCH"
    && /con_1/.test(f.calls[2].body || ""));

  f = router({ record: { ok: false, status: 500, body: "db down" } });
  o = await call({ env: CONFIGURED, body: { email: "a@b.com" }, fetchImpl: f });
  t("if the record fails -> 500 and says E3 with the upstream status",
    o.code === 500 && /Reference: E3\/500/.test(o.body));
  t("and nothing is sent to Resend, so no unrecorded subscriber exists",
    f.calls.every(c => !c.url.includes("audiences")));

  f = router({ resend: { ok: false, status: 422, body: "nope" } });
  o = await call({ env: CONFIGURED, body: { email: "a@b.com" }, fetchImpl: f });
  t("if delivery fails -> E2, and the record survives as a work-queue row",
    o.code === 500 && /Reference: E2/.test(o.body)
    && f.calls[0].url.includes("whatholdsup_subscribers")
    && f.calls.length === 2);

  o = await call({ env: { ...CONFIGURED, SUPABASE_URL: "" },
                   body: { email: "a@b.com" }, fetchImpl: router() });
  t("missing database config is E1, not a silent half-signup",
    o.code === 500 && /Reference: E1/.test(o.body));

  console.log("\n  " + pass + " passed, " + fail + " failed\n");
  process.exit(fail ? 1 : 0);
})();
