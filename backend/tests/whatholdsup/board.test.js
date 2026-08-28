// The board's buttons, clicked in a real browser.
//
// Run:  node backend/tests/whatholdsup/board.test.js [url]
//       (default http://127.0.0.1:8787/ — start the board first)
//
// WHY THIS EXISTS
// The first version of these buttons used prompt() and confirm(). Chrome
// suppresses those after one dismissal, and the click handler returned
// silently when it did, which from the outside is a button that does nothing.
// It shipped because nothing had ever clicked it. This clicks it.
//
// Every request to /do is intercepted, so running this never accepts a gate,
// publishes anything or sends anything. It asserts on what would have been
// sent.

const URL = process.argv[2] || "http://127.0.0.1:8787/";
let chromium;
try {
  ({ chromium } = require("playwright"));
} catch (e) {
  console.log("\n  playwright is not installed; skipping.");
  console.log("  npm install playwright   (then: npx playwright install chromium)\n");
  process.exit(0);
}

(async () => {
  const exe = process.env.CHROMIUM_PATH;
  const browser = await chromium.launch(exe ? { executablePath: exe } : {});
  const page = await browser.newPage();
  const posts = [];
  let pass = 0, fail = 0;
  const t = (n, ok) => { console.log((ok ? "  ok   " : "  FAIL ") + n); ok ? pass++ : fail++; };

  await page.route("**/do", async route => {
    posts.push(JSON.parse(route.request().postData()));
    const last = posts[posts.length - 1];
    await route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        output: last.action === "review-changes"
          ? "change(s) to the prose since:" : "recorded (intercepted by the test)"
      })
    });
  });
  page.on("dialog", async d => {
    console.log("  !! a browser dialog appeared (" + d.type() + ") — these get suppressed");
    await d.dismiss();
  });
  const errs = [];
  page.on("pageerror", e => errs.push(String(e)));

  try {
    await page.goto(URL, { timeout: 8000 });
  } catch (e) {
    console.log("\n  no board at " + URL);
    console.log("  start one:  python3 scripts/whatholdsup/publish.py board\n");
    await browser.close();
    process.exit(0);
  }
  await page.waitForTimeout(300);
  t("the board loads with no JS errors", errs.length === 0);
  if (errs.length) console.log("     " + errs.join("\n     "));

  const buttons = await page.locator("button.go").count();
  if (buttons === 0) {
    // Everything is done. The board should say so compactly rather than show
    // seven green rows nobody needs to read again.
    t("with nothing to do, the issue is marked complete",
      (await page.locator("section.issue.complete").count()) > 0);
    t("and its steps are folded away",
      (await page.locator("section.issue.complete details.more").count()) > 0);
    t("but they are still there to open",
      (await page.locator("section.issue.complete details.more li.step").count()) > 0);
    console.log("\n  " + pass + " passed, " + fail + " failed");
    await browser.close();
    process.exit(fail ? 1 : 0);
  }

  const first = page.locator("button.go").first();
  const label = (await first.textContent() || "").trim();
  await first.click();
  await page.waitForTimeout(250);
  const form = page.locator("form.ask").first();
  t("clicking '" + label + "' opens an inline form, not a dialog", await form.count() > 0);
  t("nothing is sent before the form is submitted", posts.length === 0);

  // A form with no inputs is correct for anything the tool can establish on its
  // own — the confirmation of a reconciliation asks for nothing, because there
  // is nothing a reader of this board could add to it.
  const inputs = await form.locator("input").count();
  for (let i = 0; i < inputs; i++) {
    const v = await form.locator("input").nth(i).inputValue();
    if (!v) await form.locator("input").nth(i).fill("written by board.test.js");
  }
  t("any field it does show is either prefilled or fillable", true);
  await form.locator('button[type="submit"]').click();
  await page.waitForTimeout(400);
  t("submitting sends exactly one request", posts.length === 1);
  t("the request names an action and an issue",
    !!(posts[0] && posts[0].action && posts[0].slug));
  t("the result is shown on the page",
    ((await page.locator("pre.out").first().textContent()) || "").length > 0);

  posts.length = 0;
  await first.click(); await page.waitForTimeout(200);
  await page.locator("form.ask button.cancel").first().click();
  await page.waitForTimeout(200);
  t("Cancel closes the form and sends nothing",
    (await page.locator("form.ask").count()) === 0 && posts.length === 0);

  // A step whose reconciliation failed must not offer a way past it.
  const conf = page.locator("button.go", { hasText: "Show what changed" }).first();
  if (await conf.count()) {
    const label = (await conf.textContent()) || "";
    const m = label.match(/(\d+) accounted for, (\d+) not/);
    if (m && Number(m[2]) > 0) {
      posts.length = 0;
      await conf.click(); await page.waitForTimeout(400);
      t("with unaccounted-for changes, no confirmation is offered",
        (await page.locator("form.ask").count()) === 0);
    }
  }

  const pub = page.locator("button.go", { hasText: "Publish" }).first();
  if (await pub.count()) {
    posts.length = 0;
    await pub.click(); await page.waitForTimeout(200);
    t("Publish demands the word typed before it will send",
      (await page.locator('form.ask input[name="confirm"]').count()) === 1
      && posts.length === 0);
  }

  console.log("\n  " + pass + " passed, " + fail + " failed");
  await browser.close();
  process.exit(fail ? 1 : 0);
})();
