"""Hyphens are one character; minus signs and dashes are not (advisor's ruling B on P117, 2026-11-25).

Found on orchestrator trial 1 attempt 25 (WHU-OT1-02zc): Q-01, "a twin-track approach is needed, ...", quoted S001 with
an ASCII hyphen; S001's held text prints U+2010 HYPHEN ("twin‐track"). quotations.match_held found it in no held
text and the page stopped ("quotation sources were opened"). Ruled: match_held treats only the ASCII hyphen, U+2010
and U+2011 as equivalent; U+2212 MINUS SIGN and U+2013 EN DASH stay distinct ("−3" never matches "3" or "-3").

Before this, match_held read held text through spancheck._norm, which folded U+2212, U+2013 and U+2014 to "-", so a
page's "-3" matched a held "−3" (and a page's "−3" missed the same held text). Held text is quoted here only
as constructed strings; S001's real text is read from the local trial library (gitignored), never copied in.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
CASE = ROOT / "issues" / "WHU-OT1-02zc-whu-lean-orch-t1-q1-02zc"
SLUG = "whu-lean-orch-t1-q1-02zc"

import quotations as Q     # noqa: E402
import spancheck as SC     # noqa: E402

HYPHEN, NB_HYPHEN, MINUS, EN, EM = "‐", "‑", "−", "–", "—"


# --------------------------------------------------------------- the normalisers, value by value

@pytest.mark.parametrize("c", ["-", HYPHEN, NB_HYPHEN])
def test_every_hyphen_becomes_the_ascii_hyphen_in_every_form(c):
    for kw in ({}, {"fold_dashes": False}, {"fold_accents": False}, {"fold_dashes": False, "fold_accents": False}):
        assert Q.norm("twin%strack" % c, **kw) == "twin-track"
    assert Q._hyphens("twin%strack" % c) == "twin-track"
    assert len(Q._hyphens("twin%strack" % c)) == len("twin%strack" % c)       # one character for one


@pytest.mark.parametrize("c", [MINUS, EN, EM])
def test_match_helds_forms_keep_minus_and_dashes(c):
    assert Q.norm("a %s3 change" % c, fold_dashes=False) == "a %s3 change" % c
    assert SC._norm("a %s3 change" % c, fold_dashes=False) == "a %s3 change" % c
    assert Q._hyphens(c) == c


def test_the_default_forms_are_unchanged_for_other_callers():
    assert Q.norm("a %s3 and %s and %s" % (MINUS, EN, EM)) == "a %s3 and - and -" % MINUS   # as _SMART always did
    assert SC._norm("a %s3 and %s and %s" % (MINUS, EN, EM)) == "a -3 and - and -"
    assert SC._norm("twin%strack" % HYPHEN) == "twin%strack" % HYPHEN                         # spancheck: untouched


def test_minus_three_never_matches_three_or_ascii_minus_three_in_any_form_match_held_produces():
    page = "the pooled change was %s3 points on the scale in the trial" % MINUS
    for held in ("the pooled change was 3 points on the scale in the trial",
                 "the pooled change was -3 points on the scale in the trial",
                 "the pooled change was %s3 points on the scale in the trial" % EN,
                 "the pooled change was %s3 points on the scale in the trial" % HYPHEN):
        for fa in (True, False):
            qn = Q.norm(page, fold_dashes=False, fold_accents=fa)
            body = Q.norm(SC._norm(held, fold_dashes=False), fold_dashes=False, fold_accents=fa)
            assert not Q.quoted_in(qn, body), held
            back = Q.norm(held, fold_dashes=False, fold_accents=fa)
            assert not Q.quoted_in(back, Q.norm(SC._norm(page, fold_dashes=False), fold_dashes=False,
                                                fold_accents=fa)), held
    same = Q.norm(SC._norm(page, fold_dashes=False), fold_dashes=False)
    assert Q.quoted_in(Q.norm(page, fold_dashes=False), same)                # and a minus still matches a minus


# --------------------------------------------------------------- through match_held

def _run(tmp_path, monkeypatch, page_quote, held_text):
    import source_store as store
    case = tmp_path / "WHU-X-demo"
    (case / "draft").mkdir(parents=True)
    (case / "issue.json").write_text(json.dumps({"question": "A question?"}))
    page = case / "draft" / "demo.html"
    page.write_text("<p>The review says that “%s” [1].</p>" % page_quote, encoding="utf-8")
    monkeypatch.setattr(Q, "case_dir", lambda slug: case)
    monkeypatch.setattr(store, "held", lambda slug: {"S001": {"sha256": "0" * 64}})
    monkeypatch.setattr(SC, "_texts", lambda slug, sid: [("s001.txt", held_text)])
    got = Q.match_held("demo", page)
    rows = json.loads((case / "quotations.json").read_text())["quotations"]
    return got, rows


def test_a_quotation_with_an_ascii_hyphen_matches_held_text_with_u2010(tmp_path, monkeypatch):
    held = ("Background. A twin%strack approach is needed, which both addresses the specific needs of children "
            "with disabilities. More text follows." % HYPHEN)
    got, rows = _run(tmp_path, monkeypatch, "A twin-track approach is needed, which both addresses the specific needs",
                     held)
    assert got["unmatched"] == [] and rows[0]["source_id"] == "S001"
    assert HYPHEN in rows[0]["verbatim"]                                     # the source's own character, kept
    assert rows[0]["verbatim"] == held[rows[0]["offsets"][0]:rows[0]["offsets"][1]]


@pytest.mark.parametrize("page_c,held_c", [("-", MINUS), (MINUS, "-"), ("-", EN), (EN, "-"), (MINUS, "")])
def test_a_minus_or_dash_never_matches_another_dash_through_match_held(tmp_path, monkeypatch, page_c, held_c):
    tail = "3 points on the depression scale at twelve weeks"
    got, rows = _run(tmp_path, monkeypatch, "the change was %s%s" % (page_c, tail),
                     "Results. The change was %s%s, as reported." % (held_c, tail))
    assert got["unmatched"] and rows[0].get("unmatched") is True


def test_a_minus_matches_a_minus_through_match_held(tmp_path, monkeypatch):
    tail = "3 points on the depression scale at twelve weeks"
    got, rows = _run(tmp_path, monkeypatch, "the change was %s%s" % (MINUS, tail),
                     "Results. The change was %s%s, as reported." % (MINUS, tail))
    assert got["unmatched"] == [] and MINUS in rows[0]["verbatim"]


# --------------------------------------------------------------- Q-01 against S001's held text (local only)

def test_02zc_q01_matches_s001s_held_text(tmp_path, monkeypatch):
    import source_store as store
    from orch import run_env as RE
    if not store.LIB_TRIAL.exists():
        pytest.skip("the trial library is local only (gitignored)")
    q01 = next(r for r in json.loads((CASE / "quotations.json").read_text())["quotations"] if r["id"] == "Q-01")
    assert q01.get("unmatched") is True and "twin-track" in q01["quote"]   # as the run recorded it
    snap = RE.snapshot()
    try:
        RE.use(CASE)
        texts = [t for _f, t in SC._texts(SLUG, "S001")]
        if not texts:
            pytest.skip("S001's held text is not in this library")
        assert any("twin%strack" % HYPHEN in t for t in texts)
        monkeypatch.setattr(Q, "path", lambda slug: tmp_path / "quotations.json")   # never the committed record
        Q.match_held(SLUG, CASE / "draft" / ("%s.html" % SLUG))
        rows = {r["id"]: r for r in json.loads((tmp_path / "quotations.json").read_text())["quotations"]}
        row = next(r for r in rows.values() if r["quote"] == q01["quote"])
        assert row["source_id"] == "S001" and not row.get("unmatched")
        assert "twin%strack" % HYPHEN in row["verbatim"]
    finally:
        RE.restore(snap)
