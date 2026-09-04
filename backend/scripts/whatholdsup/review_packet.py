"""The outside-review packet: the piece, its reasoning, and its evidence base.

WHAT THIS IS FOR
----------------
Everything else in this repository checks the page against documents we hold.
None of it can check a step from facts to a conclusion, and none of it can
check a claim that nothing anywhere says otherwise. Those two things are what
an outside reader is for, so those two things are what this packet puts in
front of them: Appendix A is every inference with its premises, Appendix C is
every universal negative.

Appendix B is what we hold and, more usefully, what we could not read.
Appendix D is where our own machinery has not looked -- a coverage statement,
not a findings statement. The packet deliberately withholds our findings and
our adjudication record, because a reader shown them anchors on them.

This module is the CONTENT. `review_bundle.py` renders the same content, plus
the reviewer's prompt and the piece itself, into one self-contained HTML file
to hand over. Both read from here so the two cannot drift.
"""
import sys, json, hashlib, datetime
sys.path.insert(0, ".")
import bindings as B, source_store as store, spancheck as SC
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SLUG = "melanoma"
PAGE = ROOT / "site/whatholdsup/melanoma.html"
CASE = ROOT / "issues/WHU-001-melanoma"


def page_html() -> str:
    return PAGE.read_text(encoding="utf-8")


def page_sha() -> str:
    return hashlib.sha256(page_html().encode()).hexdigest()


# ---------------------------------------------------------------------------
# Appendix A -- every inference, with its premises re-verified at build time
# ---------------------------------------------------------------------------

def inferences() -> list[dict]:
    """Every judgement-bucket row that is on the page, with its premises
    re-verified against the document bytes.

    THE STORED SENTENCE IS NOT TRUSTED, AND THE ROW KEY IS. A row is keyed by
    the fingerprint of the sentence, and `scan()` sets on_page from that key --
    but it never rewrites the row's `sentence` field afterwards. So a row can
    be correctly matched to a sentence on the page while the text we PRINT for
    it is an older, shorter version. On 2026-09-04 exactly that had happened to
    the Morning Glory judgement: the packet showed the reviewer a claim ending
    "in any of the general", with the clause that scopes it -- "coverage we
    hold" -- missing. The reviewer would have been arguing with a sentence the
    piece does not contain.

    So the text printed here comes from the PAGE, looked up by the row's key,
    and a row whose key is not on the page stops the build.
    """
    doc = B.load(SLUG)
    live = {B.fingerprint(s): s for s in B.page_sentences(SLUG)}
    pairs = [(k, v) for k, v in doc["bindings"].items()
             if v.get("on_page") and (v.get("bucket") or "") == "judgement"]
    missing = [k for k, _ in pairs if k not in live]
    if missing:
        raise SystemExit(
            "REFUSING TO BUILD: %d judgement row(s) are marked on_page but their "
            "fingerprint is not among the page's sentences: %s. Run bindings.py "
            "scan; do not send a packet whose Appendix A quotes sentences the "
            "piece does not contain." % (len(missing), ", ".join(missing[:5])))

    order = {s: i for i, s in enumerate(B.page_sentences(SLUG))}
    pairs.sort(key=lambda kv: order.get(live[kv[0]], 9999))

    out = []
    for i, (k, v) in enumerate(pairs, 1):
        prem = []
        for p in (v.get("premises") or []):
            sid, span = p["source_id"], p["span"]
            prem.append({"source_id": sid,
                         "span": " ".join(span.split())[:400],
                         "verified": SC.b2_present(span, SLUG, sid)[0] is True})
        out.append({"n": i,
                    "sentence": " ".join(live[k].split()),
                    "drifted": B.fingerprint(v.get("sentence") or "") != k,
                    "premises": prem,
                    "step": " ".join((v.get("step") or "").split())})
    return out


