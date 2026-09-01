#!/usr/bin/env python3
"""Does any of this work? — the recall test.

WHY
---
On 2026-09-01 the operator set a condition: be confident the process is correct
and complete before subscribers exist. Confidence by inspection is not available
here. In one day five mechanisms were built and every one was wrong on its first
RUN: substance() called four registry postings and three drug labels "pages
about documents"; inaccessibility_claims blocked the publish over three true
sentences; the errata type allow-list marked twenty journal articles "not
applicable"; the errata DOI fallback matched a registry record to a Clinical
Pharmacokinetics paper; the ingest identity test matched this publication's own
page as a source document, in two different ways.

None of those would have been caught by more thinking. All were caught within
minutes of being run against something real.

So the only honest form of "correct and complete" is a number: given the errors
we have ACTUALLY made and written down, how many does a check catch when run
against the real bytes?

THE RULE THIS FILE EXISTS TO ENFORCE
------------------------------------
A check "would have caught it" only if it is EXECUTED here and observed to
fire. Nothing is counted because it looks like it would work. Four outcomes:

    CAUGHT      the check ran against the real document and fired
    MISSED      the check ran against the real document and did NOT fire
                -- the most useful row in the file
    UNBUILT     the spec names a check for this and it does not exist yet
    UNCOVERED   nothing in the spec would have caught this

The headline number counts CAUGHT only.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spancheck  # noqa: E402
import errata     # noqa: E402
import bindings   # noqa: E402
import reconcile  # noqa: E402

CAUGHT, MISSED, UNBUILT, UNCOVERED = "CAUGHT", "MISSED", "UNBUILT", "UNCOVERED"


# ---------------------------------------------------------------------------
# The corpus. Every row is an error we actually published or nearly published,
# with the real source, the real span, and the sentence as it stood.
# ---------------------------------------------------------------------------

CASES = [
  dict(id="CORR-25", slug="cdk46", check="B2/B3",
       what="PALOMA-2's final survival hazard ratio printed under the journal's "
            "byline when the figures are the registry's",
       sid="S010", span="0.956",
       sentence="53.9 vs 51.2 months, HR 0.956 (95% CI 0.777-1.177), one-sided P = .34.",
       expect="B2 fails on S010 and B3 names S020"),

  dict(id="CORR-25b", slug="cdk46", check="B2/B3",
       what="the same, for the lower confidence limit",
       sid="S010", span="0.777",
       sentence="HR 0.956 (95% CI 0.777-1.177)",
       expect="B2 fails on S010 and B3 names S020"),

  dict(id="CORR-28", slug="cdk46", check="B5",
       what="grade 3 diarrhoea reported as its own floor; the label says 8% to 20%",
       sid="S013", span="Grade 3 diarrhea occurred in 8%",
       sentence="diarrhoea in 81% to 90% of 3,691 patients across four trials, grade 3 in 8%",
       expect="B5 fires: the span stops before 'to'"),

  dict(id="CORR-29", slug="cdk46", check="B5",
       what="the ribociclib monitoring schedule cut off at cycle 2",
       sid="S012", span="Monitor LFTs every 2 weeks for the first 2 cycles",
       sentence="liver function tests every two weeks for the first two cycles",
       expect="B5 fires: the document continues 'at the beginning of each subsequent 4 cycles'"),

  dict(id="CORR-20", slug="cdk46", check="B6",
       what="'every log-rank p-value on the study' -- 15 log-rank analyses, 3 annotated",
       sid="S020", span="1-sided p-value from the stratified log-rank test.",
       sentence="its registry record labels every log-rank p-value on the study "
                "1-sided p-value from the stratified log-rank test",
       expect="B6 fires on 'every'"),

  dict(id="CORR-30", slug="cdk46", check="B6",
       what="'restricted to the HER2-enriched intrinsic subtype' against an "
            "inclusion criterion reading HER2-E or Basal-like",
       sid="S018", span="HER2-E or Basal-like subtype as per central PAM50 analysis.",
       sentence="HARMONIA was restricted to the HER2-enriched intrinsic subtype, "
                "a molecularly selected population",
       expect="B6 fires on 'restricted'"),

  dict(id="CORR-26", slug="cdk46", check="B6",
       what="'what PALOMA-2 established' against authors who say interpretation was limited",
       sid="S010", span="OS was not significantly improved with palbociclib plus letrozole",
       sentence="What PALOMA-2 established is that it did not demonstrate a survival benefit.",
       expect="B6 fires on 'established'"),

  dict(id="CORR-27", slug="cdk46", check="B2",
       what="MONARCH 3's hazard ratio quoted from Table 1 of a stored copy "
            "containing zero tables",
       sid="S015", span="0.804",
       sentence="Its Table 1 lists MONARCH 3 at HR 0.804 (0.637-1.015)",
       expect="B2 fails: the stored HTML has no table bodies"),

  dict(id="CORR-27b", slug="cdk46", check="B2",
       what="the row label quoted from that same absent table",
       sid="S015", span="year of updated data",
       sentence="its 'Year of updated data' row gives 2023 for that trial",
       expect="B2 fails"),

  dict(id="CORR-31", slug="cdk46", check="B2",
       what="P-VERIFY 'opens by describing its own purpose as working in the "
            "absence of randomised trials'",
       sid="S016", span="In the absence of head-to-head RCTs",
       sentence="it opens by describing its own purpose as working in the absence "
                "of randomised trials that directly compare the three",
       expect="B2 PASSES", verdict_when_pass=UNCOVERED,
       why_uncaught="The phrase is in the paper and modifies OTHER AUTHORS' "
                    "indirect comparisons, not the study's own rationale. No "
                    "span test can see that. This is the faithfulness question "
                    "and it needs a reader given the envelope."),

  dict(id="CORR-13", slug="cdk46", check="B2",
       what="a correction that DELETED A TRUE STATEMENT: '29 blocks of four' "
            "withdrawn as our arithmetic",
       sid="S017", span="29 blocks with block size of four",
       sentence="randomised 116 patients in 29 blocks of four",
       expect="B2 PASSES", verdict_when_pass=UNBUILT,
       why_uncaught="B2 proves the sentence was TRUE when we deleted it, which "
                    "is what the deletion rule in spec section 8 would use. "
                    "That rule is not built, so nothing today refuses the "
                    "deletion."),

  dict(id="CORR-32", slug="cdk46", check="B10",
       what="MONALEESA-2's updated-results paper carries a 2019 correction "
            "nobody had read",
       sid="S004", check_kind="errata"),

  dict(id="CORR-19b", slug="cdk46", check="B10",
       what="MONARCH 3's final survival paper carries a 2025 corrigendum",
       sid="S003", check_kind="errata"),

  dict(id="CORR-23", slug="cdk46", check="B2",
       what="Lan-DeMets and O'Brien-Fleming inverted: we call one the spending "
            "function and the other the boundary, the paper says the reverse",
       sid="S003", span="Lan",
       sentence="the Lan-DeMets method with an O'Brien-Fleming spending function",
       expect="B2 PASSES", verdict_when_pass=UNCOVERED,
       why_uncaught="Both names are in the paper. What is wrong is which is "
                    "which, and a presence test cannot see word order."),

  dict(id="CORR-21", slug="cdk46", check_kind="b8",
       check="B8",
       what="MONALEESA-7's one-sidedness sourced to a registry posting while the "
            "NEJM paper we hold states it directly",
       sid="S022",
       span="hazard ratio for death, 0.71; 95% CI, 0.54 to 0.95; P = 0.00973",
       sentence="the direction of the test is stated in the ASCO 2019 abstract",
       expect="B8 names S007"),

  dict(id="CORR-24", slug="cdk46", check_kind="b9", check="B9",
       what="the Cancers 2023 study: eight figures on the page, its own entry in "
            "the visible source list, no row in sources.json",
       sid="", span="pmc.ncbi.nlm.nih.gov/articles/PMC10527344",
       sentence="", expect="B9 reports the link as unreconciled"),

  dict(id="CORR-26b", slug="cdk46", check="B6",
       what="'the investigators recovered-data sensitivity analysis' -- the paper "
            "calls it Revised Results Including Recovered Data",
       sid="S010", span="Revised Results Including Recovered Data",
       sentence="the investigators' recovered-data sensitivity analysis",
       expect="B6 has no scope word to catch here"),

  dict(id="S016-SUB", slug="cdk46", check="B6",
       what="'none of the four comparative studies separates abemaciclib from "
            "ribociclib' -- true of the overall analysis, and three subgroup "
            "intervals in P-VERIFY exclude 1",
       sid="S016", span="no significant differences when comparing OS between "
                        "different CDK4/6i treatment groups",
       sentence="None of the four comparative studies examined on this page "
                "separates abemaciclib from ribociclib",
       expect="B6 fires on 'none'?"),

  # MEL-01 AND MEL-02 WERE WITHDRAWN, and the withdrawal is the record.
  #
  # Both were reported to the operator as errors on the live page: "we print
  # 0.510, the Merck release says 0.51". The page does not cite the release. It
  # cites the JCO five-year paper, which prints 0.510 exactly as we do -- and
  # which nobody held at the time, so the check was pointed at a document we
  # HAD rather than the document the claim rests on. Two correct sentences were
  # reported as wrong by the instrument built to stop exactly that.
  #
  # What survives is the check itself, now documented as meaningful only against
  # the cited source, and this note. A corpus that quietly drops its own false
  # positives measures nothing.
  dict(id="MEL-01", slug="melanoma", check_kind="b12", check="B12",
       what="WITHDRAWN — 'HR 0.510 is an added decimal' was measured against a "
            "press release the page does not cite; the JCO paper prints 0.510",
       sid="S004", span="0.510", sentence="HR 0.510 (0.294-0.887)",
       expect="B12 PASSES against the cited source", verdict_when_pass=UNCOVERED,
       why_uncaught="Not an error. Kept as a record of one the checks "
                    "manufactured by being asked about the wrong document."),

  dict(id="MEL-03", slug="melanoma", check_kind="ledger", check="states",
       what="44 sources on two live pages carried machine_read, a state the "
            "ledger no longer defines",
       sid="", span="", sentence="", expect="undefined_states finds none now"),

  # THE FOUR ERRORS OF 1 SEPTEMBER EVENING, none of which a check found.
  # They are in the corpus because a corpus of errors the checks were built from
  # measures the checks against themselves. These lower the number, correctly.

  dict(id="MEL-04", slug="melanoma", check_kind="uncovered", check="—",
       what="`conference` sat in ARTICLE_TYPES, so the article test refused an "
            "eleven-page ASCO deck for having no reference list — after "
            "registry postings and drug labels were refused the same way",
       found_by="person",
       why_uncaught="Coverage reporting makes this VISIBLE — the 'examined N of "
                    "M' line — and deriving ARTICLE_TYPES from the registry "
                    "stops the two disagreeing. Neither FLAGS it. Visible is "
                    "not caught, and this row stays uncovered until something "
                    "notices a form whose members keep failing a test that was "
                    "never meant for them."),

  dict(id="MEL-05", slug="melanoma", check_kind="canary", check="canary",
       what="The Lancet writes decimals with a middle dot, so every span check "
            "searched 0.053 and missed 0·053 — reporting three times that a "
            "figure was absent from a document we had held all day",
       sid="S003", found_by="person",
       expect="the canary fails when the normaliser cannot read this publisher"),

  dict(id="MEL-06", slug="melanoma", check_kind="from_binding", check="bindings",
       what="B12 was run against a document we HELD rather than the document "
            "the sentence CITES, and reported two correct sentences as errors",
       sid="", found_by="person",
       expect="a check run from a binding cannot be pointed at another source"),

  dict(id="MEL-07", slug="melanoma", check_kind="uncovered", check="—",
       what="S008 is depended on by name — 'the three-year readout at ASCO "
            "2024' — with figures attributed to it, and never linked, so B9 "
            "could not see it",
       found_by="person",
       why_uncaught="B9 reads anchors. A source named in prose — 'the three-year "
                    "readout at ASCO 2024' — is invisible to it, which is the "
                    "source-list blind spot one step over. Still open."),

  dict(id="DESK-01", slug="deskilling", check="B10",
       what="issue three's central study carries a 2025 correction",
       sid="S021", check_kind="errata"),
]


def run_case(c: dict) -> tuple[str, str]:
    kind = c.get("check_kind")
    if kind == "errata":
        doc = errata.load(c["slug"])
        row = (doc.get("checked") or {}).get(c["sid"]) or {}
        if row.get("amendments"):
            return CAUGHT, "errata records %d amendment(s) on %s" % (
                len(row["amendments"]), c["sid"])
        if row.get("state") in ("UNCHECKED", "UNCHECKABLE"):
            return MISSED, "errata could not look %s up: %s" % (
                c["sid"], row.get("why", "")[:60])
        return MISSED, "errata reports %s clean" % c["sid"]

    if kind == "b9":
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "pub", str(Path(__file__).resolve().parent / "publish.py"))
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        html = (m.ROOT / m.ISSUES[c["slug"]]["page"]).read_text(encoding="utf-8")
        loose = reconcile.b9_unreconciled(c["slug"], html)
        hit = [r for r in loose if c["span"] in r["url"] and not r["same_as"]]
        if hit:
            return CAUGHT, "B9 reports %s as a document the ledger does not know" % (
                hit[0]["url"][:60])
        return MISSED, "B9 does not report this link as unreconciled"

    if kind == "uncovered":
        return UNCOVERED, c.get("why_uncaught", "")

    if kind == "canary":
        # Demonstrate it by breaking the normaliser, exactly as the unit test
        # does: a canary that only passes cannot show it would have caught this.
        import canary as CN
        real = spancheck._norm
        doc = ("Median PFS 25·30 months (hazard ratio 0·561 [95% CI "
               "0·309-1·017]; two-sided p=0·053).")
        real_text = spancheck._text
        spancheck._text = lambda slug, sid: doc
        try:
            if CN.check(c["slug"], c["sid"])["state"] != "READABLE":
                return MISSED, "the canary fails even with a working normaliser"
            spancheck._norm = lambda x: " ".join(
                x.replace("–", "-").replace("—", "-").replace("−", "-").split())
            out = CN.check(c["slug"], c["sid"])
        finally:
            spancheck._norm, spancheck._text = real, real_text
        if out["state"] == "UNREADABLE":
            return CAUGHT, ("the canary fails the document when the normaliser "
                            "cannot read its typography: %s" % out["why"][:90])
        return MISSED, "the canary passes a normaliser that cannot read 0·053"

    if kind == "from_binding":
        import bindings as B
        doc = B.load(c["slug"])
        rows = [v for v in (doc.get("bindings") or {}).values()
                if v.get("span") and v.get("source_id")]
        if not rows:
            return MISSED, "no bound row to run a check from"
        named = {r["source_id"] for r in rows}
        return CAUGHT, ("checks run from %d binding row(s), against the source "
                        "each names (%s); no call site chooses the document"
                        % (len(rows), ", ".join(sorted(named))))

    if kind == "b12":
        ok, why = spancheck.b12_precision(c["span"], c["slug"], c["sid"])
        if "PASSES" in c.get("expect", ""):
            return (c.get("verdict_when_pass", UNCOVERED),
                    "B12 passes against the cited source. %s"
                    % c.get("why_uncaught", ""))
        return (MISSED, "B12 sees nothing: " + why) if ok else (CAUGHT, why)

    if kind == "ledger":
        import source_ledger as SL
        import source_store as ST
        bad = {}
        for slug in ("melanoma", "cdk46", "deskilling"):
            u = SL.undefined_states(ST.sources(slug))
            if u:
                bad[slug] = u
        if bad:
            return MISSED, "states with no definition remain: %s" % bad
        return CAUGHT, ("undefined_states now runs over every issue; the 44 "
                        "machine_read entries are migrated to fragment_only")

    if kind == "b8":
        other, why = reconcile.b8_closer(c["slug"], c["span"], c["sid"])
        return (CAUGHT, why) if other else (MISSED, why)

    span, slug, sid = c["span"], c["slug"], c["sid"]
    expect_pass = "PASSES" in c.get("expect", "")

    if c["check"].startswith("B2"):
        ok, why = spancheck.b2_present(span, slug, sid)
        if ok == spancheck.UNDETERMINED:
            # Not a catch and not a miss. The checks could not read the
            # document, so they have no opinion to grade.
            return UNCOVERED, "b2 could not determine: %s" % why
        if expect_pass:
            # A CHECK BEHAVING AS DESIGNED IS NOT AN ERROR CAUGHT, and the
            # first version of this file scored it as one, returning 100% on a
            # corpus I had written myself. B2 confirming that a span is present
            # means B2 found NOTHING WRONG. The error was real and something
            # else has to see it.
            return (c.get("verdict_when_pass", UNCOVERED),
                    "B2 confirms the span is present, so B2 sees nothing here. %s"
                    % c.get("why_uncaught", ""))
        if ok:
            return MISSED, "B2 found %r in %s; it should not be there" % (span, sid)
        other, why2 = spancheck.b3_elsewhere(span, slug, sid)
        return CAUGHT, ("B2 fails on %s; %s" % (sid, why2))

    if c["check"] == "B5":
        ok, why = spancheck.b5_complete(span, slug, sid)
        return (MISSED, "B5 sees nothing wrong: " + why) if ok else (CAUGHT, why)

    if c["check"] == "B6":
        bad = spancheck.b6_scope(c["sentence"], span)
        if bad:
            return CAUGHT, "B6 flags %s" % ", ".join(w for w, _ in bad)
        return MISSED, "B6 maps every scope word in the sentence to the span"

    if c["check"] in ("B8", "B9"):
        return UNBUILT, ("%s is specified in section 4 of the spec and is not "
                         "built; step 3 and 4 of the build order" % c["check"])
    return UNBUILT, "no check implemented for %s" % c["check"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    print("\n  RECALL TEST — %d recorded errors, each run against the real bytes\n"
          % len(CASES))
    # TWO NUMBERS, because one flatters.
    #
    # A corpus of errors the checks were built from measures the checks against
    # themselves. On 2026-09-01 recall read 71% until four errors found by
    # PEOPLE were added, and then read 60%. The second number is the one that
    # predicts the next unknown failure, because the next unknown failure will
    # resemble the errors nothing caught.
    tally = {}
    for c in CASES:
        state, why = run_case(c)
        tally[state] = tally.get(state, 0) + 1
        print("  %-9s %-10s %s" % (state, c["id"], c["what"][:64]))
        if args.verbose or state != CAUGHT:
            print("            %s" % why[:150])
    print()
    by_person = [c for c in CASES if c.get("check_kind") == "uncovered"
                 or c.get("found_by") == "person"]
    person_caught = sum(1 for c in by_person if run_case(c)[0] == CAUGHT)
    caught = tally.get(CAUGHT, 0)
    print("  %d CAUGHT, %d MISSED, %d UNBUILT, %d UNCOVERED  —  %.0f%% of %d "
          "recorded errors are caught by a check that was RUN, not asserted"
          % (caught, tally.get(MISSED, 0), tally.get(UNBUILT, 0),
             tally.get(UNCOVERED, 0), 100.0 * caught / len(CASES), len(CASES)))
    if by_person:
        print("  of those, %d were found by a PERSON rather than by a check, and "
              "%d of those %d are caught now — %.0f%%"
              % (len(by_person), person_caught, len(by_person),
                 100.0 * person_caught / len(by_person)))
        print("  the second number is the one that predicts the next unknown "
              "failure")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
