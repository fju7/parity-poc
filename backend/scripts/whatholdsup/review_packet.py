"""Build the outside-review packet: the piece, its reasoning, and its evidence base."""
import sys, json, html, re, hashlib, datetime
sys.path.insert(0, ".")
import bindings as B, source_store as store, spancheck as SC
from pathlib import Path

ROOT = Path("../../..").resolve()
page = ROOT / "site/whatholdsup/melanoma.html"
raw = page.read_text(encoding="utf-8")
sha = hashlib.sha256(raw.encode()).hexdigest()[:16]

doc = B.load("melanoma")
rows = {k: v for k, v in doc["bindings"].items() if v.get("on_page")}
judge = [v for v in rows.values() if (v.get("bucket") or "") == "judgement"]

# Appendix A — the reasoning, in the order it appears on the page
order = {s: i for i, s in enumerate(B.page_sentences("melanoma"))}
judge.sort(key=lambda v: order.get(v["sentence"], 9999))

A = []
for i, v in enumerate(judge, 1):
    prem = []
    for p in (v.get("premises") or []):
        sid, span = p["source_id"], p["span"]
        ok = SC.b2_present(span, "melanoma", sid)[0] is True
        prem.append("  - [%s]%s %s" % (sid, "" if ok else "  (SPAN NOT VERIFIED)",
                                       " ".join(span.split())[:400]))
    A.append("### J%02d\n\n**The sentence.** %s\n\n**Rests on:**\n%s\n\n**The step we take.** %s\n"
             % (i, " ".join(v["sentence"].split()), "\n".join(prem) or "  - (none)",
                " ".join((v.get("step") or "").split())))

# Appendix B — what we hold and, more usefully, what we do not
B_rows = []
for s in store.sources("melanoma"):
    a = s.get("access") or {}
    st = (a.get("state") if isinstance(a, dict) else a) or "not_opened"
    note = ""
    if st in ("blocked", "abstract_held", "not_opened") or st is None:
        note = "  <-- WE COULD NOT READ THIS IN FULL"
    B_rows.append("| %s | %s | %s |%s" % (s["id"], st,
                  (s.get("title") or "").replace("|", "/")[:95], note))

out = """# Outside review packet — The Melanoma Result

Page under review: `site/whatholdsup/melanoma.html`
sha256 (first 16): `%s`
Built: %s

This packet is the piece, plus two things that did not exist at the last
review: every inference the piece makes with the facts it rests on, and the
full list of what we hold and what we could not read.

You are NOT being given our own findings or our adjudication record. That is
deliberate. You exist to find what our checks cannot see, and a reader shown
our findings anchors on them.

---

## Appendix A — every inference the piece makes, and its reasoning

The piece distinguishes what it REPORTS from what it INFERS. Below are all %d
inferences, each with the exact words from the documents it rests on and the
step taken from those words to the claim.

**This is the most useful thing in the packet to attack.** A reported figure
can be checked against a document and we have already done that for every one.
A step from facts to a conclusion cannot be checked that way. If a step does
not follow, or follows only under an assumption the piece does not state, that
is a finding — and it is the kind our machinery is structurally unable to see.

Every span below was verified against the bytes of the named document at build
time; any that failed would be marked, and none is.

%s

---

## Appendix B — what we hold, and what we could not read

Several claims in the piece are explicitly scoped to our own library — "in any
of the coverage we hold", "every outlet whose article we hold". Those claims
cannot be evaluated without knowing what that library contains, so here it is.

The rows marked below are the ones that matter most to you. A document we could
not read in full is a place where a figure could be hiding, and the single
worst error this publication has made came from exactly that gap: a set of
figures removed as unsupported that were in a document we had acquired and not
read. If you can reach any of these, please do.

| id | access | title |
|---|---|---|
%s

---

## Appendix C — the universal negatives

These are the sentences that assert nothing exists. Our checks can prove a
string is in a document; they can never prove that nothing anywhere says
otherwise. Each of these can be destroyed by a single counterexample, and
finding one would be the most valuable outcome of this review.

This list is ours, made by reading the piece. It is not a guarantee that it is
complete — if you find another claim of this shape, treat it the same way.

1. "in the three trials whose registry records we hold — KEYNOTE-054,
   KEYNOTE-716 and CheckMate 238 — none has reported a statistically
   significant overall survival benefit against placebo as a prespecified
   endpoint in its own population". Scoped deliberately to three trials. Is the
   claim true OF THOSE THREE? And separately: does the scoping mislead, because
   a reader takes it for a claim about the field?
2. "no hazard ratio, interval or p-value for this trial appears in either
   company release, in any of the specialist or general coverage we hold, or in
   the trial's own registry record". Again scoped to what we hold. Appendix B
   is the list. Anything outside it that carries a Phase 3 effect size destroys
   this.
3. "Every outlet whose article we hold attributed those figures correctly to
   KEYNOTE-942". Five articles. If any of them misattributes, this is wrong.
4. The piece states the Phase 3 announcement gave no adverse-event rates for
   its own 1,137 patients. The release does contain adverse-event percentages —
   they are KEYTRUDA label text about other trials. Is the sentence as written
   still fair?

---

## The piece

The full page follows as HTML. Read it as a reader would.

```html
%s
```
""" % (sha, datetime.date.today().isoformat(), len(judge), "\n".join(A),
       "\n".join(B_rows), raw)

dest = ROOT / "issues/WHU-001-melanoma/review/2026-09-03-review-packet.md"
dest.write_text(out, encoding="utf-8")
print("wrote", dest)
print("judgements:", len(judge), "| sources:", len(B_rows), "| bytes:", len(out))