def appendix_a_md(rows: list[dict]) -> str:
    out = []
    for r in rows:
        prem = ["  - [%s]%s %s" % (p["source_id"],
                                   "" if p["verified"] else "  (SPAN NOT VERIFIED)",
                                   p["span"])
                for p in r["premises"]] or ["  - (none)"]
        out.append("### J%02d\n\n**The sentence.** %s\n\n**Rests on:**\n%s\n\n"
                   "**The step we take.** %s\n"
                   % (r["n"], r["sentence"], "\n".join(prem), r["step"]))
    return "\n".join(out)


def failed_spans(rows: list[dict]) -> int:
    return sum(1 for r in rows for p in r["premises"] if not p["verified"])


# ---------------------------------------------------------------------------
# Appendix B -- what we hold, and what we could not read
# ---------------------------------------------------------------------------

UNREAD = ("blocked", "abstract_held", "not_opened")


def library() -> list[dict]:
    out = []
    for s in store.sources(SLUG):
        a = s.get("access") or {}
        st = (a.get("state") if isinstance(a, dict) else a) or "not_opened"
        out.append({"id": s["id"], "state": st,
                    "title": (s.get("title") or "").replace("|", "/")[:95],
                    "unread": st in UNREAD or st is None})
    return out


def appendix_b_md(rows: list[dict]) -> str:
    return "\n".join(
        "| %s | %s | %s |%s" % (r["id"], r["state"], r["title"],
                                "  <-- WE COULD NOT READ THIS IN FULL"
                                if r["unread"] else "")
        for r in rows)


# ---------------------------------------------------------------------------
# what changed since the last outside review
# ---------------------------------------------------------------------------

def changed_md() -> str:
    """An unrun check is not a pass: if this cannot be computed, say so."""
    try:
        import publish as P
        ok, bad, _stale = P.reconcile(SLUG)
        rev = [r for r in json.loads(P.REVIEWS.read_text()).get("reviews", [])
               if r.get("issue") == SLUG]
        last = rev[-1] if rev else None
        return (
            "The last outside review of this piece read a file whose sha256 begins\n"
            "`%s`, on %s. Since then **%d changes to the prose** have gone\n"
            "in; %d of them reconcile to a written decision and **%d do not**.\n\n"
            "That number is the reason this is a full review and not a delta review.\n"
            "Most of the piece is not the piece that was read. Do not go looking for\n"
            "what changed — read it as a reader would, from the top, as though no\n"
            "review had happened."
            % (str(last.get("sha"))[:16] if last else "?",
               str(last.get("at"))[:10] if last else "?",
               len(ok) + len(bad), len(ok), len(bad)))
    except Exception as exc:                                # noqa: BLE001
        return ("The change count against the last review COULD NOT BE COMPUTED: %s\n"
                "Treat that as unknown, not as nothing. Read the piece whole." % exc)


# ---------------------------------------------------------------------------
# Appendix D -- where our own machinery has not looked
# ---------------------------------------------------------------------------

def coverage_md() -> str:
    D = []
    try:
        import unjudged as U
        for name, state, detail in U.preflight_rows(SLUG, PAGE):
            # the re-gating cost estimate is our budgeting, not the reviewer's
            # problem; the sentences themselves follow below.
            detail = detail.split("  —  re-gating costs")[0]
            D.append("- **%s** — %s: %s" % (name, state, detail))
        rp = PAGE.with_suffix(PAGE.suffix + ".gate.json")
        known = set(json.loads(rp.read_text(encoding="utf-8"))
                    .get("sentence_fingerprints") or [])
        if known:
            new = [s for fp, s in U.fingerprints(page_html()).items()
                   if fp not in known]
            if new:
                D.append("")
                D.append("The sentences no role has read:")
                D += ["  %d. %s" % (i, " ".join(s.split())[:300])
                      for i, s in enumerate(new, 1)]
    except Exception as exc:                                # noqa: BLE001
        D = ["- The gate-coverage check COULD NOT BE RUN: %s. Unknown, not clean."
             % exc]
    return "\n".join(D)


