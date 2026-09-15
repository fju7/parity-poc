"""D1 -- the now-only pass in reconcile(): the ten tests.

Run:  cd backend && python3 -m pytest tests/whatholdsup/test_now_only_pass.py -q

Specification: docs/whatholdsup-D1-now-only-pass-specification.md. The rule
under test: a change is explained when a person wrote down that THIS sentence
went in, and named a reason that resolves; what the sentence displaced is
bookkeeping about the diff, not about the decision.

Each test names, in its docstring, the exact weakening it exists to catch.
T1-T8 use small synthetic fixtures and drive reconcile_rows() directly. T9/T10
replay the cdk46 round from FROZEN copies under fixtures/d1_cdk46/ -- the
29 August snapshot, the page at fec7a9a2, changes.json without its change set,
and the decision-label set as it stood on 15 September -- and pin each file's
sha256, so they cannot rot when the live issue directory moves.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import publish as P            # noqa: E402

FIX = pathlib.Path(__file__).resolve().parent / "fixtures" / "d1_cdk46"
LABELS = {"CORR-01", "CORR-02", "OR-A", "AD-HOC"}


def _entry(was, now, because, **extra):
    return dict({"was": was, "now": now, "because": because, "by": "test",
                 "at": "2026-09-15T00:00:00+00:00", "note": ""}, **extra)


def _run(diff, recorded, page_text="", labels=LABELS, sets=()):
    return P.reconcile_rows(diff, recorded, set(labels), P.flatten(page_text), list(sets))


# --- T1: the rescue works ------------------------------------------------------

def test_T1_a_regrouped_sentence_is_attributed_now_only():
    """The defect itself, through the real differ. Old paragraph A B C D; new
    paragraph A X C D B -- X inserted where B was, B moved to the end. difflib
    emits (changed, B, X): a pairing nobody made. The record says X went in
    (CORR-01) and B went in at its new place (CORR-02). Phase 1 matches the
    move two-sided; phase 2 attributes X on its new text alone, because B is
    still on the page."""
    old = "<p>Alpha stays. Bravo moves. Charlie stays. Delta stays.</p>"
    new = "<p>Alpha stays. Xray is new. Charlie stays. Delta stays. Bravo moves.</p>"
    diff = P.changes_since(old, new)
    assert ("changed", "Bravo moves.", "Xray is new.") in diff
    recorded = [_entry("", "Xray is new.", "CORR-01"), _entry("", "Bravo moves.", "CORR-02")]
    ok, bad, consumed = _run(diff, recorded, page_text=new)
    assert bad == []
    by_now = {n: r for _k, _w, n, r in ok}
    assert by_now["Xray is new."]["now_only"] is True
    assert by_now["Xray is new."]["because"] == "CORR-01"
    assert not by_now["Bravo moves."].get("now_only")
    assert len(consumed) == 2


# --- T2: equality, not containment ---------------------------------------------

@pytest.mark.parametrize("undecided", [
    "The paper prints 0.71",     # a strict prefix of the recorded text: containment WOULD match
    "The paper prints 0.71.",    # the spec's literal sentence (its full stop is not even a substring)
])
def test_T2_now_match_is_equality_never_containment(undecided):
    """CATCHES: relaxing condition (b) to the containment test phase 1 uses.
    A recorded decision covers the long sentence; the short one is nobody's
    decision and must stay bad."""
    recorded = [_entry("", "The paper prints 0.71; the more precise 0.712 is the Cox "
                           "hazard ratio in the registry posting.", "CORR-01")]
    ok, bad, _ = _run([("added", "", undecided)], recorded)
    assert ok == []
    assert len(bad) == 1 and bad[0][2] == undecided
    assert P.why_unaccounted(bad[0][3]) == "no recorded decision"


# --- T3: uniqueness -------------------------------------------------------------

def test_T3_two_candidates_with_different_labels_is_ambiguous_not_first_wins():
    """CATCHES: dropping (b)'s uniqueness and taking candidates[0]. The live
    shape: cdk46's changes.json has 14 rows sharing a non-empty `now` with
    another row (D2's duplicate pairs among them), written seconds apart. Here
    the two carry DIFFERENT labels, so the record cannot say which decision
    the sentence came from."""
    same = "The figure is now attributed to the registry posting."
    recorded = [_entry("First old form.", same, "CORR-01", at="2026-09-13T14:28:12+00:00"),
                _entry("Second old form.", same, "CORR-02", at="2026-09-13T14:28:21+00:00")]
    # the row's `was` matches neither entry, so it reaches phase 2 unmatched
    ok, bad, _ = _run([("changed", "A third sentence, still on the page.", same)], recorded,
                      page_text="A third sentence, still on the page. " + same)
    assert ok == []
    assert len(bad) == 1
    why = P.why_unaccounted(bad[0][3])
    assert "cannot say which decision" in why and "CORR-01" in why and "CORR-02" in why
    assert "cannot say which decision" in P.unaccounted_summary(bad)


# --- T4: the label check survives -----------------------------------------------

def test_T4_sole_candidate_with_unresolved_label_is_reported_as_such():
    """CATCHES: dropping (c) on the grounds that a now match is evidence
    enough. Bad, and reported as an unresolved label -- never as "no recorded
    decision", which is a different and false statement."""
    recorded = [_entry("Old wording.", "New wording.", "NOPE-9")]
    # the row's `was` shares nothing with the entry's, so phase 1's containment
    # loop does not take it and the sole candidate is found in phase 2
    ok, bad, _ = _run([("changed", "A separate sentence.", "New wording.")],
                      recorded, page_text="A separate sentence. New wording.")
    assert ok == []
    assert len(bad) == 1
    r = bad[0][3]
    assert r["unresolved"] is True and r["now_only"] is True
    assert P.why_unaccounted(r) == "decision cited a label that does not resolve: NOPE-9"
    assert "no recorded decision" not in P.unaccounted_summary(bad)
    assert "NOPE-9" in P.unaccounted_summary(bad)


# --- T5: deletions are never rescued ---------------------------------------------

def test_T5_a_removed_row_is_never_rescued_on_an_empty_now():
    """CATCHES: dropping (a). A `removed` row has an empty `now`; a recorded
    entry with an empty `now` exists (a recorded deletion of something else).
    The removed sentence still appears elsewhere on the page, so (d) alone
    would let it through -- only (a) keeps a deletion out of this pass."""
    recorded = [_entry("An unrelated sentence that was recorded as removed.", "", "CORR-01")]
    page = "<p>Gone from here. Still here. Gone from here.</p>"
    ok, bad, _ = _run([("removed", "Gone from here.", "")], recorded, page_text=page)
    assert ok == []
    assert len(bad) == 1 and bad[0][0] == "removed"
    assert P.why_unaccounted(bad[0][3]) == "no recorded decision"


# --- T6: a hidden deletion still blocks --------------------------------------------

def test_T6_clean_now_match_with_a_vanished_was_stays_blocking():
    """CATCHES: dropping (d) as over-engineering. The `now` matches a recorded
    entry cleanly and its label resolves; the `was` sentence appears nowhere
    on the current page and is no recorded entry's `was`. It died with nothing
    recording it, and the row must say so."""
    recorded = [_entry("Something else entirely.", "The replacement sentence.", "CORR-01")]
    page = "<p>The replacement sentence. Other prose.</p>"
    ok, bad, _ = _run([("changed", "A sentence that vanished.", "The replacement sentence.")],
                      recorded, page_text=page)
    assert ok == []
    assert len(bad) == 1
    r = bad[0][3]
    assert r["unaccounted_deletion"] is True and r["now_only"] is True
    assert (P.why_unaccounted(r)
            == "the sentence it replaced is in no record and is no longer on the page")


# --- T7: phase ordering --------------------------------------------------------------

def test_T7_two_sided_match_wins_the_entry_even_when_it_comes_later():
    """CATCHES: interleaving the passes. Row A (earlier) can reach entry E only
    on its new text; row B (later) matches E on both sides. Phase 1 must finish
    before phase 2 starts, so B gets E two-sided and A does not get E at all."""
    E = _entry("Papa was here.", "Echo is the new text.", "CORR-01")
    diff = [("changed", "Quebec was here.", "Echo is the new text."),   # A
            ("changed", "Papa was here.", "Echo is the new text.")]     # B
    page = "<p>Quebec was here. Echo is the new text.</p>"
    ok, bad, _ = _run(diff, [E], page_text=page)
    assert [(w, r.get("now_only", False)) for _k, w, _n, r in ok] == [("Papa was here.", False)]
    assert [w for _k, w, _n, _r in bad] == ["Quebec was here."]
    assert P.why_unaccounted(bad[0][3]) == "no recorded decision"


# --- T8: the board's wording ------------------------------------------------------------

def test_T8_now_only_count_is_separate_and_never_per_change():
    """CATCHES: merging the counters. Two two-sided, one now-only, one set."""
    ok = [("changed", "a", "b", {"because": "CORR-01"}),
          ("changed", "c", "d", {"because": "CORR-02"}),
          ("changed", "e", "f", {"because": "OR-A", "now_only": True}),
          ("added", "", "g", {"because": "ROUND-1", "set_level": True, "decided_by": []})]
    s = P.attribution_sentence(ok)
    assert s.startswith("4 change(s) since, 2 traced to a per-change decision (CORR-01, CORR-02)")
    assert ("1 to a recorded decision matched on the new text alone (the diff paired them "
            "against a different old sentence; OR-A)") in s
    assert "1 to a recorded change set (ROUND-1)" in s
    assert "3 traced to a per-change decision" not in s
    assert "OR-A" not in s.split("per-change decision (")[1].split(")")[0]
    # and with nothing but two-sided matches the old wording stands
    assert P.attribution_sentence(ok[:2]) == (
        "2 change(s) since, each traced to a per-change decision (CORR-01, CORR-02)")


# --- T9/T10: the replayed round, frozen ----------------------------------------------------

_FROZEN = {
    "snapshot-2026-08-29.html": "3ca22e72fe461feaba6c0c94c667cd3ee0e2264b5064de1d6e0f6d41cc2ce979",
    "page-fec7a9a2.html": "fec7a9a2e0eebd41bebaa9b6eb98cede17b46c81b2fbe4cba3a1d1b7c551b105",
    "changes-no-sets.json": "12891aca58b53c1726c8b520695a41ce86d27445759ef61d91a0cac94f36b2c5",
    "labels.json": "35e40dfce99ffe6ca5e011389bfa4943dc622346335811a8dc19aea90547f25d",
}


@pytest.fixture(scope="module")
def cdk46_round():
    for name, digest in _FROZEN.items():
        assert hashlib.sha256((FIX / name).read_bytes()).hexdigest() == digest, \
            "frozen fixture %s has changed; T9/T10 are defined on the frozen bytes" % name
    changes = json.loads((FIX / "changes-no-sets.json").read_text(encoding="utf-8"))
    assert "change_sets" not in changes and len(changes["changes"]) == 492
    labels = set(json.loads((FIX / "labels.json").read_text(encoding="utf-8"))["labels"])
    return {"snap": (FIX / "snapshot-2026-08-29.html").read_text(encoding="utf-8"),
            "page": (FIX / "page-fec7a9a2.html").read_text(encoding="utf-8"),
            "recorded": changes["changes"], "labels": labels}


def _replay(rd, page):
    diff = P.changes_since(rd["snap"], page)
    ok, bad, _ = P.reconcile_rows(diff, rd["recorded"], rd["labels"], P.flatten(page), [])
    two = sum(1 for _k, _w, _n, r in ok if not r.get("now_only") and not r.get("set_level"))
    now_only = sum(1 for _k, _w, _n, r in ok if r.get("now_only"))
    sets = sum(1 for _k, _w, _n, r in ok if r.get("set_level"))
    return diff, ok, bad, two, now_only, sets


def test_T9_the_replayed_round_needs_no_change_set(cdk46_round):
    """The proof on the data that motivated the pass: cdk46 on 14 September,
    without the change set that was written to work around the defect."""
    diff, ok, bad, two, now_only, sets = _replay(cdk46_round, cdk46_round["page"])
    assert len(diff) == 350
    assert (two, now_only, sets, len(bad)) == (322, 28, 0, 0)
    assert all(r["because"] in cdk46_round["labels"] for _k, _w, _n, r in ok)


def test_T10_one_undecided_sentence_is_the_only_bad_row(cdk46_round):
    """The counterfactual proper, and the whole-system version of T2-T6: any
    weakening that rescues an undecided sentence turns this red. One sentence
    appearing in no recorded entry is inserted; exactly it is bad, and the
    other 350 rows are attributed exactly as in T9."""
    undecided = "This sentence was decided by nobody and recorded nowhere."
    page = cdk46_round["page"].replace("</body>", "<p>%s</p>\n</body>" % undecided, 1)
    assert page != cdk46_round["page"]
    diff, ok, bad, two, now_only, sets = _replay(cdk46_round, page)
    assert len(diff) == 351
    assert (two, now_only, sets) == (322, 28, 0)
    assert len(bad) == 1
    assert bad[0][:3] == ("added", "", undecided)
    assert P.why_unaccounted(bad[0][3]) == "no recorded decision"
