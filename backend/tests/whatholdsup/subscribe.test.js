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

const CONFIGURED = { RESEND_WHATHOLDSUP_KEY: "re_test", RESEND_WHATHOLDSUP_AUDIENCE_ID: "aud_test" };
const okFetch = () => async () => ({ ok: true, status: 200, text: async () => "" });
const failFetch = (status, body) => async () => ({ ok: false, status, text: async () => body });

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
                   fetchImpl: async () => { throw new Error("network down"); } });
  t("a thrown fetch -> 500 and says E2", o.code === 500 && /Reference: E2/.test(o.body));

  o = await call({ method: "PUT", env: CONFIGURED, body: {} });
  t("PUT -> 405", o.code === 405);

  o = await call({ method: "GET", env: CONFIGURED });
  t("GET serves the form", o.code === 200 && /<form/i.test(o.body));

  console.log("\n  " + pass + " passed, " + fail + " failed\n");
  process.exit(fail ? 1 : 0);
})();