# ---------------------------------------------------------------------------
# Appendix C -- hand-made, by reading the piece. Rewritten 2026-09-04.
# ---------------------------------------------------------------------------

APPENDIX_C = """These are the sentences that assert nothing exists. Our checks can prove a
string is in a document; they can never prove that nothing anywhere says
otherwise. Each of these can be destroyed by a single counterexample, and
finding one would be the most valuable outcome of this review.

This list is ours, made by reading the piece. It is not a guarantee that it is
complete — if you find another claim of this shape, treat it the same way.

Two of them (marked DECLARED) are also declared in machine-readable form and a
search of our own library runs against them on every publish. That search can
only see documents we hold; it is not evidence about anything outside Appendix
B, and it has already falsified one sentence on this page once.

**The two most exposed claims are 8 and 9.** Every other negative here is
scoped to something a reader can check — "we hold", "this page", "the registry
record". Those two are scoped to the world.

1. DECLARED — **"We looked: no hazard ratio, interval or p-value for this trial
   appears in either company release, in any of the specialist or general
   coverage we hold, or in the trial's own registry record, which as of
   2 September 2026 carries no posted results at all…"** Scoped to what we
   hold. Appendix B is the list. Anything outside it that carries a Phase 3
   effect size destroys this.

2. DECLARED — **"Every survival figure in the programme is exploratory and
   rests on a handful of deaths."** This ranges over the whole programme: both
   trials, every release, both papers, four registry records. The next two
   sentences name the two figures we found (0.425 on nine deaths; 0.471 on
   fourteen). A third survival figure anywhere in the programme, or either of
   those two turning out to be something other than exploratory, destroys it.

3. **"For adjuvant PD-1 inhibitors specifically — the comparison arm in this
   very trial — neither of the two placebo-controlled trials whose registry
   records we hold — KEYNOTE-054 and KEYNOTE-716 — has posted an
   overall-survival result at all. That is an absence of a finding, not a null
   one."** Two questions, and they are separate. Is it true of those two? And
   does the scoping mislead, because a reader takes it for a claim about the
   field? The paragraph that follows deliberately excludes CheckMate 238 and
   says why; check that the exclusion is honest and not convenient.

4. **"Every outlet whose article we hold attributed those figures correctly to
   KEYNOTE-942 in its own voice"** — six outlets, all named. Two ways to break
   it: an outlet that misattributes, or the qualification "in its own voice"
   doing work it should not. That phrase was added so that an outlet quoting
   someone else loosely would not count against us. Decide whether that is a
   fair distinction or a hedge that makes the sentence unfalsifiable.

5. **"Neither reading appears in any of the general coverage we hold."**
   (The Morning Glory / Pharmacy Times disagreement about stage IIB–IIC.)
   Scoped to Appendix B.

6. **"this page holds no document about one"** — a CTLA-4 inhibitor. A claim
   about our own library, checkable against Appendix B.

7. **"the Phase 3 announcement gave no adverse-event rates for its own 1,137
   patients"**. The release does contain adverse-event percentages; they are
   KEYTRUDA label text describing other trials, which is why the sentence is
   scoped to "its own 1,137 patients". Is that scoping enough, or does the
   sentence still leave a reader with a false picture of the release?

8. **"No hazard ratio, no interval, no percentage has been published."**
   (Under "Not established".) This one is NOT scoped to what we hold. As
   written it is a claim about the world. Either it is defensible as written or
   it needs the scope the sentence in 1 carries.

9. **"Merck and Moderna have not published one"** — a subgroup breakdown by
   stage. Also unscoped, and a single company slide, poster or supplementary
   table destroys it.

10. **"an outlet we can find no other publication citing"** (Morning Glory
    Sciences). A negative about our searching, not about our library. We think
    the sentence is honest because it says "we can find"; judge whether it
    reads that way, given the weight the paragraph then puts on the source.

11. **"Melanoma is not one of the topics our pipeline covers, so nothing here
    was produced by the scoring system that runs the site."** A claim about our
    own process. You cannot check it from outside and we are flagging it for
    that reason: take it as an assertion we are making, not as something this
    packet evidences."""

APPENDIX_D_TAIL = """The model-based fact-check gate has now run its budgeted number of times for
this issue. The sentences listed above as unread will not be read by it before
publication, which makes them exactly the sentences worth your attention.

Two further known blind spots, recorded in `docs/whatholdsup-open-gaps.md`:
the page's meta description ships as prose that no check reads, and material
inside `<q>` quotation marks is invisible to the test that decides whether a
sentence is empirical — so a figure that appears only inside a quotation is not
required to have a binding row."""

APPENDIX_A_INTRO = """The piece distinguishes what it REPORTS from what it INFERS. Below are all %d
inferences, each with the exact words from the documents it rests on and the
step taken from those words to the claim.

**This is the most useful thing in the packet to attack.** A reported figure
can be checked against a document and we have already done that for every one.
A step from facts to a conclusion cannot be checked that way. If a step does
not follow, or follows only under an assumption the piece does not state, that
is a finding — and it is the kind our machinery is structurally unable to see.

Every span below was checked against the bytes of the named document at build
time. %s"""

APPENDIX_B_INTRO = """Several claims in the piece are explicitly scoped to our own library — "in any
of the coverage we hold", "every outlet whose article we hold". Those claims
cannot be evaluated without knowing what that library contains, so here it is.

The rows marked below are the ones that matter most to you. A document we could
not read in full is a place where a figure could be hiding, and the single
worst error this publication has made came from exactly that gap: a set of
figures removed as unsupported that were in a document we had acquired and not
read. If you can reach any of these, please do."""

APPENDIX_D_INTRO = """This is a coverage statement, not a findings statement. It says which parts of
the page our checks have and have not examined, so you know where the absence
of a flag means nothing at all."""


def spans_line(rows: list[dict]) -> str:
    n = failed_spans(rows)
    return ("None failed." if not n else
            "**%d FAILED and are marked below — read those first.**" % n)


def main() -> int:
    today = datetime.date.today().isoformat()
    inf = inferences()
    lib = library()
    out = """# Outside review packet — The Melanoma Result

Page under review: `site/whatholdsup/melanoma.html`
sha256 (first 16): `%s`
Built: %s

This packet is the piece, plus three things that did not exist at the last
review: every inference the piece makes with the facts it rests on, the full
list of what we hold and what we could not read, and the list of places our
own machinery has not looked.

You are NOT being given our own findings or our adjudication record. That is
deliberate. You exist to find what our checks cannot see, and a reader shown
our findings anchors on them.

---

## What has changed since the last outside review

%s

---

## Appendix A — every inference the piece makes, and its reasoning

%s

%s

---

## Appendix B — what we hold, and what we could not read

%s

| id | access | title |
|---|---|---|
%s

---

## Appendix C — the universal negatives

%s

---

## Appendix D — where our own machinery has not looked

%s

%s

%s

---

## The piece

The full page follows as HTML. Read it as a reader would.

```html
%s
```
""" % (page_sha()[:16], today, changed_md(),
       APPENDIX_A_INTRO % (len(inf), spans_line(inf)), appendix_a_md(inf),
       APPENDIX_B_INTRO, appendix_b_md(lib),
       APPENDIX_C,
       APPENDIX_D_INTRO, coverage_md(), APPENDIX_D_TAIL,
       page_html())

    dest = CASE / "review" / ("%s-review-packet.md" % today)
    dest.write_text(out, encoding="utf-8")
    print("wrote", dest)
    print("judgements:", len(inf), "| failed spans:", failed_spans(inf),
          "| sources:", len(lib), "| bytes:", len(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
